"""UniChem Mapping Client for Biomapper

A client for mapping metabolite identifiers between different chemical databases
using the UniChem REST API. This client implements the standard BaseMappingClient
interface for use with MappingExecutor.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union

from biomapper.mapping.clients.base_client import BaseMappingClient, CachedMappingClientMixin
from biomapper.core.exceptions import ClientExecutionError

logger = logging.getLogger(__name__)


class UniChemClient(CachedMappingClientMixin, BaseMappingClient):
    """
    Client for mapping metabolite identifiers using the UniChem REST API.
    
    This client supports mapping between different chemical identifier systems including:
    - PubChem
    - ChEBI
    - HMDB
    - KEGG
    - InChIKey
    - LIPID MAPS
    - ChemSpider
    and many others.
    
    Configuration options:
    - source_db: Source database name (e.g., "PUBCHEM", "CHEBI")
    - target_db: Target database name (e.g., "PUBCHEM", "CHEBI")
    - timeout: Request timeout in seconds (default 30)
    - max_retries: Maximum number of retry attempts for failed requests (default 3)
    - backoff_factor: Exponential backoff factor for retries (default 0.5)
    """
    
    # UniChem source mappings
    # Source: https://www.ebi.ac.uk/unichem/sources
    SOURCE_IDS = {
        "CHEMBL": 1,
        "HMDB": 2,
        "DRUGBANK": 3,
        "PDB": 4,
        "KEGG": 6,
        "CHEBI": 7,
        "CAS": 9,
        "CHEMSPIDER": 10,
        "BRENDA": 12,
        "LIPIDMAPS": 18,
        "ZINC": 19,
        "GTOPDB": 21,
        "PUBCHEM": 22,
        "BINDINGDB": 25,
        "ATLAS": 29,
        "MOLPORT": 33,
        "SELLECK": 37,
        "EMOLECULES": 38,
        "METABOLIGHTS": 39,
        "COMPTOX": 46,
        # Special value for InChI Key searches
        "INCHIKEY": "inchikey",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the UniChem client.
        
        Args:
            config: Optional configuration dictionary with client-specific settings.
                   - source_db: Source database name (e.g., "PUBCHEM", "CHEBI")
                   - target_db: Target database name (e.g., "PUBCHEM", "CHEBI")
                   - timeout: Request timeout in seconds (default 30)
                   - max_retries: Maximum number of retry attempts (default 3)
                   - backoff_factor: Exponential backoff factor for retries (default 0.5)
        """
        # Default configuration
        default_config = {
            "base_url": "https://www.ebi.ac.uk/unichem/rest",
            "timeout": 30,
            "max_retries": 3,
            "backoff_factor": 0.5,
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        # Initialize parent classes (order matters for multiple inheritance)
        super().__init__(config=default_config, cache_size=2048)
        
        # Initialize internal state
        self._session = None
        self._initialized = False
        
        # Normalize source and target database names to uppercase
        self.source_db = self._config.get("source_db", "").upper()
        self.target_db = self._config.get("target_db", "").upper()
        
        logger.info(f"Initialized UniChemClient with source_db={self.source_db}, target_db={self.target_db}")
    
    def get_required_config_keys(self) -> List[str]:
        """
        Return a list of required configuration keys for this client.
        
        Returns:
            List of required configuration key names.
        """
        # We require source_db and target_db
        return ["source_db", "target_db"]
    
    async def _ensure_session(self):
        """
        Ensure that an HTTP session exists, creating it if necessary.
        """
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout", 30))
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
    
    async def close(self):
        """
        Close the HTTP session when finished.
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._initialized = False
    
    async def _get_unichem_source_id(self, db_name: str) -> Union[int, str]:
        """
        Get the UniChem source ID number for a database name.
        
        Args:
            db_name: The database name to get the ID for.
            
        Returns:
            The UniChem source ID (integer or string for special cases like "inchikey").
            
        Raises:
            ClientExecutionError: If the database name is not supported.
        """
        db_name = db_name.upper()
        if db_name not in self.SOURCE_IDS:
            supported_sources = ", ".join(self.SOURCE_IDS.keys())
            error_msg = f"Unsupported database: {db_name}. Supported sources: {supported_sources}"
            logger.error(error_msg)
            raise ClientExecutionError(
                error_msg,
                client_name=self.__class__.__name__,
                details={"supported_sources": list(self.SOURCE_IDS.keys())}
            )
        
        return self.SOURCE_IDS[db_name]
    
    async def _perform_request(self, url: str) -> Dict[str, Any]:
        """
        Perform an HTTP request to the UniChem API with retry logic.
        
        Args:
            url: The complete URL to request.
            
        Returns:
            The JSON response parsed as a dictionary.
            
        Raises:
            ClientExecutionError: If the request fails after max_retries.
        """
        await self._ensure_session()
        
        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)
        
        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        # No mappings found
                        return {}
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"UniChem API request failed with status {response.status}: {error_text}"
                        )
                        
                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2 ** attempt)
                            logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                        else:
                            raise ClientExecutionError(
                                f"UniChem API request failed after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "url": url,
                                    "status": response.status,
                                    "response": error_text
                                }
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error during UniChem API request: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2 ** attempt)
                    logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise ClientExecutionError(
                        f"HTTP error during UniChem API request after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"url": url, "exception": str(e)}
                    )
    
    async def _get_compound_mappings(self, compound_id: str, src_db: str) -> Dict[str, List[str]]:
        """
        Get mappings for a compound ID from the UniChem API.
        
        Args:
            compound_id: The compound ID to look up.
            src_db: The source database name.
            
        Returns:
            A dictionary mapping target database names to lists of compound IDs.
        """
        # Skip empty IDs
        if not compound_id or compound_id.strip() == "":
            return {}
        
        # Handle case where the source is specified as InChIKey
        if src_db.upper() == "INCHIKEY":
            url = f"{self._config['base_url']}/inchikey/{compound_id}"
        else:
            # Get the numeric source ID
            src_id = await self._get_unichem_source_id(src_db)
            url = f"{self._config['base_url']}/src_compound_id/{compound_id}/src_id/{src_id}"
        
        try:
            result = await self._perform_request(url)
            
            # Handle the response format, which can vary based on the endpoint
            mappings = {}
            
            if not result or (isinstance(result, list) and len(result) == 0):
                return {}
            
            # InChIKey response has a different format
            if src_db.upper() == "INCHIKEY":
                # Extract mappings from the response
                for item in result:
                    src_name = item.get("src_name", "").upper()
                    compound_id = item.get("src_compound_id", "")
                    if src_name and compound_id:
                        if src_name not in mappings:
                            mappings[src_name] = []
                        
                        if compound_id not in mappings[src_name]:
                            mappings[src_name].append(compound_id)
            else:
                # Standard mappings response
                for item in result:
                    src_name = item.get("src_name", "").upper()
                    compound_id = item.get("src_compound_id", "")
                    if src_name and compound_id:
                        if src_name not in mappings:
                            mappings[src_name] = []
                        
                        if compound_id not in mappings[src_name]:
                            mappings[src_name].append(compound_id)
            
            return mappings
            
        except ClientExecutionError:
            # Just re-raise the original error
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.error(f"Unexpected error in _get_compound_mappings: {str(e)}")
            raise ClientExecutionError(
                f"Unexpected error in UniChem API request: {str(e)}",
                client_name=self.__class__.__name__,
                details={"compound_id": compound_id, "src_db": src_db, "exception": str(e)}
            )
    
    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map metabolite identifiers from the source database to the target database.
        
        Args:
            identifiers: List of source compound identifiers to map.
            config: Optional per-call configuration that may override instance config.
                   Supported keys:
                   - source_db: Override the source database for this specific call
                   - target_db: Override the target database for this specific call
                   
        Returns:
            A dictionary mapping each input identifier to a tuple containing:
            - The first element is a list of mapped target identifiers or None if mapping failed
            - The second element is always None for this client (no component ID needed)
        """
        if not identifiers:
            return {}
        
        # Apply any per-call config overrides
        call_config = self._config.copy()
        if config:
            call_config.update(config)
        
        # Get source and target DB (use instance values if not overridden)
        source_db = call_config.get("source_db", self.source_db)
        target_db = call_config.get("target_db", self.target_db)
        
        if not source_db or not target_db:
            raise ClientExecutionError(
                "Source database or target database not specified",
                client_name=self.__class__.__name__,
                details={"source_db": source_db, "target_db": target_db}
            )
        
        logger.info(f"Mapping {len(identifiers)} identifiers from {source_db} to {target_db}")
        
        # Create results dictionary
        results = {}
        
        # Check cache first for all identifiers
        cache_results = {}
        for identifier in identifiers:
            cached_result = await self._get_from_cache(identifier)
            if cached_result is not None:
                cache_results[identifier] = cached_result
        
        # Identify which identifiers need to be looked up
        identifiers_to_lookup = [id for id in identifiers if id not in cache_results]
        
        if identifiers_to_lookup:
            logger.info(f"Looking up {len(identifiers_to_lookup)} identifiers not found in cache")
            
            # Process in chunks to avoid overwhelming the API
            chunk_size = 20
            for i in range(0, len(identifiers_to_lookup), chunk_size):
                chunk = identifiers_to_lookup[i:i+chunk_size]
                chunk_results = {}
                
                # Process each identifier in the chunk concurrently
                tasks = [self._get_compound_mappings(identifier, source_db) for identifier in chunk]
                chunk_mappings = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process the results
                for j, identifier in enumerate(chunk):
                    mapping_result = chunk_mappings[j]
                    
                    # Handle exceptions
                    if isinstance(mapping_result, Exception):
                        logger.error(f"Error mapping {identifier}: {str(mapping_result)}")
                        chunk_results[identifier] = (None, None)
                        continue
                    
                    # Extract target IDs if they exist
                    target_ids = mapping_result.get(target_db, []) if mapping_result else []
                    
                    if target_ids:
                        logger.debug(f"Mapped {identifier} to {len(target_ids)} {target_db} IDs: {target_ids}")
                        chunk_results[identifier] = (target_ids, None)
                    else:
                        logger.debug(f"No {target_db} mapping found for {identifier}")
                        chunk_results[identifier] = (None, None)
                
                # Update cache and results with this chunk
                await self._add_many_to_cache(chunk_results)
                results.update(chunk_results)
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
        
        # Add cached results to final results
        results.update(cache_results)
        
        return results
    
    async def reverse_map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map metabolite identifiers in the reverse direction (target DB to source DB).
        
        This implementation simply swaps the source and target databases and calls
        map_identifiers, which matches the behavior expected by MappingExecutor.
        
        Args:
            identifiers: List of target identifiers to map back to source identifiers.
            config: Optional per-call configuration that may override instance config.
                   
        Returns:
            A dictionary mapping each input identifier to a tuple containing:
            - The first element is a list of mapped source identifiers or None if mapping failed
            - The second element is always None for this client (no component ID needed)
        """
        if not identifiers:
            return {}
        
        # Apply any per-call config overrides
        call_config = self._config.copy()
        if config:
            call_config.update(config)
        
        # Swap source and target for reverse mapping
        source_db = call_config.get("target_db", self.target_db)
        target_db = call_config.get("source_db", self.source_db)
        
        # Create a config for the forward mapping method with swapped DBs
        reverse_config = call_config.copy()
        reverse_config["source_db"] = source_db
        reverse_config["target_db"] = target_db
        
        logger.info(f"Reverse mapping {len(identifiers)} identifiers from {source_db} to {target_db}")
        
        # Use the forward mapping implementation with swapped source/target
        return await self.map_identifiers(identifiers, config=reverse_config)
