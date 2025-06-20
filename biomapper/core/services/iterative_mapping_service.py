"""
Service for handling iterative secondary mapping logic.

This service manages the complex iterative process of finding and executing
secondary mapping paths for identifiers that were not mapped in the initial direct pass.
"""

import json
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta

from ..exceptions import BiomapperError
from ...db.models import Endpoint, EndpointPropertyConfig as EndpointProperty, OntologyPreference, MappingPath
from ...db.cache_models import PathExecutionStatus


class IterativeMappingService:
    """
    Service class that encapsulates the iterative mapping logic previously
    embedded in MappingExecutor.execute_mapping.
    """
    
    def __init__(self, logger=None):
        """Initialize the iterative mapping service."""
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    async def perform_iterative_mapping(
        self,
        unmapped_ids: List[str],
        source_endpoint_name: str,
        target_endpoint_name: str,
        primary_source_ontology: str,
        primary_target_ontology: str,
        source_property_name: str,
        primary_path: Optional[MappingPath],
        meta_session: Any,
        mapping_executor: Any,  # Reference to parent executor for method access
        mapping_session_id: Optional[str] = None,
        mapping_direction: str = "forward",
        try_reverse_mapping: bool = False,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        batch_size: int = 250,
        max_concurrent_batches: Optional[int] = None,
        max_hop_count: Optional[int] = None,
        min_confidence: float = 0.0,
    ) -> Tuple[Dict[str, Dict], Set[str], Dict[str, Dict]]:
        """
        Perform iterative secondary mapping for unmapped identifiers.
        
        This method:
        1. Finds available secondary ontology types
        2. Iterates through them to find conversion paths
        3. Executes conversions to derive primary IDs
        4. Re-attempts mapping with derived IDs
        
        Args:
            unmapped_ids: List of identifiers that couldn't be mapped directly
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            primary_source_ontology: Primary ontology type for source
            primary_target_ontology: Primary ontology type for target
            source_property_name: Property name for source
            primary_path: The primary mapping path (if found)
            meta_session: Database session
            mapping_executor: Reference to parent MappingExecutor
            mapping_session_id: Session ID for logging
            mapping_direction: Preferred mapping direction
            try_reverse_mapping: Whether to try reverse paths
            use_cache: Whether to use cache
            max_cache_age_days: Maximum cache age
            batch_size: Batch size for processing
            max_concurrent_batches: Max concurrent batches
            max_hop_count: Maximum hop count
            min_confidence: Minimum confidence threshold
            
        Returns:
            Tuple of (successful_mappings, processed_ids, derived_primary_ids)
        """
        successful_mappings = {}
        processed_ids = set()
        derived_primary_ids = {}
        
        if not unmapped_ids:
            self.logger.info("No unmapped identifiers to process in iterative mapping.")
            return successful_mappings, processed_ids, derived_primary_ids
            
        self.logger.info(f"Starting iterative mapping for {len(unmapped_ids)} unmapped identifiers")
        
        # --- Step 1: Find and prioritize available secondary ontology types ---
        all_properties = await mapping_executor._get_endpoint_properties(meta_session, source_endpoint_name)
        
        # Filter to only secondary properties
        secondary_properties = [
            prop for prop in all_properties 
            if prop.property_name != source_property_name 
            and prop.ontology_type 
            and prop.ontology_type != primary_source_ontology
        ]
        
        if not secondary_properties:
            self.logger.warning(
                f"No suitable secondary properties/ontologies found for source endpoint "
                f"'{source_endpoint_name}' (excluding primary '{source_property_name}' / "
                f"'{primary_source_ontology}'). Skipping iterative mapping."
            )
            return successful_mappings, processed_ids, derived_primary_ids
            
        # Get ontology preferences for prioritization
        preferences = await mapping_executor._get_ontology_preferences(meta_session, source_endpoint_name)
        
        # Sort secondary properties by preference priority
        if preferences:
            priority_map = {pref.ontology_name: pref.priority for pref in preferences}
            secondary_properties.sort(key=lambda prop: priority_map.get(prop.ontology_type, 999))
            self.logger.info(f"Sorted {len(secondary_properties)} secondary properties by endpoint preference priority.")
        else:
            self.logger.info(f"No ontology preferences found for '{source_endpoint_name}'. Using default property order.")
            
        # --- Step 2: Iterate through secondary types for unmapped entities ---
        for secondary_prop in secondary_properties:
            # Skip processing if all IDs now have derived primaries
            unmapped_ids_without_derived = [uid for uid in unmapped_ids if uid not in derived_primary_ids]
            if not unmapped_ids_without_derived:
                self.logger.info("All unmapped identifiers now have derived primary IDs. Skipping remaining secondary properties.")
                break
                
            secondary_source_ontology = secondary_prop.ontology_type
            secondary_source_property_name = secondary_prop.property_name
            
            self.logger.info(f"Processing secondary property '{secondary_source_property_name}' with ontology type '{secondary_source_ontology}'")
            self.logger.info(f"Remaining unmapped entities without derived primaries: {len(unmapped_ids_without_derived)}")
            
            # Find a path that converts this secondary ontology to primary source ontology
            secondary_to_primary_path = await mapping_executor._find_best_path(
                meta_session,
                secondary_source_ontology,  # From secondary source ontology
                primary_source_ontology,    # To primary SOURCE ontology (not target)
                preferred_direction=mapping_direction,
                allow_reverse=try_reverse_mapping,
            )
            
            if not secondary_to_primary_path:
                self.logger.warning(
                    f"No mapping path found from secondary ontology {secondary_source_ontology} "
                    f"to primary source ontology {primary_source_ontology}. Trying next secondary property."
                )
                continue
                
            self.logger.info(f"Found secondary-to-primary path: {secondary_to_primary_path.name} (ID: {secondary_to_primary_path.id})")
            self.logger.info(f"Executing secondary-to-primary conversion for {len(unmapped_ids_without_derived)} identifiers.")
            
            # Execute this path to convert secondary -> primary source
            conversion_results = await mapping_executor._execute_path(
                meta_session,
                secondary_to_primary_path,
                unmapped_ids_without_derived,
                secondary_source_ontology,
                primary_source_ontology,
                mapping_session_id=mapping_session_id,
                batch_size=batch_size,
                max_hop_count=max_hop_count,
                filter_confidence=min_confidence,
                max_concurrent_batches=max_concurrent_batches
            )
            
            # Process results - store derived primary IDs
            if conversion_results:
                num_newly_derived = 0
                for source_id, result_data in conversion_results.items():
                    if result_data and result_data.get("target_identifiers"):
                        derived_primary_ids[source_id] = {
                            "primary_ids": result_data["target_identifiers"],
                            "provenance": {
                                "derived_from": secondary_source_ontology,
                                "via_path": secondary_to_primary_path.name,
                                "path_id": secondary_to_primary_path.id,
                                "confidence": result_data.get("confidence_score", 0.0),
                            }
                        }
                        num_newly_derived += 1
                        
                self.logger.info(
                    f"Derived primary IDs for {num_newly_derived} entities using "
                    f"{secondary_source_ontology} -> {primary_source_ontology} conversion."
                )
            else:
                self.logger.info(
                    f"No primary IDs derived from {secondary_source_ontology} -> "
                    f"{primary_source_ontology} conversion."
                )
                
        self.logger.info(
            f"Secondary-to-primary conversion complete. Derived primary IDs for "
            f"{len(derived_primary_ids)}/{len(unmapped_ids)} unmapped entities."
        )
        
        # --- Step 3: Re-attempt Direct Primary Mapping using derived primary IDs ---
        if not derived_primary_ids:
            self.logger.info("No derived primary IDs available. Skipping re-mapping step.")
            return successful_mappings, processed_ids, derived_primary_ids
            
        self.logger.info(f"Re-attempting primary mapping using derived IDs for {len(derived_primary_ids)} entities.")
        
        if not primary_path:
            self.logger.warning(
                f"No direct mapping path from {primary_source_ontology} to "
                f"{primary_target_ontology} available for re-mapping."
            )
            return successful_mappings, processed_ids, derived_primary_ids
            
        # Process each derived ID
        for source_id, derived_data in derived_primary_ids.items():
            derived_primary_id_list = derived_data["primary_ids"]
            provenance_info = derived_data["provenance"]
            
            # For each derived primary ID, attempt the mapping to target
            for derived_primary_id in derived_primary_id_list:
                self.logger.debug(f"Attempting mapping for {source_id} using derived primary ID {derived_primary_id}")
                
                # Check cache for the derived ID
                cached_derived_mapping = None
                if use_cache:
                    self.logger.debug(
                        f"Checking cache for derived ID: {derived_primary_id} "
                        f"({primary_source_ontology}) -> {primary_target_ontology}"
                    )
                    
                    expiry_time = None
                    if max_cache_age_days is not None:
                        expiry_time = datetime.now(timezone.utc) - timedelta(days=max_cache_age_days)
                    
                    cache_results_for_derived, _ = await mapping_executor.cache_manager.check_cache(
                        input_identifiers=[derived_primary_id],
                        source_ontology=primary_source_ontology,
                        target_ontology=primary_target_ontology,
                        expiry_time=expiry_time
                    )
                    
                    if cache_results_for_derived and derived_primary_id in cache_results_for_derived:
                        cached_derived_mapping = cache_results_for_derived[derived_primary_id]
                        self.logger.info(
                            f"Cache hit for derived ID {derived_primary_id} -> "
                            f"{cached_derived_mapping.get('target_identifiers')}"
                        )
                
                # Use cache or execute path
                if cached_derived_mapping:
                    derived_mapping_results = {derived_primary_id: cached_derived_mapping}
                else:
                    self.logger.debug(f"Cache miss or not used for derived ID {derived_primary_id}. Executing primary_path.")
                    derived_mapping_results = await mapping_executor._execute_path(
                        meta_session,
                        primary_path,
                        [derived_primary_id],
                        primary_source_ontology,
                        primary_target_ontology,
                        mapping_session_id=mapping_session_id,
                        batch_size=batch_size,
                        max_hop_count=max_hop_count,
                        filter_confidence=min_confidence,
                        max_concurrent_batches=max_concurrent_batches
                    )
                
                # Process results - connect back to original source ID
                if derived_mapping_results and derived_primary_id in derived_mapping_results:
                    result_data = derived_mapping_results[derived_primary_id]
                    if result_data and result_data.get("target_identifiers"):
                        source_result = {
                            "source_identifier": source_id,
                            "target_identifiers": result_data["target_identifiers"],
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": f"Mapped via derived primary ID {derived_primary_id}" + 
                                      (" (from cache)" if cached_derived_mapping else ""),
                            "confidence_score": result_data.get("confidence_score", 0.5) * 0.9,  # Lower confidence for indirect
                            "hop_count": (result_data.get("hop_count", 0) + 1 if result_data.get("hop_count") is not None else 2),
                            "mapping_direction": result_data.get("mapping_direction", "forward"),
                            "derived_path": True,
                            "intermediate_id": derived_primary_id,
                            "mapping_path_details": result_data.get("mapping_path_details")
                        }
                        
                        # Enrich path details with derivation provenance
                        current_path_details_str = source_result.get("mapping_path_details")
                        new_path_details = self._parse_path_details(current_path_details_str)
                        new_path_details["derived_step_provenance"] = provenance_info
                        source_result["mapping_path_details"] = json.dumps(new_path_details)
                        
                        successful_mappings[source_id] = source_result
                        processed_ids.add(source_id)
                        self.logger.debug(
                            f"Successfully mapped {source_id} to {source_result['target_identifiers']} "
                            f"via derived ID {derived_primary_id}"
                        )
                        break  # Stop processing additional derived IDs once we have success
        
        # Log summary
        newly_mapped = len([sid for sid in derived_primary_ids.keys() if sid in processed_ids])
        self.logger.info(
            f"Indirect mapping using derived primary IDs successfully mapped "
            f"{newly_mapped}/{len(derived_primary_ids)} additional entities."
        )
        
        return successful_mappings, processed_ids, derived_primary_ids
    
    def _parse_path_details(self, path_details_str: Any) -> Dict:
        """Parse path details from various formats into a dictionary."""
        if isinstance(path_details_str, str):
            try:
                return json.loads(path_details_str)
            except json.JSONDecodeError:
                self.logger.warning(f"Could not parse path_details JSON: {path_details_str}")
                return {"original_mapping_step_details": path_details_str}
        elif isinstance(path_details_str, dict):
            return path_details_str
        elif path_details_str is None:
            return {}
        else:
            self.logger.warning(f"Unexpected type for path_details: {type(path_details_str)}. Storing as string.")
            return {"original_mapping_step_details": str(path_details_str)}