"""Pipeline for compound name standardization."""

import logging
from typing import List, Optional, Dict, Any

from ...core.base_mapper import MappingResult

from ...core.base_pipeline import BaseMappingPipeline, BaseNameMapper
from ...core.base_rag import BaseRAGMapper
from ...monitoring.langfuse_tracker import LangfuseTracker
from ...monitoring.metrics import MetricsTracker
from ...schemas.domain_schema import DomainType
from ...mapping.clients.chebi_client import ChEBIClient
from ...mapping.clients.refmet_client import RefMetClient
from ...mapping.clients.unichem_client import UniChemClient

from .compound_mapper import CompoundMapper, CompoundDocument

logger = logging.getLogger(__name__)


class CompoundNameMapper(BaseNameMapper[CompoundDocument]):
    """Maps compound names using multiple API clients."""
    
    def __init__(self):
        """Initialize mapper with API clients."""
        self.api_clients = [
            ChEBIClient(),
            RefMetClient(),
            UniChemClient()
        ]
        self.mapper = CompoundMapper(self.api_clients)
        
    async def map_from_names(self, names: List[str]) -> List[CompoundDocument]:
        """Map a list of names to compounds.
        
        Args:
            names: List of compound names
            
        Returns:
            List of mapped compounds
        """
        results = []
        for name in names:
            result = await self.mapper.map_entity(name)
            if result.mapped_entity:
                results.append(result.mapped_entity)
            else:
                # Add unmapped entity
                results.append(CompoundDocument(
                    name=name,
                    compound_class=None,
                    confidence=0.0,
                    source="unmapped"
                ))
        return results


class CompoundMappingPipeline(BaseMappingPipeline[CompoundDocument]):
    """Pipeline for mapping compound names to standard identifiers."""
    
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
            use_rag: Whether to use RAG for unmatched compounds
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
            rag_mapper: Optional RAG mapper to use
        """
        self.rag_mapper = rag_mapper
        super().__init__(
            domain_type=DomainType.COMPOUND,
            confidence_threshold=confidence_threshold,
            use_rag=use_rag,
            metrics=metrics,
            langfuse=langfuse
        )

    def _create_name_mapper(self) -> BaseNameMapper[CompoundDocument]:
        """Create compound name mapper."""
        return CompoundNameMapper()
    
    def _create_rag_mapper(self) -> BaseRAGMapper:
        """Create or return RAG mapper."""
        if self.rag_mapper:
            return self.rag_mapper
        
        # Import here to avoid circular dependency
        from ...mapping.rag.compound_mapper import RAGCompoundMapper
        return RAGCompoundMapper()
    
    def _get_entity_confidence(self, entity: CompoundDocument) -> float:
        """Get confidence score for mapped compound."""
        return entity.confidence
    
    def _update_entity_from_rag(
        self,
        entity: CompoundDocument,
        rag_result: MappingResult
    ) -> None:
        """Update compound with RAG mapping results."""
        entity.update_from_rag(rag_result)
