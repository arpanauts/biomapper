"""
MappingCoordinatorService - High-level mapping orchestration logic.

This service consolidates the high-level mapping orchestration logic from MappingExecutor,
specifically the execute_mapping and execute_path methods. It acts as a coordinator
between various execution services to provide clean, high-level mapping APIs.

Key Responsibilities:
- Orchestrate iterative mapping execution (execute_mapping)
- Coordinate path execution with optimized batching (execute_path)
- Delegate to specialized services for actual execution logic
"""

import logging
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.core.services.execution_services import IterativeExecutionService
from biomapper.core.services.mapping_path_execution_service import MappingPathExecutionService
from biomapper.db.models import MappingPath


class MappingCoordinatorService:
    """
    Service that coordinates high-level mapping operations.
    
    This service encapsulates the complex orchestration logic for mapping operations,
    delegating to specialized execution services for the actual implementation.
    It provides clean, high-level APIs for:
    - Iterative mapping execution with various strategies
    - Path execution with optimized batching and concurrency
    """
    
    def __init__(
        self,
        iterative_execution_service: IterativeExecutionService,
        path_execution_service: MappingPathExecutionService,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the MappingCoordinatorService.
        
        Args:
            iterative_execution_service: Service for handling iterative mapping logic
            path_execution_service: Service for executing mapping paths
            logger: Optional logger instance (creates one if not provided)
        """
        self.iterative_execution_service = iterative_execution_service
        self.path_execution_service = path_execution_service
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute_mapping(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str] = None,
        input_data: List[str] = None,
        source_property_name: str = "PrimaryIdentifier",
        target_property_name: str = "PrimaryIdentifier",
        source_ontology_type: str = None,
        target_ontology_type: str = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
        validate_bidirectional: bool = False,
        progress_callback: Optional[callable] = None,
        batch_size: int = 250,
        max_concurrent_batches: Optional[int] = None,
        max_hop_count: Optional[int] = None,
        min_confidence: float = 0.0,
        enable_metrics: Optional[bool] = None,
        mapping_executor: Any = None
    ) -> Dict[str, Any]:
        """
        Execute a mapping process based on endpoint configurations, using an iterative strategy.

        This method delegates to the IterativeExecutionService for the actual execution logic.
        The service handles:
        1. Attempt direct mapping using the primary shared ontology.
        2. Identify unmapped entities.
        3. For unmapped entities, attempt to convert secondary identifiers to the primary shared ontology.
        4. Re-attempt direct mapping using derived primary identifiers.
        5. Aggregate results.

        Args:
            source_endpoint_name: Source endpoint name
            target_endpoint_name: Target endpoint name
            input_identifiers: List of identifiers to map (deprecated, use input_data instead)
            input_data: List of identifiers to map (preferred parameter)
            source_property_name: Property name defining the primary ontology type for the source endpoint
            target_property_name: Property name defining the primary ontology type for the target endpoint
            source_ontology_type: Optional source ontology type override
            target_ontology_type: Optional target ontology type override
            use_cache: Whether to check the cache before executing mapping steps
            max_cache_age_days: Maximum age of cached results to use (None = no limit)
            mapping_direction: The preferred direction ('forward' or 'reverse')
            try_reverse_mapping: Allows using a reversed path if no forward path found
            validate_bidirectional: If True, validates forward mappings by testing reverse mapping
            progress_callback: Optional callback function for reporting progress
            batch_size: Number of identifiers to process in each batch
            max_concurrent_batches: Maximum number of batches to process concurrently
            max_hop_count: Maximum number of hops to allow in paths
            min_confidence: Minimum confidence score to accept
            enable_metrics: Whether to enable metrics tracking
            mapping_executor: Reference to the MappingExecutor for callbacks

        Returns:
            Dictionary with mapping results, including provenance and validation status
        """
        return await self.iterative_execution_service.execute(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            input_data=input_data,
            source_property_name=source_property_name,
            target_property_name=target_property_name,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            mapping_direction=mapping_direction,
            try_reverse_mapping=try_reverse_mapping,
            validate_bidirectional=validate_bidirectional,
            progress_callback=progress_callback,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            max_hop_count=max_hop_count,
            min_confidence=min_confidence,
            enable_metrics=enable_metrics,
            mapping_executor=mapping_executor,
        )

    async def execute_path(
        self,
        session: AsyncSession,  # Pass meta session
        path: Union[MappingPath, "ReversiblePath"],
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None,
        batch_size: int = 250,
        max_hop_count: Optional[int] = None,
        filter_confidence: float = 0.0,
        max_concurrent_batches: int = 5
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Execute a mapping path or its reverse, with optimized batched processing.
        
        This method delegates to MappingPathExecutionService for the actual execution logic.
        
        Args:
            session: Database session
            path: The path to execute
            input_identifiers: List of identifiers to map
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            mapping_session_id: Optional ID for the mapping session
            batch_size: Size of batches for processing large input sets
            max_hop_count: Maximum number of hops to allow (skip longer paths)
            filter_confidence: Minimum confidence threshold for results
            max_concurrent_batches: Maximum number of batches to process concurrently
            
        Returns:
            Dictionary mapping input identifiers to their results
        """
        # Delegate to MappingPathExecutionService
        return await self.path_execution_service.execute_path(
            path=path,
            input_identifiers=input_identifiers,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=mapping_session_id,
            execution_context=None,
            batch_size=batch_size,
            max_hop_count=max_hop_count,
            filter_confidence=filter_confidence,
            max_concurrent_batches=max_concurrent_batches
        )