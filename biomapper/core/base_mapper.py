"""Base classes for entity mapping."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar

from ..schemas.domain_schema import DomainDocument
from .base_client import APIResponse


T = TypeVar("T", bound=DomainDocument)


@dataclass
class MappingResult:
    """Result of mapping attempt."""
    input_text: str
    mapped_entity: Optional[T]
    confidence: float
    source: str
    metadata: Dict[str, Any]


class BaseMapper(Generic[T], ABC):
    """Base class for entity mapping."""
    
    @abstractmethod
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map text to entity.
        
        Args:
            text: Text to map
            context: Optional mapping context
            
        Returns:
            Mapping result
        """
        pass
    
    @abstractmethod
    async def batch_map(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[MappingResult]:
        """Map multiple texts to entities.
        
        Args:
            texts: Texts to map
            context: Optional mapping context
            
        Returns:
            List of mapping results
        """
        pass


class APIMapper(BaseMapper[T], ABC):
    """Base class for API-based mapping."""
    
    def __init__(self, client: Any):
        """Initialize mapper with API client."""
        self.client = client
    
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map using API client."""
        response = await self.client.search(text)
        return await self._process_response(text, response, context)
    
    async def batch_map(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[MappingResult]:
        """Map multiple texts using API client."""
        responses = await self.client.batch_search(texts)
        return [
            await self._process_response(text, response, context)
            for text, response in zip(texts, responses)
        ]
    
    @abstractmethod
    async def _process_response(
        self,
        input_text: str,
        response: APIResponse,
        context: Optional[Dict[str, Any]]
    ) -> MappingResult:
        """Process API response into mapping result.
        
        Args:
            input_text: Original input text
            response: API response
            context: Optional context
            
        Returns:
            Processed mapping result
        """
        pass


class RAGMapper(BaseMapper[T], ABC):
    """Base class for RAG-based mapping."""
    
    def __init__(
        self,
        vector_store: Any,
        llm_client: Any,
        confidence_threshold: float = 0.8
    ):
        """Initialize mapper with vector store and LLM."""
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
    
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map using RAG approach."""
        # Get similar documents
        similar_docs = await self.vector_store.get_similar(
            text,
            threshold=self.confidence_threshold
        )
        
        # Generate mapping with LLM
        mapping = await self._generate_mapping(text, similar_docs, context)
        
        return mapping
    
    @abstractmethod
    async def _generate_mapping(
        self,
        text: str,
        similar_docs: List[T],
        context: Optional[Dict[str, Any]]
    ) -> MappingResult:
        """Generate mapping using retrieved documents.
        
        Args:
            text: Input text
            similar_docs: Retrieved similar documents
            context: Optional context
            
        Returns:
            Generated mapping
        """
        pass
