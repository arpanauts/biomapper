"""Base classes for the Biomapper Embedder module."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Optional
import numpy as np


class BaseEmbedder(ABC):
    """Base class for all embedders."""

    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        pass

    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector with shape (embedding_dim,)
        """
        pass


class BaseVectorStore(ABC):
    """Base class for vector storage backends."""

    @abstractmethod
    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> List[str]:
        """Add embeddings with metadata to the store.

        Args:
            embeddings: Array of embeddings with shape (n_embeddings, embedding_dim)
            metadata: List of metadata dictionaries, one per embedding

        Returns:
            List of IDs for the added embeddings
        """
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding
            k: Number of results to return

        Returns:
            List of dictionaries with search results including 'id', 'similarity' and 'metadata'
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """Delete embeddings by ID.

        Args:
            ids: List of embedding IDs to delete

        Returns:
            True if deletion was successful
        """
        pass
