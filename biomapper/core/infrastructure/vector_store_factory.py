"""
Vector store factory with fallback implementations for biomapper.
"""

from typing import Dict, Any, List, Protocol
import numpy as np
import logging


class VectorStore(Protocol):
    """Protocol for vector store implementations."""

    def create_collection(self, name: str, dimension: int) -> bool:
        """Create a new vector collection."""
        ...

    def upsert_vectors(
        self, collection: str, vectors: np.ndarray, metadata: List[Dict]
    ) -> bool:
        """Insert or update vectors in collection."""
        ...

    def search(
        self, collection: str, query_vector: np.ndarray, top_k: int = 10
    ) -> List[Dict]:
        """Search for similar vectors."""
        ...

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        ...


class InMemoryVectorStore:
    """Simple in-memory vector store implementation."""

    def __init__(self):
        self.collections: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)

    def create_collection(self, name: str, dimension: int) -> bool:
        """Create a new in-memory collection."""
        try:
            self.collections[name] = {
                "dimension": dimension,
                "vectors": np.array([]).reshape(0, dimension),
                "metadata": [],
            }
            self.logger.info(
                f"Created in-memory collection '{name}' with dimension {dimension}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create collection '{name}': {e}")
            return False

    def upsert_vectors(
        self, collection: str, vectors: np.ndarray, metadata: List[Dict]
    ) -> bool:
        """Add vectors to in-memory collection."""
        try:
            if collection not in self.collections:
                self.create_collection(collection, vectors.shape[1])

            coll = self.collections[collection]

            if len(coll["vectors"]) == 0:
                coll["vectors"] = vectors
                coll["metadata"] = metadata
            else:
                coll["vectors"] = np.vstack([coll["vectors"], vectors])
                coll["metadata"].extend(metadata)

            self.logger.debug(
                f"Added {len(vectors)} vectors to collection '{collection}'"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to upsert vectors to '{collection}': {e}")
            return False

    def search(
        self, collection: str, query_vector: np.ndarray, top_k: int = 10
    ) -> List[Dict]:
        """Search for similar vectors using cosine similarity."""
        try:
            if collection not in self.collections:
                return []

            coll = self.collections[collection]
            if len(coll["vectors"]) == 0:
                return []

            try:
                from sklearn.metrics.pairwise import cosine_similarity

                # Calculate similarities
                similarities = cosine_similarity([query_vector], coll["vectors"])[0]

                # Get top-k indices
                top_indices = np.argsort(similarities)[-top_k:][::-1]

                results = []
                for idx in top_indices:
                    result = {
                        "score": float(similarities[idx]),
                        "metadata": coll["metadata"][idx]
                        if idx < len(coll["metadata"])
                        else {},
                        "vector": coll["vectors"][idx],
                    }
                    results.append(result)

                return results
            except ImportError:
                # Fallback to basic numpy operations if sklearn not available
                from numpy.linalg import norm

                # Compute cosine similarities manually
                query_norm = norm(query_vector)
                if query_norm == 0:
                    return []

                similarities = []
                for vector in coll["vectors"]:
                    vector_norm = norm(vector)
                    if vector_norm == 0:
                        similarity = 0.0
                    else:
                        similarity = np.dot(query_vector, vector) / (
                            query_norm * vector_norm
                        )
                    similarities.append(similarity)

                similarities = np.array(similarities)
                top_indices = np.argsort(similarities)[-top_k:][::-1]

                results = []
                for idx in top_indices:
                    result = {
                        "score": float(similarities[idx]),
                        "metadata": coll["metadata"][idx]
                        if idx < len(coll["metadata"])
                        else {},
                        "vector": coll["vectors"][idx],
                    }
                    results.append(result)

                return results

        except Exception as e:
            self.logger.error(f"Search failed in collection '{collection}': {e}")
            return []

    def delete_collection(self, name: str) -> bool:
        """Delete an in-memory collection."""
        try:
            if name in self.collections:
                del self.collections[name]
                self.logger.info(f"Deleted collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete collection '{name}': {e}")
            return False


class QdrantVectorStore:
    """Qdrant vector store implementation (when available)."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self.client = None
        self.logger = logging.getLogger(__name__)

        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(host=host, port=port)
            self.logger.info(f"Connected to Qdrant at {host}:{port}")
        except ImportError:
            self.logger.warning("Qdrant client not available")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Qdrant: {e}")

    def create_collection(self, name: str, dimension: int) -> bool:
        """Create Qdrant collection."""
        if not self.client:
            return False

        try:
            from qdrant_client.models import Distance, VectorParams

            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            self.logger.info(f"Created Qdrant collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create Qdrant collection '{name}': {e}")
            return False

    def upsert_vectors(
        self, collection: str, vectors: np.ndarray, metadata: List[Dict]
    ) -> bool:
        """Upsert vectors to Qdrant collection."""
        if not self.client:
            return False

        try:
            from qdrant_client.models import PointStruct

            points = [
                PointStruct(id=i, vector=vector.tolist(), payload=meta)
                for i, (vector, meta) in enumerate(zip(vectors, metadata))
            ]

            self.client.upsert(collection_name=collection, points=points)
            self.logger.debug(
                f"Upserted {len(vectors)} vectors to Qdrant collection '{collection}'"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to upsert to Qdrant collection '{collection}': {e}"
            )
            return False

    def search(
        self, collection: str, query_vector: np.ndarray, top_k: int = 10
    ) -> List[Dict]:
        """Search Qdrant collection."""
        if not self.client:
            return []

        try:
            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector.tolist(),
                limit=top_k,
            )

            formatted_results = []
            for result in results:
                formatted_results.append(
                    {"score": result.score, "metadata": result.payload, "id": result.id}
                )

            return formatted_results
        except Exception as e:
            self.logger.error(f"Qdrant search failed in collection '{collection}': {e}")
            return []

    def delete_collection(self, name: str) -> bool:
        """Delete Qdrant collection."""
        if not self.client:
            return False

        try:
            self.client.delete_collection(collection_name=name)
            self.logger.info(f"Deleted Qdrant collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete Qdrant collection '{name}': {e}")
            return False


class VectorStoreFactory:
    """Factory for creating vector store instances with fallback."""

    @staticmethod
    def create_vector_store(
        preferred: str = "qdrant",
        fallback: str = "inmemory",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
    ) -> VectorStore:
        """Create vector store with fallback logic."""

        logger = logging.getLogger(__name__)

        if preferred == "qdrant":
            qdrant_store = QdrantVectorStore(qdrant_host, qdrant_port)
            if qdrant_store.client:
                logger.info("Using Qdrant vector store")
                return qdrant_store
            else:
                logger.warning("Qdrant unavailable, falling back to in-memory store")

        if fallback == "inmemory":
            logger.info("Using in-memory vector store")
            return InMemoryVectorStore()

        # Additional fallback implementations could be added here
        # (FAISS, ChromaDB, etc.)

        raise ValueError("No suitable vector store implementation found")


# Usage example for actions
def get_vector_store() -> VectorStore:
    """Get vector store instance for actions to use."""
    return VectorStoreFactory.create_vector_store(
        preferred="qdrant", fallback="inmemory"
    )
