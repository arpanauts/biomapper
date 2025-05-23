"""Simplified UMLS Client for Biomapper

A simplified client for mapping metabolite and compound names to standardized identifiers
using the UMLS Terminology Services (UTS) REST API. This client implements the
standard BaseMappingClient interface for use with MappingExecutor but only uses
the search functionality of the UMLS API.
"""

import logging
import aiohttp
import asyncio
import os
import time
import re
from typing import Dict, List, Optional, Any, Tuple, Set, Union

from biomapper.mapping.clients.base_client import BaseMappingClient, CachedMappingClientMixin
from biomapper.core.exceptions import ClientExecutionError, ClientInitializationError

logger = logging.getLogger(__name__)


class UMLSClientSimplified(CachedMappingClientMixin, BaseMappingClient):
    """
    Simplified client for concept mapping via UMLS Terminology Services.
    
    This client supports mapping between entity names and Concept Unique Identifiers (CUIs),
    with a focus on chemical substances and metabolites. It leverages only the search
    functionality of the UMLS Terminology Services (UTS) REST API.
    
    Configuration options:
    - api_key: UMLS API key for authentication (required)
    - target_db: Target database name for mapping (e.g., "CHEBI", "PUBCHEM")
    - timeout: Request timeout in seconds (default 30)
    - max_retries: Maximum number of retry attempts for failed requests (default 3)
    - backoff_factor: Exponential backoff factor for retries (default 0.5)
    """
    
    # Mapping of target database names to UMLS source abbreviations
    DB_TO_UMLS_SOURCE = {
        "PUBCHEM": "PUBCHEM",
        "CHEBI": "CHEBI",
        "HMDB": "HMDB",
        "KEGG": "KEGG",
        "DRUGBANK": "DRUGBANKID",
        "MESH": "MSH",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the simplified UMLS client.
        
        Args:
            config: Optional configuration dictionary with client-specific settings.
                   - api_key: UMLS API key for authentication (required)
                   - target_db: Target database name (e.g., "CHEBI", "PUBCHEM")
                   - timeout: Request timeout in seconds (default 30)
                   - max_retries: Maximum number of retry attempts (default 3)
                   - backoff_factor: Exponential backoff factor for retries (default 0.5)
        """
        # Default configuration
        default_config = {
            "base_url": "https://uts-ws.nlm.nih.gov/rest",
            "api_version": "current",
            "timeout": 30,
            "max_retries": 3,
            "backoff_factor": 0.5,
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        # Get API key from config or environment variable
        api_key = default_config.get("api_key")
        if not api_key:
            api_key = os.environ.get("UMLS_API_KEY")
            if api_key:
                default_config["api_key"] = api_key
        
        # Initialize parent classes (order matters for multiple inheritance)
        super().__init__(config=default_config, cache_size=2048)
        
        # Initialize internal state
        self._session = None
        self._initialized = False
        
        # Normalize target database name to uppercase
        self.target_db = self._config.get("target_db", "").upper()
        
        logger.info(f"Initialized UMLSClientSimplified with target_db={self.target_db}")
    
    def get_required_config_keys(self) -> List[str]:
        """
        Return a list of required configuration keys for this client.
        
        Returns:
            List of required configuration key names.
        """
        # We require api_key for authentication
        return ["api_key"]
    
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
    
    async def _perform_search(
        self, 
        query: str, 
        search_type: str = "exact"
    ) -> List[Dict[str, Any]]:
        """
        Perform a search in the UMLS Metathesaurus using direct API key authentication.
        
        Args:
            query: The term to search for.
            search_type: The type of search (exact, words, etc.)
            
        Returns:
            List of dictionaries containing the search results.
            
        Raises:
            ClientExecutionError: If the search fails.
        """
        await self._ensure_session()
        
        # Get API key
        api_key = self._config.get("api_key")
        if not api_key:
            raise ClientExecutionError(
                "UMLS API key not provided",
                client_name=self.__class__.__name__,
                details={"error": "Missing API key"}
            )
        
        # Build search URL and parameters
        search_url = f"{self._config.get('base_url')}/search/{self._config.get('api_version')}"
        
        params = {
            "string": query,
            "searchType": search_type,
            "pageSize": 50,
            "pageNumber": 1,
            "returnIdType": "concept",
            "apiKey": api_key,  # Direct API key authentication
        }
        
        logger.debug(f"Searching UMLS for: {query}")
        
        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)
        
        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(search_url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        results = result.get("result", {}).get("results", [])
                        logger.debug(f"Found {len(results)} results for {query}")
                        return results
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"UMLS search failed with status {response.status}: {error_text}"
                        )
                        
                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2 ** attempt)
                            logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                        else:
                            raise ClientExecutionError(
                                f"UMLS search failed after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "query": query,
                                    "status": response.status,
                                    "response": error_text
                                }
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error during UMLS search: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2 ** attempt)
                    logger.info(f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise ClientExecutionError(
                        f"HTTP error during UMLS search after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={
                            "query": query,
                            "exception": str(e)
                        }
                    )
    
    def _extract_cui_from_search_result(self, result: Dict[str, Any]) -> str:
        """
        Extract the CUI from a search result.
        
        Args:
            result: Search result dictionary from the UMLS API.
            
        Returns:
            The CUI string.
        """
        return result.get("ui", "")
    
    def _get_confidence_from_search_result(self, result: Dict[str, Any], index: int) -> float:
        """
        Calculate a confidence score for a search result.
        
        Args:
            result: Search result dictionary from the UMLS API.
            index: The index of the result in the search results list.
            
        Returns:
            A confidence score between 0 and 1.
        """
        # Simple confidence scoring based on result position and match type
        base_score = 1.0 - (index * 0.05)  # Decrease score for later results
        
        # Adjust score based on match exactness
        name = result.get("name", "").lower()
        if name == result.get("query", "").lower():
            base_score *= 1.0  # Exact match
        else:
            base_score *= 0.8  # Partial match
        
        # Ensure score is between 0 and 1
        return max(0.1, min(1.0, base_score))
    
    async def map_identifiers(
        self, terms: List[str], **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map terms to standardized identifiers via UMLS search.
        
        Args:
            terms: List of terms to map.
            **kwargs: Additional keyword arguments, which may include:
                     - config: Optional per-call configuration
                     
        Returns:
            A dictionary mapping each input term to a tuple containing:
            - The first element is a list of mapped target identifiers or None if mapping failed
            - The second element is the confidence score as a string, or None if not available
        """
        if not terms:
            return {}
        
        # Extract config from kwargs if provided
        config = kwargs.get("config", {})
        
        # Apply any per-call config overrides
        call_config = self._config.copy()
        if config:
            call_config.update(config)
        
        # Get target DB (use instance value if not overridden)
        target_db = call_config.get("target_db", self.target_db).upper()
        
        # Get the corresponding UMLS source abbreviation
        target_source = None
        if target_db in self.DB_TO_UMLS_SOURCE:
            target_source = self.DB_TO_UMLS_SOURCE[target_db]
        
        if not target_source:
            logger.warning(f"Unsupported target database: {target_db}")
            # Return empty mappings for all terms
            return {term: (None, None) for term in terms}
        
        logger.info(f"Mapping {len(terms)} terms to {target_db} identifiers via UMLS search")
        
        # Create results dictionary
        results = {}
        
        # Check cache first for all terms
        cache_results = {}
        for term in terms:
            cached_result = await self._get_from_cache(term)
            if cached_result is not None:
                cache_results[term] = cached_result
        
        # Identify which terms need to be looked up
        terms_to_lookup = [term for term in terms if term not in cache_results]
        
        if terms_to_lookup:
            logger.info(f"Looking up {len(terms_to_lookup)} terms not found in cache")
            
            # Process each term individually
            for term in terms_to_lookup:
                try:
                    # Perform an exact search first
                    search_results = await self._perform_search(term, search_type="exact")
                    
                    if not search_results:
                        # Try a less strict search if exact match fails
                        search_results = await self._perform_search(term, search_type="words")
                    
                    if not search_results:
                        logger.debug(f"No search results found for {term}")
                        results[term] = (None, None)
                        continue
                    
                    # Process search results to extract CUIs and score them
                    identifiers = []
                    best_confidence = 0.0
                    
                    for i, result in enumerate(search_results):
                        cui = self._extract_cui_from_search_result(result)
                        if cui and cui not in identifiers:
                            identifiers.append(cui)
                            
                            # Calculate confidence score
                            confidence = self._get_confidence_from_search_result(result, i)
                            if confidence > best_confidence:
                                best_confidence = confidence
                    
                    if identifiers:
                        logger.debug(f"Mapped {term} to {len(identifiers)} identifiers: {identifiers}")
                        results[term] = (identifiers, str(best_confidence))
                    else:
                        logger.debug(f"No valid identifiers found for {term}")
                        results[term] = (None, None)
                    
                    # Update cache
                    await self._add_to_cache(term, results[term])
                    
                except Exception as e:
                    logger.error(f"Error mapping {term}: {str(e)}")
                    results[term] = (None, None)
                
                # Add a short delay between requests to avoid overwhelming the API
                await asyncio.sleep(0.5)
        
        # Add cached results to final results
        results.update(cache_results)
        
        return results
    
    async def reverse_map_identifiers(
        self, identifiers: List[str], **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map identifiers to terms via UMLS.
        
        This implementation simply searches for the identifier as a term.
        
        Args:
            identifiers: List of identifiers to map back to terms.
            **kwargs: Additional keyword arguments, which may include:
                     - config: Optional per-call configuration
                     
        Returns:
            A dictionary mapping each input identifier to a tuple containing:
            - The first element is a list of mapped terms or None if mapping failed
            - The second element is the confidence score as a string, or None if not available
        """
        if not identifiers:
            return {}
        
        # Extract config from kwargs if provided
        config = kwargs.get("config", {})
        
        # Apply any per-call config overrides
        call_config = self._config.copy()
        if config:
            call_config.update(config)
        
        # Get source DB (use target_db as source for reverse mapping)
        source_db = call_config.get("target_db", self.target_db).upper()
        
        # Get the corresponding UMLS source abbreviation
        source_source = None
        if source_db in self.DB_TO_UMLS_SOURCE:
            source_source = self.DB_TO_UMLS_SOURCE[source_db]
        
        if not source_source:
            logger.warning(f"Unsupported source database for reverse mapping: {source_db}")
            # Return empty mappings for all identifiers
            return {identifier: (None, None) for identifier in identifiers}
        
        logger.warning(
            f"Reverse mapping with UMLS is not optimal. "
            f"Consider using a database-specific client for reverse mapping."
        )
        
        logger.info(f"Reverse mapping {len(identifiers)} identifiers from {source_db}")
        
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
            
            # Process each identifier
            for identifier in identifiers_to_lookup:
                try:
                    # Search for the identifier with source prefix
                    search_query = f"{source_source}:{identifier}"
                    search_results = await self._perform_search(search_query, search_type="exact")
                    
                    if not search_results:
                        logger.debug(f"No results found for {search_query}")
                        results[identifier] = (None, None)
                        continue
                    
                    # Extract names from search results
                    names = []
                    best_confidence = 0.0
                    
                    for i, result in enumerate(search_results):
                        name = result.get("name")
                        if name and name not in names:
                            names.append(name)
                            
                            # Calculate confidence score
                            confidence = self._get_confidence_from_search_result(result, i)
                            if confidence > best_confidence:
                                best_confidence = confidence
                    
                    if names:
                        logger.debug(f"Mapped {identifier} to {len(names)} names: {names}")
                        results[identifier] = (names, str(best_confidence))
                    else:
                        logger.debug(f"No names found for {identifier}")
                        results[identifier] = (None, None)
                    
                    # Update cache
                    await self._add_to_cache(identifier, results[identifier])
                    
                except Exception as e:
                    logger.error(f"Error reverse mapping {identifier}: {str(e)}")
                    results[identifier] = (None, None)
                
                # Add a delay between requests to avoid overwhelming the API
                await asyncio.sleep(0.5)
        
        # Add cached results to final results
        results.update(cache_results)
        
        return results