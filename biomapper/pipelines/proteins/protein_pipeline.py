"""Pipeline for protein name standardization."""

import logging
from typing import List, Optional, Dict, Any

from ...core.base_pipeline import BaseMappingPipeline, BaseNameMapper
from ...core.base_rag import BaseRAGMapper
from ...monitoring.langfuse_tracker import LangfuseTracker
from ...monitoring.metrics import MetricsTracker
from ...schemas.domain_schema import DomainType
from ...mapping.clients.uniprot_focused_mapper import UniprotFocusedMapper

from .protein_mapper import ProteinMapper, ProteinDocument

logger = logging.getLogger(__name__)


class ProteinNameMapper(BaseNameMapper[ProteinDocument]):
    """Maps protein names using UniProt API."""
    
    def __init__(self):
        """Initialize mapper with UniProt client."""
        self.uniprot_client = UniprotFocusedMapper()
        self.mapper = ProteinMapper(self.uniprot_client)
        
    async def map_from_names(self, names: List[str]) -> List[ProteinDocument]:
        """Map a list of names to proteins.
        
        Args:
            names: List of protein names
            
        Returns:
            List of mapped proteins
        """
        results = []
        for name in names:
            result = await self.mapper.map_entity(name)
            if result.mapped_entity:
                results.append(result.mapped_entity)
            else:
                # Add unmapped entity
                results.append(ProteinDocument(
                    name=name,
                    confidence=0.0,
                    source="unmapped"
                ))
        return results


class ProteinMappingPipeline(BaseMappingPipeline[ProteinDocument]):
    """Pipeline for mapping protein names to standard identifiers."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.8,
        use_rag: bool = True,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
        rag_mapper: Optional[BaseRAGMapper] = None
    ):
        """Initialize pipeline.
        
        Args:
            confidence_threshold: Minimum confidence for a match
            use_rag: Whether to use RAG for unmatched proteins
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
            rag_mapper: Optional RAG mapper to use
        """
        self.rag_mapper = rag_mapper
        super().__init__(
            domain_type=DomainType.PROTEIN,
            confidence_threshold=confidence_threshold,
            use_rag=use_rag,
            metrics=metrics,
            langfuse=langfuse
        )

    def _create_name_mapper(self) -> BaseNameMapper[ProteinDocument]:
        """Create protein name mapper."""
        return ProteinNameMapper()
    
    def _create_rag_mapper(self) -> BaseRAGMapper:
        """Create or return RAG mapper."""
        if self.rag_mapper:
            return self.rag_mapper
        
        # Import here to avoid circular dependency
        from ...mapping.rag.protein_mapper import RAGProteinMapper
        return RAGProteinMapper()
    
    def _get_entity_confidence(self, entity: ProteinDocument) -> float:
        """Get confidence score for mapped protein."""
        return entity.confidence
    
    def _update_entity_from_rag(
        self,
        entity: ProteinDocument,
        rag_result: MappingResult
    ) -> None:
        """Update protein with RAG mapping results."""
        entity.update_from_rag(rag_result)
