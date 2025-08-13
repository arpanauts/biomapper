"""
METABOLITE_CTS_BRIDGE Action.

Integrates with the Chemical Translation Service (CTS) API to bridge between
different metabolite identifier types (HMDB, InChIKey, CHEBI, KEGG, PubChem, etc.).
"""

import asyncio
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

import aiohttp
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.action_results import ActionResult
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction

logger = logging.getLogger(__name__)


# Exception Classes
class CTSError(Exception):
    """Base exception for CTS-related errors."""


class CTSAPIError(CTSError):
    """CTS API returned an error."""


class CTSTimeoutError(CTSError):
    """CTS API request timed out."""


class CTSRateLimitError(CTSError):
    """CTS API rate limit exceeded."""


class FallbackServiceError(CTSError):
    """Fallback service failed."""


# Parameter and Result Models
class MetaboliteCtsBridgeParams(BaseModel):
    """Parameters for CTS bridge metabolite matching."""

    # Input/Output
    source_key: str = Field(..., description="Source dataset key")
    target_key: str = Field(..., description="Target dataset key")
    output_key: str = Field(..., description="Output dataset key")

    # Identifier configuration
    source_id_column: str = Field(..., description="Column with source identifiers")
    source_id_type: str = Field(
        ...,
        description="Type of source identifier",
        pattern="^(hmdb|inchikey|chebi|kegg|pubchem|cas|smiles)$",
    )
    target_id_column: str = Field(..., description="Column with target identifiers")
    target_id_type: str = Field(
        ...,
        description="Type of target identifier",
        pattern="^(hmdb|inchikey|chebi|kegg|pubchem|cas|smiles)$",
    )

    # CTS configuration
    batch_size: int = Field(100, description="Batch size for CTS API calls")
    max_retries: int = Field(3, description="Maximum retries for failed requests")
    timeout_seconds: int = Field(30, description="Timeout per request")
    cache_results: bool = Field(True, description="Cache successful translations")
    cache_file: Optional[str] = Field(None, description="Path to cache file")

    # Fallback options
    use_fallback_services: bool = Field(
        True, description="Use alternative services if CTS fails"
    )
    fallback_services: List[str] = Field(
        default_factory=lambda: ["pubchem", "chemspider"],
        description="Fallback translation services",
    )

    # Matching configuration
    confidence_threshold: float = Field(
        0.8, description="Minimum confidence for matches"
    )
    handle_multiple_translations: str = Field(
        "best",
        description="How to handle multiple translation results",
        pattern="^(first|best|all)$",
    )

    # Error handling
    skip_on_error: bool = Field(True, description="Skip IDs that fail translation")
    log_failures: bool = Field(True, description="Log translation failures")


class MetaboliteCtsBridgeResult(BaseModel):
    """Result of CTS bridge metabolite matching."""

    success: bool
    total_source_ids: int
    total_target_ids: int
    successful_translations: int
    failed_translations: int
    matches_found: int
    confidence_scores: Dict[str, float]
    api_statistics: Dict[str, Any]
    cache_statistics: Dict[str, Any]
    error_log: Optional[List[str]] = None


# Rate Limiter
class AsyncRateLimiter:
    """Async rate limiter for API calls."""

    def __init__(self, requests_per_second: float):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to maintain rate limit."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self.last_request_time

            if time_since_last < self.min_interval:
                await asyncio.sleep(self.min_interval - time_since_last)

            self.last_request_time = asyncio.get_event_loop().time()


# CTS Cache
class CTSCache:
    """Cache for CTS translation results."""

    def __init__(self, cache_file: Optional[str] = None, ttl_days: int = 30):
        self.cache_file = cache_file or "/tmp/biomapper_cts_cache.pkl"
        self.ttl = timedelta(days=ttl_days)
        self.cache = self._load_cache()
        self.hits = 0
        self.misses = 0

    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        cache_path = Path(self.cache_file)
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                return {}
        return {}

    def get(self, key: str) -> Optional[List[str]]:
        """Get cached translation if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                self.hits += 1
                return entry["value"]
            else:
                del self.cache[key]  # Remove expired entry
                self.misses += 1
        else:
            self.misses += 1
        return None

    def set(self, key: str, value: List[str]):
        """Cache translation result."""
        self.cache[key] = {"value": value, "timestamp": datetime.now()}

    def save(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def cache_key(self, identifier: str, from_type: str, to_type: str) -> str:
        """Generate cache key."""
        return f"{from_type}:{to_type}:{identifier}"


# CTS Client
class CTSClient:
    """Client for Chemical Translation Service API."""

    BASE_URL = "https://cts.fiehnlab.ucdavis.edu/rest/convert"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def translate_identifier(
        self,
        identifier: str,
        from_type: str,
        to_type: str,
        session: aiohttp.ClientSession,
    ) -> Optional[List[str]]:
        """Translate single identifier via CTS API."""

        # CTS API endpoint format
        url = f"{self.BASE_URL}/{from_type}/{to_type}/{identifier}"

        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        return self._parse_cts_response(data)
                    except Exception as e:
                        raise CTSAPIError(f"Failed to parse CTS response: {e}")
                elif response.status == 404:
                    return None  # ID not found
                else:
                    raise CTSAPIError(f"CTS returned {response.status}")

        except asyncio.TimeoutError:
            raise CTSTimeoutError(f"CTS timeout for {identifier}")
        except aiohttp.ClientError as e:
            raise CTSAPIError(f"CTS network error: {str(e)}")

    def _parse_cts_response(self, data: List) -> List[str]:
        """Parse CTS API response format."""
        # CTS returns array with result objects
        results = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "result" in item:
                    result = item["result"]
                    if isinstance(result, list):
                        results.extend(result)
                    elif result:
                        results.append(result)
        return results


# Batch Processor
class BatchProcessor:
    """Process identifiers in batches with rate limiting."""

    def __init__(self, batch_size: int = 100, requests_per_second: float = 10):
        self.batch_size = batch_size
        self.rate_limiter = AsyncRateLimiter(requests_per_second)
        self.cts_client = CTSClient()

    async def process_batch(
        self, identifiers: List[str], from_type: str, to_type: str
    ) -> Dict[str, Optional[List[str]]]:
        """Process batch of identifiers with rate limiting."""

        results = {}
        async with aiohttp.ClientSession() as session:
            tasks = []

            for identifier in identifiers:
                task = self.translate_with_retry(
                    identifier, from_type, to_type, session
                )
                tasks.append(task)

            # Gather results
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for identifier, result in zip(identifiers, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"Translation failed for {identifier}: {result}")
                    results[identifier] = None
                else:
                    results[identifier] = result

        return results

    async def translate_with_retry(
        self,
        identifier: str,
        from_type: str,
        to_type: str,
        session: aiohttp.ClientSession,
        max_retries: int = 3,
    ) -> Optional[List[str]]:
        """Translate with exponential backoff retry."""

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire()

                return await self.cts_client.translate_identifier(
                    identifier, from_type, to_type, session
                )
            except CTSTimeoutError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise
            except CTSAPIError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise


# Fallback Translator
class FallbackTranslator:
    """Fallback translation services when CTS fails."""

    async def translate_via_pubchem(
        self, identifier: str, from_type: str, to_type: str
    ) -> Optional[List[str]]:
        """Use PubChem PUG REST API as fallback."""

        # PubChem API endpoints
        if from_type == "inchikey" and to_type == "hmdb":
            # First get PubChem CID from InChIKey
            cid = await self._inchikey_to_cid(identifier)
            if cid:
                # Then get HMDB from CID via synonyms
                return await self._cid_to_hmdb(cid)

        # Add other translation paths as needed
        return None

    async def _inchikey_to_cid(self, inchikey: str) -> Optional[str]:
        """Convert InChIKey to PubChem CID."""
        # Implementation would use PubChem API
        # For now, return None (would be implemented with actual API calls)
        return None

    async def _cid_to_hmdb(self, cid: str) -> Optional[List[str]]:
        """Convert PubChem CID to HMDB ID."""
        # Implementation would use PubChem API
        # For now, return None (would be implemented with actual API calls)
        return None

    async def translate_via_chemspider(
        self, identifier: str, from_type: str, to_type: str
    ) -> Optional[List[str]]:
        """Use ChemSpider API as fallback (requires API key)."""
        # Implementation depends on ChemSpider API access
        return None


# Main Action Class
@register_action("METABOLITE_CTS_BRIDGE")
class MetaboliteCtsBridgeAction(
    TypedStrategyAction[MetaboliteCtsBridgeParams, ActionResult]
):
    """CTS bridge action for metabolite identifier translation."""

    def __init__(self):
        super().__init__()
        self.api_call_count = 0
        self.fallback_translator = FallbackTranslator()

    def get_params_model(self) -> type[MetaboliteCtsBridgeParams]:
        """Get the parameter model class."""
        return MetaboliteCtsBridgeParams

    def get_result_model(self) -> type[ActionResult]:
        """Get the result model class."""
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MetaboliteCtsBridgeParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> ActionResult:
        """Execute CTS bridge metabolite matching."""

        logger.info(
            f"Starting CTS translation: {params.source_id_type} to {params.target_id_type}"
        )

        # Get datasets from context
        context_dict = (
            context if isinstance(context, dict) else context.custom_action_data
        )
        if "datasets" not in context_dict:
            context_dict = {"datasets": context_dict}

        source_df = context_dict["datasets"][params.source_key].copy()
        target_df = context_dict["datasets"][params.target_key].copy()

        # Extract unique identifiers
        source_ids = source_df[params.source_id_column].dropna().unique().tolist()
        target_ids = target_df[params.target_id_column].dropna().unique().tolist()

        logger.info(
            f"Processing {len(source_ids)} source IDs and {len(target_ids)} target IDs"
        )

        # Initialize cache
        cache = CTSCache(params.cache_file) if params.cache_results else None

        # Process translations
        translations = await self._process_translations(source_ids, params, cache)

        # Match with target dataset
        matches = self._match_translated_ids(
            translations, target_df, params.target_id_column
        )

        # Filter by confidence threshold
        if not matches.empty:
            matches = matches[matches["confidence"] >= params.confidence_threshold]

        # Store results
        context_dict["datasets"][params.output_key] = matches

        # Calculate statistics
        successful_translations = len([t for t in translations.values() if t])
        failed_translations = len(source_ids) - successful_translations

        # Update context statistics
        if "statistics" not in context_dict:
            context_dict["statistics"] = {}

        context_dict["statistics"]["cts_bridge"] = {
            "total_source": len(source_ids),
            "total_target": len(target_ids),
            "successful_translations": successful_translations,
            "failed_translations": failed_translations,
            "matches_found": len(matches),
            "cache_hits": cache.hits if cache else 0,
            "cache_misses": cache.misses if cache else 0,
            "api_calls": self.api_call_count,
        }

        # Save cache
        if cache:
            cache.save()
            logger.info(f"Cache saved with {len(cache.cache)} entries")

        # Build result
        result_data = {
            "total_source_ids": len(source_ids),
            "total_target_ids": len(target_ids),
            "successful_translations": successful_translations,
            "failed_translations": failed_translations,
            "matches_found": len(matches),
            "confidence_scores": {},
            "api_statistics": {
                "api_calls": self.api_call_count,
                "cache_hits": cache.hits if cache else 0,
                "cache_misses": cache.misses if cache else 0,
            },
            "cache_statistics": {
                "total_entries": len(cache.cache) if cache else 0,
                "hit_rate": (cache.hits / (cache.hits + cache.misses))
                if cache and (cache.hits + cache.misses) > 0
                else 0,
            },
        }

        logger.info(
            f"CTS bridge complete: {result_data['matches_found']} matches from {result_data['successful_translations']} translations"
        )

        return ActionResult(
            success=True,
            message=f"CTS bridge completed: {result_data['matches_found']} matches found",
            data=result_data,
        )

    async def _process_translations(
        self,
        source_ids: List[str],
        params: MetaboliteCtsBridgeParams,
        cache: Optional[CTSCache],
    ) -> Dict[str, Optional[List[str]]]:
        """Process translations with caching and batching."""

        translations = {}
        to_translate = []

        # Check cache first
        for identifier in source_ids:
            if cache:
                cache_key = cache.cache_key(
                    identifier, params.source_id_type, params.target_id_type
                )
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    translations[identifier] = cached_result
                    logger.debug(f"Cache hit for {identifier}")
                else:
                    to_translate.append(identifier)
            else:
                to_translate.append(identifier)

        logger.info(
            f"Translating {len(to_translate)} IDs (cached: {len(translations)})"
        )

        # Process in batches
        processor = BatchProcessor(batch_size=params.batch_size)

        for i in range(0, len(to_translate), params.batch_size):
            batch = to_translate[i : i + params.batch_size]
            logger.debug(
                f"Processing batch {i // params.batch_size + 1} with {len(batch)} IDs"
            )

            try:
                batch_results = await processor.process_batch(
                    batch, params.source_id_type, params.target_id_type
                )

                self.api_call_count += len(batch)

                # Update cache and translations
                for identifier, result in batch_results.items():
                    translations[identifier] = result

                    if cache and result is not None:
                        cache_key = cache.cache_key(
                            identifier, params.source_id_type, params.target_id_type
                        )
                        cache.set(cache_key, result)

                    # Try fallback if failed and enabled
                    if result is None and params.use_fallback_services:
                        fallback_result = await self._try_fallback(
                            identifier, params.source_id_type, params.target_id_type
                        )
                        if fallback_result:
                            translations[identifier] = fallback_result
                            if cache:
                                cache_key = cache.cache_key(
                                    identifier,
                                    params.source_id_type,
                                    params.target_id_type,
                                )
                                cache.set(cache_key, fallback_result)

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                if not params.skip_on_error:
                    raise

                # Mark batch as failed
                for identifier in batch:
                    translations[identifier] = None

        return translations

    async def _try_fallback(
        self, identifier: str, from_type: str, to_type: str
    ) -> Optional[List[str]]:
        """Try fallback translation services."""

        try:
            result = await self.fallback_translator.translate_via_pubchem(
                identifier, from_type, to_type
            )
            if result:
                logger.info(f"PubChem fallback successful for {identifier}")
                return result
        except Exception as e:
            logger.debug(f"PubChem fallback failed for {identifier}: {e}")

        return None

    def _match_translated_ids(
        self,
        source_translations: Dict[str, Optional[List[str]]],
        target_df: pd.DataFrame,
        target_column: str,
    ) -> pd.DataFrame:
        """Match translated IDs with target dataset."""

        matches = []

        for source_id, translated_ids in source_translations.items():
            if not translated_ids:
                continue

            # Find matches in target dataset
            for translated_id in translated_ids:
                mask = target_df[target_column] == translated_id
                if mask.any():
                    # Calculate confidence based on translation path
                    confidence = self._calculate_confidence(
                        source_id,
                        translated_id,
                        len(translated_ids),
                        "hmdb",  # TODO: Use actual source type
                    )

                    matches.append(
                        {
                            "source_id": source_id,
                            "target_id": translated_id,
                            "confidence": confidence,
                            "match_type": "cts_bridge",
                        }
                    )

        if matches:
            return pd.DataFrame(matches)
        else:
            return pd.DataFrame(
                columns=["source_id", "target_id", "confidence", "match_type"]
            )

    def _calculate_confidence(
        self, source_id: str, target_id: str, num_translations: int, source_type: str
    ) -> float:
        """Calculate match confidence score."""

        # Base confidence from CTS
        base_confidence = 0.85

        # Reduce confidence if multiple translations
        if num_translations > 1:
            base_confidence *= 1.0 / num_translations

        # Adjust based on ID types
        if source_type == "inchikey":
            base_confidence *= 0.95  # InChIKey is highly specific
        elif source_type == "hmdb":
            base_confidence *= 0.90  # HMDB is reliable

        return min(base_confidence, 1.0)

    async def _validate_identifier(self, identifier: Any, id_type: str) -> bool:
        """Validate identifier format."""

        if identifier is None or identifier == "":
            return False

        identifier_str = str(identifier)

        # Validate format based on type
        if id_type == "hmdb":
            # HMDB format: HMDB followed by 7 digits
            return bool(re.match(r"^HMDB\d{7}$", identifier_str))
        elif id_type == "inchikey":
            # InChIKey format: XXXXXXXXXXXXXX-YYYYYYYYYY-Z
            return bool(re.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$", identifier_str))
        elif id_type == "chebi":
            # CHEBI format: CHEBI:digits
            return bool(re.match(r"^CHEBI:\d+$", identifier_str))
        elif id_type == "kegg":
            # KEGG compound format: C followed by digits
            return bool(re.match(r"^C\d{5}$", identifier_str))
        elif id_type == "pubchem":
            # PubChem CID: just digits
            return bool(re.match(r"^\d+$", identifier_str))

        # Default: accept if not empty
        return True
