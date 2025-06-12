"""Client to resolve historical and secondary UniProt IDs to current primary accessions.

When identifiers are retired, merged, or split in UniProt, they become secondary accessions
that point to one or more current primary accessions. This client handles the resolution
of these historical IDs to their current primary forms.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple, Set

from biomapper.core.exceptions import ClientInitializationError, ClientExecutionError
from typing import Dict, List, Optional, Any, Tuple, Set # Added Set

from biomapper.mapping.clients.base_client import (
    BaseMappingClient,
    CachedMappingClientMixin,
)

logger = logging.getLogger(__name__)

# UniProt API endpoints
UNIPROT_REST_BASE_URL = "https://rest.uniprot.org/uniprotkb"
UNIPROT_API_SEARCH_URL = f"{UNIPROT_REST_BASE_URL}/search"
DEFAULT_REQUEST_TIMEOUT = 30  # seconds


class UniProtHistoricalResolverClient(CachedMappingClientMixin, BaseMappingClient):
    """Client to resolve historical and secondary UniProt accession numbers to current primary accessions.
    
    This client uses the UniProt REST API to properly resolve:
    - Secondary accessions to their current primary accession
    - Demerged accessions (one ID split into multiple entries)
    - Obsolete/deleted accessions
    
    It returns extra metadata in the component_id field to indicate whether the
    identifier was:
    - Already a primary ID
    - A secondary ID that resolved to a primary ID
    - A demerged ID that resolved to multiple primary IDs
    - An obsolete ID that no longer exists
    """

    def __init__(
        self, 
        config: Optional[Dict[str, Any]] = None,
        cache_size: int = 10000,
        base_url: str = UNIPROT_API_SEARCH_URL,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ):
        """Initialize the client with configuration.
        
        Args:
            config: Optional configuration dictionary.
            cache_size: Maximum number of entries to store in the cache.
            base_url: The base URL for the UniProt REST API.
            timeout: Request timeout in seconds.
        """
        # Initialize parent class
        super().__init__(cache_size=cache_size, config=config)
        
        # Initialize client-specific attributes
        self.base_url = base_url
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        # Mark as initialized
        self._initialized = True
        self._cache_preload_needed = False  # No preloading necessary
    
    async def _fetch_uniprot_search_results(self, query: str) -> Dict[str, Any]:
        """Execute a search query against the UniProt REST API.
        
        Args:
            query: The search query (e.g., "accession:P12345 OR accession:P67890")
            
        Returns:
            The parsed JSON response from the UniProt API.
            
        Raises:
            ClientExecutionError: If the API request fails.
        """
        params = {
            "query": query,
            "format": "json",
            "size": 500,  # Maximum number of results to return
        }
        
        request_timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            async with self.semaphore:
                async with aiohttp.ClientSession(timeout=request_timeout) as session:
                    logger.debug(f"Querying UniProt REST API: {self.base_url} with params: {params}")
                    logger.info(f"UniProtClient DEBUG: Querying UniProt with: {query}")
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"UniProtClient DEBUG: Response for query [{query}]: {len(data.get('results', []))} results")
                            return data
                        else:
                            error_text = await response.text()
                            error_msg = f"UniProt API error: Status {response.status}, Message: {error_text}"
                            logger.error(error_msg)
                            raise ClientExecutionError(
                                error_msg,
                                client_name=self.__class__.__name__,
                                details={"query": query, "status": response.status}
                            )
        except aiohttp.ClientError as e:
            logger.error(f"HTTP Error querying UniProt API: {e}")
            raise ClientExecutionError(
                f"HTTP Error querying UniProt API: {str(e)}",
                client_name=self.__class__.__name__,
                details={"query": query, "error": str(e)}
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout querying UniProt API after {self.timeout}s")
            raise ClientExecutionError(
                f"Timeout querying UniProt API after {self.timeout}s",
                client_name=self.__class__.__name__,
                details={"query": query, "timeout": self.timeout}
            )
        except Exception as e:
            logger.error(f"Unexpected error during UniProt API query: {e}", exc_info=True)
            raise ClientExecutionError(
                f"Unexpected error during UniProt API query: {str(e)}",
                client_name=self.__class__.__name__,
                details={"query": query, "error": str(e)}
            )
    
    async def _check_as_secondary_accessions(self, ids: List[str]) -> Dict[str, List[str]]:
        """Check if any of the given IDs appear as secondary accessions in UniProt.
        
        This is critical for detecting demerged IDs that map to multiple primary accessions.
        
        Args:
            ids: List of UniProt accessions to check
            
        Returns:
            Dictionary mapping each ID to a list of primary accessions (empty if not found)
        """
        # Skip if no IDs to check
        if not ids:
            return {}
            
        # Build the query
        query_parts = []
        for acc_id in ids:
            query_parts.append(f"sec_acc:{acc_id}")
            
        query = " OR ".join(f"({part})" for part in query_parts)
        
        # Execute the query
        results = await self._fetch_uniprot_search_results(query)
        
        # Process the results
        sec_to_primary_map = {}
        for id in ids:
            sec_to_primary_map[id] = []
            
        if "results" in results:
            for entry in results["results"]:
                primary_acc = entry.get("primaryAccession")
                if not primary_acc:
                    continue
                    
                sec_accs = entry.get("secondaryAccessions", [])
                
                # Check each input ID against secondary accessions
                for acc_id in ids:
                    if acc_id in sec_accs:
                        if acc_id not in sec_to_primary_map:
                            sec_to_primary_map[acc_id] = []
                        if primary_acc not in sec_to_primary_map[acc_id]:
                            sec_to_primary_map[acc_id].append(primary_acc)
        
        return sec_to_primary_map
    
    async def _check_as_primary_accessions(self, ids: List[str]) -> Dict[str, bool]:
        """Check if any of the given IDs are primary accessions in UniProt.
        
        Args:
            ids: List of UniProt accessions to check
            
        Returns:
            Dictionary mapping each ID to a boolean indicating if it's a primary accession
        """
        # Skip if no IDs to check
        if not ids:
            return {}
            
        # Build the query
        query_parts = []
        for acc_id in ids:
            query_parts.append(f"accession:{acc_id}")
            
        query = " OR ".join(f"({part})" for part in query_parts)
        
        # Execute the query
        results = await self._fetch_uniprot_search_results(query)
        
        # Process the results
        primary_map = {id: False for id in ids}
        
        logger.info(f"UniProtClient DEBUG: Checking primary accessions for {ids}")
        
        if "results" in results:
            logger.info(f"UniProtClient DEBUG: Found {len(results['results'])} entries in API response")
            for entry in results["results"]:
                primary_acc = entry.get("primaryAccession")
                if not primary_acc:
                    logger.debug(f"UniProtClient DEBUG: Entry without primaryAccession: {entry}")
                    continue
                    
                # Check if this primary accession matches any of our input IDs
                if primary_acc in primary_map:
                    primary_map[primary_acc] = True
                    logger.info(f"UniProtClient DEBUG: Found primary accession match: {primary_acc}")
                else:
                    logger.debug(f"UniProtClient DEBUG: Primary accession {primary_acc} not in our input list")
        else:
            logger.warning(f"UniProtClient DEBUG: No 'results' key in API response: {results.keys()}")
        
        logger.info(f"UniProtClient DEBUG: Primary accession check results: {primary_map}")
        return primary_map
    
    async def _resolve_batch(self, batch_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Resolve a batch of UniProt accessions using the REST API.
        
        Args:
            batch_ids: List of UniProt accession numbers to resolve.
            
        Returns:
            A dictionary mapping each input ID to its resolution information.
        """
        # Initialize results for all input IDs
        results = {}
        for acc_id in batch_ids:
            results[acc_id] = {
                "found": False,
                "is_primary": False,
                "is_secondary": False,
                "is_obsolete": True,  # Assume obsolete until found
                "primary_ids": [],
                "organism": None,
                "gene_names": [],
            }
        
        # Skip if no IDs to process
        if not batch_ids:
            return results
            
        # Filter out invalid or empty IDs
        valid_ids = []
        invalid_ids = []
        
        import re
        # UniProt regex pattern (simplified)
        uniprot_pattern = re.compile(r'^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9](\d+)?$')
        
        for acc_id in batch_ids:
            if not acc_id or not isinstance(acc_id, str):
                invalid_ids.append(acc_id)
                continue
                
            cleaned_id = acc_id.strip()
            if not cleaned_id:
                invalid_ids.append(acc_id)
                continue
                
            if uniprot_pattern.match(cleaned_id):
                valid_ids.append(cleaned_id)
            else:
                logger.debug(f"ID {cleaned_id} failed validation - doesn't match UniProt format")
                invalid_ids.append(acc_id)
        
        # Mark invalid IDs as obsolete
        for acc_id in invalid_ids:
            results[acc_id] = {
                "found": False,
                "is_primary": False,
                "is_secondary": False,
                "is_obsolete": True,
                "primary_ids": [],
                "organism": None,
                "gene_names": [],
            }
            
        if not valid_ids:
            logger.info("No valid UniProt IDs to process")
            return results
            
        logger.info(f"UniProtClient DEBUG: _resolve_batch processing {len(valid_ids)} valid IDs: {valid_ids}")
            
        try:
            # STEP 1: Check if any of these IDs appear as secondary accessions in other entries
            # This helps detect demerged IDs that map to multiple primaries
            secondary_map = await self._check_as_secondary_accessions(valid_ids)
            logger.info(f"UniProtClient DEBUG: Secondary accession check found: {len([k for k,v in secondary_map.items() if v])} IDs as secondary")
            
            # STEP 2: For IDs that don't appear as secondary accessions, check if they are primary accessions
            non_secondary_ids = [id for id in valid_ids if not secondary_map.get(id)]
            logger.info(f"UniProtClient DEBUG: Checking {len(non_secondary_ids)} IDs as potential primary accessions: {non_secondary_ids}")
            primary_map = await self._check_as_primary_accessions(non_secondary_ids)
            
            # Process the results - first handle those that appear as secondary accessions
            for acc_id, primary_ids in secondary_map.items():
                if primary_ids:  # This ID appears as a secondary accession
                    if len(primary_ids) > 1:
                        # Demerged ID (one secondary ID maps to multiple primaries)
                        results[acc_id] = {
                            "found": True,
                            "is_primary": False,
                            "is_secondary": False,  # Not a simple secondary, but a demerged ID
                            "is_obsolete": False,
                            "primary_ids": primary_ids,
                            "organism": None,  # Cannot set for demerged IDs
                            "gene_names": [],
                        }
                    else:
                        # Regular secondary ID (maps to a single primary)
                        results[acc_id] = {
                            "found": True,
                            "is_primary": False,
                            "is_secondary": True,
                            "is_obsolete": False,
                            "primary_ids": primary_ids,
                            "organism": None,
                            "gene_names": [],
                        }
            
            # Process the results - then handle those that are primary accessions
            for acc_id, is_primary in primary_map.items():
                if is_primary:  # This ID is a primary accession
                    results[acc_id] = {
                        "found": True,
                        "is_primary": True,
                        "is_secondary": False,
                        "is_obsolete": False,
                        "primary_ids": [acc_id],  # Primary ID maps to itself
                        "organism": None,
                        "gene_names": [],
                    }
                else:
                    # If not found as primary and not in secondary_map, it's obsolete
                    # This is already the default state in results, no need to update
                    logger.info(f"UniProtClient DEBUG: ID {acc_id} not found as primary (already marked obsolete)")
                    pass
            
            # Log final results
            logger.info(f"UniProtClient DEBUG: _resolve_batch final results summary:")
            for acc_id, info in results.items():
                if info["found"]:
                    logger.info(f"  {acc_id}: Found=True, Primary={info['is_primary']}, PrimaryIDs={info['primary_ids']}")
                else:
                    logger.info(f"  {acc_id}: Found=False (obsolete)")
                        
            return results
            
        except Exception as e:
            logger.error(f"Error resolving batch of UniProt IDs: {e}", exc_info=True)
            # Initialize all as failed
            for acc_id in batch_ids:
                results[acc_id] = {
                    "found": False,
                    "is_primary": False,
                    "is_secondary": False,
                    "is_obsolete": True,
                    "primary_ids": [],
                    "organism": None,
                    "gene_names": [],
                }
            return results
    
    def _preprocess_ids(self, identifiers: List[str]) -> List[str]:
        """Preprocess identifiers to split composite IDs and remove duplicates."""
        processed_ids: Set[str] = set()
        for identifier in identifiers:
            # Split by comma, then by underscore, and flatten the list
            parts = [part.strip() for p_comma in identifier.split(',') for part in p_comma.split('_') if part.strip()]
            for part in parts:
                if part: # Ensure non-empty string after stripping
                    processed_ids.add(part)
        return list(processed_ids)

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Resolve a list of possibly historical UniProt accessions to current primary accessions.
        
        Args:
            identifiers: List of UniProt accession identifiers to resolve.
            config: Optional per-call configuration overrides.
                    Can include 'bypass_cache': True to skip cache checking.
            
        Returns:
            Dictionary mapping each input identifier to a tuple:
            - First element: List of current primary IDs (or None if not resolvable)
            - Second element: Resolution metadata string, e.g., "primary", "secondary:P12345", "demerged", "obsolete"
        """
        if not self._initialized:
            raise ClientInitializationError(
                "Client not properly initialized", 
                client_name=self.__class__.__name__
            )
            
        if not identifiers:
            return {}
            
        results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        
        # Check if cache preloading is needed
        if hasattr(self, "_cache_preload_needed") and self._cache_preload_needed:
            await self._preload_cache()
            self._cache_preload_needed = False
        
        # Check if cache should be bypassed
        bypass_cache = config and config.get('bypass_cache', False)
        if bypass_cache:
            logger.info("UniProtHistoricalResolverClient: Bypassing cache as requested")
        
        # Preprocess identifiers to handle composite IDs
        original_identifiers = list(identifiers) # Keep a copy of the original input
        processed_identifiers = self._preprocess_ids(identifiers)

        # Initialize results dictionary - this will store results for preprocessed IDs
        # We will map these back to original_identifiers at the end
        processed_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = { 
            identifier: (None, "error:not_processed") for identifier in processed_identifiers
        }
        
        # Filter out already cached identifiers if cache is enabled
        if not bypass_cache:
            cached_results = await self._get_from_cache(processed_identifiers)
            # Update results with cached entries and identify non-cached IDs
            non_cached_ids = []
            for identifier in processed_identifiers:
                if identifier in cached_results:
                    processed_results[identifier] = cached_results[identifier]
                else:
                    non_cached_ids.append(identifier)
        else:
            non_cached_ids = list(processed_identifiers)
        
        if not non_cached_ids:
            logger.info("All preprocessed UniProt IDs found in cache.")
            # Map results back to original identifiers
            final_results = {}
            for orig_id in original_identifiers:
                # For a composite original ID, we need to decide how to aggregate results
                # For now, let's take the first part's result as a placeholder strategy
                # A more sophisticated strategy might be needed depending on requirements
                current_processed_ids_for_orig = self._preprocess_ids([orig_id])
                if current_processed_ids_for_orig:
                    final_results[orig_id] = processed_results.get(current_processed_ids_for_orig[0], (None, "error:split_id_not_found"))
                else:
                    final_results[orig_id] = (None, "error:empty_after_preprocess")
            return final_results
        
        logger.info(f"Resolving {len(non_cached_ids)} preprocessed UniProt IDs from API (total {len(processed_identifiers)} preprocessed, from {len(original_identifiers)} original requested).")
        
        # Process batches using preprocessed IDs
        batch_size = 50  # UniProt recommends batching for multiple queries
        for i in range(0, len(non_cached_ids), batch_size):
            batch = non_cached_ids[i:i + batch_size]
            try:
                batch_results_for_processed = await self._resolve_batch(batch)
                for identifier, raw_result_dict in batch_results_for_processed.items():
                    final_primary_ids: Optional[List[str]] = raw_result_dict.get("primary_ids")
                    metadata_str: Optional[str] = None

                    is_primary = raw_result_dict.get("is_primary", False)
                    is_secondary = raw_result_dict.get("is_secondary", False)
                    found = raw_result_dict.get("found", False)

                    if is_primary:
                        metadata_str = "primary"
                        # Ensure final_primary_ids is [identifier] for primary, as per _resolve_batch convention
                        final_primary_ids = [identifier]
                    elif is_secondary:
                        if final_primary_ids and len(final_primary_ids) == 1:
                            metadata_str = f"secondary:{final_primary_ids[0]}"
                        elif final_primary_ids and len(final_primary_ids) > 1: # Secondary that demerged
                            metadata_str = "demerged"
                            # primary_ids are already set correctly by _resolve_batch for this
                        else: # is_secondary but no/empty primary_ids from _resolve_batch
                            metadata_str = "error:secondary_no_target"
                            final_primary_ids = None
                    elif found: # Not primary, not secondary, but _resolve_batch marked as found
                        if final_primary_ids and len(final_primary_ids) > 1:
                            metadata_str = "demerged"
                        elif final_primary_ids and len(final_primary_ids) == 1:
                            # Found, one primary_id, but not categorized as primary or secondary by _resolve_batch.
                            # This indicates an unexpected state or a gap in _resolve_batch's classification.
                            metadata_str = "error:found_unclassified"
                            final_primary_ids = None 
                        else: # Found but no primary_ids or an empty list of primary_ids
                            metadata_str = "obsolete" # Treat as obsolete if found but no valid primary IDs
                            final_primary_ids = None
                    else: # Not found (found is False)
                        metadata_str = "obsolete"
                        final_primary_ids = None
                    
                    # Fallback if metadata_str somehow wasn't set (should be covered by above logic)
                    if metadata_str is None:
                        metadata_str = "error:metadata_processing_failed"
                        final_primary_ids = None
                    
                    # Ensure primary_ids is None if metadata indicates error or no resolution (e.g. "obsolete")
                    if metadata_str == "obsolete" or metadata_str.startswith("error:"):
                        final_primary_ids = None
                    
                    transformed_result: Tuple[Optional[List[str]], Optional[str]] = (final_primary_ids, metadata_str)
                    
                    processed_results[identifier] = transformed_result
                    if not bypass_cache:
                        await self._add_to_cache(identifier, transformed_result)
            except Exception as e:
                logger.error(f"Error processing batch {batch}: {str(e)}")
                for identifier in batch:
                    if identifier not in processed_results or processed_results[identifier][1] == "error:not_processed":
                        error_result = (None, f"error:batch_processing_failed:{str(e)}")
                        processed_results[identifier] = error_result
                        if not bypass_cache:
                            await self._add_to_cache(identifier, error_result)
        
        # Map processed_results back to original_identifiers for the final output
        final_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        for orig_id in original_identifiers:
            # Get the constituent parts of the original ID. _preprocess_ids cleans and splits.
            split_parts = self._preprocess_ids([orig_id]) 

            if not split_parts:
                final_results[orig_id] = (None, "error:empty_after_preprocess")
                continue

            if len(split_parts) == 1:
                # The original ID (possibly after cleaning) corresponds to a single processed ID.
                single_part_key = split_parts[0]
                result_tuple = processed_results.get(single_part_key)
                if result_tuple:
                    final_results[orig_id] = result_tuple
                else:
                    # This case should ideally not happen if all processed_ids are in processed_results
                    final_results[orig_id] = (None, f"error:part_not_found_in_results:{single_part_key}")
            else:
                # This orig_id was composite and split into multiple parts. Aggregate results.
                collected_primary_ids: Set[str] = set()
                collected_metadata_details: List[str] = [] # To store "part_id:metadata_str"
                
                has_successful_resolution = False # True if any part yields primary IDs
                has_error_in_parts = False       # True if any part's metadata indicates an error

                for part_id in split_parts:
                    # Default if part_id is somehow not in processed_results (should not happen with current logic)
                    part_primary_ids, part_meta_str = processed_results.get(part_id, (None, f"error:part_not_found:{part_id}"))
                    
                    if part_primary_ids:
                        collected_primary_ids.update(part_primary_ids)
                        has_successful_resolution = True
                    
                    if part_meta_str:
                        collected_metadata_details.append(f"{part_id}:{part_meta_str}")
                        if part_meta_str.startswith("error:"):
                            has_error_in_parts = True
                    else: # Should not happen if processed_results is populated correctly by transformation logic
                        collected_metadata_details.append(f"{part_id}:error:missing_metadata")
                        has_error_in_parts = True

                final_agg_primary_ids: Optional[List[str]] = sorted(list(collected_primary_ids)) if collected_primary_ids else None
                
                # Construct the aggregated metadata string
                final_agg_metadata_str: str
                unique_metadata_strings = sorted(list(set(collected_metadata_details))) # Unique, sorted details from each part

                if has_error_in_parts:
                    final_agg_metadata_str = "composite:error_in_parts|" + "|".join(unique_metadata_strings)
                elif not final_agg_primary_ids: # No primary IDs resolved from any part, and no specific errors flagged above
                    # Check if all parts were strictly 'obsolete'
                    all_strictly_obsolete = True
                    for part_id_check in split_parts:
                        # Need to re-fetch from processed_results to check original metadata string for 'obsolete'
                        _, meta_check = processed_results.get(part_id_check, (None, "")) # Default meta to empty if not found
                        if meta_check != "obsolete":
                            all_strictly_obsolete = False
                            break
                    if all_strictly_obsolete:
                        final_agg_metadata_str = "composite:all_parts_obsolete"
                    else:
                        final_agg_metadata_str = "composite:no_primary_ids_found|" + "|".join(unique_metadata_strings)
                else: # Has primary IDs and no errors in parts
                    final_agg_metadata_str = "composite:resolved|" + "|".join(unique_metadata_strings)
                
                final_results[orig_id] = (final_agg_primary_ids, final_agg_metadata_str)

        # Count statistics for logging based on processed_results (reflects API interaction)
        primary_count = secondary_count = demerged_count = obsolete_count = error_count = 0
        
        for _, (primary_ids, metadata) in processed_results.items():
            if metadata == "primary":
                primary_count += 1
            elif metadata and metadata.startswith("secondary:"):
                secondary_count += 1
            elif metadata == "demerged":
                demerged_count += 1
            elif metadata == "obsolete":
                obsolete_count += 1
            elif metadata and metadata.startswith("error:"):
                error_count += 1
        
        # Log statistics
        logger.info(
            f"Resolved {len(processed_identifiers)} preprocessed UniProt IDs (from {len(original_identifiers)} original): "
            f"{primary_count} primary, {secondary_count} secondary, "
            f"{demerged_count} demerged, {obsolete_count} obsolete, {error_count} errors"
        )
        
        return final_results

    async def reverse_map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Not supported for this client.
        
        Raises:
            NotImplementedError: Always, as reverse mapping is not applicable.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support reverse_map_identifiers"
        )


# Example script for testing
async def run_example():
    """Test the UniProtHistoricalResolverClient with known test cases."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Running UniProtHistoricalResolverClient example...")
    
    client = UniProtHistoricalResolverClient()
    
    # Test cases:
    test_ids = [
        "P01308",  # Primary accession (Insulin)
        "Q99895",  # Secondary accession (should map to P01308)
        "P0CG05",  # Demerged ID (split into multiple entries: P0DOY2, P0DOY3)
        "NONEXISTENT",  # ID that doesn't exist at all
    ]
    
    results = await client.map_identifiers(test_ids)
    
    print("\n--- Resolution Results ---")
    for acc_id, result in results.items():
        primary_ids, metadata = result
        if primary_ids:
            print(f"{acc_id} -> {', '.join(primary_ids)} ({metadata})")
        else:
            print(f"{acc_id} -> Not resolvable ({metadata})")


if __name__ == "__main__":
    asyncio.run(run_example())