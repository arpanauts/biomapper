"""Base pipeline for entity mapping and standardization."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TypeVar, Generic

from ..monitoring.langfuse_tracker import LangfuseTracker
from ..monitoring.metrics import MetricsTracker
from .base_rag import BaseRAGMapper
from .base_mapper import BaseMapper, MappingResult
from ..schemas.domain_schema import DomainDocument, DomainType

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Generic result from a mapping pipeline."""
    mappings: List[DomainDocument]
    metrics: Dict[str, Any]
    unmatched_count: int = 0
    rag_mapped_count: int = 0


T = TypeVar("T", bound=DomainDocument)


class BaseNameMapper(ABC, Generic[T]):
    """Base class for name mapping implementations."""
    
    @abstractmethod
    async def map_from_names(self, names: List[str]) -> List[T]:
        """Map a list of names to domain documents."""
        pass


class BaseMappingPipeline(ABC, Generic[T]):
    """Base pipeline for mapping entity names to standard identifiers."""
    
    def __init__(
        self,
        domain_type: DomainType,
        confidence_threshold: float = 0.8,
        use_rag: bool = True,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None
    ):
        """Initialize the pipeline.
        
        Args:
            domain_type: Type of domain this pipeline handles
            confidence_threshold: Minimum confidence for a match
            use_rag: Whether to use RAG for unmatched entities
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
        """
        self.domain_type = domain_type
        self.confidence_threshold = confidence_threshold
        self.use_rag = use_rag
        self.metrics = metrics or MetricsTracker()
        self.langfuse = langfuse
        
        # Initialize components
        self.name_mapper = self._create_name_mapper()
        if use_rag:
            self.rag_mapper = self._create_rag_mapper()

    @abstractmethod
    def _create_name_mapper(self) -> BaseNameMapper[T]:
        """Create the appropriate name mapper for this domain."""
        pass
    
    @abstractmethod
    def _create_rag_mapper(self) -> BaseRAGMapper:
        """Create the appropriate RAG mapper for this domain."""
        pass
    
    @abstractmethod
    def _get_entity_confidence(self, entity: T) -> float:
        """Get confidence score for a mapped entity."""
        pass
    
    @abstractmethod
    def _update_entity_from_rag(self, entity: T, rag_result: Any) -> None:
        """Update entity with RAG mapping results."""
        pass

    async def process_names(self, names: List[str]) -> PipelineResult:
        """Process a list of entity names.
        
        Args:
            names: List of names to process
            
        Returns:
            PipelineResult with mappings and metrics
        """
        # Step 1: Initial mapping using domain-specific mapper
        initial_mappings = await self.name_mapper.map_from_names(names)
        
        # Step 2: Process results
        matched = []
        unmatched = []
        
        for mapping in initial_mappings:
            if self._get_entity_confidence(mapping) >= self.confidence_threshold:
                matched.append(mapping)
            else:
                unmatched.append(mapping)
                
        # Step 3: Use RAG for unmatched entities if enabled
        rag_mapped = []
        if self.use_rag and unmatched:
            for entity in unmatched:
                try:
                    # Convert entity to search text for RAG
                    rag_result = await self.rag_mapper.map_query(entity.to_search_text())
                    
                    # Update entity with RAG results if confident
                    if rag_result.best_match and rag_result.best_match.confidence >= self.confidence_threshold:
                        self._update_entity_from_rag(entity, rag_result)
                        rag_mapped.append(entity)
                    else:
                        matched.append(entity)  # Keep original low-confidence mapping
                        
                except Exception as e:
                    logger.error(f"RAG mapping failed for {entity}: {e}")
                    matched.append(entity)  # Keep original low-confidence mapping
        
        # Combine results
        final_mappings = matched + rag_mapped
        
        return PipelineResult(
            mappings=final_mappings,
            metrics={
                "total_entities": len(names),
                "initially_matched": len(matched),
                "unmatched": len(unmatched),
                "rag_mapped": len(rag_mapped),
                "domain_type": self.domain_type
            },
            unmatched_count=len(unmatched),
            rag_mapped_count=len(rag_mapped)
        )
