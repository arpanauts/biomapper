"""
PathExecutionManager: Core component for executing mapping paths.

This module contains the PathExecutionManager class, which is responsible for
executing mapping paths with optimized batched processing. It handles the 
detailed execution of a single mapping path including batching, concurrency
management, and result aggregation.
"""

import asyncio
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.cache_manager import CacheManager
from biomapper.core.metamapper.entities import MappingPath, MappingPathStep
from biomapper.exceptions import ClientInitializationError, PathExecutionError
from biomapper.types import PathExecutionStatus
from biomapper.utils.logging import get_logger
from biomapper.utils.time_helpers import get_current_utc_time


class PathExecutionManager:
    """
    Manages the execution of mapping paths with optimized batched processing.
    
    This class is responsible for:
    - Batching of input identifiers
    - Concurrency management using asyncio.Semaphore
    - Iterating through MappingPathStep objects
    - Invoking appropriate client methods for each step
    - Handling results, errors, and filtering for each identifier within a batch
    - Aggregating results from all batches
    - Interacting with the CacheManager to store results
    """
    
    def __init__(
        self,
        metamapper_session_factory,
        cache_manager: CacheManager,
        logger=None,
        semaphore: Optional[asyncio.Semaphore] = None,
        max_retries: int = 3,
        retry_delay: int = 1,
        batch_size: int = 250,
        max_concurrent_batches: int = 5,
        enable_metrics: bool = True,
        load_client_func=None,
        execute_mapping_step_func=None,
        calculate_confidence_score_func=None,
        create_mapping_path_details_func=None,
        determine_mapping_source_func=None,
        track_mapping_metrics_func=None
    ):
        """
        Initialize the PathExecutionManager.
        
        Args:
            metamapper_session_factory: Factory for creating metamapper sessions
            cache_manager: CacheManager instance for caching results
            logger: Logger instance (optional)
            semaphore: Semaphore for concurrency control (optional)
            max_retries: Maximum number of retries for client calls
            retry_delay: Delay between retries in seconds
            batch_size: Size of batches for processing large input sets
            max_concurrent_batches: Maximum number of batches to process concurrently
            enable_metrics: Whether to enable metrics tracking
            load_client_func: Function to load clients (dependency injection)
            execute_mapping_step_func: Function to execute mapping steps (dependency injection)
            calculate_confidence_score_func: Function to calculate confidence scores
            create_mapping_path_details_func: Function to create mapping path details
            determine_mapping_source_func: Function to determine mapping source
            track_mapping_metrics_func: Function to track metrics
        """
        self.metamapper_session_factory = metamapper_session_factory
        self.cache_manager = cache_manager
        self.logger = logger or get_logger(__name__)
        self.semaphore = semaphore
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_metrics = enable_metrics
        
        # Dependency injection for functions that need access to MappingExecutor's context
        self._load_client = load_client_func
        self._execute_mapping_step = execute_mapping_step_func
        self._calculate_confidence_score = calculate_confidence_score_func or self._default_calculate_confidence_score
        self._create_mapping_path_details = create_mapping_path_details_func or self._default_create_mapping_path_details
        self._determine_mapping_source = determine_mapping_source_func or self._default_determine_mapping_source
        self.track_mapping_metrics = track_mapping_metrics_func
    
    async def execute_path(
        self,
        path: Union[MappingPath, "ReversiblePath"],
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        resource_clients: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
        batch_size: Optional[int] = None,
        max_hop_count: Optional[int] = None,
        filter_confidence: float = 0.0,
        max_concurrent_batches: Optional[int] = None
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Execute a mapping path or its reverse, with optimized batched processing.
        
        Args:
            path: The path to execute
            input_identifiers: List of identifiers to map
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            mapping_session_id: Optional ID for the mapping session
            execution_context: Optional execution context for logging
            resource_clients: Pre-initialized clients (optional)
            session: Database session (optional, for backward compatibility)
            batch_size: Size of batches for processing large input sets
            max_hop_count: Maximum number of hops to allow (skip longer paths)
            filter_confidence: Minimum confidence threshold for results
            max_concurrent_batches: Maximum number of batches to process concurrently
            
        Returns:
            Dictionary mapping input identifiers to their results
        """
        # Use provided values or defaults
        batch_size = batch_size or self.batch_size
        max_concurrent_batches = max_concurrent_batches or self.max_concurrent_batches
        
        # Skip execution if max_hop_count is specified and this path exceeds it
        path_hop_count = len(path.steps) if hasattr(path, "steps") and path.steps else 1
        if max_hop_count is not None and path_hop_count > max_hop_count:
            self.logger.info(f"Skipping path {path.id} with {path_hop_count} hops (exceeds max_hop_count of {max_hop_count})")
            return {input_id: {
                "source_identifier": input_id,
                "target_identifiers": None,
                "mapped_value": None,  # No mapping due to skip
                "status": PathExecutionStatus.SKIPPED.value,
                "message": f"Path skipped (hop count {path_hop_count} exceeds max_hop_count {max_hop_count})",
                "path_id": path.id,
                "path_name": path.name,
                "is_reverse": getattr(path, "is_reverse", False),
                "hop_count": path_hop_count,
                "mapping_direction": "reverse" if getattr(path, "is_reverse", False) else "forward",
                "confidence_score": 0.0
            } for input_id in input_identifiers}
            
        # Add performance tracking
        execution_start_time = time.time()
        metrics = {
            "path_id": path.id,
            "input_count": len(input_identifiers),
            "batch_size": batch_size,
            "max_concurrent_batches": max_concurrent_batches,
            "is_reverse": getattr(path, "is_reverse", False),
            "start_time": execution_start_time,
            "processing_times": {},
            "success_count": 0,
            "error_count": 0,
            "filtered_count": 0
        }
        
        self.logger.debug(f"Executing path {path.id} for {len(input_identifiers)} IDs with batch_size={batch_size}")
        
        # Convert input to a list (needed for batching)
        input_ids_list = list(set(input_identifiers))  # Deduplicate while preserving order
        
        # Create batches for processing
        batches = [input_ids_list[i:i+batch_size] for i in range(0, len(input_ids_list), batch_size)]
        self.logger.debug(f"Split {len(input_ids_list)} identifiers into {len(batches)} batches")
        
        # Initialize results dictionary to store combined results
        combined_results = {}
        
        # Create a semaphore to limit concurrent batch processing
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        # Define batch processing function with performance tracking
        async def process_batch(batch_index: int, batch_ids: List[str]):
            async with semaphore:
                batch_start_time = time.time()
                batch_metrics = {
                    "start_time": batch_start_time,
                    "batch_size": len(batch_ids),
                    "success_count": 0,
                    "error_count": 0,
                    "filtered_count": 0
                }
                
                self.logger.debug(f"Processing batch {batch_index+1}/{len(batches)} with {len(batch_ids)} identifiers")
                batch_set = set(batch_ids)
                
                try:
                    # Start timing the path execution
                    path_execution_start = get_current_utc_time()
                    
                    # Execute path steps directly for this batch
                    is_reverse_execution = getattr(path, 'is_reverse', False)
                    self.logger.debug(f"Executing {'reverse' if is_reverse_execution else 'forward'} path {path.id}")
                    
                    # Start with the initial input identifiers
                    current_input_ids = batch_set
                    self.logger.info(f"EXEC_PATH_DEBUG ({path.name}): Batch {batch_index+1} current_input_ids: {current_input_ids}")
                    # Dict to track execution progress: input_id -> {final_ids: List[str], provenance: List[Dict]}
                    execution_progress = {input_id: {
                        'final_ids': [],
                        'provenance': [{
                            'path_id': path.id,
                            'path_name': getattr(path, 'name', f"Path-{path.id}"),
                            'steps_details': []
                        }]
                    } for input_id in batch_ids}
                    
                    # Get the steps to execute (in correct order based on direction)
                    steps_to_execute = path.steps
                    if is_reverse_execution and hasattr(path, 'steps') and path.steps:
                        # For reverse paths, execute steps in reverse order
                        steps_to_execute = list(reversed(path.steps))
                    
                    # Track unique identifiers at each step to avoid duplicates
                    step_input_ids = set(current_input_ids)
                    
                    # Execute each step in the path
                    for step_index, step in enumerate(steps_to_execute):
                        step_start_time = time.time()
                        step_id = step.id if hasattr(step, 'id') else f"step_{step_index}"
                        step_name = step.name if hasattr(step, 'name') else f"Step {step_index}"
                        self.logger.debug(f"Executing step {step_id} ({step_name}) with {len(step_input_ids)} input IDs")
                        
                        if not step_input_ids:
                            self.logger.debug(f"No input IDs for step {step_id} - skipping")
                            break
                        
                        try:
                            # Execute the mapping step with the current set of input IDs
                            input_values_for_step = list(step_input_ids)
                            self.logger.info(f"EXEC_PATH_DEBUG ({path.name}): Step '{step.id}', inputs: {input_values_for_step}")
                            
                            step_results = await self._execute_mapping_step(
                                step=step,
                                input_values=input_values_for_step,
                                is_reverse=is_reverse_execution
                            )
                            
                            self.logger.info(f"EXEC_PATH_DEBUG ({path.name}): Step '{step.id}', step_results: {step_results}")
                            
                            # Track which original inputs connect to which outputs through this step
                            # and update provenance information
                            next_step_input_ids = set()
                            
                            # Go through all original input IDs still in the execution path
                            for original_input_id, progress_data in execution_progress.items():
                                current_progress = progress_data.copy()
                                
                                # For the first step, the input ID will be one of our original batch IDs
                                # For subsequent steps, we need to trace through previous mappings
                                if step_index == 0:
                                    if original_input_id in step_results:
                                        # Direct result for this original input ID
                                        mapped_ids, source_component = step_results[original_input_id]
                                        
                                        if mapped_ids:  # If mapping was successful
                                            # Add the mapped IDs to the next step's inputs
                                            next_step_input_ids.update(mapped_ids)
                                            
                                            # If this is the last step, these are our final results for this input
                                            if len(steps_to_execute) == 1:
                                                current_progress['final_ids'] = mapped_ids
                                            
                                            # Add step details to provenance
                                            step_detail = {
                                                'step_id': step_id,
                                                'step_name': step_name,
                                                'resource_id': step.mapping_resource.id, # Changed to .id
                                                'client_name': getattr(step, 'client_name', 'Unknown'),
                                                'input_ids': [original_input_id],
                                                'output_ids': mapped_ids,
                                                'resolved_historical': False,  # This would need to be set based on actual resolution
                                                'execution_time': time.time() - step_start_time
                                            }
                                            current_progress['provenance'][0]['steps_details'].append(step_detail)
                                            execution_progress[original_input_id] = current_progress
                                else:
                                    # For subsequent steps, we need to check if any of our previous output IDs
                                    # are inputs to the current step
                                    if 'provenance' in current_progress and current_progress['provenance']:
                                        previous_step_detail = current_progress['provenance'][0]['steps_details'][-1] if current_progress['provenance'][0]['steps_details'] else None
                                        
                                        if previous_step_detail and 'output_ids' in previous_step_detail:
                                            previous_output_ids = previous_step_detail['output_ids']
                                            
                                            # Check if any of our previous outputs were mapped in this step
                                            all_mapped_ids = []
                                            input_ids_for_step = []
                                            
                                            for prev_output_id in previous_output_ids:
                                                if prev_output_id in step_results:
                                                    # This previous output was mapped in this step
                                                    mapped_ids, source_component = step_results[prev_output_id]
                                                    
                                                    if mapped_ids:  # If mapping was successful
                                                        # Add to our running list for this original input
                                                        all_mapped_ids.extend(mapped_ids)
                                                        next_step_input_ids.update(mapped_ids)
                                                        input_ids_for_step.append(prev_output_id)
                                            
                                            # If we got any mappings for this original input in this step
                                            if all_mapped_ids:
                                                # If this is the last step, these are our final results
                                                if step_index == len(steps_to_execute) - 1:
                                                    current_progress['final_ids'] = all_mapped_ids
                                                
                                                # Add step details to provenance
                                                step_detail = {
                                                    'step_id': step_id,
                                                    'step_name': step_name,
                                                    'resource_id': step.mapping_resource.id, # Changed to .id
                                                    'client_name': getattr(step, 'client_name', 'Unknown'),
                                                    'input_ids': input_ids_for_step,
                                                    'output_ids': all_mapped_ids, 
                                                    'resolved_historical': False,  # Would need to be set based on actual resolution
                                                    'execution_time': time.time() - step_start_time
                                                }
                                                current_progress['provenance'][0]['steps_details'].append(step_detail)
                                                execution_progress[original_input_id] = current_progress
                            
                            # Update the input IDs for the next step
                            step_input_ids = next_step_input_ids
                            
                            self.logger.debug(f"Step {step_id} completed with {len(next_step_input_ids)} output IDs")
                            
                        except Exception as e:
                            self.logger.error(f"Error executing step {step_id}: {str(e)}", exc_info=True)
                            # We continue with the next step to see if partial results can be obtained
                    
                    # Now execution_progress contains our raw results
                    raw_results = execution_progress
                    
                    self.logger.info(f"EXEC_PATH_DEBUG ({path.name}): Batch {batch_index+1} final execution_progress: {execution_progress}")
                    
                    # Transform the results
                    batch_results = {}
                    for original_id, result_data in raw_results.items():
                        if not result_data or not result_data.get('final_ids'):
                            # No mapping found for this ID
                            continue
                        
                        # Extract the final mapped IDs
                        final_ids = result_data.get('final_ids', [])
                        
                        # Get provenance data (first entry if multiple exist)
                        provenance = result_data.get('provenance', [{}])[0]
                        
                        # Extract path details from provenance
                        path_id = provenance.get('path_id')
                        path_name = provenance.get('path_name')
                        steps_details = provenance.get('steps_details', [])
                        
                        # Check if any step involved historical ID resolution
                        resolved_historical = any(
                            step.get('resolved_historical', False) 
                            for step in steps_details
                        )
                        
                        # Calculate hop count (number of steps)
                        hop_count = len(steps_details)
                        
                        # Determine mapping direction
                        mapping_direction = "reverse" if getattr(path, 'is_reverse', False) else "forward"
                        
                        # Get detailed path step information for confidence calculation
                        path_step_details = {}
                        for i, step in enumerate(steps_details):
                            path_step_details[str(i)] = {
                                "resource_id": step.get("resource_id"),
                                "resource_name": step.get("client_name", ""),
                                "resolved_historical": step.get("resolved_historical", False)
                            }
                        
                        # Calculate confidence score
                        confidence_score = self._calculate_confidence_score(
                            {}, 
                            hop_count, 
                            getattr(path, 'is_reverse', False),
                            path_step_details
                        )
                        
                        self.logger.debug(f"Source: {original_id}, Hops: {hop_count}, Reversed: {getattr(path, 'is_reverse', False)}, Confidence: {confidence_score}")
                        
                        # Create mapping path details
                        mapping_path_details = self._create_mapping_path_details(
                            path_id=path_id,
                            path_name=path_name,
                            hop_count=hop_count,
                            mapping_direction=mapping_direction,
                            path_step_details=path_step_details,
                            additional_metadata={
                                "resolved_historical": resolved_historical,
                                "confidence_score": confidence_score,
                                "source_ontology": source_ontology,
                                "target_ontology": target_ontology
                            }
                        )
                        
                        # Build the result structure
                        batch_results[original_id] = {
                            "source_identifier": original_id,
                            "target_identifiers": final_ids,
                            "mapped_value": final_ids[0] if final_ids else None,  # First target ID is the primary mapped value
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": f"Successfully mapped via path: {path_name}",
                            "confidence_score": confidence_score,
                            "mapping_path_details": mapping_path_details,
                            "hop_count": hop_count,
                            "mapping_direction": mapping_direction,
                            "mapping_source": self._determine_mapping_source(path_step_details)
                        }
                    
                    return batch_results
                    
                except Exception as e:
                    # Record batch error in metrics
                    batch_metrics["error_count"] = len(batch_ids)
                    metrics["error_count"] += len(batch_ids)
                    batch_metrics["error"] = str(e)
                    batch_metrics["error_type"] = type(e).__name__
                    
                    error_time = time.time()
                    batch_metrics["total_time"] = error_time - batch_start_time
                    metrics["processing_times"][f"batch_{batch_index}"] = batch_metrics
                    
                    self.logger.error(f"Error executing batch {batch_index+1} of path {path.id}: {str(e)}", exc_info=True)
                    # Return failed results for each ID in this batch
                    return {input_id: {
                        "source_identifier": input_id,
                        "target_identifiers": None,
                        "mapped_value": None,  # No mapping due to error
                        "status": PathExecutionStatus.EXECUTION_ERROR.value,
                        "message": f"Error during path execution: {str(e)}",
                        "confidence_score": 0.0,
                        "mapping_direction": "reverse" if getattr(path, "is_reverse", False) else "forward",
                        "error_details": {
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    } for input_id in batch_ids}
                
                finally:
                    # Record batch completion metrics regardless of success/failure
                    batch_end_time = time.time()
                    batch_metrics["total_time"] = batch_end_time - batch_start_time
                    metrics["processing_times"][f"batch_{batch_index}"] = batch_metrics
        
        # Process batches concurrently
        batch_tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        batch_results_list = await asyncio.gather(*batch_tasks)
        
        # Combine all batch results
        for batch_result in batch_results_list:
            if batch_result:
                combined_results.update(batch_result)
        
        # Add error entries for any IDs not found in results
        missing_ids = 0
        for input_id in input_identifiers:
            if input_id not in combined_results:
                missing_ids += 1
                combined_results[input_id] = {
                    "source_identifier": input_id,
                    "target_identifiers": None,
                    "mapped_value": None,  # No mapping found
                    "status": PathExecutionStatus.NO_MAPPING_FOUND.value,
                    "message": f"No mapping found via path: {path.name}",
                    "confidence_score": 0.0,
                    "mapping_direction": "reverse" if getattr(path, 'is_reverse', False) else "forward",
                    "path_id": path.id,
                    "path_name": path.name
                }
        
        # Record final execution metrics
        execution_end_time = time.time()
        total_execution_time = execution_end_time - execution_start_time
        
        metrics["end_time"] = execution_end_time
        metrics["total_execution_time"] = total_execution_time
        metrics["missing_ids"] = missing_ids
        metrics["result_count"] = len(combined_results)
        
        # Log performance metrics
        success_rate = (metrics["success_count"] / len(input_identifiers) * 100) if input_identifiers else 0
        self.logger.info(
            f"Path {path.id} execution completed in {total_execution_time:.3f}s: "
            f"{metrics['success_count']}/{len(input_identifiers)} successful ({success_rate:.1f}%), "
            f"{metrics['error_count']} errors, {metrics['filtered_count']} filtered"
        )
        
        # If configured, send metrics to monitoring system
        if self.enable_metrics and self.track_mapping_metrics:
            try:
                await self.track_mapping_metrics("path_execution", metrics)
            except Exception as e:
                self.logger.warning(f"Failed to track metrics: {str(e)}")
        
        return combined_results
    
    # Default implementations for helper methods (used if not injected)
    def _default_calculate_confidence_score(
        self, 
        result: Dict[str, Any], 
        hop_count: Optional[int], 
        is_reversed: bool, 
        path_step_details: Dict[str, Any]
    ) -> float:
        """
        Default implementation of confidence score calculation.
        
        The confidence score is determined by:
        1. Existing score in the result (if provided)
        2. Number of hops in the mapping path
        3. Whether the path was executed in reverse
        4. Type of mapping resources used (e.g., direct API vs RAG)
        
        Args:
            result: The mapping result dictionary
            hop_count: Number of steps in the mapping path
            is_reversed: Whether the path was executed in reverse
            path_step_details: Detailed information about the path steps
            
        Returns:
            A confidence score between 0.0 and 1.0
        """
        # Check if result already has a confidence score
        if result.get("confidence_score") is not None:
            return result["confidence_score"]
        
        # Base confidence calculation from hop count
        if hop_count is not None:
            if hop_count <= 1:
                base_confidence = 0.95  # Direct mapping (highest confidence)
            elif hop_count == 2:
                base_confidence = 0.85  # 2-hop mapping (high confidence)
            else:
                # Decrease confidence for longer paths: 0.95 → 0.85 → 0.75 → 0.65 → ...
                base_confidence = max(0.15, 0.95 - ((hop_count - 1) * 0.1))
        else:
            base_confidence = 0.7  # Default if hop_count is unknown
        
        # Apply penalty for reverse paths
        if is_reversed:
            base_confidence = max(0.1, base_confidence - 0.1)
        
        # Apply additional adjustments based on resource types
        resource_types = []
        for step_key, step_info in path_step_details.items():
            if not isinstance(step_info, dict):
                continue
                
            # Check resource name for clues
            resource_name = step_info.get("resource_name", "").lower()
            client_path = step_info.get("resource_client", "").lower()
            
            # Determine source based on resource name or client path
            if "spoke" in resource_name or "spoke" in client_path:
                resource_types.append("spoke")
            elif "rag" in resource_name or "rag" in client_path:
                resource_types.append("rag")
            elif "llm" in resource_name or "llm" in client_path:
                resource_types.append("llm")
            elif "ramp" in resource_name or "ramp" in client_path:
                resource_types.append("ramp")
                
        # Apply adjustments for specific resources
        if "rag" in resource_types:
            base_confidence = max(0.1, base_confidence - 0.05)  # Small penalty for RAG-based mappings
        if "llm" in resource_types:
            base_confidence = max(0.1, base_confidence - 0.1)   # Larger penalty for LLM-based mappings
        
        return round(base_confidence, 2)  # Round to 2 decimal places for consistency
    
    def _default_create_mapping_path_details(
        self,
        path_id: int,
        path_name: str,
        hop_count: Optional[int],
        mapping_direction: str,
        path_step_details: Dict[str, Any],
        log_id: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Default implementation to create structured mapping_path_details.
        
        Args:
            path_id: The ID of the mapping path
            path_name: The name of the mapping path
            hop_count: Number of steps in the path
            mapping_direction: Direction of the mapping (forward, reverse, bidirectional)
            path_step_details: Detailed information about the path steps
            log_id: Optional ID of the execution log entry
            additional_metadata: Optional additional metadata to include
            
        Returns:
            A dictionary with structured path details ready to be serialized to JSON
        """
        # Initialize details with core information
        details = {
            "path_id": path_id,
            "path_name": path_name,
            "hop_count": hop_count,
            "direction": mapping_direction,
            "log_id": log_id,
            "execution_timestamp": datetime.utcnow().isoformat(),
            "steps": {}
        }
        
        # Add step details if available
        if path_step_details:
            details["steps"] = path_step_details
        
        # Add any additional metadata
        if additional_metadata:
            details["additional_metadata"] = additional_metadata
            
        return details
    
    def _default_determine_mapping_source(self, path_step_details: Dict[str, Any]) -> str:
        """
        Default implementation to determine mapping source.
        
        Args:
            path_step_details: Detailed information about the path steps
            
        Returns:
            A string indicating the mapping source (api, spoke, rag, etc.)
        """
        # Default source if we can't determine
        default_source = "api"
        
        # Check for empty details
        if not path_step_details:
            return default_source
            
        # Check each step for resource type clues
        for step_key, step_info in path_step_details.items():
            if not isinstance(step_info, dict):
                continue
                
            # Check resource name for clues
            resource_name = step_info.get("resource_name", "").lower()
            client_path = step_info.get("resource_client", "").lower()
            
            # Determine source based on resource name or client path
            if "spoke" in resource_name or "spoke" in client_path:
                return "spoke"
            elif "rag" in resource_name or "rag" in client_path:
                return "rag"
            elif "llm" in resource_name or "llm" in client_path:
                return "llm"
            elif "ramp" in resource_name or "ramp" in client_path:
                return "ramp"
                
        return default_source