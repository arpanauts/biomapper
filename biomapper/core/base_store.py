"""Base class for vector stores."""

from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict


class BaseVectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def add_documents(self, documents: List[Any], embeddings: Optional[List[Any]] = None) -> None:
        """Add documents to the store."""
        pass
    
    @abstractmethod
    async def get_similar(self, query: str, k: int = 5, threshold: float = 0.0, 
                         filter_criteria: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Get similar documents."""
        pass