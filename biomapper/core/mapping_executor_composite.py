"""Integration module for the MappingExecutor and composite identifier handling.

This module provides extension methods and mixins for the MappingExecutor
to leverage the CompositeIdentifierHandler and CompositeMiddleware.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
import asyncio

from sqlalchemy.orm import Session

from biomapper.core.composite_handler import CompositeIdentifierHandler, CompositeMiddleware
from biomapper.core.exceptions import ConfigurationError, MappingExecutionError

logger = logging.getLogger(__name__)


class CompositeIdentifierMixin:
    """Mixin class to add composite identifier handling to the MappingExecutor.
    
    This mixin should be applied to the MappingExecutor class to integrate
    composite identifier handling functionality.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the composite identifier mixin."""
        # Call the parent initializer
        super().__init__(*args, **kwargs)
        
        # Initialize the composite identifier handler
        self._composite_handler = CompositeIdentifierHandler()
        self._composite_middleware = CompositeMiddleware(self._composite_handler)
        self._composite_initialized = False
    
    async def _initialize_composite_handler(self, session: Session) -> None:
        """Initialize the composite identifier handler with the database session.
        
        Args:
            session: SQLAlchemy database session for metamapper.db
        """
        if not self._composite_initialized:
            await self._composite_handler.initialize(session)
            self._composite_initialized = True
            logger.info("Composite identifier handler initialized")
    
    async def _preprocess_identifiers(
        self, 
        session: Session,
        identifiers: List[str], 
        source_ontology: str
    ) -> Tuple[Dict[str, List[Tuple[str, str]]], List[str], Dict[str, str]]:
        """Preprocess identifiers to handle composite IDs before mapping.
        
        Args:
            session: SQLAlchemy database session
            identifiers: List of identifiers to process
            source_ontology: The ontology type of the source identifiers
            
        Returns:
            Tuple containing:
            - preprocessed_map: Map of original IDs to component (ID, ontology) tuples
            - all_component_ids: Flattened list of all component IDs to process
            - component_to_original: Map from component IDs back to their original IDs
        """
        # Ensure the handler is initialized
        if not self._composite_initialized:
            await self._initialize_composite_handler(session)
        
        # Check if we need to process composite identifiers for this ontology type
        if not self._composite_handler.has_patterns_for_ontology(source_ontology):
            # No patterns for this ontology, return the identifiers unchanged
            preprocessed_map = {id_: [(id_, source_ontology)] for id_ in identifiers}
            return preprocessed_map, identifiers, {id_: id_ for id_ in identifiers}
        
        # Preprocess the identifiers using the middleware
        preprocessed_map = await self._composite_middleware.preprocess_identifiers(
            identifiers, source_ontology
        )
        
        # Create a flattened list of all component IDs
        all_component_ids = []
        component_to_original = {}
        
        for original_id, components in preprocessed_map.items():
            for component_id, _ in components:
                all_component_ids.append(component_id)
                component_to_original[component_id] = original_id
        
        return preprocessed_map, all_component_ids, component_to_original
    
    async def _aggregate_component_results(
        self,
        original_identifiers: List[str],
        component_results: Dict[str, Any],
        preprocessed_map: Dict[str, List[Tuple[str, str]]],
        source_ontology: str
    ) -> Dict[str, Any]:
        """Aggregate mapping results from individual components back to original identifiers.
        
        Args:
            original_identifiers: The original identifiers before preprocessing
            component_results: The mapping results for each component
            preprocessed_map: The map from original identifiers to components
            source_ontology: The ontology type of the source identifiers
            
        Returns:
            Dictionary mapping original identifiers to aggregated mapping results
        """
        return await self._composite_middleware.aggregate_results(
            original_identifiers,
            component_results,
            preprocessed_map,
            source_ontology
        )
    
    async def execute_mapping_with_composite_handling(
        self,
        session: Session,
        identifiers: List[str],
        source_endpoint: str,
        target_endpoint: str,
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a mapping operation with composite identifier handling.
        
        This method wraps the standard execute_mapping method with additional
        preprocessing for composite identifiers and aggregation of results.
        
        Args:
            session: SQLAlchemy database session
            identifiers: List of identifiers to map
            source_endpoint: Name of the source endpoint
            target_endpoint: Name of the target endpoint
            source_ontology: Ontology type of the source identifiers
            target_ontology: Ontology type of the target identifiers
            mapping_session_id: Optional session ID for tracking the mapping operation
            **kwargs: Additional keyword arguments for the execute_mapping method
            
        Returns:
            Dictionary with mapping results
        """
        # Initialize the composite handler if needed
        if not self._composite_initialized:
            await self._initialize_composite_handler(session)
        
        # Check if we need to handle composite identifiers
        if not self._composite_handler.has_patterns_for_ontology(source_ontology):
            # No composite patterns for this ontology, use standard mapping
            return await self.execute_mapping(
                session,
                identifiers,
                source_endpoint,
                target_endpoint,
                source_ontology,
                target_ontology,
                mapping_session_id,
                **kwargs
            )
        
        # Preprocess identifiers to handle composite IDs
        preprocessed_map, all_component_ids, component_to_original = await self._preprocess_identifiers(
            session, identifiers, source_ontology
        )
        
        # Log the preprocessing results
        composite_count = sum(1 for id_ in identifiers if len(preprocessed_map[id_]) > 1)
        logger.info(
            f"Composite identifier preprocessing: {composite_count}/{len(identifiers)} "
            f"identifiers are composite, resulting in {len(all_component_ids)} total components"
        )
        
        # Execute mapping on the component IDs
        component_results = await self.execute_mapping(
            session,
            all_component_ids,
            source_endpoint,
            target_endpoint,
            source_ontology,
            target_ontology,
            mapping_session_id,
            **kwargs
        )
        
        # Aggregate the results back to the original identifiers
        aggregated_results = await self._aggregate_component_results(
            identifiers,
            component_results,
            preprocessed_map,
            source_ontology
        )
        
        # Calculate success metrics
        original_success_count = sum(1 for id_ in identifiers if component_results.get(id_, (None, None))[0])
        aggregated_success_count = sum(1 for id_ in identifiers if aggregated_results.get(id_, (None, None))[0])
        
        logger.info(
            f"Composite identifier mapping results: Direct success {original_success_count}/{len(identifiers)} "
            f"({original_success_count/len(identifiers)*100:.1f}%), After aggregation: "
            f"{aggregated_success_count}/{len(identifiers)} "
            f"({aggregated_success_count/len(identifiers)*100:.1f}%)"
        )
        
        return aggregated_results
