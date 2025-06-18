"""Vector storage backends for the Biomapper Embedder module."""

from .vector_store import FAISSVectorStore

try:
    from .qdrant_store import QdrantVectorStore
except ImportError:
    QdrantVectorStore = None

__all__ = ["FAISSVectorStore", "QdrantVectorStore"]
