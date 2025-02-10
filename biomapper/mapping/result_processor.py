"""Module for processing and scoring mapping results."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..monitoring.langfuse_tracker import LangfuseTracker
from ..monitoring.metrics import MetricsTracker
from ..schemas.metabolite_schema import MetaboliteDocument
from ..mapping.metabolite.name import MetaboliteMapping, MetaboliteClass


class MappingSource(str, Enum):
    """Source of a mapping result."""
    REFMET = "refmet"
    CHEBI = "chebi"
    UNICHEM = "unichem"
    SPOKE = "spoke"
    RAG = "rag"


class ConfidenceLevel(str, Enum):
    """Confidence level in mapping result."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class ProcessedResult:
    """Processed and validated mapping result."""
    input_name: str
    compound_class: Optional[MetaboliteClass] = None
    primary_compound: Optional[str] = None
    secondary_compound: Optional[str] = None
    mapped_id: Optional[str] = None
    mapped_name: Optional[str] = None
    source: Optional[MappingSource] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


class ResultProcessor:
    """Processes and combines results from multiple mapping sources."""

    def __init__(
        self,
        high_confidence_threshold: float = 0.8,
        medium_confidence_threshold: float = 0.5,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
    ) -> None:
        """Initialize the result processor.

        Args:
            high_confidence_threshold: Threshold for high confidence results
            medium_confidence_threshold: Threshold for medium confidence results
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
        """
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.metrics = metrics
        self.langfuse = langfuse

    def process_name_mapping(
        self, mapping: MetaboliteMapping
    ) -> ProcessedResult:
        """Process a result from MetaboliteNameMapper.

        Args:
            mapping: Result from MetaboliteNameMapper

        Returns:
            Processed and standardized result
        """
        # Start with base result
        result = ProcessedResult(
            input_name=mapping.input_name,
            compound_class=mapping.compound_class,
            primary_compound=mapping.primary_compound,
            secondary_compound=mapping.secondary_compound,
        )

        # Try mapping sources in priority order
        if mapping.refmet_id:
            result.mapped_id = mapping.refmet_id
            result.mapped_name = mapping.refmet_name
            result.source = MappingSource.REFMET
            result.confidence_score = 0.9
        elif mapping.chebi_id:
            result.mapped_id = mapping.chebi_id
            result.mapped_name = mapping.chebi_name
            result.source = MappingSource.CHEBI
            result.confidence_score = 0.85
        elif mapping.pubchem_id:
            result.mapped_id = mapping.pubchem_id
            result.source = MappingSource.UNICHEM
            result.confidence_score = 0.8

        # Record metadata
        result.metadata = {
            "mapping_source": mapping.mapping_source or "unknown",
            "original_class": mapping.compound_class.value if mapping.compound_class else "unknown",
            "has_refmet": bool(mapping.refmet_id),
            "has_chebi": bool(mapping.chebi_id),
            "has_pubchem": bool(mapping.pubchem_id),
        }

        # Set confidence level based on score
        result.confidence = self._get_confidence_level(result.confidence_score)

        # Record metrics if available
        if self.metrics:
            self.metrics.record_metrics(
                {
                    "name_mapping_confidence": result.confidence_score,
                    "name_mapping_source": result.source.value if result.source else "none"
                },
                trace_id=mapping.metadata.get("trace_id") if mapping.metadata else None
            )

        return result

    def process_spoke_mapping(
        self, 
        mapping: Dict[str, Any], 
        base_result: Optional[ProcessedResult] = None
    ) -> ProcessedResult:
        """Process a result from SPOKE mapping.

        Args:
            mapping: Result from SPOKE mapper
            base_result: Optional base result to extend

        Returns:
            Processed and standardized result
        """
        # Use base result if provided, otherwise create new
        result = base_result or ProcessedResult(
            input_name=mapping.get("input_name", "unknown")
        )

        # Update with SPOKE data if found
        if spoke_id := mapping.get("spoke_id"):
            result.mapped_id = spoke_id
            result.source = MappingSource.SPOKE
            result.confidence_score = mapping.get("confidence_score", 0.0)
            
            # Add SPOKE metadata
            result.metadata.update({
                "spoke_node_type": mapping.get("node_type"),
                "spoke_properties": mapping.get("properties", {}),
                **mapping.get("metadata", {})
            })

        # Update confidence level
        result.confidence = self._get_confidence_level(result.confidence_score)

        return result

    def process_rag_mapping(
        self,
        mapping: Dict[str, Any],
        base_result: Optional[ProcessedResult] = None
    ) -> ProcessedResult:
        """Process a result from RAG mapping.

        Args:
            mapping: Result from RAG mapper
            base_result: Optional base result to extend

        Returns:
            Processed and standardized result
        """
        # Use base result if provided, otherwise create new
        result = base_result or ProcessedResult(
            input_name=mapping.get("query_term", "unknown")
        )

        # Update with RAG data if a match was found
        if best_match := mapping.get("best_match"):
            result.mapped_id = best_match.get("target_id")
            result.mapped_name = best_match.get("target_name")
            result.source = MappingSource.RAG
            result.confidence_score = float(best_match.get("confidence", 0))

            # Add RAG metadata
            result.metadata.update({
                "rag_matches": len(mapping.get("matches", [])),
                "rag_metrics": mapping.get("metrics", {}),
                **best_match.get("metadata", {})
            })

        # Update confidence level
        result.confidence = self._get_confidence_level(result.confidence_score)

        return result

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Get confidence level based on score.

        Args:
            score: Confidence score between 0 and 1

        Returns:
            Corresponding confidence level
        """
        if score >= self.high_confidence_threshold:
            return ConfidenceLevel.HIGH
        elif score >= self.medium_confidence_threshold:
            return ConfidenceLevel.MEDIUM
        elif score > 0:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNKNOWN

    def should_try_rag(self, result: ProcessedResult) -> bool:
        """Determine if RAG should be attempted.

        Args:
            result: Current processed result

        Returns:
            True if RAG should be attempted, False otherwise
        """
        # Try RAG if:
        # 1. No mapping found
        # 2. Low confidence result
        # 3. Missing key information
        return (
            result.mapped_id is None or
            result.confidence_score < self.medium_confidence_threshold or
            (result.source != MappingSource.RAG and not result.mapped_name)
        )

    def combine_results(
        self,
        name_result: Optional[MetaboliteMapping] = None,
        spoke_result: Optional[Dict[str, Any]] = None,
        rag_result: Optional[Dict[str, Any]] = None,
    ) -> ProcessedResult:
        """Combine results from multiple sources.

        Args:
            name_result: Result from name mapping
            spoke_result: Result from SPOKE mapping
            rag_result: Result from RAG mapping

        Returns:
            Combined and processed result

        Notes:
            Processes results in priority order:
            1. Name mapping (RefMet/ChEBI)
            2. SPOKE mapping
            3. RAG mapping
        """
        # Start with name mapping if available
        result = None
        if name_result:
            result = self.process_name_mapping(name_result)

            # Record metrics if available
            if self.metrics:
                self.metrics.record_metrics({
                    "name_mapping_confidence": result.confidence_score,
                    "name_mapping_source": result.source.value if result.source else "none"
                }, trace_id=name_result.metadata.get("trace_id") if name_result.metadata else None)

        # Add SPOKE data if available
        if spoke_result:
            result = self.process_spoke_mapping(spoke_result, result)

        # Add RAG data if available or if previous results weren't confident
        if rag_result or (result and self.should_try_rag(result)):
            if rag_result:
                result = self.process_rag_mapping(rag_result, result)

        # Ensure we have a result
        if not result:
            # Create empty result if no mappings available
            result = ProcessedResult(
                input_name="unknown",
                confidence=ConfidenceLevel.UNKNOWN,
                confidence_score=0.0
            )

        return result

    def process_batch(
        self,
        names: List[str],
        name_results: Optional[List[MetaboliteMapping]] = None,
        spoke_results: Optional[List[Dict[str, Any]]] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None,
    ) -> List[ProcessedResult]:
        """Process a batch of mapping results.

        Args:
            names: Original input names
            name_results: Results from name mapping
            spoke_results: Results from SPOKE mapping
            rag_results: Results from RAG mapping

        Returns:
            List of processed results
        """
        results = []
        for idx, name in enumerate(names):
            # Get corresponding results if available
            name_result = name_results[idx] if name_results else None
            spoke_result = spoke_results[idx] if spoke_results else None
            rag_result = rag_results[idx] if rag_results else None

            # Combine and process results
            result = self.combine_results(name_result, spoke_result, rag_result)
            if not result.input_name or result.input_name == "unknown":
                result.input_name = name

            results.append(result)

        return results
