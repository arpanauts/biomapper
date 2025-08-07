"""Vector database-enhanced matching action for metabolites."""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel, Field
from fastembed import TextEmbedding
from qdrant_client import QdrantClient

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class VectorEnhancedMatchParams(BaseModel):
    """Parameters for vector-enhanced matching."""

    unmatched_dataset_key: str = Field(
        description="Key for unmatched items from API enrichment"
    )
    target_dataset_key: Optional[str] = Field(
        default=None, description="Optional target dataset for additional matching"
    )
    qdrant_url: str = Field(default="localhost:6333", description="Qdrant server URL")
    qdrant_collection: str = Field(
        default="hmdb_metabolites", description="Qdrant collection name"
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5", description="FastEmbed model name"
    )
    similarity_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Minimum similarity score for matches"
    )
    top_k: int = Field(
        default=5, ge=1, description="Number of candidates to retrieve per query"
    )
    output_key: str = Field(description="Key to store vector matches")
    track_metrics: bool = Field(default=True, description="Track detailed metrics")
    batch_size: int = Field(
        default=50, description="Batch size for embedding generation"
    )


class VectorMatchMetrics(BaseModel):
    """Metrics for vector-enhanced matching."""

    stage: str = "vector_enhanced"
    total_unmatched_input: int
    total_matched: int
    match_rate: float
    avg_similarity_score: float
    avg_candidates_per_query: float
    execution_time: float
    embedding_time: float
    search_time: float
    similarity_distribution: Dict[str, int]


class VectorMatchResult(BaseModel):
    """Result from vector matching."""

    metabolite: Dict[str, Any]
    hmdb_match: Dict[str, Any]
    similarity_score: float
    rank: int
    matched_on: str  # Which text was used for matching


@register_action("VECTOR_ENHANCED_MATCH")
class VectorEnhancedMatchAction(
    TypedStrategyAction[VectorEnhancedMatchParams, StandardActionResult]
):
    """Match metabolites using vector similarity search."""

    def get_params_model(self) -> type[VectorEnhancedMatchParams]:
        """Return the params model class."""
        return VectorEnhancedMatchParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult

    def __init__(self) -> None:
        """Initialize action."""
        super().__init__()
        self.embedding_model: Optional[TextEmbedding] = None
        self.qdrant_client: Optional[QdrantClient] = None

    def _initialize_clients(self, params: VectorEnhancedMatchParams) -> None:
        """Initialize FastEmbed and Qdrant clients."""
        if not self.embedding_model:
            logger.info(f"Initializing FastEmbed with model: {params.embedding_model}")
            self.embedding_model = TextEmbedding(model_name=params.embedding_model)

        if not self.qdrant_client:
            logger.info(f"Connecting to Qdrant at: {params.qdrant_url}")
            self.qdrant_client = QdrantClient(params.qdrant_url)

            # Verify collection exists
            try:
                collection_info = self.qdrant_client.get_collection(
                    params.qdrant_collection
                )
                logger.info(
                    f"Connected to collection '{params.qdrant_collection}' "
                    f"with {collection_info.points_count} points"
                )
            except Exception as e:
                raise ValueError(
                    f"Qdrant collection '{params.qdrant_collection}' not found. "
                    f"Please run the HMDB indexing script first. Error: {e}"
                )

    def _prepare_search_texts(
        self, metabolite: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """Prepare multiple search texts for a metabolite.

        Returns list of (text, source) tuples.
        """
        search_texts = []

        # Original biochemical name
        if bio_name := metabolite.get("BIOCHEMICAL_NAME"):
            search_texts.append((bio_name, "original_name"))

        # CTS enriched names
        for cts_name in metabolite.get("cts_enriched_names", []):
            search_texts.append((cts_name, "cts_enriched"))

        # Try creating a combined description
        if bio_name:
            # Add context if available
            if pathway := metabolite.get("SUB_PATHWAY"):
                contextual = f"{bio_name} {pathway}"
                search_texts.append((contextual, "name_with_pathway"))

            if super_pathway := metabolite.get("SUPER_PATHWAY"):
                contextual = f"{bio_name} {super_pathway}"
                search_texts.append((contextual, "name_with_super_pathway"))

        # Deduplicate while preserving order and source
        seen = set()
        unique_texts = []
        for text, source in search_texts:
            if text and text.lower() not in seen:
                seen.add(text.lower())
                unique_texts.append((text, source))

        return unique_texts

    def _calculate_similarity_bucket(self, score: float) -> str:
        """Categorize similarity score into buckets."""
        if score >= 0.90:
            return "very_high"
        elif score >= 0.85:
            return "high"
        elif score >= 0.80:
            return "medium"
        elif score >= 0.75:
            return "low"
        else:
            return "very_low"

    async def _batch_vector_search(
        self, metabolites: List[Dict[str, Any]], params: VectorEnhancedMatchParams
    ) -> Tuple[List[VectorMatchResult], float, float]:
        """Perform batch vector search for metabolites.

        Returns tuple of (match results, embedding time, search time).
        """
        all_results = []
        embedding_time = 0.0
        search_time = 0.0

        # Process in batches
        for i in range(0, len(metabolites), params.batch_size):
            batch = metabolites[i : i + params.batch_size]

            # Prepare all search texts for this batch
            batch_search_data = []
            for metabolite in batch:
                search_texts = self._prepare_search_texts(metabolite)
                for text, source in search_texts:
                    batch_search_data.append(
                        {"metabolite": metabolite, "text": text, "source": source}
                    )

            if not batch_search_data:
                continue

            # Generate embeddings
            embed_start = time.time()
            texts = [item["text"] for item in batch_search_data]
            assert self.embedding_model is not None
            embeddings = list(self.embedding_model.embed(texts))
            embedding_time += time.time() - embed_start

            # Search for each embedding
            search_start = time.time()
            for item, embedding in zip(batch_search_data, embeddings):
                try:
                    # Search in Qdrant
                    assert self.qdrant_client is not None
                    search_result = self.qdrant_client.search(
                        collection_name=params.qdrant_collection,
                        query_vector=embedding.tolist(),
                        limit=params.top_k,
                        score_threshold=params.similarity_threshold,
                    )

                    # Process results
                    for rank, point in enumerate(search_result):
                        if point.score >= params.similarity_threshold:
                            match_result = VectorMatchResult(
                                metabolite=item["metabolite"],  # type: ignore
                                hmdb_match=point.payload or {},
                                similarity_score=point.score,
                                rank=rank + 1,
                                matched_on=item["source"],  # type: ignore
                            )
                            all_results.append(match_result)
                            break  # Take first match above threshold

                except Exception as e:
                    logger.warning(f"Vector search error for '{item['text']}': {e}")

            search_time += time.time() - search_start

        return all_results, embedding_time, search_time

    def _deduplicate_matches(
        self, matches: List[VectorMatchResult]
    ) -> List[VectorMatchResult]:
        """Deduplicate matches, keeping best score per metabolite."""
        best_matches = {}

        for match in matches:
            metabolite_id = match.metabolite.get("BIOCHEMICAL_NAME", "")

            if metabolite_id not in best_matches:
                best_matches[metabolite_id] = match
            elif match.similarity_score > best_matches[metabolite_id].similarity_score:
                best_matches[metabolite_id] = match

        return list(best_matches.values())

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: VectorEnhancedMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute vector-enhanced matching."""

        start_time = time.time()

        # Initialize clients
        self._initialize_clients(params)

        # Get datasets - handle both dict and typed context
        if hasattr(context, "get_action_data"):
            datasets = context.get_action_data("datasets", {})
        else:
            datasets = context.get("datasets", {})

        unmatched_data = datasets.get(params.unmatched_dataset_key, [])

        if not unmatched_data:
            logger.warning(
                f"No unmatched data found in '{params.unmatched_dataset_key}'"
            )
            return StandardActionResult(
                input_identifiers=[],
                output_identifiers=[],
                output_ontology_type="",
                provenance=[],
                details={"matched": 0},
            )

        logger.info(
            f"Starting vector search for {len(unmatched_data)} unmatched metabolites"
        )

        # Perform vector search
        matches, embedding_time, search_time = await self._batch_vector_search(
            unmatched_data, params
        )

        # Deduplicate to get best match per metabolite
        unique_matches = self._deduplicate_matches(matches)

        # Convert to standard match format
        final_matches = []
        similarity_dist: Dict[str, int] = {}
        total_similarity = 0.0
        still_unmatched = []

        # Create set of matched metabolites
        matched_metabolites = {
            m.metabolite.get("BIOCHEMICAL_NAME", "") for m in unique_matches
        }

        for match in unique_matches:
            match_record = {
                "source": match.metabolite,
                "target": {
                    "hmdb_id": match.hmdb_match.get("hmdb_id", ""),
                    "name": match.hmdb_match.get("name", ""),
                    "synonyms": match.hmdb_match.get("synonyms", []),
                    "inchikey": match.hmdb_match.get("inchikey", ""),
                },
                "score": match.similarity_score,
                "method": f"vector_search_{match.matched_on}",
                "stage": "vector_enhanced",
                "rank": match.rank,
                "matched_text": match.metabolite.get(
                    "BIOCHEMICAL_NAME"
                    if match.matched_on == "original_name"
                    else "cts_enriched_names",
                    [""],
                )[0]
                if match.matched_on == "cts_enriched"
                else match.metabolite.get("BIOCHEMICAL_NAME", ""),
            }
            final_matches.append(match_record)

            # Track similarity distribution
            bucket = self._calculate_similarity_bucket(match.similarity_score)
            similarity_dist[bucket] = similarity_dist.get(bucket, 0) + 1
            total_similarity += match.similarity_score

        # Identify still unmatched
        for metabolite in unmatched_data:
            if metabolite.get("BIOCHEMICAL_NAME", "") not in matched_metabolites:
                still_unmatched.append(metabolite)

        # Calculate metrics
        execution_time = time.time() - start_time
        avg_similarity = (
            total_similarity / len(unique_matches) if unique_matches else 0.0
        )

        metrics = VectorMatchMetrics(
            stage="vector_enhanced",
            total_unmatched_input=len(unmatched_data),
            total_matched=len(unique_matches),
            match_rate=len(unique_matches) / len(unmatched_data)
            if unmatched_data
            else 0.0,
            avg_similarity_score=avg_similarity,
            avg_candidates_per_query=params.top_k,
            execution_time=execution_time,
            embedding_time=embedding_time,
            search_time=search_time,
            similarity_distribution=similarity_dist,
        )

        # Store results - handle both dict and typed context
        if hasattr(context, "set_action_data"):
            # Typed context
            datasets[params.output_key] = final_matches
            unmatched_key = (
                f"unmatched.vector.{params.unmatched_dataset_key.split('.')[-1]}"
            )
            datasets[unmatched_key] = still_unmatched
            context.set_action_data("datasets", datasets)

            if params.track_metrics:
                context.set_action_data("metrics", {"vector_enhanced": metrics.dict()})
        else:
            # Dict context
            if "datasets" not in context:
                context["datasets"] = {}
            context["datasets"][params.output_key] = final_matches

            unmatched_key = (
                f"unmatched.vector.{params.unmatched_dataset_key.split('.')[-1]}"
            )
            context["datasets"][unmatched_key] = still_unmatched

            if params.track_metrics:
                if "metrics" not in context:
                    context["metrics"] = {}
                context["metrics"]["vector_enhanced"] = metrics.dict()

        logger.info(
            f"Vector matching complete: {len(unique_matches)} matched "
            f"({metrics.match_rate:.1%}), avg similarity: {avg_similarity:.3f}, "
            f"time: {execution_time:.2f}s"
        )

        return StandardActionResult(
            input_identifiers=[],
            output_identifiers=[],
            output_ontology_type="",
            provenance=[],
            details={
                "metrics": metrics.dict(),
                "matched_count": len(unique_matches),
                "still_unmatched": len(still_unmatched),
                "embedding_time": embedding_time,
                "search_time": search_time,
            },
        )
