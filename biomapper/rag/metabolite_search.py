"""Search interface for finding HMDB metabolites by name."""

import logging
from typing import List, Dict, Any
import asyncio

from qdrant_client import QdrantClient
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class MetaboliteSearcher:
    """Search interface for finding HMDB metabolites by name."""

    def __init__(
        self,
        qdrant_url: str = "localhost:6333",
        collection_name: str = "hmdb_metabolites",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
    ):
        """Initialize the searcher.

        Args:
            qdrant_url: URL for Qdrant instance
            collection_name: Name of collection containing metabolites
            embedding_model: FastEmbed model name for generating embeddings
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model

        # Initialize clients
        self.client = QdrantClient(qdrant_url)
        self.embedding_model = TextEmbedding(model_name=embedding_model)

        logger.info(f"Initialized MetaboliteSearcher with model: {embedding_model}")

    async def search_by_name(
        self, compound_name: str, limit: int = 10, score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for metabolites by compound name.

        Args:
            compound_name: Name of compound to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold

        Returns:
            List of matches with scores and metadata, sorted by score descending
        """
        # Generate embedding for query
        embeddings = list(self.embedding_model.embed([compound_name]))
        query_vector = embeddings[0]

        # Search in Qdrant - Qdrant handles the limit for us
        search_results = self.client.search(
            collection_name=self.collection_name, query_vector=query_vector, limit=limit
        )

        # Filter by score threshold and format results
        results = []
        for result in search_results:
            if result.score >= score_threshold:
                # Combine score with payload data
                result_dict: Dict[str, Any] = {"score": result.score}
                if result.payload:
                    result_dict.update(result.payload)
                results.append(result_dict)

        # Results are already sorted by score descending from Qdrant
        return results

    async def batch_search(
        self, compound_names: List[str], limit_per_query: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search for multiple compounds efficiently.

        Args:
            compound_names: List of compound names to search for
            limit_per_query: Maximum results per compound

        Returns:
            Dictionary mapping compound names to their search results
        """
        if not compound_names:
            return {}

        # Batch embed all queries for efficiency
        embeddings = list(self.embedding_model.embed(compound_names))

        # Perform searches concurrently
        search_tasks = []
        for i, compound_name in enumerate(compound_names):
            task = self._search_with_embedding(
                compound_name, embeddings[i], limit_per_query
            )
            search_tasks.append(task)

        # Execute all searches concurrently
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Combine results
        batch_results: Dict[str, List[Dict[str, Any]]] = {}
        for i, compound_name in enumerate(compound_names):
            result = search_results[i]
            if isinstance(result, Exception):
                logger.error(f"Error searching for {compound_name}: {result}")
                batch_results[compound_name] = []
            else:
                # Type cast is safe because we know it's not an Exception
                batch_results[compound_name] = result  # type: ignore[assignment]

        return batch_results

    async def _search_with_embedding(
        self, compound_name: str, embedding: List[float], limit: int
    ) -> List[Dict[str, Any]]:
        """Search using pre-computed embedding.

        Args:
            compound_name: Name of compound (for logging)
            embedding: Pre-computed embedding vector
            limit: Maximum number of results

        Returns:
            List of search results
        """
        try:
            # Search in Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit,
            )

            # Format results
            results = []
            for result in search_results:
                result_dict: Dict[str, Any] = {"score": result.score}
                if result.payload:
                    result_dict.update(result.payload)
                results.append(result_dict)

            return results

        except Exception as e:
            logger.error(f"Error in _search_with_embedding for {compound_name}: {e}")
            return []
