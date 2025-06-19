"""Cache-aware entity mapper with bidirectional transitivity support."""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from ..core.base_mapper import BaseMapper, MappingResult
from ..schemas.domain_schema import DomainDocument
from .manager import CacheManager

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DomainDocument)


class CachedMapper(BaseMapper[T]):
    """Mapper that uses the local cache before calling the underlying mapper."""

    def __init__(
        self,
        base_mapper: BaseMapper[T],
        document_class: Type[T],
        source_type: str,
        target_type: str,
        cache_manager: Optional[CacheManager] = None,
        ttl_days: int = 365,
        min_confidence: float = 0.7,
        track_api_usage: bool = True,
        use_derived_mappings: bool = True,
    ) -> None:
        """Initialize the cached mapper.

        Args:
            base_mapper: Underlying mapper implementation to use for cache misses
            document_class: Domain document class for mapped entities
            source_type: Source entity type for this mapper
            target_type: Target entity type for this mapper
            cache_manager: Cache manager instance
            ttl_days: Time-to-live in days for cached mappings
            min_confidence: Minimum confidence threshold for valid mappings
            track_api_usage: Whether to track API usage in statistics
            use_derived_mappings: Whether to use derived mappings
        """
        self.base_mapper = base_mapper
        self.document_class = document_class
        self.source_type = source_type
        self.target_type = target_type
        self.cache_manager = cache_manager or CacheManager()
        self.ttl_days = ttl_days
        self.min_confidence = min_confidence
        self.track_api_usage = track_api_usage
        self.use_derived_mappings = use_derived_mappings

        logger.info(
            f"Initialized CachedMapper for {source_type}->{target_type} "
            f"(TTL: {ttl_days} days, confidence: {min_confidence})"
        )

        # Ensure entity type configuration exists
        self.cache_manager.set_entity_type_config(
            source_type=source_type,
            target_type=target_type,
            ttl_days=ttl_days,
            confidence_threshold=min_confidence,
        )

    async def map_entity(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map text to entity with cache support.

        Args:
            text: Text to map
            context: Optional mapping context

        Returns:
            Mapping result
        """
        if context is None:
            context = {}

        # Skip cache for specific requests if indicated in context
        if context.get("skip_cache", False):
            logger.debug(f"Skipping cache for {self.source_type}:{text}")
            return await self._map_with_api(text, context)

        # Normalize entity ID if needed
        entity_id = self._normalize_entity_id(text)

        # Try to find in cache
        cache_results = self.cache_manager.lookup(
            source_id=entity_id,
            source_type=self.source_type,
            target_type=self.target_type,
            include_derived=self.use_derived_mappings,
            min_confidence=self.min_confidence,
        )

        if cache_results:
            # Found in cache
            logger.debug(f"Cache hit for {self.source_type}:{entity_id}")

            # Get highest confidence mapping
            best_mapping = max(cache_results, key=lambda m: m["confidence"])

            # Convert to domain document
            domain_doc = self._create_domain_doc(best_mapping)

            return MappingResult(
                input_text=text,
                mapped_entity=domain_doc,
                confidence=best_mapping["confidence"],
                source=f"cache:{best_mapping['mapping_source']}",
                metadata={
                    "cache_hit": True,
                    "is_derived": best_mapping.get("is_derived", False),
                    "mapping_id": best_mapping.get("id"),
                    **best_mapping.get("metadata", {}),
                },
            )

        # Not found in cache, use API
        logger.debug(f"Cache miss for {self.source_type}:{entity_id}")
        result = await self._map_with_api(text, context)

        # Add to cache if mapping was successful
        if result.mapped_entity:
            self._add_to_cache(text, result)

        return result

    async def batch_map(
        self, texts: List[str], context: Optional[Dict[str, Any]] = None
    ) -> List[MappingResult]:
        """Map multiple texts to entities with cache support.

        Args:
            texts: Texts to map
            context: Optional mapping context

        Returns:
            List of mapping results
        """
        if context is None:
            context = {}

        # Skip cache if requested
        if context.get("skip_cache", False):
            logger.debug(f"Skipping cache for batch of {len(texts)} items")
            return await self.base_mapper.batch_map(texts, context)

        # Process each text with cache support
        results = []
        cache_misses = []
        cache_miss_indices = []

        for i, text in enumerate(texts):
            # Normalize entity ID
            entity_id = self._normalize_entity_id(text)

            # Try to find in cache
            cache_results = self.cache_manager.lookup(
                source_id=entity_id,
                source_type=self.source_type,
                target_type=self.target_type,
                include_derived=self.use_derived_mappings,
                min_confidence=self.min_confidence,
            )

            if cache_results:
                # Found in cache
                best_mapping = max(cache_results, key=lambda m: m["confidence"])
                domain_doc = self._create_domain_doc(best_mapping)

                results.append(
                    MappingResult(
                        input_text=text,
                        mapped_entity=domain_doc,
                        confidence=best_mapping["confidence"],
                        source=f"cache:{best_mapping['mapping_source']}",
                        metadata={
                            "cache_hit": True,
                            "is_derived": best_mapping.get("is_derived", False),
                            "mapping_id": best_mapping.get("id"),
                            **best_mapping.get("metadata", {}),
                        },
                    )
                )
            else:
                # Cache miss - add to list for batch API call
                cache_misses.append(text)
                cache_miss_indices.append(i)

        # If we have cache misses, fetch them from the API
        if cache_misses:
            logger.debug(
                f"Cache miss for {len(cache_misses)} out of {len(texts)} items"
            )
            api_results = await self.base_mapper.batch_map(cache_misses, context)

            # Add API results to the final results list and cache
            for i, api_result in enumerate(api_results):
                original_index = cache_miss_indices[i]

                # Insert at the correct position
                while len(results) <= original_index:
                    results.append(None)

                results[original_index] = api_result

                # Add to cache if mapping was successful
                if api_result.mapped_entity:
                    self._add_to_cache(api_result.input_text, api_result)

        return results

    def _normalize_entity_id(self, text: str) -> str:
        """Normalize entity ID for consistent cache lookups.

        Args:
            text: Input entity ID or text

        Returns:
            Normalized entity ID
        """
        # For now, just use the text as-is
        # This could be extended with entity-specific normalization
        return text

    def _create_domain_doc(self, mapping: Dict[str, Any]) -> T:
        """Create domain document from mapping data.

        Args:
            mapping: Mapping data from cache

        Returns:
            Domain document instance
        """
        # Create domain document instance
        doc = self.document_class()

        # Set ID and type
        doc.id = mapping["target_id"]
        doc.type = mapping["target_type"]

        # Add other metadata if available
        if "metadata" in mapping and mapping["metadata"]:
            for key, value in mapping["metadata"].items():
                if hasattr(doc, key):
                    setattr(doc, key, value)

        return doc

    async def _map_with_api(self, text: str, context: Dict[str, Any]) -> MappingResult:
        """Map text to entity using the underlying API mapper.

        Args:
            text: Text to map
            context: Mapping context

        Returns:
            Mapping result
        """
        # Track API call in stats if enabled
        if self.track_api_usage:
            self.cache_manager._update_stats(
                self.cache_manager._session_scope().__enter__(), api_call=True
            )

        # Call underlying mapper
        result = await self.base_mapper.map_entity(text, context)

        # Add cache miss indicator to metadata
        if result.metadata is None:
            result.metadata = {}

        result.metadata["cache_hit"] = False

        return result

    def _add_to_cache(self, text: str, result: MappingResult) -> None:
        """Add successful mapping result to cache.

        Args:
            text: Original input text
            result: Mapping result
        """
        if not result.mapped_entity:
            return

        # Extract entity ID and metadata
        entity_id = self._normalize_entity_id(text)
        target_id = result.mapped_entity.id
        target_type = getattr(result.mapped_entity, "type", self.target_type)

        # Prepare metadata from mapping result
        metadata = {}
        if result.metadata:
            metadata = {
                k: str(v) for k, v in result.metadata.items() if k != "cache_hit"
            }

        # Determine mapping source from result.source
        mapping_source = result.source
        if ":" in mapping_source:
            mapping_source = mapping_source.split(":", 1)[1]

        # Add to cache
        self.cache_manager.add_mapping(
            source_id=entity_id,
            source_type=self.source_type,
            target_id=target_id,
            target_type=target_type,
            confidence=result.confidence,
            mapping_source=mapping_source,
            metadata=metadata,
            ttl_days=self.ttl_days,
            bidirectional=True,
        )
