"""Pipeline for metabolite name standardization."""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..core.base_pipeline import BaseMappingPipeline, BaseNameMapper
from ..mapping.rag.compound_mapper import RAGCompoundMapper
from ..monitoring.langfuse_tracker import LangfuseTracker
from ..monitoring.metrics import MetricsTracker
from ..schemas.domain_schema import DomainType
from .metabolite import MetaboliteMapping, MetaboliteNameMapper

logger = logging.getLogger(__name__)


class MetaboliteNameMapperWrapper(BaseNameMapper[MetaboliteMapping]):
    """Wrapper for MetaboliteNameMapper to conform to BaseNameMapper interface."""
    
    def __init__(self):
        self.mapper = MetaboliteNameMapper()
        
    def map_from_names(self, names: List[str]) -> List[MetaboliteMapping]:
        return self.mapper.map_from_names(names)


class MetaboliteMappingPipeline(BaseMappingPipeline[MetaboliteMapping]):
    """Pipeline for mapping metabolite names to standard identifiers."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.8,
        use_rag: bool = True,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None
    ):
        super().__init__(
            domain_type=DomainType.COMPOUND,
            confidence_threshold=confidence_threshold,
            use_rag=use_rag,
            metrics=metrics,
            langfuse=langfuse
        )

    def _create_name_mapper(self) -> BaseNameMapper[MetaboliteMapping]:
        return MetaboliteNameMapperWrapper()
    
    def _create_rag_mapper(self) -> RAGCompoundMapper:
        return RAGCompoundMapper(
            embedder=None,  # TODO: Add embedder implementation
            metrics=self.metrics,
            langfuse=self.langfuse
        )
    
    def _get_entity_confidence(self, entity: MetaboliteMapping) -> float:
        return entity.confidence
    
    def _update_entity_from_rag(self, entity: MetaboliteMapping, rag_result: Any) -> None:
        best_match = max(rag_result.matches, key=lambda m: m.confidence, default=None)
        if best_match:
            entity.hmdb_id = best_match.compound_id
            entity.confidence = best_match.confidence
            entity.mapping_source = "rag"

    async def map_from_file(
        self,
        input_file: Path,
        name_column: str,
        output_file: Optional[Path] = None
    ) -> None:
        """Map metabolite names from a file.
        
        Args:
            input_file: Path to input file (CSV or TSV)
            name_column: Name of column containing metabolite names
            output_file: Optional path to save results
        """
        # Read names from file
        df = pd.read_csv(input_file)
        names = df[name_column].tolist()
        
        # Process names
        result = await self.process_names(names)
        
        # Save results if output file specified
        if output_file:
            mappings_df = pd.DataFrame([vars(m) for m in result.mappings])
            mappings_df.to_csv(output_file, index=False)
