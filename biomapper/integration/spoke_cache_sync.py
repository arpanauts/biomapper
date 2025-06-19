"""Integration module for synchronizing between SPOKE graph and SQLite mapping cache."""

import datetime
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from biomapper.cache.manager import CacheManager
from biomapper.cache.monitoring import track_cache_operation, CacheEventType
from biomapper.db.models import EntityMapping
from biomapper.spoke.client import SpokeClient
from biomapper.transitivity.builder import TransitivityBuilder


logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """Direction for synchronization between SPOKE and cache."""

    SPOKE_TO_CACHE = "spoke_to_cache"
    CACHE_TO_SPOKE = "cache_to_spoke"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class SyncConfig:
    """Configuration for SPOKE-cache synchronization."""

    # Sync settings
    sync_batch_size: int = 1000
    sync_interval_hours: int = 24
    max_items_per_sync: int = 10000

    # Entity type mappings between SPOKE and cache
    spoke_to_cache_type_map: Dict[str, str] = None
    cache_to_spoke_type_map: Dict[str, str] = None

    # Confidence settings
    default_confidence: float = 0.9
    min_confidence_threshold: float = 0.7

    # Filter settings
    entity_types_to_sync: Optional[List[str]] = None
    excluded_entity_types: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize default mappings if not provided."""
        if self.spoke_to_cache_type_map is None:
            self.spoke_to_cache_type_map = {
                "Compound": "compound",
                "ChEBI": "chebi",
                "HMDB": "hmdb",
                "KEGG": "kegg",
                "PubChem": "pubchem.compound",
                "UniProt": "uniprot",
                "Gene": "gene",
                "Protein": "protein",
                "Pathway": "pathway",
                "Disease": "disease",
                "Anatomy": "anatomy",
            }

        if self.cache_to_spoke_type_map is None:
            # Create reverse mapping
            self.cache_to_spoke_type_map = {
                cache_type: spoke_type
                for spoke_type, cache_type in self.spoke_to_cache_type_map.items()
            }


class SpokeCacheSync:
    """Synchronization between SPOKE knowledge graph and SQLite mapping cache."""

    def __init__(
        self,
        spoke_client: SpokeClient,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[SyncConfig] = None,
    ):
        """Initialize synchronization manager.

        Args:
            spoke_client: SPOKE client for accessing the knowledge graph
            cache_manager: Cache manager instance
            config: Synchronization configuration
        """
        self.spoke_client = spoke_client
        self.cache_manager = cache_manager or CacheManager()
        self.config = config or SyncConfig()

        # Initialize transitivity builder
        self.transitivity_builder = TransitivityBuilder(
            cache_manager=self.cache_manager,
            min_confidence=self.config.min_confidence_threshold,
        )

    async def sync_entity_mappings(
        self,
        entity_id: str,
        entity_type: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        max_depth: int = 1,
        build_transitive: bool = True,
    ) -> Dict[str, Any]:
        """Synchronize mappings for a specific entity.

        Args:
            entity_id: Entity identifier
            entity_type: Entity type
            direction: Synchronization direction
            max_depth: Maximum depth for SPOKE relationships
            build_transitive: Whether to build transitive relationships after sync

        Returns:
            Dictionary with synchronization results
        """
        results = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "spoke_mappings_found": 0,
            "mappings_added_to_cache": 0,
            "mappings_added_to_spoke": 0,
            "transitive_mappings_created": 0,
            "errors": [],
            "duration_ms": 0,
        }

        start_time = time.time()

        try:
            # SPOKE to cache synchronization
            if direction in (SyncDirection.SPOKE_TO_CACHE, SyncDirection.BIDIRECTIONAL):
                with track_cache_operation(
                    operation_type=CacheEventType.API_CALL,
                    entity_type=entity_type,
                    metadata={"source": "spoke", "operation": "get_entity_mappings"},
                ):
                    # Convert cache type to SPOKE type if needed
                    spoke_type = self.config.cache_to_spoke_type_map.get(
                        entity_type, entity_type
                    )

                    # Get mappings from SPOKE
                    spoke_mappings = await self.spoke_client.get_entity_mappings(
                        entity_id=entity_id,
                        entity_type=spoke_type,
                        max_depth=max_depth,
                    )

                results["spoke_mappings_found"] = len(spoke_mappings)

                # Add mappings to cache
                for mapping in spoke_mappings:
                    target_id = mapping["target_id"]
                    target_type = mapping["target_type"]

                    # Convert SPOKE type to cache type
                    target_type_in_cache = self.config.spoke_to_cache_type_map.get(
                        target_type, target_type.lower()
                    )

                    # Get confidence score
                    confidence = mapping.get(
                        "confidence", self.config.default_confidence
                    )

                    # Skip if below threshold
                    if confidence < self.config.min_confidence_threshold:
                        continue

                    try:
                        # Add to cache
                        self.cache_manager.add_mapping(
                            source_id=entity_id,
                            source_type=entity_type,
                            target_id=target_id,
                            target_type=target_type_in_cache,
                            confidence=confidence,
                            mapping_source="spoke",
                            metadata=mapping.get("metadata", {}),
                        )

                        results["mappings_added_to_cache"] += 1
                    except Exception as e:
                        results["errors"].append(
                            f"Error adding mapping to cache: {str(e)}"
                        )

            # Cache to SPOKE synchronization
            if direction in (SyncDirection.CACHE_TO_SPOKE, SyncDirection.BIDIRECTIONAL):
                # Get mappings from cache
                cache_mappings = self.cache_manager.lookup(
                    source_id=entity_id,
                    source_type=entity_type,
                    include_metadata=True,
                )

                # Convert cache type to SPOKE type
                spoke_type = self.config.cache_to_spoke_type_map.get(
                    entity_type, entity_type
                )

                # Add mappings to SPOKE
                for mapping in cache_mappings:
                    # Skip mappings that came from SPOKE to avoid loops
                    if mapping.get("mapping_source") == "spoke":
                        continue

                    target_id = mapping["target_id"]
                    target_type = mapping["target_type"]

                    # Convert cache type to SPOKE type
                    target_type_in_spoke = self.config.cache_to_spoke_type_map.get(
                        target_type, target_type.title()
                    )

                    try:
                        # Add to SPOKE
                        with track_cache_operation(
                            operation_type=CacheEventType.API_CALL,
                            entity_type=entity_type,
                            metadata={
                                "target": "spoke",
                                "operation": "add_entity_mapping",
                            },
                        ):
                            await self.spoke_client.add_entity_mapping(
                                source_id=entity_id,
                                source_type=spoke_type,
                                target_id=target_id,
                                target_type=target_type_in_spoke,
                                confidence=mapping["confidence"],
                                metadata=mapping.get("metadata", {}),
                            )

                        results["mappings_added_to_spoke"] += 1
                    except Exception as e:
                        results["errors"].append(
                            f"Error adding mapping to SPOKE: {str(e)}"
                        )

            # Build transitive relationships if requested
            if build_transitive:
                transitive_count = self.transitivity_builder.build_transitive_mappings()
                results["transitive_mappings_created"] = transitive_count

        except Exception as e:
            results["errors"].append(f"Error during synchronization: {str(e)}")

        # Calculate duration
        end_time = time.time()
        results["duration_ms"] = round((end_time - start_time) * 1000, 2)

        return results

    async def sync_all_entities(
        self,
        entity_types: Optional[List[str]] = None,
        direction: SyncDirection = SyncDirection.SPOKE_TO_CACHE,
        last_updated_since: Optional[datetime.datetime] = None,
        build_transitive: bool = True,
    ) -> Dict[str, Any]:
        """Synchronize all entities from SPOKE to the cache.

        Args:
            entity_types: List of entity types to synchronize
            direction: Synchronization direction
            last_updated_since: Only sync entities updated since this time
            build_transitive: Whether to build transitive relationships after sync

        Returns:
            Dictionary with synchronization results
        """
        results = {
            "total_entities_processed": 0,
            "total_mappings_added_to_cache": 0,
            "total_mappings_added_to_spoke": 0,
            "transitive_mappings_created": 0,
            "errors": [],
            "entity_types_processed": set(),
            "duration_ms": 0,
        }

        start_time = time.time()

        try:
            # Use configured entity types if none specified
            if entity_types is None:
                if self.config.entity_types_to_sync:
                    entity_types = self.config.entity_types_to_sync
                else:
                    # Use all mapped types
                    entity_types = list(self.config.cache_to_spoke_type_map.keys())

            # Filter excluded types
            if self.config.excluded_entity_types:
                entity_types = [
                    t
                    for t in entity_types
                    if t not in self.config.excluded_entity_types
                ]

            # Process each entity type
            for entity_type in entity_types:
                try:
                    # Convert cache type to SPOKE type
                    spoke_type = self.config.cache_to_spoke_type_map.get(
                        entity_type, entity_type
                    )

                    # Get entities from SPOKE
                    with track_cache_operation(
                        operation_type=CacheEventType.API_CALL,
                        entity_type=entity_type,
                        metadata={"source": "spoke", "operation": "get_entities"},
                    ):
                        entities = await self.spoke_client.get_entities(
                            entity_type=spoke_type,
                            last_updated_since=last_updated_since,
                            limit=self.config.max_items_per_sync,
                        )

                    logger.info(
                        f"Found {len(entities)} entities of type {spoke_type} in SPOKE"
                    )

                    # Process in batches
                    for i in range(0, len(entities), self.config.sync_batch_size):
                        batch = entities[i : i + self.config.sync_batch_size]

                        for entity in batch:
                            entity_id = entity["id"]

                            # Synchronize this entity
                            entity_result = await self.sync_entity_mappings(
                                entity_id=entity_id,
                                entity_type=entity_type,
                                direction=direction,
                                build_transitive=False,  # Build once at the end
                            )

                            # Update results
                            results["total_entities_processed"] += 1
                            results["total_mappings_added_to_cache"] += entity_result[
                                "mappings_added_to_cache"
                            ]
                            results["total_mappings_added_to_spoke"] += entity_result[
                                "mappings_added_to_spoke"
                            ]

                            # Add any errors
                            results["errors"].extend(entity_result["errors"])

                    # Mark this type as processed
                    results["entity_types_processed"].add(entity_type)

                except Exception as e:
                    results["errors"].append(
                        f"Error processing entity type {entity_type}: {str(e)}"
                    )

            # Build transitive relationships if requested
            if build_transitive:
                transitive_count = self.transitivity_builder.build_transitive_mappings()
                results["transitive_mappings_created"] = transitive_count

        except Exception as e:
            results["errors"].append(f"Error during full synchronization: {str(e)}")

        # Calculate duration
        end_time = time.time()
        results["duration_ms"] = round((end_time - start_time) * 1000, 2)

        # Convert set to list for JSON serialization
        results["entity_types_processed"] = list(results["entity_types_processed"])

        return results

    async def sync_new_mappings_to_spoke(
        self,
        since: Optional[datetime.datetime] = None,
        only_derived: bool = False,
        min_confidence: float = 0.8,
    ) -> Dict[str, Any]:
        """Synchronize new mappings from the cache to SPOKE.

        Args:
            since: Only sync mappings created since this time
            only_derived: Only sync derived (transitive) mappings
            min_confidence: Minimum confidence threshold for syncing

        Returns:
            Dictionary with synchronization results
        """
        results = {
            "mappings_added_to_spoke": 0,
            "errors": [],
            "duration_ms": 0,
        }

        start_time = time.time()

        try:
            # Create session to query mappings
            with self.cache_manager._session_scope() as session:
                # Build query
                query = session.query(EntityMapping).filter(
                    EntityMapping.confidence >= min_confidence,
                    EntityMapping.mapping_source
                    != "spoke",  # Don't sync mappings from SPOKE
                )

                # Add time filter if specified
                if since:
                    query = query.filter(EntityMapping.last_updated >= since)

                # Add derived filter if specified
                if only_derived:
                    query = query.filter(EntityMapping.is_derived == True)

                # Get total count
                total_mappings = query.count()
                logger.info(f"Found {total_mappings} mappings to sync to SPOKE")

                # Process in batches
                processed = 0
                for mapping in query.yield_per(self.config.sync_batch_size):
                    try:
                        # Convert cache types to SPOKE types
                        source_type_in_spoke = self.config.cache_to_spoke_type_map.get(
                            mapping.source_type, mapping.source_type.title()
                        )

                        target_type_in_spoke = self.config.cache_to_spoke_type_map.get(
                            mapping.target_type, mapping.target_type.title()
                        )

                        # Add to SPOKE
                        with track_cache_operation(
                            operation_type=CacheEventType.API_CALL,
                            entity_type=mapping.source_type,
                            metadata={
                                "target": "spoke",
                                "operation": "add_entity_mapping",
                            },
                        ):
                            # Get metadata if available
                            metadata = {}
                            if mapping.metadata:
                                metadata = {m.key: m.value for m in mapping.metadata}

                            # Add derivation path metadata if this is a derived mapping
                            if mapping.is_derived and mapping.derivation_path:
                                metadata["derivation_path"] = mapping.derivation_path

                            await self.spoke_client.add_entity_mapping(
                                source_id=mapping.source_id,
                                source_type=source_type_in_spoke,
                                target_id=mapping.target_id,
                                target_type=target_type_in_spoke,
                                confidence=mapping.confidence,
                                metadata=metadata,
                            )

                        results["mappings_added_to_spoke"] += 1

                    except Exception as e:
                        error_msg = (
                            f"Error syncing mapping {mapping.source_type}:{mapping.source_id} -> "
                            f"{mapping.target_type}:{mapping.target_id}: {str(e)}"
                        )
                        results["errors"].append(error_msg)

                    # Update progress
                    processed += 1
                    if processed % 100 == 0:
                        logger.info(f"Processed {processed}/{total_mappings} mappings")

        except Exception as e:
            results["errors"].append(f"Error during mapping synchronization: {str(e)}")

        # Calculate duration
        end_time = time.time()
        results["duration_ms"] = round((end_time - start_time) * 1000, 2)

        return results


async def sync_entities_from_list(
    entity_list_file: str,
    spoke_client: SpokeClient,
    cache_manager: Optional[CacheManager] = None,
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
    build_transitive: bool = True,
) -> Dict[str, Any]:
    """Synchronize entities from a list file.

    Args:
        entity_list_file: Path to file containing entity IDs and types
        spoke_client: SPOKE client
        cache_manager: Cache manager
        direction: Synchronization direction
        build_transitive: Whether to build transitive relationships

    Returns:
        Dictionary with synchronization results
    """
    results = {
        "entities_processed": 0,
        "mappings_added_to_cache": 0,
        "mappings_added_to_spoke": 0,
        "transitive_mappings_created": 0,
        "errors": [],
    }

    try:
        # Create sync manager
        sync_manager = SpokeCacheSync(
            spoke_client=spoke_client,
            cache_manager=cache_manager,
        )

        # Read entity list file
        with open(entity_list_file, "r") as f:
            entities = []

            # Check if it's JSON or CSV-like
            first_line = f.readline().strip()
            f.seek(0)

            if first_line.startswith("{") or first_line.startswith("["):
                # JSON format
                entities = json.load(f)
            else:
                # CSV-like format
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        entity_id = parts[0].strip()
                        entity_type = parts[1].strip()
                        entities.append({"id": entity_id, "type": entity_type})

        # Process entities
        for entity in entities:
            entity_id = entity["id"]
            entity_type = entity["type"]

            # Synchronize entity
            entity_result = await sync_manager.sync_entity_mappings(
                entity_id=entity_id,
                entity_type=entity_type,
                direction=direction,
                build_transitive=False,  # Build once at the end
            )

            # Update results
            results["entities_processed"] += 1
            results["mappings_added_to_cache"] += entity_result[
                "mappings_added_to_cache"
            ]
            results["mappings_added_to_spoke"] += entity_result[
                "mappings_added_to_spoke"
            ]

            # Add any errors
            results["errors"].extend(entity_result["errors"])

        # Build transitive relationships if requested
        if build_transitive:
            transitive_count = (
                sync_manager.transitivity_builder.build_transitive_mappings()
            )
            results["transitive_mappings_created"] = transitive_count

    except Exception as e:
        results["errors"].append(f"Error processing entity list: {str(e)}")

    return results
