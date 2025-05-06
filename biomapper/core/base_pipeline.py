"""Base pipeline for entity mapping and standardization."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TypeVar, Generic, Union, cast, Sequence

from ..monitoring.langfuse_tracker import LangfuseTracker
from ..monitoring.metrics import MetricsTracker
from .base_rag import BaseRAGMapper, Document
from .base_mapper import BaseMapper, MappingResult
from ..schemas.domain_schema import DomainDocument, DomainType
from ..schemas.rag_schema import LLMMapperResult, Match

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Generic result from a mapping pipeline."""

    mappings: Sequence[DomainDocument]  # Use Sequence for covariance
    metrics: Dict[str, Any]
    unmatched_count: int = 0
    rag_mapped_count: int = 0


T = TypeVar("T", bound=DomainDocument)


class BaseNameMapper(ABC, Generic[T]):
    """Base class for name mapping implementations.

    Responsible for mapping entity names to structured domain-specific documents.
    """

    @abstractmethod
    async def map_from_names(self, names: List[str]) -> List[T]:
        """Map a list of entity names to domain-specific documents.

        Args:
            names: List of entity names/identifiers to map

        Returns:
            List of domain-specific documents corresponding to the input names

        Raises:
            ValueError: If names list is empty or contains invalid elements
        """
        pass


class BaseMappingPipeline(ABC, Generic[T]):
    """Base pipeline for mapping entity names to standard identifiers."""

    def __init__(
        self,
        domain_type: DomainType,
        confidence_threshold: float = 0.8,
        use_rag: bool = True,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
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
        """Create the appropriate name mapper for this domain.

        Returns:
            A name mapper instance specific to this domain type
        """
        pass

    @abstractmethod
    def _create_rag_mapper(self) -> BaseRAGMapper[Document]:
        """Create the appropriate RAG mapper for this domain.

        Returns:
            A RAG mapper instance for this domain type
        """
        pass

    @abstractmethod
    def _get_entity_confidence(self, entity: T) -> float:
        """Get confidence score for a mapped entity.

        Args:
            entity: The entity to assess confidence for

        Returns:
            A confidence score between 0.0 and 1.0
        """
        pass

    @abstractmethod
    def _update_entity_from_rag(self, entity: T, rag_result: LLMMapperResult) -> None:
        """Update entity with RAG mapping results.

        Args:
            entity: The entity to update
            rag_result: Results from RAG mapping including matches and metadata

        Raises:
            ValueError: If entity cannot be updated with the provided RAG result
        """
        pass

    async def process_names(self, names: List[str]) -> PipelineResult:
        """Process a list of entity names.

        Args:
            names: List of names to process

        Returns:
            PipelineResult with mappings and metrics

        Raises:
            ValueError: If names list is empty
        """
        if not names:
            raise ValueError("Names list cannot be empty")

        # Step 1: Initial mapping using domain-specific mapper
        initial_mappings: List[T] = await self.name_mapper.map_from_names(names)

        # Step 2: Process results
        matched: List[T] = []
        unmatched: List[T] = []

        for mapping in initial_mappings:
            if self._get_entity_confidence(mapping) >= self.confidence_threshold:
                matched.append(mapping)
            else:
                unmatched.append(mapping)

        # Step 3: Use RAG for unmatched entities if enabled
        rag_mapped: List[T] = []
        if self.use_rag and unmatched and hasattr(self, "rag_mapper"):
            for entity in unmatched:
                try:
                    # Ensure entity has the required method
                    if not hasattr(entity, "to_search_text"):
                        logger.warning(
                            f"Entity {entity} does not have to_search_text method, skipping RAG"
                        )
                        matched.append(entity)
                        continue

                    # Convert entity to search text for RAG
                    rag_result: LLMMapperResult = await self.rag_mapper.map_entity(
                        entity.to_search_text()
                    )

                    # Update entity with RAG results if confident
                    # Check for valid matches with sufficient confidence
                    has_matches = (
                        hasattr(rag_result, "matches")
                        and rag_result.matches is not None
                        and len(rag_result.matches) > 0
                    )

                    confident_match = False
                    if has_matches:
                        try:
                            # Try to access and compare confidence as a float
                            top_match = rag_result.matches[0]
                            confidence_value = float(
                                top_match.confidence
                            )  # Explicit conversion to float
                            confident_match = (
                                confidence_value >= self.confidence_threshold
                            )
                        except (AttributeError, ValueError, TypeError):
                            # Handle cases where confidence isn't accessible or not comparable
                            logger.debug(
                                f"Could not assess confidence for match in {entity}"
                            )
                            confident_match = False

                    if confident_match:
                        self._update_entity_from_rag(entity, rag_result)
                        rag_mapped.append(entity)
                    else:
                        matched.append(entity)  # Keep original low-confidence mapping

                except Exception as e:
                    logger.error(f"RAG mapping failed for {entity}: {e}")
                    matched.append(entity)  # Keep original low-confidence mapping

        # Combine results
        final_mappings: List[T] = matched + rag_mapped

        # Build metrics dictionary
        metrics_dict: Dict[str, Any] = {
            "total_entities": len(names),
            "initially_matched": len(matched),
            "unmatched": len(unmatched),
            "rag_mapped": len(rag_mapped),
            "domain_type": self.domain_type,
        }

        # Cast to satisfy mypy - the generic type T is known to be a subclass of DomainDocument
        return PipelineResult(
            mappings=cast(Sequence[DomainDocument], final_mappings),
            metrics=metrics_dict,
            unmatched_count=len(unmatched),
            rag_mapped_count=len(rag_mapped),
        )
