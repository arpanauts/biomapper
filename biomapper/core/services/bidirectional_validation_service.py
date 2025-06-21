"""
Bidirectional Validation Service

This service handles the process of re-running mappings in the reverse direction 
to validate the initial results. It encapsulates the logic previously embedded 
in the MappingExecutor.execute_mapping method.
"""

import logging
from typing import Dict, Any, Set, Optional


class BidirectionalValidationService:
    """
    Service for performing bidirectional validation of mapping results.
    
    This validates forward mappings by running a reverse mapping and checking 
    if target IDs map back to their original source.
    """
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
    
    async def validate_mappings(
        self,
        mapping_executor: Any,  # Avoid circular import by using Any
        meta_session: Any,  # AsyncSession type
        successful_mappings: Dict[str, Dict[str, Any]],
        source_endpoint_name: str,
        target_endpoint_name: str,
        source_property_name: str,
        target_property_name: str,
        source_endpoint: Any,
        target_endpoint: Any,
        mapping_session_id: str,
        batch_size: int = 250,
        max_concurrent_batches: Optional[int] = None,
        min_confidence: float = 0.0
    ) -> Dict[str, Dict[str, Any]]:
        """
        Perform bidirectional validation on successful mappings.
        
        Args:
            mapping_executor: Reference to MappingExecutor for accessing helper methods
            meta_session: Database session for metamapper operations
            successful_mappings: Dictionary of source_id -> mapping results to validate
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            source_property_name: Property name for source ontology
            target_property_name: Property name for target ontology
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            mapping_session_id: ID of the current mapping session
            batch_size: Batch size for processing
            max_concurrent_batches: Maximum concurrent batches
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dictionary of enriched mappings with validation status
        """
        self.logger.info("--- Performing Bidirectional Validation ---")
        
        # Skip if no successful mappings to validate
        if not successful_mappings:
            self.logger.info("No successful mappings to validate. Skipping bidirectional validation.")
            return successful_mappings
        
        # Extract all target IDs that need validation
        target_ids_to_validate = self._extract_target_ids(successful_mappings)
        
        if not target_ids_to_validate:
            self.logger.info("No target IDs found to validate.")
            return successful_mappings
        
        self.logger.info(f"Found {len(target_ids_to_validate)} unique target IDs to validate")
        
        # Get ontology types
        primary_source_ontology = await mapping_executor._get_ontology_type(
            meta_session, source_endpoint_name, source_property_name
        )
        primary_target_ontology = await mapping_executor._get_ontology_type(
            meta_session, target_endpoint_name, target_property_name
        )
        
        # Find reverse mapping path
        self.logger.info(f"Step 1: Finding reverse mapping path from {primary_target_ontology} back to {primary_source_ontology}...")
        reverse_path = await mapping_executor._find_best_path(
            meta_session,
            primary_target_ontology,  # Using target as source
            primary_source_ontology,  # Using source as target
            preferred_direction="forward",  # We want a direct T->S path
            allow_reverse=True,  # Allow using S->T paths in reverse if needed
            source_endpoint=target_endpoint,  # Note: swapped for reverse
            target_endpoint=source_endpoint,  # Note: swapped for reverse
        )
        
        if not reverse_path:
            self.logger.warning(
                f"No reverse mapping path found from {primary_target_ontology} to {primary_source_ontology}. "
                "Validation incomplete."
            )
            # Return original mappings without validation status
            return successful_mappings
        
        self.logger.info(f"Step 2: Found reverse path: {reverse_path.name} (id={reverse_path.id})")
        
        # Execute reverse mapping
        self.logger.info("Step 3: Reverse mapping from target to source...")
        reverse_results = await mapping_executor._execute_path(
            meta_session,
            reverse_path,
            list(target_ids_to_validate),
            primary_target_ontology,
            primary_source_ontology,
            mapping_session_id=mapping_session_id,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            filter_confidence=min_confidence
        )
        
        # Reconcile bidirectional mappings
        self.logger.info("Step 4: Reconciling bidirectional mappings...")
        validated_mappings = self._reconcile_bidirectional_mappings(
            successful_mappings,
            reverse_results
        )
        
        return validated_mappings
    
    def _extract_target_ids(self, successful_mappings: Dict[str, Dict[str, Any]]) -> Set[str]:
        """
        Extract all unique target IDs from successful mappings.
        
        Args:
            successful_mappings: Dictionary of mapping results
            
        Returns:
            Set of unique target IDs
        """
        target_ids = set()
        for result in successful_mappings.values():
            if result and result.get("target_identifiers"):
                target_ids.update(result["target_identifiers"])
        return target_ids
    
    def _reconcile_bidirectional_mappings(
        self,
        forward_mappings: Dict[str, Dict[str, Any]],
        reverse_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich forward mappings with bidirectional validation status.
        
        Instead of filtering, this adds validation status information to each mapping
        that succeeded in the primary S->T direction.
        
        Args:
            forward_mappings: Dictionary of source_id -> mapping_result from forward mapping
            reverse_results: Dictionary of target_id -> reverse_mapping_result from reverse mapping
            
        Returns:
            Dictionary of enriched source_id -> mapping_result with validation status added
        """
        validated_count = 0
        unidirectional_count = 0
        
        # Build target_id -> source_ids mapping from reverse results
        target_to_sources = self._build_target_to_sources_mapping(reverse_results)
        
        enriched_mappings = {}
        for source_id, fwd_res_item in forward_mappings.items():
            enriched_result = fwd_res_item.copy()
            
            if not fwd_res_item or not fwd_res_item.get("target_identifiers"):
                enriched_result["validation_status"] = "Successful (NoFwdTarget)"
                unidirectional_count += 1
            else:
                forward_mapped_target_ids = fwd_res_item["target_identifiers"]
                current_status_for_source = None

                for target_id_from_fwd_map in forward_mapped_target_ids:
                    if target_id_from_fwd_map in target_to_sources:
                        all_possible_reverse_sources_for_target = target_to_sources[target_id_from_fwd_map]
                        
                        if source_id in all_possible_reverse_sources_for_target:
                            primary_reverse_mapped_id = reverse_results.get(target_id_from_fwd_map, {}).get("mapped_value")
                            
                            # Normalize primary_reverse_mapped_id if it's an Arivale ID
                            normalized_primary_reverse_id = self._normalize_arivale_id(primary_reverse_mapped_id)

                            if normalized_primary_reverse_id == source_id:
                                current_status_for_source = "Validated"
                            else:
                                current_status_for_source = "Validated (Ambiguous)"
                            break  # Found validation status for this source_id
            
                if current_status_for_source:
                    enriched_result["validation_status"] = current_status_for_source
                    validated_count += 1
                else:
                    # No validation path found to the original source_id
                    any_fwd_target_had_reverse_data = any(tid in target_to_sources for tid in forward_mapped_target_ids)
                    if any_fwd_target_had_reverse_data:
                        enriched_result["validation_status"] = "Successful"
                    else:
                        enriched_result["validation_status"] = "Successful (NoReversePath)"
                    unidirectional_count += 1
            
            enriched_mappings[source_id] = enriched_result
    
        self.logger.info(
            f"Validation status: {validated_count} validated (bidirectional), "
            f"{unidirectional_count} successful (one-directional only)"
        )
        return enriched_mappings
    
    def _build_target_to_sources_mapping(self, reverse_results: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        Build a mapping of target_id -> set of source_ids it can reverse map to.
        
        Args:
            reverse_results: Dictionary of reverse mapping results
            
        Returns:
            Dictionary mapping target_id to set of source_ids
        """
        target_to_sources = {}
        
        for target_id, rev_res_item in reverse_results.items():
            if rev_res_item and rev_res_item.get("target_identifiers"):
                all_reverse_mapped_to_source_ids = set(rev_res_item["target_identifiers"])
                
                # Handle Arivale ID components in reverse mapped IDs
                # If client returns "INF_P12345", ensure "P12345" is also considered.
                current_set_copy = set(all_reverse_mapped_to_source_ids)  # Iterate over a copy
                for rs_id in current_set_copy:
                    normalized_id = self._normalize_arivale_id(rs_id)
                    if normalized_id != rs_id:
                        all_reverse_mapped_to_source_ids.add(normalized_id)
                
                target_to_sources[target_id] = all_reverse_mapped_to_source_ids
        
        return target_to_sources
    
    def _normalize_arivale_id(self, identifier: Optional[str]) -> Optional[str]:
        """
        Normalize Arivale IDs by removing prefixes.
        
        Args:
            identifier: The identifier to normalize
            
        Returns:
            Normalized identifier or original if not an Arivale ID
        """
        if not identifier:
            return identifier
        
        arivale_prefixes = ('INF_', 'CAM_', 'CVD_', 'CVD2_', 'DEV_')
        if any(identifier.startswith(p) for p in arivale_prefixes):
            parts = identifier.split('_', 1)
            if len(parts) > 1 and parts[1]:  # Check that there's content after the prefix
                return parts[1]  # Return the part after the prefix
        
        return identifier