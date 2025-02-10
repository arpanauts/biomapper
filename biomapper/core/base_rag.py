"""Base classes for RAG (Retrieval Augmented Generation) functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypeVar, Generic
import logging

import numpy as np
from pydantic import BaseModel

from ..monitoring.langfuse_tracker import LangfuseTracker
from ..monitoring.metrics import MetricsTracker
from ..schemas.rag_schema import LLMMapperResult, Match, RAGMetrics
from .base_store import BaseVectorStore
from .base_mapper import BaseMapper

logger = logging.getLogger(__name__)


# Re-export common exceptions
class RAGError(Exception):
    """Base exception for RAG-related errors."""
    pass


class EmbeddingError(RAGError):
    """Error during text embedding."""
    pass


class RetrievalError(RAGError):
    """Error during document retrieval."""
    pass


class GenerationError(RAGError):
    """Error during text generation."""
    pass


@dataclass
class Document:
    """Base document for RAG retrieval."""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


T = TypeVar("T", bound=Document)


class BaseEmbedder(ABC):
    """Base class for text embedders."""
    
    @abstractmethod
    async def embed_text(self, text: str) -> np.ndarray:
        """Embed text into a vector.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            EmbeddingError: If embedding fails
        """
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If embedding fails
        """
        pass


class BasePromptManager(ABC):
    """Base class for managing prompts."""
    
    @abstractmethod
    def get_prompt(
        self,
        query: str,
        context: List[Document],
        **kwargs: Any
    ) -> str:
        """Get prompt for generation.
        
        Args:
            query: User query
            context: Retrieved documents
            **kwargs: Additional prompt parameters
            
        Returns:
            Formatted prompt string
        """
        pass


class BaseRAGMapper(BaseMapper[T]):
    """Base class for RAG-based mapping."""
    
    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedder: BaseEmbedder,
        prompt_manager: BasePromptManager,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None
    ):
        """Initialize RAG mapper.
        
        Args:
            vector_store: Vector store for document retrieval
            embedder: Text embedder
            prompt_manager: Prompt manager
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.prompt_manager = prompt_manager
        self.metrics = metrics or MetricsTracker()
        self.langfuse = langfuse
        
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMMapperResult:
        """Map text using RAG approach.
        
        Args:
            text: Text to map
            context: Optional context
            
        Returns:
            Mapping result with matches and metrics
            
        Raises:
            RAGError: If mapping fails
        """
        try:
            # Get text embedding
            query_embedding = await self.embedder.embed_text(text)
            
            # Get similar documents
            similar_docs = await self.vector_store.get_similar(
                query_embedding,
                filter_criteria=context
            )
            
            # Generate prompt
            prompt = self.prompt_manager.get_prompt(
                query=text,
                context=similar_docs,
                **context or {}
            )
            
            # Generate matches
            matches = await self._generate_matches(prompt, similar_docs)
            
            return LLMMapperResult(
                matches=matches,
                metrics=RAGMetrics(
                    retrieval_time=0.0,  # TODO: Add timing
                    generation_time=0.0,
                    total_time=0.0
                )
            )
            
        except Exception as e:
            raise RAGError(f"RAG mapping failed: {e}") from e
    
    @abstractmethod
    async def _generate_matches(
        self,
        prompt: str,
        context: List[Document],
        **kwargs: Any
    ) -> List[Match]:
        """Generate matches from prompt and context.
        
        Args:
            prompt: Generated prompt
            context: Retrieved documents
            **kwargs: Additional generation parameters
            
        Returns:
            List of matches with confidence scores
            
        Raises:
            GenerationError: If generation fails
        """
        pass
