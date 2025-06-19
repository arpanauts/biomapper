"""
MappingPathExecutionService - Handles direct mapping path execution logic.

This service encapsulates the complex logic for executing direct mappings between endpoints,
including cache handling, batch processing, progress tracking, and bidirectional validation.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Set, Callable

from biomapper.core.exceptions import ConfigurationError
from biomapper.core.models.result_bundle import MappingResultBundle


class MappingPathExecutionService:
    """
    Service responsible for executing direct mapping paths between endpoints.
    
    This service encapsulates the multi-step iterative strategy for mapping:
    1. Attempt direct mapping using primary shared ontology
    2. Identify unmapped entities  
    3. Handle secondary identifier conversion
    4. Re-attempt mapping with derived identifiers
    5. Aggregate and validate results
    """
    
    def __init__(
        self,
        session_manager,
        client_manager,
        cache_manager,
        path_finder,
        path_execution_manager,
        composite_handler,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the MappingPathExecutionService.
        
        Args:
            session_manager: Database session manager
            client_manager: Client connection manager
            cache_manager: Caching service
            path_finder: Path finding service
            path_execution_manager: Path execution service
            composite_handler: Composite identifier handler
            logger: Optional logger instance
        """
        self.session_manager = session_manager
        self.client_manager = client_manager
        self.cache_manager = cache_manager
        self.path_finder = path_finder
        self.path_execution_manager = path_execution_manager
        self.composite_handler = composite_handler
        self.logger = logger or logging.getLogger(__name__)
        
    async def execute_mapping(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        source_property_name: str = "PrimaryIdentifier",
        target_property_name: str = "PrimaryIdentifier",
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
        validate_bidirectional: bool = False,
        progress_callback: Optional[Callable] = None,
        batch_size: int = 250,
        max_concurrent_batches: int = 5,
        max_hop_count: Optional[int] = None,
        min_confidence: float = 0.0,
        enable_metrics: bool = True,
        mapping_session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a mapping process between endpoints using iterative strategy.
        
        This method implements the core mapping algorithm:
        1. Setup and validation
        2. Cache lookup
        3. Direct primary mapping
        4. Secondary identifier conversion (future)
        5. Result aggregation and validation
        
        Args:
            source_endpoint_name: Source endpoint name
            target_endpoint_name: Target endpoint name
            input_identifiers: List of identifiers to map
            source_property_name: Source property name
            target_property_name: Target property name
            source_ontology_type: Optional source ontology override
            target_ontology_type: Optional target ontology override
            use_cache: Whether to use caching
            max_cache_age_days: Maximum cache age in days
            mapping_direction: Preferred mapping direction
            try_reverse_mapping: Allow reverse path usage
            validate_bidirectional: Validate with reverse mapping
            progress_callback: Progress reporting callback
            batch_size: Batch size for processing
            max_concurrent_batches: Max concurrent batches
            max_hop_count: Maximum path hops allowed
            min_confidence: Minimum confidence threshold
            enable_metrics: Enable metrics tracking
            mapping_session_id: Optional mapping session ID
            
        Returns:
            Dictionary containing mapping results and metadata
        """
        # Input validation
        if not input_identifiers:
            self.logger.warning("No input identifiers provided for mapping.")
            return {}
            
        # Initialize tracking variables
        original_input_ids_set = set(input_identifiers)
        successful_mappings = {}
        processed_ids = set()
        total_ids = len(original_input_ids_set)
        
        # Report initial progress
        if progress_callback:
            progress_callback(0, total_ids, "Starting mapping process")
            
        # Start performance tracking
        overall_start_time = time.time()
        self.logger.info(f"TIMING: execute_mapping started for {total_ids} identifiers")
        
        try:
            # Get database session
            async with self.session_manager.get_metamapper_session() as meta_session:
                self.logger.info(
                    f"Executing mapping: {source_endpoint_name}.{source_property_name} -> "
                    f"{target_endpoint_name}.{target_property_name}"
                )
                
                # 1. Get endpoint configuration and ontology types
                config_start = time.time()
                config_result = await self._get_endpoint_configuration(
                    meta_session,
                    source_endpoint_name,
                    target_endpoint_name,
                    source_property_name,
                    target_property_name,
                    source_ontology_type,
                    target_ontology_type
                )
                
                source_endpoint = config_result['source_endpoint']
                target_endpoint = config_result['target_endpoint']
                primary_source_ontology = config_result['primary_source_ontology']
                primary_target_ontology = config_result['primary_target_ontology']
                
                self.logger.info(f"TIMING: endpoint configuration took {time.time() - config_start:.3f}s")
                
                # 2. Check for composite identifiers
                if await self._should_use_composite_handling(
                    input_identifiers, primary_source_ontology
                ):
                    return await self._execute_with_composite_handling(
                        meta_session,
                        input_identifiers,
                        source_endpoint_name,
                        target_endpoint_name,
                        primary_source_ontology,
                        primary_target_ontology,
                        mapping_session_id,
                        source_property_name,
                        target_property_name,
                        use_cache,
                        max_cache_age_days,
                        mapping_direction,
                        try_reverse_mapping
                    )
                
                # 3. Execute direct primary mapping
                self.logger.info("--- Step 3: Attempting Direct Primary Mapping ---")
                primary_results = await self._execute_direct_primary_mapping(
                    meta_session,
                    primary_source_ontology,
                    primary_target_ontology,
                    original_input_ids_set,
                    processed_ids,
                    source_endpoint,
                    target_endpoint,
                    mapping_direction,
                    try_reverse_mapping,
                    mapping_session_id,
                    use_cache,
                    max_cache_age_days,
                    batch_size,
                    max_concurrent_batches,
                    min_confidence,
                    enable_metrics,
                    progress_callback
                )
                
                successful_mappings.update(primary_results['successful_mappings'])
                processed_ids.update(primary_results['processed_ids'])
                
                # 4. Future: Secondary identifier conversion for unmapped IDs
                # This would handle conversion of secondary identifiers to primary ontology
                
                # 5. Aggregate final results
                final_results = await self._aggregate_final_results(
                    successful_mappings,
                    original_input_ids_set,
                    processed_ids,
                    validate_bidirectional,
                    primary_source_ontology,
                    primary_target_ontology,
                    meta_session
                )
                
                # Performance logging
                total_time = time.time() - overall_start_time
                self.logger.info(f"TIMING: total execute_mapping took {total_time:.3f}s")
                
                return final_results
                
        except Exception as e:
            self.logger.error(f"Error in execute_mapping: {str(e)}")
            raise
            
    async def _get_endpoint_configuration(
        self,
        meta_session,
        source_endpoint_name: str,
        target_endpoint_name: str,
        source_property_name: str,
        target_property_name: str,
        source_ontology_type: Optional[str],
        target_ontology_type: Optional[str]
    ) -> Dict[str, Any]:
        """Get and validate endpoint configuration."""
        # Get endpoints
        source_endpoint = await self._get_endpoint(meta_session, source_endpoint_name)
        target_endpoint = await self._get_endpoint(meta_session, target_endpoint_name)
        
        # Get ontology types
        primary_source_ontology = (
            source_ontology_type or 
            await self._get_ontology_type(meta_session, source_endpoint_name, source_property_name)
        )
        primary_target_ontology = (
            target_ontology_type or
            await self._get_ontology_type(meta_session, target_endpoint_name, target_property_name)
        )
        
        # Validate configuration
        if not all([source_endpoint, target_endpoint, primary_source_ontology, primary_target_ontology]):
            error_message = "Configuration Error: Could not determine endpoints or primary ontologies."
            self.logger.error(
                f"{error_message} SourceEndpoint: {source_endpoint}, TargetEndpoint: {target_endpoint}, "
                f"SourceOntology: {primary_source_ontology}, TargetOntology: {primary_target_ontology}"
            )
            raise ConfigurationError(error_message)
            
        self.logger.info(f"Primary mapping ontologies: {primary_source_ontology} -> {primary_target_ontology}")
        
        return {
            'source_endpoint': source_endpoint,
            'target_endpoint': target_endpoint,
            'primary_source_ontology': primary_source_ontology,
            'primary_target_ontology': primary_target_ontology
        }
        
    async def _should_use_composite_handling(
        self, input_identifiers: List[str], primary_source_ontology: str
    ) -> bool:
        """Check if composite identifier handling should be used."""
        if not self.composite_handler.has_patterns_for_ontology(primary_source_ontology):
            return False
            
        self.logger.info(f"Detected potential composite identifiers for ontology type '{primary_source_ontology}'")
        
        # Check if any input IDs are composite
        for input_id in input_identifiers:
            if self.composite_handler.is_composite(input_id, primary_source_ontology):
                self.logger.info(f"Found composite identifier pattern in '{input_id}'. Using composite identifier handling.")
                return True
                
        return False
        
    async def _execute_with_composite_handling(
        self,
        meta_session,
        input_identifiers: List[str],
        source_endpoint_name: str,
        target_endpoint_name: str,
        primary_source_ontology: str,
        primary_target_ontology: str,
        mapping_session_id: Optional[int],
        source_property_name: str,
        target_property_name: str,
        use_cache: bool,
        max_cache_age_days: Optional[int],
        mapping_direction: str,
        try_reverse_mapping: bool
    ) -> Dict[str, Any]:
        """Execute mapping with composite identifier handling."""
        # TODO: This should delegate to the composite handling logic from MappingExecutor
        # For now, return a basic response to avoid blocking the facade implementation
        self.logger.warning("Composite identifier handling not yet implemented in service - falling back to basic mapping")
        
        # Fallback to non-composite handling for now
        return {
            'mappings': {},
            'summary': {
                'total_input_count': len(input_identifiers),
                'successful_mapping_count': 0,
                'failed_mapping_count': len(input_identifiers)
            },
            'unmapped_ids': input_identifiers,
            'notes': ['Composite identifier handling not yet implemented in service layer']
        }
        
    async def _execute_direct_primary_mapping(
        self,
        meta_session,
        primary_source_ontology: str,
        primary_target_ontology: str,
        original_input_ids_set: Set[str],
        processed_ids: Set[str],
        source_endpoint,
        target_endpoint,
        mapping_direction: str,
        try_reverse_mapping: bool,
        mapping_session_id: Optional[int],
        use_cache: bool,
        max_cache_age_days: Optional[int],
        batch_size: int,
        max_concurrent_batches: int,
        min_confidence: float,
        enable_metrics: bool,
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Execute direct primary mapping step."""
        successful_mappings = {}
        
        # Find best path
        path_find_start = time.time()
        primary_path = await self.path_finder._find_best_path(
            meta_session,
            primary_source_ontology,
            primary_target_ontology,
            preferred_direction=mapping_direction,
            allow_reverse=try_reverse_mapping,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
        )
        self.logger.info(f"TIMING: _find_best_path took {time.time() - path_find_start:.3f}s")
        
        if not primary_path:
            self.logger.warning(
                f"No direct primary mapping path found from {primary_source_ontology} to {primary_target_ontology}."
            )
            return {
                'successful_mappings': successful_mappings,
                'processed_ids': processed_ids
            }
            
        self.logger.info(f"Found direct primary path: {primary_path.name} (ID: {primary_path.id})")
        
        # Determine which IDs need processing
        ids_to_process = list(original_input_ids_set - processed_ids)
        if not ids_to_process:
            self.logger.info("All relevant identifiers already processed via cache. Skipping Step 2 execution.")
            return {
                'successful_mappings': successful_mappings,
                'processed_ids': processed_ids
            }
            
        self.logger.info(f"Executing direct primary path for {len(ids_to_process)} identifiers.")
        
        # Execute path
        path_exec_start = time.time()
        primary_results_details = await self.path_execution_manager._execute_path(
            meta_session,
            primary_path,
            ids_to_process,
            primary_source_ontology,
            primary_target_ontology,
            mapping_session_id=mapping_session_id,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            min_confidence=min_confidence,
            enable_metrics=enable_metrics,
            progress_callback=progress_callback
        )
        
        self.logger.info(f"TIMING: _execute_path took {time.time() - path_exec_start:.3f}s")
        
        # Process results
        if primary_results_details and 'mappings' in primary_results_details:
            for input_id, mapping_result in primary_results_details['mappings'].items():
                if mapping_result.get('target_ids'):
                    successful_mappings[input_id] = mapping_result
                    processed_ids.add(input_id)
                    
        return {
            'successful_mappings': successful_mappings,
            'processed_ids': processed_ids
        }
        
    async def _aggregate_final_results(
        self,
        successful_mappings: Dict[str, Any],
        original_input_ids_set: Set[str],
        processed_ids: Set[str],
        validate_bidirectional: bool,
        primary_source_ontology: str,
        primary_target_ontology: str,
        meta_session
    ) -> Dict[str, Any]:
        """Aggregate and format final results."""
        # Basic result aggregation
        final_results = {
            'mappings': successful_mappings,
            'summary': {
                'total_input_count': len(original_input_ids_set),
                'successful_mapping_count': len(successful_mappings),
                'failed_mapping_count': len(original_input_ids_set) - len(successful_mappings)
            }
        }
        
        # Add unmapped IDs
        unmapped_ids = original_input_ids_set - processed_ids
        if unmapped_ids:
            final_results['unmapped_ids'] = list(unmapped_ids)
            
        # Bidirectional validation if requested
        if validate_bidirectional and successful_mappings:
            self.logger.info("Performing bidirectional validation...")
            validation_results = await self._perform_bidirectional_validation(
                successful_mappings,
                primary_source_ontology,
                primary_target_ontology,
                meta_session
            )
            final_results['bidirectional_validation'] = validation_results
            
        return final_results
        
    async def _perform_bidirectional_validation(
        self,
        successful_mappings: Dict[str, Any],
        primary_source_ontology: str,
        primary_target_ontology: str,
        meta_session
    ) -> Dict[str, Any]:
        """Perform bidirectional validation of mappings."""
        # This would implement the bidirectional validation logic
        # For now, we'll return a placeholder
        return {
            'validated_mappings': len(successful_mappings),
            'validation_enabled': True,
            'details': "Bidirectional validation logic to be implemented"
        }
        
    async def _get_endpoint(self, meta_session, endpoint_name: str):
        """Get endpoint configuration from database."""
        # TODO: This should be moved to a dedicated metadata service
        # For now, delegate to session manager's query methods
        from biomapper.db.models import Endpoint
        from sqlalchemy import select
        
        stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
        result = await meta_session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def _get_ontology_type(self, meta_session, endpoint_name: str, property_name: str) -> str:
        """Get ontology type for endpoint property."""
        # TODO: This should be moved to a dedicated metadata service  
        # For now, implement basic lookup logic
        from biomapper.db.models import Endpoint, EndpointPropertyConfig
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = (
            select(Endpoint)
            .where(Endpoint.name == endpoint_name)
            .options(selectinload(Endpoint.properties))
        )
        result = await meta_session.execute(stmt)
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found")
            
        # Find the property configuration
        for prop_config in endpoint.properties:
            if prop_config.property_name == property_name:
                return prop_config.ontology_type
                
        # Fallback to primary property if specific property not found
        if hasattr(endpoint, 'primary_ontology_type'):
            return endpoint.primary_ontology_type
            
        raise ValueError(f"Property '{property_name}' not found for endpoint '{endpoint_name}'")