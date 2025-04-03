"""
Biomapper Embedder Module.

This module provides functionality for generating, storing, and retrieving 
embeddings from various biological text sources.
"""

__version__ = "0.1.0"

# Import core components for easier access
from .generators.text_embedder import TextEmbedder
from .storage.vector_store import FAISSVectorStore

# Import Qdrant if available
try:
    from .storage.qdrant_store import QdrantVectorStore
except ImportError:
    pass

__all__ = [
    "TextEmbedder",
    "FAISSVectorStore",
    "QdrantVectorStore",
]
