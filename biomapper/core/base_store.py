"""Base classes for vector stores and document storage."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
import numpy as np

from ..schemas.domain_schema import DomainDocument


T = TypeVar("T", bound=DomainDocument)


class BaseVectorStore(Generic[T], ABC):
    """Base class for vector stores."""
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[T],
        embeddings: Optional[List[np.ndarray]] = None
    ) -> None:
        """Add documents to the store.
        
        Args:
            documents: List of documents to add
            embeddings: Optional pre-computed embeddings
        """
        pass
    
    @abstractmethod
    async def get_similar(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.0,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get similar documents for a query.
        
        Args:
            query: Query string or embedding
            k: Number of results to return
            threshold: Minimum similarity threshold
            filter_criteria: Optional filters to apply
            
        Returns:
            List of similar documents
        """
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str]) -> None:
        """Delete documents from store.
        
        Args:
            document_ids: IDs of documents to delete
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all documents from store."""
        pass


class BaseDocumentStore(Generic[T], ABC):
    """Base class for document storage."""
    
    @abstractmethod
    async def add(self, documents: List[T]) -> None:
        """Add documents to store.
        
        Args:
            documents: Documents to add
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        document_ids: List[str]
    ) -> List[Optional[T]]:
        """Get documents by ID.
        
        Args:
            document_ids: IDs to retrieve
            
        Returns:
            List of documents (None for not found)
        """
        pass
    
    @abstractmethod
    async def update(self, documents: List[T]) -> None:
        """Update existing documents.
        
        Args:
            documents: Documents to update
        """
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str]) -> None:
        """Delete documents.
        
        Args:
            document_ids: IDs to delete
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: Dict[str, Any],
        limit: int = 10,
        offset: int = 0
    ) -> List[T]:
        """Search documents with query.
        
        Args:
            query: Search criteria
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Matching documents
        """
        pass
