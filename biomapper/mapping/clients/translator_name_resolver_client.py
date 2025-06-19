"""Translator Name Resolver Client for Biomapper

A client for resolving entity names to standardized identifiers using the 
Translator Name Resolution API. This client implements the standard BaseMappingClient
interface for use with MappingExecutor.
"""

import logging
import aiohttp
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple, Set, Union

from biomapper.mapping.clients.base_client import BaseMappingClient, CachedMappingClientMixin
from biomapper.core.exceptions import ClientExecutionError, ClientInitializationError

logger = logging.getLogger(__name__)


class TranslatorNameResolverClient(CachedMappingClientMixin, BaseMappingClient):
    """
    Client for resolving entity names using the Translator Name Resolution API.
    
    This client supports mapping between entity names and standardized identifiers,
    with a focus on metabolites/compounds. It leverages the Name Resolution API
    developed by the Translator SRI team at RENCI.
    
    Configuration options:
    - target_db: Target database name for mapping (e.g., "CHEBI", "PUBCHEM")
    - timeout: Request timeout in seconds (default 30)
    - max_retries: Maximum number of retry attempts for failed requests (default 3)
    - backoff_factor: Exponential backoff factor for retries (default 0.5)
    - match_threshold: Minimum score threshold for matches (default 0.5)
    """
    
    # Mapping of target database names to CURIE prefixes
    DB_TO_CURIE_PREFIX = {
        "PUBCHEM": ["PUBCHEM.COMPOUND", "PUBCHEM"],
        "CHEBI": ["CHEBI"],
        "HMDB": ["HMDB"],
        "KEGG": ["KEGG.COMPOUND", "KEGG"],
        "DRUGBANK": ["DRUGBANK"],
        "MESH": ["MESH"],
        "LOINC": ["LOINC"],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Translator Name Resolver client.
        
        Args:
            config: Optional configuration dictionary with client-specific settings.
                   - target_db: Target database name (e.g., "CHEBI", "PUBCHEM")
                   - timeout: Request timeout in seconds (default 30)
                   - max_retries: Maximum number of retry attempts (default 3)
                   - backoff_factor: Exponential backoff factor for retries (default 0.5)
                   - match_threshold: Minimum score threshold for matches (default 0.5)
        """
        # Default configuration
        default_config = {
            "base_url": "https://name-resolution-sri.renci.org/lookup",
            "timeout": 30,
            "max_retries": 3,
            "backoff_factor": 0.5,
            "match_threshold": 0.5,
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        # Initialize parent classes (order matters for multiple inheritance)
        super().__init__(config=default_config, cache_size=2048)
        
        # Initialize internal state
        self._session = None
        self._initialized = False
        
        # Normalize target database name to uppercase
        self.target_db = self._config.get("target_db", "").upper()
        self.match_threshold = float(self._config.get("match_threshold", 0.5))
        
        logger.info(f"Initialized TranslatorNameResolverClient with target_db={self.target_db}")
    
    def get_required_config_keys(self) -> List[str]:
        """
        Return a list of required configuration keys for this client.
        
        Returns:
            List of required configuration key names.
        """
        # We require target_db to know which identifiers to extract
        return ["target_db"]
    
    async def _ensure_session(self):
        """
        Ensure that an HTTP session exists, creating it if necessary.
        """
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout", 30))
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
            logger.debug("Created new HTTP session")
    
    async def close(self):
        """
        Close the HTTP session when finished.
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._initialized = False
            logger.debug("Closed HTTP session")
    
    async def _perform_request(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform an HTTP request to the Name Resolution API with retry logic.
        
        Args:
            url: The base URL to request.
            params: Query parameters to include in the request.
            
        Returns:
            The JSON response parsed as a list of dictionaries.
            
        Raises:
            ClientExecutionError: If the request fails after max_retries.
        """
        await self._ensure_session()
        
        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)
        
        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    elif response.status == 404:
                        # No mappings found
                        return []
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"Name Resolution API request failed with status {response.status}: {error_text}"
                        )
                        
                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2 ** attempt)
                            logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                        else:
                            raise ClientExecutionError(
                                f"Name Resolution API request failed after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "url": url,
                                    "params": params,
                                    "status": response.status,
                                    "response": error_text
                                }
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error during Name Resolution API request: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2 ** attempt)
                    logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise ClientExecutionError(
                        f"HTTP error during Name Resolution API request after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"url": url, "params": params, "exception": str(e)}
                    )
    
    def _filter_matches_by_target_db(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter matches to only include those for the target database.
        
        Args:
            matches: List of match dictionaries from the API.
            
        Returns:
            Filtered list of matches that match the target database.
        """
        if not self.target_db:
            # If no target DB specified, return all matches
            return matches
        
        if self.target_db not in self.DB_TO_CURIE_PREFIX:
            # If target DB is not supported, return empty list
            return []
        
        target_prefixes = self.DB_TO_CURIE_PREFIX[self.target_db]
        filtered_matches = []
        
        for match in matches:
            curie = match.get("curie", "")
            if not curie or ":" not in curie:
                continue
                
            # Extract the prefix part (before the colon)
            prefix = curie.split(":", 1)[0].upper()
            
            # Check if this prefix matches any of our target prefixes
            if any(prefix == target_prefix for target_prefix in target_prefixes):
                filtered_matches.append(match)
        
        return filtered_matches
    
    def _extract_identifier_from_curie(self, curie: str) -> str:
        """
        Extract the actual identifier part from a CURIE.
        
        Args:
            curie: The CURIE string (e.g., "CHEBI:15377")
            
        Returns:
            The identifier part (e.g., "15377")
        """
        if ":" in curie:
            return curie.split(":", 1)[1]
        return curie
    
    async def _lookup_entity_name(self, name: str, target_biolink_type: str) -> List[Dict[str, Any]]:
        """
        Look up an entity name using the Name Resolution API.
        
        Args:
            name: The entity name to look up.
            target_biolink_type: The Biolink type to filter results for.
            
        Returns:
            List of match dictionaries from the API.
        """
        # Skip empty names
        if not name or name.strip() == "":
            return []
        
        # Build the query parameters
        params = {
            "string": name,
            "biolink_type": target_biolink_type,
            "limit": 50,  # Get a reasonable number of results
            "offset": 0
        }
        
        logger.debug(f"Looking up entity name: {name} with type: {target_biolink_type}")
        
        try:
            # Perform the API request
            matches = await self._perform_request(self._config["base_url"], params=params)
            
            # Filter by target database if specified
            filtered_matches = self._filter_matches_by_target_db(matches)
            
            # Filter by match threshold
            threshold = self.match_threshold
            threshold_filtered = [
                match for match in filtered_matches 
                if float(match.get("score", 0)) >= threshold
            ]
            
            logger.debug(
                f"Found {len(matches)} matches, {len(filtered_matches)} for target DB, "
                f"{len(threshold_filtered)} above threshold"
            )
            
            return threshold_filtered
            
        except ClientExecutionError:
            # Just re-raise the original error
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(f"Unexpected error in _lookup_entity_name: {str(e)}")
            raise ClientExecutionError(
                f"Unexpected error in Name Resolution API request: {str(e)}",
                client_name=self.__class__.__name__,
                details={"name": name, "exception": str(e)}
            )
    
    async def map_identifiers(
        self, names: List[str], target_biolink_type: str = "biolink:SmallMolecule", **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map entity names to standardized identifiers.
        
        Args:
            names: List of entity names to map.
            target_biolink_type: The Biolink type to filter results for.
                                Default is "biolink:SmallMolecule" for metabolites.
            **kwargs: Additional keyword arguments, which may include:
                     - config: Optional per-call configuration
                     
        Returns:
            A dictionary mapping each input name to a tuple containing:
            - The first element is a list of mapped target identifiers or None if mapping failed
            - The second element is the confidence score as a string, or None if not available
        """
        if not names:
            return {}
        
        # Extract config from kwargs if provided
        config = kwargs.get("config", {})
        
        # Apply any per-call config overrides
        call_config = self._config.copy()
        if config:
            call_config.update(config)
        
        # Get target DB (use instance value if not overridden)
        target_db = call_config.get("target_db", self.target_db).upper()
        match_threshold = float(call_config.get("match_threshold", self.match_threshold))
        
        if not target_db:
            logger.warning("No target database specified, results may not be filtered properly")
        
        logger.info(f"Mapping {len(names)} names to {target_db} identifiers")
        
        # Create results dictionary
        results = {}
        
        # Check cache first for all names
        cache_results = {}
        for name in names:
            cached_result = await self._get_from_cache(name)
            if cached_result is not None:
                cache_results[name] = cached_result
        
        # Identify which names need to be looked up
        names_to_lookup = [name for name in names if name not in cache_results]
        
        if names_to_lookup:
            logger.info(f"Looking up {len(names_to_lookup)} names not found in cache")
            
            # Process in chunks to avoid overwhelming the API
            chunk_size = 5
            for i in range(0, len(names_to_lookup), chunk_size):
                chunk = names_to_lookup[i:i+chunk_size]
                chunk_results = {}
                
                # Process each name in the chunk concurrently
                tasks = [self._lookup_entity_name(name, target_biolink_type) for name in chunk]
                chunk_mappings = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process the results
                for j, name in enumerate(chunk):
                    mapping_result = chunk_mappings[j]
                    
                    # Handle exceptions
                    if isinstance(mapping_result, Exception):
                        logger.error(f"Error mapping {name}: {str(mapping_result)}")
                        chunk_results[name] = (None, None)
                        continue
                    
                    if not mapping_result:
                        logger.debug(f"No mapping found for {name}")
                        chunk_results[name] = (None, None)
                        continue
                    
                    # Extract identifiers and scores
                    target_ids = []
                    best_score = 0.0
                    
                    for match in mapping_result:
                        curie = match.get("curie", "")
                        score = float(match.get("score", 0))
                        
                        if not curie:
                            continue
                        
                        # Extract the identifier part
                        identifier = self._extract_identifier_from_curie(curie)
                        
                        if identifier:
                            target_ids.append(identifier)
                            if score > best_score:
                                best_score = score
                    
                    if target_ids:
                        logger.debug(f"Mapped {name} to {len(target_ids)} identifiers: {target_ids}")
                        chunk_results[name] = (target_ids, str(best_score))
                    else:
                        logger.debug(f"No valid identifiers found for {name}")
                        chunk_results[name] = (None, None)
                
                # Update cache and results with this chunk
                await self._add_many_to_cache(chunk_results)
                results.update(chunk_results)
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
        
        # Add cached results to final results
        results.update(cache_results)
        
        return results
    
    async def reverse_map_identifiers(
        self, identifiers: List[str], **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Reverse mapping is not directly supported by the Name Resolution API.
        
        This implementation raises a NotImplementedError as it's not feasible
        to efficiently map from identifiers to names with this API.
        
        Args:
            identifiers: List of identifiers to map back to names.
            **kwargs: Additional keyword arguments.
                   
        Raises:
            NotImplementedError: Always raised as this method is not supported.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement reverse_map_identifiers "
            f"as the Name Resolution API does not efficiently support mapping from "
            f"identifiers to names."
        )