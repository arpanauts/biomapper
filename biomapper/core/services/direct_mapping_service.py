"""
Direct Mapping Service for biomapper.

This service handles the initial direct mapping logic that attempts to map identifiers
between source and target endpoints using a primary shared ontology. This is the first
major step in the mapping process, extracted from the monolithic execute_mapping method.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Set, Union
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.db.models import MappingPath, Endpoint


class DirectMappingService:
    """
    Service responsible for executing direct mapping between source and target ontologies.
    
    This service encapsulates the logic for finding and executing a direct mapping path
    between the primary source and target ontologies. It was extracted from the 
    MappingExecutor.execute_mapping method to improve modularity and maintainability.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the DirectMappingService.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def execute_direct_mapping(
        self,
        meta_session: AsyncSession,
        path_finder,
        path_executor,
        primary_source_ontology: str,
        primary_target_ontology: str,
        original_input_ids_set: Set[str],
        processed_ids: Set[str],
        successful_mappings: Dict[str, Any],
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
        source_endpoint: Optional[Endpoint] = None,
        target_endpoint: Optional[Endpoint] = None,
        mapping_session_id: Optional[str] = None,
        batch_size: int = 100,
        max_hop_count: int = 5,
        min_confidence: float = 0.0,
        max_concurrent_batches: int = 5
    ) -> Dict[str, Any]:
        """
        Execute direct primary mapping between source and target ontologies.
        
        This method attempts to find and execute a direct mapping path from the primary
        source ontology to the primary target ontology. It processes only those identifiers
        that haven't been processed yet (not found in cache or previous steps).
        
        Args:
            meta_session: SQLAlchemy async session for metadata queries
            path_finder: Service for finding mapping paths
            path_executor: Service for executing mapping paths
            primary_source_ontology: Primary ontology type for the source
            primary_target_ontology: Primary ontology type for the target
            original_input_ids_set: Set of all input identifiers to process
            processed_ids: Set of identifiers already processed
            successful_mappings: Dictionary to store successful mapping results
            mapping_direction: Direction preference ("forward" or "reverse")
            try_reverse_mapping: Whether to attempt reverse mapping
            source_endpoint: Source endpoint entity
            target_endpoint: Target endpoint entity
            mapping_session_id: ID of the current mapping session
            batch_size: Number of identifiers to process per batch
            max_hop_count: Maximum number of hops allowed in path
            min_confidence: Minimum confidence threshold for mappings
            max_concurrent_batches: Maximum number of concurrent batches
            
        Returns:
            Dictionary containing:
                - path_found: Whether a direct path was found
                - path_name: Name of the path if found
                - path_id: ID of the path if found
                - newly_mapped_count: Number of newly mapped identifiers
                - execution_time: Time taken to execute the mapping
        """
        self.logger.info("--- Attempting Direct Primary Mapping ---")
        start_time = time.time()
        
        result = {
            "path_found": False,
            "path_name": None,
            "path_id": None,
            "newly_mapped_count": 0,
            "execution_time": 0.0
        }
        
        # Find the best direct path
        path_find_start = time.time()
        primary_path = await path_finder.find_best_path(
            meta_session,
            primary_source_ontology,
            primary_target_ontology,
            bidirectional=try_reverse_mapping,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint
        )
        self.logger.info(f"TIMING: find_best_path took {time.time() - path_find_start:.3f}s")
        
        if not primary_path:
            self.logger.warning(
                f"No direct primary mapping path found from {primary_source_ontology} to {primary_target_ontology}."
            )
            result["execution_time"] = time.time() - start_time
            return result
        
        # Path found - update result
        result["path_found"] = True
        result["path_name"] = primary_path.name
        result["path_id"] = primary_path.id
        
        self.logger.info(f"Found direct primary path: {primary_path.name} (ID: {primary_path.id})")
        
        # Determine which IDs need processing (not found in cache or previous steps)
        ids_to_process = list(original_input_ids_set - processed_ids)
        
        if not ids_to_process:
            self.logger.info("All relevant identifiers already processed via cache. Skipping direct mapping execution.")
            result["execution_time"] = time.time() - start_time
            return result
        
        self.logger.info(f"Executing direct primary path for {len(ids_to_process)} identifiers.")
        
        # Execute the path
        path_exec_start = time.time()
        primary_results_details = await path_executor._execute_path(
            meta_session,
            primary_path,
            ids_to_process,
            primary_source_ontology,
            primary_target_ontology,
            mapping_session_id=mapping_session_id,
            batch_size=batch_size,
            max_hop_count=max_hop_count,
            filter_confidence=min_confidence,
            max_concurrent_batches=max_concurrent_batches
        )
        self.logger.info(f"TIMING: _execute_path took {time.time() - path_exec_start:.3f}s")
        
        # Process results from direct path
        if primary_results_details:
            num_newly_mapped = 0
            for source_id, result_data in primary_results_details.items():
                # Ensure result_data is not None and contains target_identifiers
                if result_data and result_data.get("target_identifiers") is not None:
                    if source_id not in successful_mappings:
                        successful_mappings[source_id] = result_data
                        processed_ids.add(source_id)
                        num_newly_mapped += 1
                    else:
                        # Handle potential updates or conflicts if needed
                        self.logger.debug(
                            f"Identifier {source_id} already mapped, skipping update from direct path."
                        )
            
            result["newly_mapped_count"] = num_newly_mapped
            self.logger.info(f"Direct primary path execution mapped {num_newly_mapped} additional identifiers.")
        else:
            self.logger.info("Direct primary path execution yielded no new mappings.")
        
        result["execution_time"] = time.time() - start_time
        return result