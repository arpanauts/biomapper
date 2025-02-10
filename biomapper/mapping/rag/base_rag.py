"""Base classes for RAG-based mapping implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypeVar, Generic
import time
import logging

import numpy as np
from pydantic import BaseModel

from ...monitoring.langfuse_tracker import LangfuseTracker
from ...monitoring.metrics import MetricsTracker
from ...monitoring.traces import TraceManager
from ...schemas.rag_schema import LLMMapperResult, Match, RAGMetrics
from ...schemas.store_schema import VectorStoreConfig

logger = logging.getLogger(__name__)


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


class BaseVectorStore(Generic[T], ABC):
    """Base class for vector stores."""

    @abstractmethod
    async def add_documents(self, documents: List[T]) -> None:
        """Add documents to the store.
        
        Args:
            documents: List of documents to add
        """
        pass

    @abstractmethod
    async def get_relevant(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: float = 0.0
    ) -> List[T]:
        """Get relevant documents for a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of documents to retrieve
            threshold: Minimum similarity threshold

        Returns:
            List of relevant documents
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all documents from the store."""
        pass


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
    async def get_prompt(
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


class BaseRAGMapper(ABC):
    """Base class for RAG-based mapping."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedder: BaseEmbedder,
        prompt_manager: BasePromptManager,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
        store_config: Optional[VectorStoreConfig] = None,
    ) -> None:
        """Initialize RAG mapper.
        
        Args:
            vector_store: Vector store for document retrieval
            embedder: Text embedder
            prompt_manager: Prompt manager
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
            store_config: Optional vector store configuration
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.prompt_manager = prompt_manager
        self.metrics = metrics or MetricsTracker()
        self.langfuse = langfuse
        self.store_config = store_config

    async def map_query(self, query: str, **kwargs: Any) -> LLMMapperResult:
        """Map a query using RAG.
        
        Args:
            query: Query to map
            **kwargs: Additional mapping parameters

        Returns:
            Mapping result with matches and metrics
        """
        trace_id = await self.langfuse.trace_mapping(query) if self.langfuse else None
        start_time = time.time()

        try:
            # Get query embedding
            query_embedding = await self.embedder.embed_text(query)

            # Retrieve relevant documents
            retrieval_start = time.time()
            docs = await self.vector_store.get_relevant(
                query_embedding,
                k=kwargs.get("k", 5),
                threshold=kwargs.get("threshold", 0.0)
            )
            retrieval_latency = (time.time() - retrieval_start) * 1000

            # Generate response
            generation_start = time.time()
            prompt = await self.prompt_manager.get_prompt(query, docs, **kwargs)
            matches = await self._generate_matches(prompt, docs, **kwargs)
            generation_latency = (time.time() - generation_start) * 1000

            # Calculate metrics
            total_latency = (time.time() - start_time) * 1000
            metrics = RAGMetrics(
                retrieval_latency_ms=retrieval_latency,
                generation_latency_ms=generation_latency,
                total_latency_ms=total_latency,
                tokens_used=kwargs.get("tokens_used", 0),
                context_relevance=kwargs.get("context_relevance", 0.0),
                answer_faithfulness=kwargs.get("answer_faithfulness", 0.0),
            )

            # Record metrics
            if self.metrics:
                self.metrics.record_metrics(metrics, trace_id)

            return LLMMapperResult(
                query_term=query,
                matches=matches,
                best_match=max(matches, key=lambda m: float(m.confidence)) if matches else None,
                metrics=metrics.dict(),
                trace_id=trace_id or "",
            )

        except Exception as e:
            logger.error(f"Error in RAG mapping: {e}", exc_info=True)
            if trace_id and self.langfuse:
                await self.langfuse.record_error(trace_id, str(e))

            return LLMMapperResult(
                query_term=query,
                matches=[],
                best_match=Match(id="", name="", confidence="0.0", reasoning=str(e)),
                metrics={
                    "retrieval_latency_ms": 0.0,
                    "generation_latency_ms": 0.0,
                    "total_latency_ms": 0.0,
                    "tokens_used": 0,
                    "context_relevance": 0.0,
                    "answer_faithfulness": 0.0,
                },
                trace_id=trace_id or "",
                error=str(e)
            )

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
