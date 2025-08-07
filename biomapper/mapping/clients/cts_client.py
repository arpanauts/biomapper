"""Chemical Translation Service (CTS) API client for metabolite identifier conversion."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import aiohttp
from urllib.parse import quote
from datetime import datetime, timedelta

from biomapper.mapping.clients.base_client import BaseMappingClient
from biomapper.core.exceptions import ClientExecutionError, ClientError, ErrorCode
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScoringAlgorithm(str, Enum):
    """Available scoring algorithms for InChIKey scoring."""
    BIOLOGICAL = "biological"
    POPULARITY = "popularity"


class CTSConversionResult(BaseModel):
    """Result from a CTS conversion request."""
    from_identifier: str = Field(alias="fromIdentifier")
    search_term: str = Field(alias="searchTerm")
    to_identifier: str = Field(alias="toIdentifier")
    results: List[str]  # Note: field is "results" not "result"


class InChIKeyScore(BaseModel):
    """Score for an InChIKey."""
    inchikey: str = Field(alias="InChIKey")
    score: float


class CTSScoringResult(BaseModel):
    """Result from CTS scoring endpoint."""
    search_term: str = Field(alias="searchTerm")
    from_type: str = Field(alias="from")
    result: List[InChIKeyScore]


class BiologicalCount(BaseModel):
    """Biological database counts for an InChIKey."""
    kegg: Optional[int] = Field(alias="KEGG", default=0)
    biocyc: Optional[int] = Field(alias="BioCyc", default=0)
    hmdb: Optional[int] = Field(alias="Human Metabolome Database", default=0)
    total: int


class CTSClient(BaseMappingClient):
    """Client for the Chemical Translation Service API.
    
    CTS provides conversions between chemical identifiers including:
    - InChI, InChIKey
    - PubChem CID/SID
    - HMDB ID
    - KEGG ID
    - ChEBI ID
    - CAS Registry Number
    - Chemical names
    - And many more
    """
    
    BASE_URL = "https://cts.fiehnlab.ucdavis.edu/rest"
    
    # Common ID type abbreviations mapping to full CTS names
    ID_TYPE_MAPPING = {
        "HMDB": "Human Metabolome Database",
        "KEGG": "KEGG",
        "ChEBI": "ChEBI",
        "PubChem": "PubChem CID",
        "InChIKey": "InChIKey",
        "InChI": "InChI",
        "SMILES": "SMILES",
        "Chemical Name": "Chemical Name",
        "CAS": "CAS",
        "DrugBank": "DrugBank",
        "ChemSpider": "ChemSpider",
        "LMSD": "LMSD",
        "LipidMAPS": "LipidMAPS"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = self._config.get('rate_limit_per_second', 10)
        self.timeout = self._config.get('timeout_seconds', 30)
        self.retry_attempts = self._config.get('retry_attempts', 3)
        self.cache_ttl = self._config.get('cache_ttl_minutes', 60)
        
        # In-memory cache with TTL
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._valid_from_ids: Optional[Set[str]] = None
        self._valid_to_ids: Optional[Set[str]] = None
        
    async def initialize(self) -> None:
        """Initialize async HTTP session and load valid ID types."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Pre-load valid ID types
        await self._load_valid_id_types()
        self._initialized = True
        
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _load_valid_id_types(self) -> None:
        """Load and cache valid source and target ID types."""
        try:
            self._valid_from_ids = set(await self.get_valid_from_ids())
            self._valid_to_ids = set(await self.get_valid_to_ids())
            logger.info(f"Loaded {len(self._valid_from_ids)} source types and {len(self._valid_to_ids)} target types")
        except Exception as e:
            logger.warning(f"Failed to load valid ID types: {e}")
            # Set to None to try again later
            self._valid_from_ids = None
            self._valid_to_ids = None
    
    def _validate_id_types(self, from_type: str, to_type: str) -> None:
        """Validate that ID types are supported."""
        # Map common abbreviations to full names
        from_type_mapped = self.ID_TYPE_MAPPING.get(from_type, from_type)
        to_type_mapped = self.ID_TYPE_MAPPING.get(to_type, to_type)
        
        if self._valid_from_ids and from_type_mapped not in self._valid_from_ids:
            raise ValueError(f"Invalid source ID type: {from_type}. Valid types: {sorted(self._valid_from_ids)}")
        if self._valid_to_ids and to_type_mapped not in self._valid_to_ids:
            raise ValueError(f"Invalid target ID type: {to_type}. Valid types: {sorted(self._valid_to_ids)}")
    
    def _get_cache_key(self, endpoint: str, **params: Any) -> str:
        """Generate cache key for request."""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < timedelta(minutes=self.cache_ttl):
                return value
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, value: Any) -> None:
        """Set value in cache with timestamp."""
        self._cache[cache_key] = (value, datetime.now())
    
    async def _make_request(self, endpoint: str, **kwargs: Any) -> Any:
        """Make HTTP request with retry logic."""
        if not self.session:
            await self.initialize()
            
        assert self.session is not None  # Type narrowing
        url = f"{self.BASE_URL}/{endpoint}"
        
        for attempt in range(self.retry_attempts):
            try:
                async with self.session.get(url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return None
                    else:
                        error_text = await response.text()
                        raise ClientExecutionError(
                            f"CTS API error {response.status}: {error_text}",
                            client_name="CTSClient",
                            details={"status": response.status, "error": error_text}
                        )
                        
            except asyncio.TimeoutError:
                if attempt == self.retry_attempts - 1:
                    raise ClientError(
                        f"CTS API timeout after {self.retry_attempts} attempts",
                        error_code=ErrorCode.CLIENT_TIMEOUT_ERROR,
                        client_name="CTSClient",
                        details={"attempts": self.retry_attempts}
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except aiohttp.ClientError as e:
                if attempt == self.retry_attempts - 1:
                    raise ClientExecutionError(
                        f"CTS API connection error: {str(e)}",
                        client_name="CTSClient",
                        details={"error": str(e)}
                    )
                await asyncio.sleep(2 ** attempt)
    
    async def convert(
        self,
        identifier: str,
        from_type: str,
        to_type: str,
        use_cache: bool = True
    ) -> Optional[List[str]]:
        """Convert a single identifier from one type to another.
        
        Args:
            identifier: The identifier to convert
            from_type: Source identifier type (e.g., "HMDB", "InChIKey")
            to_type: Target identifier type (e.g., "Chemical Name", "PubChem CID")
            use_cache: Whether to use cached results
            
        Returns:
            List of converted identifiers, or None if conversion failed
        """
        # Validate ID types if we have the data
        self._validate_id_types(from_type, to_type)
        
        # Map common abbreviations to full names for API call
        from_type_api = self.ID_TYPE_MAPPING.get(from_type, from_type)
        to_type_api = self.ID_TYPE_MAPPING.get(to_type, to_type)
        
        # Check cache
        cache_key = self._get_cache_key("convert", from_type=from_type_api, to_type=to_type_api, id=identifier)
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached  # type: ignore
        
        # Make request
        endpoint = f"convert/{quote(from_type_api)}/{quote(to_type_api)}/{quote(identifier)}"
        
        try:
            data = await self._make_request(endpoint)
            if data and isinstance(data, list) and len(data) > 0:
                result = CTSConversionResult(**data[0])
                
                # Cache and return
                if use_cache:
                    self._set_cache(cache_key, result.results)
                return result.results
            return []
            
        except Exception as e:
            logger.warning(f"CTS conversion error for {identifier}: {str(e)}")
            return []
    
    async def convert_batch(
        self,
        identifiers: List[str],
        from_type: str,
        to_types: List[str],
        include_failed: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Dict[str, List[str]]]:
        """Convert a batch of identifiers to multiple target types.
        
        Args:
            identifiers: List of source identifiers
            from_type: Source identifier type (e.g., "HMDB")
            to_types: List of target types (e.g., ["InChIKey", "PubChem CID"])
            include_failed: Whether to include failed conversions in results
            use_cache: Whether to use cached results
            
        Returns:
            Dict mapping source ID to dict of target types and their values
            Example: {"HMDB0000001": {"InChIKey": ["XUIMIQQOPSSXEZ-UHFFFAOYSA-N"], "PubChem CID": ["5793"]}}
        """
        results = {}
        
        # Rate limiting
        delay = 1.0 / self.rate_limit
        
        for identifier in identifiers:
            conversions = {}
            
            for to_type in to_types:
                # Convert
                converted = await self.convert(identifier, from_type, to_type, use_cache)
                
                if converted or include_failed:
                    conversions[to_type] = converted or []
                    
                # Rate limiting
                await asyncio.sleep(delay)
                
            results[identifier] = conversions
            
        return results
    
    async def score_inchikeys(
        self,
        identifier: str,
        from_type: str,
        algorithm: ScoringAlgorithm = ScoringAlgorithm.BIOLOGICAL
    ) -> List[InChIKeyScore]:
        """Get scored InChIKeys for an identifier.
        
        Args:
            identifier: The identifier to convert to scored InChIKeys
            from_type: Source identifier type
            algorithm: Scoring algorithm to use
            
        Returns:
            List of InChIKeys with scores, sorted by score descending
        """
        cache_key = self._get_cache_key("score", from_type=from_type, id=identifier, algo=algorithm.value)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached  # type: ignore
        
        endpoint = f"score/{quote(from_type)}/{quote(identifier)}/{algorithm.value}"
        
        try:
            data = await self._make_request(endpoint)
            if data:
                result = CTSScoringResult(**data)
                scores = sorted(result.result, key=lambda x: x.score, reverse=True)
                self._set_cache(cache_key, scores)
                return scores
            return []
            
        except Exception as e:
            logger.warning(f"CTS scoring error for {identifier}: {str(e)}")
            return []
    
    async def get_valid_from_ids(self) -> List[str]:
        """Get list of valid source identifier types."""
        data = await self._make_request("fromValues")
        return data or []
    
    async def get_valid_to_ids(self) -> List[str]:
        """Get list of valid target identifier types."""
        data = await self._make_request("toValues")
        return data or []
    
    async def expand_formula(self, formula: str) -> Optional[str]:
        """Expand a chemical formula.
        
        Args:
            formula: Chemical formula to expand (e.g., "H2O")
            
        Returns:
            Expanded formula (e.g., "HHO") or None if failed
        """
        cache_key = self._get_cache_key("expandformula", formula=formula)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached  # type: ignore
        
        endpoint = f"expandformula/{quote(formula)}"
        
        try:
            data = await self._make_request(endpoint)
            if data and "result" in data:
                result = data["result"]
                self._set_cache(cache_key, result)
                return result  # type: ignore
            return None
            
        except Exception as e:
            logger.warning(f"Formula expansion error for {formula}: {str(e)}")
            return None
    
    async def inchikey_to_mol(self, inchikey: str) -> Optional[str]:
        """Convert InChIKey to MDL/SDF molecule definition.
        
        Args:
            inchikey: InChIKey to convert
            
        Returns:
            MDL/SDF string or None if failed
        """
        cache_key = self._get_cache_key("inchikeytomol", inchikey=inchikey)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached  # type: ignore
        
        endpoint = f"inchikeytomol/{quote(inchikey)}"
        
        try:
            data = await self._make_request(endpoint)
            if data and "molecule" in data:
                molecule = data["molecule"]
                self._set_cache(cache_key, molecule)
                return molecule  # type: ignore
            return None
            
        except Exception as e:
            logger.warning(f"InChIKey to mol error for {inchikey}: {str(e)}")
            return None
    
    async def count_biological_ids(self, inchikey: str) -> BiologicalCount:
        """Count biological database occurrences for an InChIKey.
        
        Args:
            inchikey: InChIKey to count
            
        Returns:
            BiologicalCount with database counts
        """
        cache_key = self._get_cache_key("countBiological", inchikey=inchikey)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached  # type: ignore
        
        endpoint = f"countBiological/{quote(inchikey)}"
        
        try:
            data = await self._make_request(endpoint)
            if data:
                count = BiologicalCount(**data)
                self._set_cache(cache_key, count)
                return count
            return BiologicalCount(total=0)
            
        except Exception as e:
            logger.warning(f"Biological count error for {inchikey}: {str(e)}")
            return BiologicalCount(total=0)
    
    async def get_synonyms(self, identifier: str, id_type: str) -> List[str]:
        """Get chemical name synonyms for an identifier.
        
        Convenience method that converts to Chemical Name.
        """
        return await self.convert(identifier, id_type, "Chemical Name") or []
    
    async def enrich_metabolite(
        self,
        identifier: str,
        id_type: str,
        target_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Enrich a metabolite with multiple identifier types and metadata.
        
        Args:
            identifier: Source identifier
            id_type: Source identifier type
            target_types: List of target types to convert to (defaults to common types)
            
        Returns:
            Dict with enriched data including conversions, scores, and counts
        """
        if target_types is None:
            target_types = ["InChIKey", "Chemical Name", "PubChem CID", "KEGG", "HMDB", "ChEBI"]
        
        # Parallel requests for efficiency
        tasks: List[Any] = []
        
        # Conversions
        for target_type in target_types:
            if target_type != id_type:  # Skip self-conversion
                tasks.append(self.convert(identifier, id_type, target_type))
        
        # Get InChIKey first for additional enrichment
        inchikey_result = await self.convert(identifier, id_type, "InChIKey")
        inchikey = inchikey_result[0] if inchikey_result else None
        
        if inchikey:
            # Biological counts
            tasks.append(self.count_biological_ids(inchikey))
            # Scored InChIKeys
            tasks.append(self.score_inchikeys(identifier, id_type))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build enrichment result
        enrichment: Dict[str, Any] = {
            "source_identifier": identifier,
            "source_type": id_type,
            "conversions": {},
            "inchikey_scores": [],
            "biological_counts": None
        }
        
        # Process conversion results
        result_idx = 0
        conversions = enrichment["conversions"]
        for target_type in target_types:
            if target_type != id_type:
                if result_idx < len(results) and not isinstance(results[result_idx], Exception):
                    conversions[target_type] = results[result_idx] or []
                result_idx += 1
        
        # Add InChIKey if we got it from conversions
        if inchikey:
            conversions["InChIKey"] = [inchikey]
            
            # Process additional enrichment
            if result_idx < len(results):
                # Biological counts
                if not isinstance(results[result_idx], Exception):
                    enrichment["biological_counts"] = results[result_idx]
                result_idx += 1
                
                # InChIKey scores
                if result_idx < len(results) and not isinstance(results[result_idx], Exception):
                    enrichment["inchikey_scores"] = results[result_idx]
        
        return enrichment
    
    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Map a list of source identifiers to target identifiers.
        
        This is the standard biomapper interface that converts identifiers using CTS.
        
        Args:
            identifiers: List of source identifiers to map.
            config: Configuration dict with keys:
                - from_type: Source identifier type (required)
                - to_type: Target identifier type (required)
                - use_cache: Whether to use cache (default: True)
            
        Returns:
            Dictionary mapping each input identifier to (target_ids, component_id) tuple.
        """
        if not config:
            raise ValueError("CTS client requires config with 'from_type' and 'to_type'")
        
        from_type = config.get('from_type')
        to_type = config.get('to_type')
        use_cache = config.get('use_cache', True)
        
        if not from_type or not to_type:
            raise ValueError("Config must specify 'from_type' and 'to_type'")
        
        results = {}
        
        for identifier in identifiers:
            try:
                converted = await self.convert(identifier, from_type, to_type, use_cache)
                results[identifier] = self.format_result(converted, None)
            except Exception as e:
                logger.warning(f"Failed to convert {identifier}: {e}")
                results[identifier] = self.format_result(None, None)
        
        return results