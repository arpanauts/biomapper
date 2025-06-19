"""
MappingPathExecutionService: Service for executing individual mapping paths.

This service handles the execution of a single, complete mapping path including
step execution, result processing, and provenance tracking. It provides a focused
interface for path execution mechanics, separated from the higher-level mapping
orchestration logic.
"""

import asyncio
import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Tuple, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..engine_components.cache_manager import CacheManager
from ..engine_components.client_manager import ClientManager
from ...db.models import MappingPath, MappingPathStep
from ..exceptions import ClientInitializationError, MappingExecutionError
from ...db.cache_models import PathExecutionStatus


class MappingPathExecutionService:
    """
    Service responsible for executing individual mapping paths.
    
    This service handles:
    - Execution of a given mapping path for a batch of identifiers
    - Interaction with ClientManager to get client instances for each step
    - Processing results from each step
    - Handling bidirectional validation if requested
    - Calculating confidence scores for mappings
    - Assembling final MappingResultBundle with detailed provenance
    """
    
    def __init__(
        self,
        session_manager,
        client_manager: ClientManager,
        cache_manager: CacheManager,
        path_finder,
        path_execution_manager,
        composite_handler,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the MappingPathExecutionService.
        
        Args:
            session_manager: Database session manager
            client_manager: ClientManager instance for getting client instances
            cache_manager: CacheManager instance for caching results
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
        # Store reference to executor for _execute_mapping_step delegation
        self._executor = None
    
    def set_executor(self, executor):
        """Set reference to MappingExecutor for delegation."""
        self._executor = executor
    
    async def execute_path(
        self,
        path: Union[MappingPath, "ReversiblePath"],
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        batch_size: int = 250,
        max_hop_count: Optional[int] = None,
        filter_confidence: float = 0.0,
        max_concurrent_batches: int = 5
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Execute a mapping path for a list of identifiers.
        
        Args:
            path: The mapping path to execute
            input_identifiers: List of identifiers to map
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            mapping_session_id: Optional ID for the mapping session
            execution_context: Optional execution context for logging
            batch_size: Size of batches for processing large input sets
            max_hop_count: Maximum number of hops to allow (skip longer paths)
            filter_confidence: Minimum confidence threshold for results
            max_concurrent_batches: Maximum number of batches to process concurrently
            
        Returns:
            Dictionary mapping input identifiers to their results
        """
        # Skip execution if max_hop_count is specified and this path exceeds it
        path_hop_count = len(path.steps) if hasattr(path, "steps") and path.steps else 1
        if max_hop_count is not None and path_hop_count > max_hop_count:
            self.logger.info(f"Skipping path {path.id} with {path_hop_count} hops (exceeds max_hop_count of {max_hop_count})")
            return {input_id: {
                "source_identifier": input_id,
                "target_identifiers": None,
                "mapped_value": None,
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
                    path_execution_start = datetime.now(timezone.utc).isoformat()
                    
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
                            
                            step_results = await self._executor._execute_mapping_step(
                                step=step,
                                input_values=input_values_for_step,
                                is_reverse=is_reverse_execution
                            )
                            
                            self.logger.info(f"EXEC_PATH_DEBUG ({path.name}): Step '{step.id}', step_results: {step_results}")
                            
                            # Process step results and update execution progress
                            next_step_input_ids = self._process_step_results(
                                step_results, execution_progress, step_index, steps_to_execute,
                                step_id, step_name, step, step_start_time
                            )
                            
                            # Update the input IDs for the next step
                            step_input_ids = next_step_input_ids
                            
                            self.logger.debug(f"Step {step_id} completed with {len(next_step_input_ids)} output IDs")
                            
                        except Exception as e:
                            self.logger.error(f"Error executing step {step_id}: {str(e)}", exc_info=True)
                            # We continue with the next step to see if partial results can be obtained
                    
                    # Transform the results using the processed execution progress
                    batch_results = self._process_path_results(
                        execution_progress, path, source_ontology, target_ontology
                    )
                    
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
                        "mapped_value": None,
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
                    "mapped_value": None,
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
        
        return combined_results
    
    def _process_step_results(
        self,
        step_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]],
        execution_progress: Dict[str, Dict[str, Any]],
        step_index: int,
        steps_to_execute: List[MappingPathStep],
        step_id: str,
        step_name: str,
        step: MappingPathStep,
        step_start_time: float
    ) -> set:
        """
        Process the results from a mapping step and update execution progress.
        
        Returns:
            Set of input IDs for the next step
        """
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
                            'resource_id': step.mapping_resource.id,
                            'client_name': getattr(step, 'client_name', 'Unknown'),
                            'input_ids': [original_input_id],
                            'output_ids': mapped_ids,
                            'resolved_historical': False,
                            'execution_time': time.time() - step_start_time
                        }
                        current_progress['provenance'][0]['steps_details'].append(step_detail)
                        execution_progress[original_input_id] = current_progress
            else:
                # For subsequent steps, check if any of our previous output IDs are inputs to the current step
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
                                'resource_id': step.mapping_resource.id,
                                'client_name': getattr(step, 'client_name', 'Unknown'),
                                'input_ids': input_ids_for_step,
                                'output_ids': all_mapped_ids, 
                                'resolved_historical': False,
                                'execution_time': time.time() - step_start_time
                            }
                            current_progress['provenance'][0]['steps_details'].append(step_detail)
                            execution_progress[original_input_id] = current_progress
        
        return next_step_input_ids
    
    def _process_path_results(
        self,
        raw_results: Dict[str, Dict[str, Any]],
        path: Union[MappingPath, "ReversiblePath"],
        source_ontology: str,
        target_ontology: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process raw path execution results into structured mapping results.
        
        Args:
            raw_results: Raw execution progress from path execution
            path: The mapping path that was executed
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            
        Returns:
            Dictionary of processed mapping results
        """
        processed_results = {}
        
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
            processed_results[original_id] = {
                "source_identifier": original_id,
                "target_identifiers": final_ids,
                "mapped_value": final_ids[0] if final_ids else None,
                "status": PathExecutionStatus.SUCCESS.value,
                "message": f"Successfully mapped via path: {path_name}",
                "confidence_score": confidence_score,
                "mapping_path_details": mapping_path_details,
                "hop_count": hop_count,
                "mapping_direction": mapping_direction,
                "mapping_source": self._determine_mapping_source(path_step_details)
            }
        
        return processed_results
    
    def _calculate_confidence_score(
        self, 
        result: Dict[str, Any], 
        hop_count: Optional[int], 
        is_reversed: bool, 
        path_step_details: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for a mapping result.
        
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
    
    def _create_mapping_path_details(
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
        Create structured mapping_path_details.
        
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
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": {}
        }
        
        # Add step details if available
        if path_step_details:
            details["steps"] = path_step_details
        
        # Add any additional metadata
        if additional_metadata:
            details["additional_metadata"] = additional_metadata
            
        return details
    
    def _determine_mapping_source(self, path_step_details: Dict[str, Any]) -> str:
        """
        Determine mapping source based on path step details.
        
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