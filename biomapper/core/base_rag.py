"""Base class for RAG/embedder components."""

from abc import ABC, abstractmethod
from typing import List, Any, Optional


class BaseEmbedder(ABC):
    """Abstract base class for embedding generators."""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[Any]:
        """Generate embeddings for given texts."""
        pass
    
    @abstractmethod
    def embed_single(self, text: str) -> Any:
        """Generate embedding for a single text."""
        pass