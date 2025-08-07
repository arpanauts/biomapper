"""UMLS Terminology Services Client for Biomapper

A client for mapping metabolite and compound names to standardized identifiers
using the UMLS Terminology Services (UTS) REST API. This client implements the
standard BaseMappingClient interface for use with MappingExecutor.
"""

import logging
import aiohttp
import asyncio
import os
import time
import re
from typing import Dict, List, Optional, Any, Tuple

from biomapper.mapping.clients.base_client import (
    BaseMappingClient,
    CachedMappingClientMixin,
)
from biomapper.core.exceptions import ClientExecutionError

logger = logging.getLogger(__name__)


class UMLSClient(CachedMappingClientMixin, BaseMappingClient):
    """
    Client for concept mapping via UMLS Terminology Services.

    This client supports mapping between entity names and Concept Unique Identifiers (CUIs),
    with a focus on chemical substances and metabolites. It leverages the UMLS
    Terminology Services (UTS) REST API.

    Configuration options:
    - api_key: UMLS API key for authentication (required)
    - target_db: Target database name for mapping (e.g., "CHEBI", "PUBCHEM")
    - timeout: Request timeout in seconds (default 30)
    - max_retries: Maximum number of retry attempts for failed requests (default 3)
    - backoff_factor: Exponential backoff factor for retries (default 0.5)
    - tgt_validity_hours: Validity period for TGT in hours (default 7)
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

    # Semantic types for metabolites/compounds
    METABOLITE_SEMANTIC_TYPES = [
        "T109",  # Organic Chemical
        "T119",  # Lipid
        "T123",  # Biologically Active Substance
        "T127",  # Vitamin
        "T196",  # Element, Ion, or Isotope
        "T197",  # Inorganic Chemical
        "T118",  # Carbohydrate
        "T121",  # Pharmacologic Substance
        "T131",  # Hazardous or Poisonous Substance
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the UMLS client.

        Args:
            config: Optional configuration dictionary with client-specific settings.
                   - api_key: UMLS API key for authentication (required)
                   - target_db: Target database name (e.g., "CHEBI", "PUBCHEM")
                   - timeout: Request timeout in seconds (default 30)
                   - max_retries: Maximum number of retry attempts (default 3)
                   - backoff_factor: Exponential backoff factor for retries (default 0.5)
                   - tgt_validity_hours: Validity period for TGT in hours (default 7)
        """
        # Default configuration
        default_config = {
            "base_url": "https://uts-ws.nlm.nih.gov/rest",
            "auth_url": "https://utslogin.nlm.nih.gov/cas/v1/api-key",
            "api_version": "current",
            "timeout": 30,
            "max_retries": 3,
            "backoff_factor": 0.5,
            "tgt_validity_hours": 7,
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
        self._tgt = None  # Ticket Granting Ticket
        self._tgt_timestamp = 0  # When the TGT was obtained

        # Normalize target database name to uppercase
        self.target_db = self._config.get("target_db", "").upper()

        logger.info(f"Initialized UMLSClient with target_db={self.target_db}")

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
            self._tgt = None
            self._tgt_timestamp = 0
            logger.debug("Closed HTTP session")

    async def _get_tgt(self) -> str:
        """
        Get a Ticket Granting Ticket (TGT) from the UMLS authentication service.

        The TGT is used to obtain single-use Service Tickets for each API request.
        TGTs are valid for multiple hours, so we cache them to avoid unnecessary auth requests.

        Returns:
            The TGT string for obtaining service tickets.

        Raises:
            ClientExecutionError: If authentication fails.
        """
        await self._ensure_session()

        # Check if we have a valid TGT already
        current_time = time.time()
        tgt_validity_hours = self._config.get("tgt_validity_hours", 7)
        tgt_validity_seconds = tgt_validity_hours * 3600

        if self._tgt and (current_time - self._tgt_timestamp) < tgt_validity_seconds:
            logger.debug("Using existing TGT")
            return self._tgt

        # Get a new TGT
        api_key = self._config.get("api_key")
        if not api_key:
            raise ClientExecutionError(
                "UMLS API key not provided",
                client_name=self.__class__.__name__,
                details={"error": "Missing API key"},
            )

        auth_url = self._config.get("auth_url")
        data = {"apikey": api_key}

        logger.debug("Obtaining new TGT")

        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)

        for attempt in range(max_retries + 1):
            try:
                async with self._session.post(auth_url, data=data) as response:
                    if response.status == 201:
                        # Parse the TGT from the response
                        response_text = await response.text()

                        # Extract TGT URL from response using regex
                        # Example: <form action="https://utslogin.nlm.nih.gov/cas/v1/api-key/TGT-12345-67890-abcde">
                        match = re.search(r'action="([^"]+)"', response_text)
                        if match:
                            tgt_url = match.group(1)
                            self._tgt = tgt_url
                            self._tgt_timestamp = current_time
                            logger.debug(f"Obtained new TGT: {tgt_url}")
                            return tgt_url
                        else:
                            raise ClientExecutionError(
                                "Could not extract TGT from response",
                                client_name=self.__class__.__name__,
                                details={"response": response_text},
                            )
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"UMLS authentication failed with status {response.status}: {error_text}"
                        )

                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2**attempt)
                            logger.info(
                                f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                        else:
                            raise ClientExecutionError(
                                f"UMLS authentication failed after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "status": response.status,
                                    "response": error_text,
                                },
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error during UMLS authentication: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    logger.info(
                        f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise ClientExecutionError(
                        f"HTTP error during UMLS authentication after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"exception": str(e)},
                    )

    async def _get_service_ticket(self) -> str:
        """
        Get a single-use Service Ticket (ST) for making API requests.

        Uses the TGT to obtain a Service Ticket that can be used for a single API request.

        Returns:
            The Service Ticket string.

        Raises:
            ClientExecutionError: If obtaining the service ticket fails.
        """
        await self._ensure_session()

        # Make sure we have a valid TGT
        tgt_url = await self._get_tgt()

        # Get a service ticket
        service_url = (
            f"{self._config.get('base_url')}/search/{self._config.get('api_version')}"
        )
        data = {"service": service_url}

        logger.debug("Obtaining service ticket")

        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)

        for attempt in range(max_retries + 1):
            try:
                async with self._session.post(tgt_url, data=data) as response:
                    if response.status == 200:
                        service_ticket = await response.text()
                        logger.debug(f"Obtained service ticket: {service_ticket}")
                        return service_ticket
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"Failed to get service ticket with status {response.status}: {error_text}"
                        )

                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2**attempt)
                            logger.info(
                                f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                        else:
                            # TGT might be invalid, clear it so we get a new one next time
                            self._tgt = None
                            self._tgt_timestamp = 0

                            raise ClientExecutionError(
                                f"Failed to get service ticket after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "status": response.status,
                                    "response": error_text,
                                },
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error while getting service ticket: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    logger.info(
                        f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    # TGT might be invalid, clear it so we get a new one next time
                    self._tgt = None
                    self._tgt_timestamp = 0

                    raise ClientExecutionError(
                        f"HTTP error while getting service ticket after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"exception": str(e)},
                    )

    async def _perform_search(
        self,
        query: str,
        search_type: str = "exact",
        semantic_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform a search in the UMLS Metathesaurus.

        Args:
            query: The term to search for.
            search_type: The type of search (exact, words, etc.)
            semantic_types: Optional list of semantic types to filter by.

        Returns:
            List of dictionaries containing the search results.

        Raises:
            ClientExecutionError: If the search fails.
        """
        await self._ensure_session()

        # Get a service ticket
        service_ticket = await self._get_service_ticket()

        # Build search URL and parameters
        search_url = (
            f"{self._config.get('base_url')}/search/{self._config.get('api_version')}"
        )

        params = {
            "string": query,
            "ticket": service_ticket,
            "searchType": search_type,
            "pageSize": 100,
            "pageNumber": 1,
            "returnIdType": "concept",
        }

        # Add semantic type filtering if provided
        if semantic_types:
            params["sabs"] = ",".join(semantic_types)

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
                            delay = backoff_factor * (2**attempt)
                            logger.info(
                                f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)

                            # Get a new service ticket for the retry
                            service_ticket = await self._get_service_ticket()
                            params["ticket"] = service_ticket
                        else:
                            raise ClientExecutionError(
                                f"UMLS search failed after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "query": query,
                                    "status": response.status,
                                    "response": error_text,
                                },
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error during UMLS search: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    logger.info(
                        f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                    # Get a new service ticket for the retry
                    service_ticket = await self._get_service_ticket()
                    params["ticket"] = service_ticket
                else:
                    raise ClientExecutionError(
                        f"HTTP error during UMLS search after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"query": query, "exception": str(e)},
                    )

    async def _get_concept_details(self, cui: str) -> Dict[str, Any]:
        """
        Get detailed information about a UMLS concept.

        Args:
            cui: The Concept Unique Identifier (CUI) to get details for.

        Returns:
            Dictionary containing the concept details.

        Raises:
            ClientExecutionError: If retrieving the concept details fails.
        """
        await self._ensure_session()

        # Get a service ticket
        service_ticket = await self._get_service_ticket()

        # Build concept URL
        concept_url = f"{self._config.get('base_url')}/content/{self._config.get('api_version')}/CUI/{cui}"

        params = {
            "ticket": service_ticket,
        }

        logger.debug(f"Getting details for concept: {cui}")

        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(concept_url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"Got details for concept: {cui}")
                        return result.get("result", {})
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"Failed to get concept details with status {response.status}: {error_text}"
                        )

                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2**attempt)
                            logger.info(
                                f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)

                            # Get a new service ticket for the retry
                            service_ticket = await self._get_service_ticket()
                            params["ticket"] = service_ticket
                        else:
                            raise ClientExecutionError(
                                f"Failed to get concept details after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "cui": cui,
                                    "status": response.status,
                                    "response": error_text,
                                },
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error while getting concept details: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    logger.info(
                        f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                    # Get a new service ticket for the retry
                    service_ticket = await self._get_service_ticket()
                    params["ticket"] = service_ticket
                else:
                    raise ClientExecutionError(
                        f"HTTP error while getting concept details after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"cui": cui, "exception": str(e)},
                    )

    async def _get_concept_atoms(self, cui: str) -> List[Dict[str, Any]]:
        """
        Get the atoms (source-asserted identifiers) for a UMLS concept.

        Args:
            cui: The Concept Unique Identifier (CUI) to get atoms for.

        Returns:
            List of dictionaries containing the concept atoms.

        Raises:
            ClientExecutionError: If retrieving the concept atoms fails.
        """
        await self._ensure_session()

        # Get a service ticket
        service_ticket = await self._get_service_ticket()

        # Build atoms URL
        atoms_url = f"{self._config.get('base_url')}/content/{self._config.get('api_version')}/CUI/{cui}/atoms"

        params = {
            "ticket": service_ticket,
            "pageSize": 100,
        }

        logger.debug(f"Getting atoms for concept: {cui}")

        max_retries = self._config.get("max_retries", 3)
        backoff_factor = self._config.get("backoff_factor", 0.5)

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(atoms_url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        atoms = result.get("result", [])
                        logger.debug(f"Got {len(atoms)} atoms for concept: {cui}")
                        return atoms
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"Failed to get concept atoms with status {response.status}: {error_text}"
                        )

                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2**attempt)
                            logger.info(
                                f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)

                            # Get a new service ticket for the retry
                            service_ticket = await self._get_service_ticket()
                            params["ticket"] = service_ticket
                        else:
                            raise ClientExecutionError(
                                f"Failed to get concept atoms after {max_retries} retries",
                                client_name=self.__class__.__name__,
                                details={
                                    "cui": cui,
                                    "status": response.status,
                                    "response": error_text,
                                },
                            )
            except aiohttp.ClientError as e:
                logger.warning(f"HTTP error while getting concept atoms: {str(e)}")
                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    logger.info(
                        f"Retrying after {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                    # Get a new service ticket for the retry
                    service_ticket = await self._get_service_ticket()
                    params["ticket"] = service_ticket
                else:
                    raise ClientExecutionError(
                        f"HTTP error while getting concept atoms after {max_retries} retries: {str(e)}",
                        client_name=self.__class__.__name__,
                        details={"cui": cui, "exception": str(e)},
                    )

    def _extract_target_identifiers(
        self, atoms: List[Dict[str, Any]], target_source: str
    ) -> List[str]:
        """
        Extract target identifiers from concept atoms.

        Args:
            atoms: List of concept atoms from the UMLS API.
            target_source: The source abbreviation to extract identifiers for.

        Returns:
            List of extracted identifiers.
        """
        target_ids = []

        for atom in atoms:
            # Check if this atom is from the target source
            source = atom.get("rootSource")
            if not source or source != target_source:
                continue

            # Get the identifier
            identifier = atom.get("code")
            if identifier and identifier not in target_ids:
                target_ids.append(identifier)

        return target_ids

    def _is_metabolite_concept(self, concept: Dict[str, Any]) -> bool:
        """
        Check if a concept represents a metabolite or chemical compound.

        Args:
            concept: Concept dictionary from the UMLS API.

        Returns:
            True if the concept is a metabolite, False otherwise.
        """
        semantic_types = concept.get("semanticTypes", [])

        for sem_type in semantic_types:
            type_uri = sem_type.get("uri", "")
            # Extract the semantic type code from the URI
            # URI format: https://uts-ws.nlm.nih.gov/rest/semantic-network/current/TUI/T109
            match = re.search(r"TUI/([^/]+)$", type_uri)
            if match and match.group(1) in self.METABOLITE_SEMANTIC_TYPES:
                return True

        return False

    async def _resolve_term(self, term: str) -> List[Dict[str, Any]]:
        """
        Resolve a term to UMLS concepts and extract target identifiers.

        Args:
            term: The term to resolve.

        Returns:
            List of dictionaries containing the resolved concepts with their details.
        """
        # Skip empty terms
        if not term or term.strip() == "":
            return []

        # Find UMLS concepts matching the term
        search_results = await self._perform_search(term, search_type="exact")

        if not search_results:
            # Try a less strict search if exact match fails
            search_results = await self._perform_search(term, search_type="words")

        # Filter for metabolite concepts and gather full details
        metabolite_concepts = []

        for result in search_results:
            cui = result.get("ui")
            if not cui:
                continue

            # Get full concept details
            concept_details = await self._get_concept_details(cui)

            # Check if this is a metabolite concept
            if self._is_metabolite_concept(concept_details):
                # Get the atoms for this concept
                atoms = await self._get_concept_atoms(cui)

                # Add atoms to the concept
                concept_details["atoms"] = atoms

                # Calculate a match score based on various factors
                name_similarity = 1.0
                if term.lower() != concept_details.get("name", "").lower():
                    # Simple name similarity score (placeholder for more sophisticated algorithm)
                    name_similarity = 0.8

                concept_details["score"] = name_similarity

                metabolite_concepts.append(concept_details)

        return metabolite_concepts

    async def map_identifiers(
        self, terms: List[str], **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map terms to standardized identifiers via UMLS.

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

        logger.info(f"Mapping {len(terms)} terms to {target_db} identifiers via UMLS")

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

            # Process in chunks to avoid overwhelming the API
            chunk_size = 3  # Small chunk size due to API complexity
            for i in range(0, len(terms_to_lookup), chunk_size):
                chunk = terms_to_lookup[i : i + chunk_size]
                chunk_results = {}

                # Process each term in the chunk concurrently
                tasks = [self._resolve_term(term) for term in chunk]
                chunk_mappings = await asyncio.gather(*tasks, return_exceptions=True)

                # Process the results
                for j, term in enumerate(chunk):
                    mapping_result = chunk_mappings[j]

                    # Handle exceptions
                    if isinstance(mapping_result, Exception):
                        logger.error(f"Error mapping {term}: {str(mapping_result)}")
                        chunk_results[term] = (None, None)
                        continue

                    if not mapping_result:
                        logger.debug(f"No UMLS concepts found for {term}")
                        chunk_results[term] = (None, None)
                        continue

                    # Extract target identifiers from all matching concepts
                    all_target_ids = []
                    best_score = 0.0

                    for concept in mapping_result:
                        atoms = concept.get("atoms", [])
                        target_ids = self._extract_target_identifiers(
                            atoms, target_source
                        )

                        if target_ids:
                            all_target_ids.extend(target_ids)

                            # Update best score if this concept has a better match
                            score = float(concept.get("score", 0))
                            if score > best_score:
                                best_score = score

                    # Remove duplicates while preserving order
                    seen = set()
                    unique_target_ids = []
                    for id in all_target_ids:
                        if id not in seen:
                            seen.add(id)
                            unique_target_ids.append(id)

                    if unique_target_ids:
                        logger.debug(
                            f"Mapped {term} to {len(unique_target_ids)} identifiers: {unique_target_ids}"
                        )
                        chunk_results[term] = (unique_target_ids, str(best_score))
                    else:
                        logger.debug(f"No {target_db} identifiers found for {term}")
                        chunk_results[term] = (None, None)

                # Update cache and results with this chunk
                await self._add_many_to_cache(chunk_results)
                results.update(chunk_results)

                # Larger delay for UMLS API to avoid rate limiting
                await asyncio.sleep(0.5)

        # Add cached results to final results
        results.update(cache_results)

        return results

    async def reverse_map_identifiers(
        self, identifiers: List[str], **kwargs
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map identifiers to terms via UMLS.

        This implementation is not very efficient with UMLS, but provides basic functionality.

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
            logger.warning(
                f"Unsupported source database for reverse mapping: {source_db}"
            )
            # Return empty mappings for all identifiers
            return {identifier: (None, None) for identifier in identifiers}

        logger.warning(
            "Reverse mapping with UMLS is not optimal and may be slow. "
            "Consider using a database-specific client for reverse mapping."
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
            logger.info(
                f"Looking up {len(identifiers_to_lookup)} identifiers not found in cache"
            )

            # For reverse mapping, we'll search for the code directly
            # This is not very efficient with UMLS, but it's the best we can do
            for identifier in identifiers_to_lookup:
                try:
                    # Search for the identifier
                    search_query = f"{source_source}:{identifier}"
                    search_results = await self._perform_search(
                        search_query, search_type="exact"
                    )

                    if not search_results:
                        logger.debug(f"No results found for {search_query}")
                        results[identifier] = (None, None)
                        continue

                    # Extract names from the search results
                    names = []
                    best_score = 0.0

                    for result in search_results:
                        name = result.get("name")
                        if name and name not in names:
                            names.append(name)

                            # Simple scoring based on result order
                            score = 1.0 - (search_results.index(result) * 0.1)
                            if score > best_score:
                                best_score = score

                    if names:
                        logger.debug(
                            f"Mapped {identifier} to {len(names)} names: {names}"
                        )
                        results[identifier] = (names, str(best_score))
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
