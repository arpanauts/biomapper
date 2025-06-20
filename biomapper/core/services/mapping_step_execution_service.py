"""
Service for executing individual mapping steps.

This service encapsulates the logic for executing a single step of a mapping path,
including client interaction, caching, and error handling.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple

from biomapper.core.exceptions import (
    ClientError,
    ClientExecutionError,
    ClientInitializationError,
    ErrorCode,
)
from biomapper.db.models import MappingPathStep


class MappingStepExecutionService:
    """Service for executing individual mapping steps."""
    
    def __init__(self, client_manager, cache_manager=None, logger=None):
        """
        Initialize the mapping step execution service.
        
        Args:
            client_manager: Manager for loading and managing mapping clients
            cache_manager: Optional cache manager for caching results
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.client_manager = client_manager
        self.cache_manager = cache_manager
        
    async def execute_step(
        self,
        step: MappingPathStep,
        input_values: List[str],
        is_reverse: bool = False
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Execute a single mapping step, handling reverse execution if needed.
        
        Args:
            step: The mapping step to execute
            input_values: List of input identifiers
            is_reverse: If True, execute in reverse direction (output→input)
            
        Returns:
            Dictionary mapping input IDs to tuples: (list of output IDs, successful source component ID or None)
        """
        step_start = time.time()
        self.logger.debug(f"TIMING: execute_step started for {len(input_values)} identifiers")
        
        try:
            client_load_start = time.time()
            client_instance = await self.client_manager.get_client_instance(step.mapping_resource)
            self.logger.debug(f"TIMING: get_client_instance took {time.time() - client_load_start:.3f}s")
        except ClientInitializationError:
            # Propagate initialization errors directly
            raise
            
        try:
            if not is_reverse:
                # Normal forward execution
                return await self._execute_forward_mapping(
                    client_instance, step, input_values, step_start
                )
            else:
                # Reverse execution
                return await self._execute_reverse_mapping(
                    client_instance, step, input_values, step_start
                )
                
        except ClientError as ce:
            self._handle_client_error(ce, step)
        except Exception as e:
            self._handle_unexpected_error(e, step)
            
    async def _execute_forward_mapping(
        self,
        client_instance,
        step: MappingPathStep,
        input_values: List[str],
        step_start: float
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Execute forward mapping through the client."""
        self.logger.debug(
            f"execute_step calling {client_instance.__class__.__name__}.map_identifiers with {len(input_values)} identifiers."
        )
        if len(input_values) < 10:
            self.logger.debug(f"  Input sample: {input_values}")
        else:
            self.logger.debug(f"  Input sample: {input_values[:10]}...")
            
        mapping_start = time.time()
        
        # Check if we should bypass cache for specific clients
        client_config = None
        if (hasattr(client_instance, '__class__') and 
            client_instance.__class__.__name__ == 'UniProtHistoricalResolverClient' and
            os.environ.get('BYPASS_UNIPROT_CACHE', '').lower() == 'true'):
            self.logger.info("Bypassing cache for UniProtHistoricalResolverClient")
            client_config = {'bypass_cache': True}
            
        client_results_from_map_identifiers = await client_instance.map_identifiers(
            input_values, config=client_config
        )
        self.logger.debug(f"TIMING: client.map_identifiers took {time.time() - mapping_start:.3f}s")
        
        processed_step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        
        # Process client results
        for input_id, client_tuple in client_results_from_map_identifiers.items():
            mapped_ids_list, _ = client_tuple  # metadata_or_component_id is the second part
            
            if mapped_ids_list:
                processed_step_results[input_id] = (mapped_ids_list, None)
            else:
                processed_step_results[input_id] = (None, None)
                
        # Ensure all input values have an entry
        for val in input_values:
            if val not in processed_step_results:
                processed_step_results[val] = (None, None)
                
        self.logger.debug(f"TIMING: execute_step completed in {time.time() - step_start:.3f}s")
        return processed_step_results
        
    async def _execute_reverse_mapping(
        self,
        client_instance,
        step: MappingPathStep,
        input_values: List[str],
        step_start: float
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Execute reverse mapping through the client."""
        # Try specialized reverse method first
        if hasattr(client_instance, "reverse_map_identifiers"):
            self.logger.debug(
                f"Using specialized reverse_map_identifiers method for {step.mapping_resource.name}"
            )
            client_results_dict = await client_instance.reverse_map_identifiers(input_values)
            
            processed_step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
            
            successful_mappings = client_results_dict.get('input_to_primary', {})
            for input_id, mapped_primary_id in successful_mappings.items():
                processed_step_results[input_id] = ([mapped_primary_id], None)
                
            errors_list = client_results_dict.get('errors', [])
            for error_detail in errors_list:
                error_input_id = error_detail.get('input_id')
                if error_input_id:
                    processed_step_results[error_input_id] = (None, None)
                    
            # Ensure all input values have an entry
            for val in input_values:
                if val not in processed_step_results:
                    processed_step_results[val] = (None, None)
                    
            self.logger.debug(f"TIMING: execute_step (reverse) completed in {time.time() - step_start:.3f}s")
            return processed_step_results
            
        # Fall back to inverting forward mapping results
        self.logger.info(
            f"Executing reverse mapping for {step.mapping_resource.name} by inverting forward results"
        )
        forward_results_dict = await client_instance.map_identifiers(input_values)
        
        # Invert the mapping
        inverted_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        
        for client_source_id, client_target_id in forward_results_dict.get('input_to_primary', {}).items():
            if client_target_id in input_values:
                if client_target_id not in inverted_results:
                    inverted_results[client_target_id] = ([], None)
                if inverted_results[client_target_id][0] is not None:
                    inverted_results[client_target_id][0].append(client_source_id)
                else:
                    inverted_results[client_target_id] = ([client_source_id], None)
                    
        # Add empty results for unmapped values
        for original_step_input_id in input_values:
            if original_step_input_id not in inverted_results:
                inverted_results[original_step_input_id] = (None, None)
                
        return inverted_results
        
    def _handle_client_error(self, ce: ClientError, step: MappingPathStep):
        """Handle client errors during step execution."""
        self.logger.error(
            f"ClientError during execution step for {step.mapping_resource.name}: {ce}",
            exc_info=False,
        )
        
        # Ensure details is always a dictionary
        details_dict = (
            ce.details
            if isinstance(ce.details, dict)
            else {"error_message": str(ce.details)}
        )
        
        raise ClientExecutionError(
            f"Client error during step execution: {ce.message}",
            client_name=step.mapping_resource.name,
            details=details_dict,
        ) from ce
        
    def _handle_unexpected_error(self, e: Exception, step: MappingPathStep):
        """Handle unexpected errors during step execution."""
        error_details = {"original_exception": str(e)}
        self.logger.error(
            f"Unexpected error during execution step for {step.mapping_resource.name}: {e}",
            exc_info=True,
        )
        raise ClientExecutionError(
            "Unexpected error during step execution",
            client_name=step.mapping_resource.name,
            details=error_details,
        ) from e