"""Semantic metabolite matching using embeddings and LLM validation."""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field
from sklearn.metrics.pairwise import cosine_similarity

from actions.registry import register_action
from actions.typed_base import (
    TypedStrategyAction,
)

logger = logging.getLogger(__name__)


class SemanticMetaboliteMatchParams(BaseModel):
    """Parameters for semantic metabolite matching."""

    unmatched_dataset: str = Field(..., description="Key for unmatched metabolites")
    reference_map: str = Field(
        ..., description="Key for reference metabolites to match against"
    )
    context_fields: Dict[str, List[str]] = Field(
        ..., description="Fields to use for context per dataset"
    )
    embedding_model: str = Field(
        "text-embedding-ada-002", description="OpenAI embedding model"
    )
    llm_model: str = Field("gpt-4", description="LLM model for validation")
    confidence_threshold: float = Field(
        0.75, ge=0.0, le=1.0, description="Minimum confidence for matches"
    )
    include_reasoning: bool = Field(
        True, description="Include LLM reasoning in results"
    )
    max_llm_calls: int = Field(
        100, description="Maximum LLM API calls to prevent runaway costs"
    )
    embedding_similarity_threshold: float = Field(
        0.85, description="Minimum embedding similarity for LLM validation"
    )
    batch_size: int = Field(10, description="Batch size for embedding generation")
    output_key: str = Field(..., description="Key for matched results")
    unmatched_key: Optional[str] = Field(None, description="Key for final unmatched")


class EmbeddingCache:
    """Simple cache for embeddings to avoid duplicate API calls."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the embedding cache."""
        self.memory_cache: Dict[str, List[float]] = {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        cache_key = hashlib.md5(text.encode()).hexdigest()

        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # Check disk cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        embedding = json.load(f)
                        self.memory_cache[cache_key] = embedding
                        return embedding
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding: {e}")

        return None

    def set(self, text: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        cache_key = hashlib.md5(text.encode()).hexdigest()

        # Store in memory
        self.memory_cache[cache_key] = embedding

        # Store on disk
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            try:
                with open(cache_file, "w") as f:
                    json.dump(embedding, f)
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {e}")


class SemanticMatchResult(BaseModel):
    """Result model for semantic metabolite matching."""

    success: bool
    message: str
    data: Dict[str, Any] = {}
    error: Optional[str] = None


@register_action("SEMANTIC_METABOLITE_MATCH")
class SemanticMetaboliteMatchAction(
    TypedStrategyAction[SemanticMetaboliteMatchParams, SemanticMatchResult]
):
    """LLM-based semantic matching for metabolites using context and embeddings."""

    def __init__(self, db_session: Any = None):
        """Initialize the action."""
        super().__init__(db_session)
        self.embedding_cache = None
        self.openai_client = None

    def get_params_model(self) -> type[SemanticMetaboliteMatchParams]:
        """Get the Pydantic model for action parameters."""
        return SemanticMetaboliteMatchParams

    def get_result_model(self) -> type[SemanticMatchResult]:
        """Get the Pydantic model for action results."""
        return SemanticMatchResult

    def _initialize_clients(self) -> None:
        """Initialize OpenAI client and embedding cache."""
        if self.openai_client is None:
            try:
                import openai

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")

                self.openai_client = openai.OpenAI(api_key=api_key)

                # Initialize cache
                cache_dir = os.getenv("SEMANTIC_MATCH_CACHE_DIR")
                self.embedding_cache = EmbeddingCache(cache_dir)

            except ImportError:
                raise ImportError(
                    "OpenAI library not found. Please install with: pip install openai"
                )

    def _create_context_string(
        self, metabolite: Dict[str, Any], fields: List[str], dataset_name: str
    ) -> str:
        """Create rich context string for embedding."""
        context_parts = []

        # Primary name
        name_field = fields[0] if fields else None
        name = metabolite.get(name_field, "unknown") if name_field else "unknown"
        context_parts.append(f"Metabolite: {name}")

        # Add pathway information
        pathway_fields = ["SUPER_PATHWAY", "SUB_PATHWAY", "pathway", "category"]
        for field in pathway_fields:
            if field in metabolite and metabolite[field]:
                context_parts.append(f"{field}: {metabolite[field]}")

        # Add description fields
        for field in fields:
            if "description" in field.lower() and metabolite.get(field):
                context_parts.append(f"Description: {metabolite[field]}")

        # Add any additional context fields
        for field in fields[1:]:  # Skip primary name field
            if field not in metabolite:
                continue
            value = metabolite[field]
            if value and field not in pathway_fields:
                context_parts.append(f"{field}: {value}")

        return " | ".join(context_parts)

    async def _generate_embeddings(
        self, texts: List[str], model: str
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        embeddings = []

        for text in texts:
            # Check cache first
            cached = self.embedding_cache.get(text)
            if cached is not None:
                embeddings.append(cached)
                continue

            try:
                # Generate embedding
                response = self.openai_client.embeddings.create(input=text, model=model)
                embedding = response.data[0].embedding

                # Cache the result
                self.embedding_cache.set(text, embedding)
                embeddings.append(embedding)

            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                # Return zero vector on failure
                embeddings.append([0.0] * 1536)  # Default ada-002 dimension

        return embeddings

    async def _generate_embeddings_batch(
        self,
        metabolites: List[Dict[str, Any]],
        fields: List[str],
        dataset_name: str,
        model: str,
        batch_size: int,
    ) -> Dict[int, List[float]]:
        """Generate embeddings for a list of metabolites in batches."""
        # Create context strings
        contexts = [
            self._create_context_string(m, fields, dataset_name) for m in metabolites
        ]

        # Process in batches
        all_embeddings = []
        for i in range(0, len(contexts), batch_size):
            batch = contexts[i : i + batch_size]
            batch_embeddings = await self._generate_embeddings(batch, model)
            all_embeddings.extend(batch_embeddings)

        # Return as dict with indices
        return {i: emb for i, emb in enumerate(all_embeddings)}

    def _find_candidates(
        self,
        source_embedding: List[float],
        reference_embeddings: Dict[int, List[float]],
        threshold: float,
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """Find top-k most similar reference metabolites."""
        # Convert to numpy arrays
        source_vec = np.array(source_embedding).reshape(1, -1)

        similarities = []
        for ref_idx, ref_embedding in reference_embeddings.items():
            ref_vec = np.array(ref_embedding).reshape(1, -1)

            # Calculate cosine similarity
            similarity = cosine_similarity(source_vec, ref_vec)[0, 0]

            if similarity >= threshold:
                similarities.append((ref_idx, float(similarity)))

        # Return top-k sorted by similarity
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

    def _extract_additional_info(self, metabolite: Dict[str, Any]) -> str:
        """Extract additional context information from metabolite."""
        info_parts = []

        # Look for common metadata fields
        metadata_fields = [
            "HMDB_ID",
            "hmdb_id",
            "KEGG_ID",
            "kegg_id",
            "CAS",
            "cas_number",
            "formula",
            "molecular_formula",
            "pubchem_id",
            "PLATFORM",
            "platform",
        ]

        for field in metadata_fields:
            if field in metabolite and metabolite[field]:
                info_parts.append(f"{field}: {metabolite[field]}")

        return ", ".join(info_parts) if info_parts else "No additional metadata"

    async def _validate_match_with_llm(
        self,
        source_metabolite: Dict[str, Any],
        candidate_metabolite: Dict[str, Any],
        embedding_similarity: float,
        model: str,
    ) -> Tuple[bool, float, str]:
        """Use LLM to validate if metabolites are truly the same."""
        # Build source info
        source_name = source_metabolite.get("BIOCHEMICAL_NAME", "Unknown")
        source_pathway = source_metabolite.get("SUPER_PATHWAY", "Unknown")
        source_subpathway = source_metabolite.get("SUB_PATHWAY", "Unknown")
        source_info = self._extract_additional_info(source_metabolite)

        # Build candidate info
        candidate_name = candidate_metabolite.get("unified_name", "Unknown")
        candidate_desc = candidate_metabolite.get("description", "No description")
        candidate_category = candidate_metabolite.get("category", "Unknown")
        candidate_info = self._extract_additional_info(candidate_metabolite)

        prompt = f"""I need to determine if these two metabolites are the same compound:

Metabolite A:
- Name: {source_name}
- Pathway: {source_pathway}
- Sub-pathway: {source_subpathway}
- Additional info: {source_info}

Metabolite B:
- Name: {candidate_name}
- Description: {candidate_desc}
- Category: {candidate_category}
- Platform: Nightingale NMR
- Additional info: {candidate_info}

Embedding similarity: {embedding_similarity:.3f}

Are these the same metabolite? Respond with:
1. YES/NO/UNCERTAIN
2. Confidence (0-1)
3. Brief reasoning (1-2 sentences)

Format: YES|0.95|These are both referring to total cholesterol measurements."""

        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a biochemistry expert validating metabolite matches.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=150,
            )

            # Parse response
            content = response.choices[0].message.content.strip()
            parts = content.split("|", 2)

            if len(parts) >= 3:
                decision = parts[0].strip().upper()
                confidence = float(parts[1].strip())
                reasoning = parts[2].strip()

                is_match = decision == "YES"
                return is_match, confidence, reasoning
            else:
                logger.warning(f"Unexpected LLM response format: {content}")
                return False, 0.0, "Failed to parse LLM response"

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return False, 0.0, f"LLM error: {str(e)}"

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: SemanticMetaboliteMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> SemanticMatchResult:
        """Execute semantic metabolite matching with embeddings and LLM validation."""
        # Initialize clients
        self._initialize_clients()

        # Load datasets
        datasets = context.get("datasets", {})
        unmatched = datasets.get(params.unmatched_dataset, [])
        reference = datasets.get(params.reference_map, [])

        if not unmatched:
            return SemanticMatchResult(
                success=True,
                message=f"No unmatched metabolites found in {params.unmatched_dataset}",
                data={"matched_count": 0, "unmatched_count": 0},
            )

        if not reference:
            return SemanticMatchResult(
                success=False,
                message=f"No reference metabolites found in {params.reference_map}",
                error="Missing reference dataset",
            )

        logger.info(
            f"Starting semantic matching for {len(unmatched)} unmatched metabolites "
            f"against {len(reference)} reference metabolites"
        )

        # Get context fields for each dataset
        unmatched_fields = params.context_fields.get(
            params.unmatched_dataset.split("_")[0], ["name"]
        )
        reference_fields = params.context_fields.get(
            params.reference_map.split("_")[0], ["name"]
        )

        # Generate embeddings for all metabolites
        logger.info("Generating embeddings for unmatched metabolites...")
        source_embeddings = await self._generate_embeddings_batch(
            unmatched,
            unmatched_fields,
            params.unmatched_dataset,
            params.embedding_model,
            params.batch_size,
        )

        logger.info("Generating embeddings for reference metabolites...")
        reference_embeddings = await self._generate_embeddings_batch(
            reference,
            reference_fields,
            params.reference_map,
            params.embedding_model,
            params.batch_size,
        )

        # Find candidates and validate with LLM
        matches = []
        still_unmatched = []
        llm_calls = 0

        for source_idx, source_metabolite in enumerate(unmatched):
            if llm_calls >= params.max_llm_calls:
                logger.warning(f"Reached LLM call limit ({params.max_llm_calls})")
                still_unmatched.append(source_metabolite)
                continue

            # Get source embedding
            source_emb = source_embeddings.get(source_idx)
            if source_emb is None or all(v == 0 for v in source_emb):
                logger.warning(f"No valid embedding for metabolite {source_idx}")
                still_unmatched.append(source_metabolite)
                continue

            # Find candidates
            candidates = self._find_candidates(
                source_emb,
                reference_embeddings,
                params.embedding_similarity_threshold,
                top_k=5,
            )

            matched = False
            for ref_idx, similarity in candidates:
                candidate = reference[ref_idx]

                # Validate with LLM
                is_match, confidence, reasoning = await self._validate_match_with_llm(
                    source_metabolite, candidate, similarity, params.llm_model
                )
                llm_calls += 1

                if is_match and confidence >= params.confidence_threshold:
                    match_result = {
                        **source_metabolite,
                        "matched_name": candidate.get("unified_name", ""),
                        "matched_description": candidate.get("description", ""),
                        "match_confidence": confidence,
                        "embedding_similarity": similarity,
                        "match_method": "semantic_llm",
                        "match_source": params.reference_map,
                    }

                    if params.include_reasoning:
                        match_result["match_reasoning"] = reasoning

                    matches.append(match_result)
                    matched = True
                    break

            if not matched:
                still_unmatched.append(source_metabolite)

        # Store results
        datasets[params.output_key] = matches
        if params.unmatched_key:
            datasets[params.unmatched_key] = still_unmatched

        # Log results
        logger.info(
            f"Semantic matching complete: {len(matches)} matches found, "
            f"{len(still_unmatched)} still unmatched, {llm_calls} LLM calls made"
        )

        return SemanticMatchResult(
            success=True,
            message=f"Found {len(matches)} semantic matches using {llm_calls} LLM calls",
            data={
                "matched_count": len(matches),
                "unmatched_count": len(still_unmatched),
                "llm_calls": llm_calls,
                "cache_hits": sum(
                    1
                    for text in [
                        self._create_context_string(m, unmatched_fields, "")
                        for m in unmatched
                    ]
                    if self.embedding_cache.get(text) is not None
                ),
            },
        )
