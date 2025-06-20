"""
ResultAggregationService - Service for aggregating mapping results into MappingResultBundle.

This service extracts the final result aggregation logic from MappingExecutor.execute_mapping,
providing a clean separation of concerns for result bundling and statistics calculation.
"""

import logging
from typing import Dict, List, Set, Any, Optional

from biomapper.core.models.result_bundle import MappingResultBundle
from biomapper.db.cache_models import PathExecutionStatus


class ResultAggregationService:
    """
    Service responsible for aggregating mapping results and creating MappingResultBundle.
    
    This service takes raw mapping results from the execution process and packages them
    into a comprehensive MappingResultBundle with proper statistics and provenance.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the ResultAggregationService.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def aggregate_mapping_results(
        self,
        successful_mappings: Dict[str, Dict[str, Any]],
        original_input_ids: List[str],
        processed_ids: Set[str],
        strategy_name: str = "mapping_execution",
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate mapping results, adding entries for unmapped identifiers.
        
        This method takes the successful mappings and ensures all original input
        identifiers have an entry in the final results, adding "no mapping found"
        entries for any identifiers that were not successfully processed.
        
        Args:
            successful_mappings: Dictionary of successfully mapped identifiers
            original_input_ids: Original list of input identifiers
            processed_ids: Set of identifiers that were processed (successfully or not)
            strategy_name: Name of the mapping strategy
            source_ontology_type: Source ontology type
            target_ontology_type: Target ontology type
            
        Returns:
            Complete mapping results dictionary with entries for all input identifiers
        """
        self.logger.info("Aggregating final mapping results")
        
        # Start with successful mappings
        final_results = successful_mappings.copy()
        
        # Convert input list to set for efficient lookup
        original_input_ids_set = set(original_input_ids)
        
        # Add entries for unmapped identifiers
        unmapped_count = 0
        for input_id in original_input_ids_set:
            if input_id not in processed_ids:
                # Create a "no mapping found" entry
                final_results[input_id] = self._create_unmapped_entry(input_id)
                unmapped_count += 1
        
        self.logger.info(
            f"Aggregation complete. Successfully processed {len(processed_ids)}/{len(original_input_ids_set)} inputs. "
            f"({unmapped_count} unmapped)"
        )
        
        return final_results
    
    def aggregate_error_results(
        self,
        successful_mappings: Dict[str, Dict[str, Any]],
        original_input_ids: List[str],
        processed_ids: Set[str],
        error: Exception,
        error_status: PathExecutionStatus = PathExecutionStatus.ERROR,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate results when an error occurred during mapping execution.
        
        This method ensures partial results are preserved while marking unprocessed
        identifiers with appropriate error status.
        
        Args:
            successful_mappings: Dictionary of successfully mapped identifiers before error
            original_input_ids: Original list of input identifiers
            processed_ids: Set of identifiers that were processed before error
            error: The exception that occurred
            error_status: Status to use for error entries
            
        Returns:
            Complete mapping results dictionary with error entries for unprocessed identifiers
        """
        self.logger.warning("Aggregating partial results due to error during execution")
        
        # Start with successful mappings
        final_results = successful_mappings.copy()
        
        # Convert input list to set for efficient lookup
        original_input_ids_set = set(original_input_ids)
        
        # Add error entries for unprocessed identifiers
        error_count = 0
        for input_id in original_input_ids_set:
            if input_id not in processed_ids:
                # Create an error entry
                final_results[input_id] = self._create_error_entry(input_id, error, error_status)
                error_count += 1
        
        self.logger.warning(
            f"Returning partial results due to error. {error_count} inputs potentially affected."
        )
        
        return final_results
    
    def create_result_bundle_from_dict(
        self,
        mapping_results: Dict[str, Dict[str, Any]],
        strategy_name: str,
        initial_identifiers: List[str],
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> MappingResultBundle:
        """
        Create a MappingResultBundle from aggregated mapping results.
        
        This method converts a dictionary of mapping results into a properly
        structured MappingResultBundle with statistics and metadata.
        
        Args:
            mapping_results: Dictionary of mapping results
            strategy_name: Name of the mapping strategy
            initial_identifiers: Original input identifiers
            source_ontology_type: Source ontology type
            target_ontology_type: Target ontology type
            execution_metadata: Optional metadata about the execution
            
        Returns:
            MappingResultBundle containing the results and statistics
        """
        # Create the result bundle
        result_bundle = MappingResultBundle(
            strategy_name=strategy_name,
            initial_identifiers=initial_identifiers,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
        )
        
        # Calculate statistics
        total_count = len(mapping_results)
        successful_count = sum(
            1 for result in mapping_results.values()
            if result.get("status") == PathExecutionStatus.SUCCESS.value
        )
        failed_count = sum(
            1 for result in mapping_results.values()
            if result.get("status") in [
                PathExecutionStatus.NO_MAPPING_FOUND.value,
                PathExecutionStatus.ERROR.value,
                PathExecutionStatus.FAILED.value,
            ]
        )
        
        # Add execution summary step
        result_bundle.add_step_result(
            step_id="mapping_execution",
            step_description="Complete mapping execution",
            action_type="execute_mapping",
            input_identifiers=initial_identifiers,
            output_identifiers=[
                result["source_identifier"]
                for result in mapping_results.values()
                if result.get("target_identifiers") is not None
            ],
            status="completed",
            details={
                "total_inputs": total_count,
                "successful_mappings": successful_count,
                "failed_mappings": failed_count,
                "execution_metadata": execution_metadata or {},
            },
        )
        
        # Finalize the bundle
        result_bundle.finalize(status="completed")
        
        return result_bundle
    
    def _create_unmapped_entry(self, identifier: str) -> Dict[str, Any]:
        """
        Create a standard entry for an unmapped identifier.
        
        Args:
            identifier: The unmapped identifier
            
        Returns:
            Dictionary entry for the unmapped identifier
        """
        return {
            "source_identifier": identifier,
            "target_identifiers": None,
            "status": PathExecutionStatus.NO_MAPPING_FOUND.value,
            "message": "No successful mapping found via direct or secondary paths.",
            "confidence_score": 0.0,
            "mapping_path_details": None,
            "hop_count": None,
            "mapping_direction": None,
        }
    
    def _create_error_entry(
        self,
        identifier: str,
        error: Exception,
        status: PathExecutionStatus = PathExecutionStatus.ERROR,
    ) -> Dict[str, Any]:
        """
        Create a standard entry for an identifier that encountered an error.
        
        Args:
            identifier: The identifier that encountered an error
            error: The exception that occurred
            status: The error status to use
            
        Returns:
            Dictionary entry for the error case
        """
        return {
            "source_identifier": identifier,
            "target_identifiers": None,
            "status": status.value,
            "message": f"Mapping failed due to error: {str(error)}",
            "confidence_score": 0.0,
            "mapping_path_details": None,
            "hop_count": None,
            "mapping_direction": None,
            "error_details": {
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        }