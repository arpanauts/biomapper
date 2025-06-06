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
        
        # Process identifiers in batches
        batch_size = 25  # Smaller batches for reliability
        batches = [identifiers[i:i+batch_size] for i in range(0, len(identifiers), batch_size)]
        
        for batch in batches:
            # Check cache first (unless bypassed)
            filtered_batch = []
            for identifier in batch:
                if not bypass_cache:
                    cached_result = await self._get_from_cache(identifier)
                    if cached_result is not None:
                        results[identifier] = cached_result
                    else:
                        filtered_batch.append(identifier)
                else:
                    filtered_batch.append(identifier)
            
            # Skip if all were in cache
            if not filtered_batch:
                continue
                
            try:
                # Resolve the batch
                batch_results = await self._resolve_batch(filtered_batch)
                
                # Process the results
                for identifier in filtered_batch:
                    if identifier in batch_results:
                        resolution_info = batch_results[identifier]
                        
                        if resolution_info["found"]:
                            # Determine resolution type
                            if resolution_info["is_primary"]:
                                metadata = "primary"
                            elif len(resolution_info["primary_ids"]) > 1:
                                metadata = "demerged"
                            else:
                                metadata = f"secondary:{resolution_info['primary_ids'][0]}"
                                
                            result = (resolution_info["primary_ids"], metadata)
                        else:
                            result = (None, "obsolete")
                            
                        # Store in results and cache (unless bypassed)
                        results[identifier] = result
                        if not bypass_cache:
                            await self._add_to_cache(identifier, result)
                    else:
                        # Should not happen, but handle for safety
                        error_result = (None, "error:not_processed")
                        results[identifier] = error_result
                        if not bypass_cache:
                            await self._add_to_cache(identifier, error_result)
                        
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                for identifier in filtered_batch:
                    if identifier not in results:
                        error_result = (None, f"error:{str(e)}")
                        results[identifier] = error_result
                        if not bypass_cache:
                            await self._add_to_cache(identifier, error_result)
        
        # Count statistics for logging
        primary_count = secondary_count = demerged_count = obsolete_count = error_count = 0
        
        for _, (primary_ids, metadata) in results.items():
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
            f"Resolved {len(identifiers)} UniProt IDs: "
            f"{primary_count} primary, {secondary_count} secondary, "
            f"{demerged_count} demerged, {obsolete_count} obsolete, {error_count} errors"
        )
        
        return results

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