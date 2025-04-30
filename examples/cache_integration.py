#!/usr/bin/env python
"""Example script demonstrating the Biomapper SQLite mapping cache with transitivity.

This script shows how to initialize and use the mapping cache with bidirectional
transitivity to speed up biological entity mapping and discover new relationships.
"""

import asyncio
import logging
import os
import sys
from pprint import pprint
from typing import Dict, List, Optional

from biomapper.cache.manager import CacheManager
from biomapper.cache.mapper import CachedMapper
from biomapper.db.session import get_db_manager
from biomapper.mapping.clients.chebi_client import ChEBIClient
from biomapper.mapping.clients.unichem_client import UniChemClient
from biomapper.standardization.ramp_client import RaMPClient, RaMPConfig
from biomapper.transitivity.builder import TransitivityBuilder


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def populate_initial_mappings():
    """Populate the cache with initial mappings from various sources."""
    logger.info("Populating initial mappings from external sources...")

    # Initialize clients
    chebi_client = ChEBIClient()
    unichem_client = UniChemClient()
    ramp_client = RaMPClient()

    # Initialize cache manager
    cache_manager = CacheManager(default_ttl_days=365, confidence_threshold=0.7)

    # Example: Add some ChEBI mappings
    try:
        # Map glucose between ChEBI and PubChem
        chebi_id = "CHEBI:17234"  # Glucose
        pubchem_mappings = await unichem_client.get_compound_mappings(
            chebi_id, "chebi", "pubchem"
        )

        for mapping in pubchem_mappings:
            cache_manager.add_mapping(
                source_id=chebi_id,
                source_type="chebi",
                target_id=f"PUBCHEM.COMPOUND:{mapping['compound_id']}",
                target_type="pubchem.compound",
                confidence=1.0,
                mapping_source="unichem",
                metadata={"compound_name": "Glucose"},
            )
            logger.info(
                f"Added mapping: {chebi_id} -> PUBCHEM.COMPOUND:{mapping['compound_id']}"
            )

        # Map glucose between ChEBI and HMDB
        hmdb_mappings = await unichem_client.get_compound_mappings(
            chebi_id, "chebi", "hmdb"
        )

        for mapping in hmdb_mappings:
            cache_manager.add_mapping(
                source_id=chebi_id,
                source_type="chebi",
                target_id=mapping["compound_id"],
                target_type="hmdb",
                confidence=1.0,
                mapping_source="unichem",
                metadata={"compound_name": "Glucose"},
            )
            logger.info(f"Added mapping: {chebi_id} -> {mapping['compound_id']}")

        # Add some RaMP mappings
        hmdb_id = "HMDB0000122"  # Glucose
        ramp_mappings = ramp_client.get_analyte_mappings(hmdb_id)

        if ramp_mappings and "kegg" in ramp_mappings:
            for kegg_id in ramp_mappings["kegg"]:
                cache_manager.add_mapping(
                    source_id=hmdb_id,
                    source_type="hmdb",
                    target_id=f"KEGG:{kegg_id}",
                    target_type="kegg",
                    confidence=0.9,
                    mapping_source="ramp",
                    metadata={"compound_name": "Glucose"},
                )
                logger.info(f"Added mapping: {hmdb_id} -> KEGG:{kegg_id}")

    except Exception as e:
        logger.error(f"Error populating initial mappings: {e}")
        return False

    return True


def build_transitive_relationships():
    """Build transitive relationships between entities."""
    logger.info("Building transitive relationships...")

    # Initialize cache manager and transitivity builder
    cache_manager = CacheManager()
    builder = TransitivityBuilder(
        cache_manager=cache_manager,
        min_confidence=0.7,
        max_chain_length=3,
        confidence_decay=0.9,
    )

    # Build transitive mappings
    new_count = builder.build_transitive_mappings()
    logger.info(f"Created {new_count} new transitive mappings")

    # Build extended transitive mappings (chains of length > 2)
    if new_count > 0:
        extended_count = builder.build_extended_transitive_mappings()
        logger.info(f"Created {extended_count} extended transitive mappings")

    return True


async def demonstrate_cached_mapper():
    """Demonstrate the use of the cached mapper."""
    logger.info("Demonstrating cached mapper...")

    # Initialize clients
    chebi_client = ChEBIClient()

    # Create a simple mapper from the client
    from biomapper.mapping.clients.chebi_client import ChEBIMapper
    from biomapper.schemas.domain_schema import CompoundDocument

    # Create base mapper
    base_mapper = ChEBIMapper(chebi_client)

    # Wrap with cached mapper
    cached_mapper = CachedMapper(
        base_mapper=base_mapper,
        document_class=CompoundDocument,
        source_type="compound_name",
        target_type="chebi",
        ttl_days=365,
        min_confidence=0.7,
        use_derived_mappings=True,
    )

    # Demonstrate cache lookup pattern
    test_compounds = ["glucose", "fructose", "galactose", "mannose"]

    for compound in test_compounds:
        # First lookup (potential cache miss)
        start_time = asyncio.get_event_loop().time()
        result1 = await cached_mapper.map_entity(compound)
        elapsed1 = asyncio.get_event_loop().time() - start_time

        if result1.mapped_entity:
            logger.info(
                f"Mapped '{compound}' to {result1.mapped_entity.id} "
                f"(cache: {'hit' if result1.metadata.get('cache_hit') else 'miss'}, "
                f"time: {elapsed1:.3f}s)"
            )

            # Second lookup (should be cache hit)
            start_time = asyncio.get_event_loop().time()
            result2 = await cached_mapper.map_entity(compound)
            elapsed2 = asyncio.get_event_loop().time() - start_time

            logger.info(
                f"Repeat mapping '{compound}' to {result2.mapped_entity.id} "
                f"(cache: {'hit' if result2.metadata.get('cache_hit') else 'miss'}, "
                f"time: {elapsed2:.3f}s)"
            )

            # Calculate speedup
            if elapsed1 > 0:
                speedup = elapsed1 / max(elapsed2, 0.0001)
                logger.info(f"Cache speedup: {speedup:.1f}x")
        else:
            logger.warning(f"Could not map '{compound}'")

    return True


def show_cache_stats():
    """Show cache statistics."""
    logger.info("Cache statistics:")

    cache_manager = CacheManager()
    stats = cache_manager.get_cache_stats()

    if not stats:
        logger.info("No statistics available yet.")
        return

    for day_stats in stats:
        date = day_stats["date"]
        hit_ratio = day_stats["hit_ratio"] * 100
        hits = day_stats["hits"]
        misses = day_stats["misses"]
        direct = day_stats["direct_lookups"]
        derived = day_stats["derived_lookups"]
        api_calls = day_stats["api_calls"]
        transitive = day_stats["transitive_derivations"]

        logger.info(f"Date: {date}")
        logger.info(f"  Hit ratio: {hit_ratio:.1f}% ({hits} hits, {misses} misses)")
        logger.info(f"  Direct lookups: {direct}, Derived lookups: {derived}")
        logger.info(f"  API calls: {api_calls}, Transitive derivations: {transitive}")


def demonstrate_bidirectional_lookup(entity_id, entity_type):
    """Demonstrate the bidirectional lookup capability."""
    logger.info(f"Bidirectional lookup for {entity_type}:{entity_id}")

    cache_manager = CacheManager()
    mappings = cache_manager.bidirectional_lookup(
        entity_id=entity_id, entity_type=entity_type, include_derived=True
    )

    # Group by target type
    by_type = {}
    for mapping in mappings:
        # Determine if this entity is source or target
        if mapping["source_id"] == entity_id and mapping["source_type"] == entity_type:
            # This entity is the source, target is the other entity
            other_type = mapping["target_type"]
            other_id = mapping["target_id"]
        else:
            # This entity is the target, source is the other entity
            other_type = mapping["source_type"]
            other_id = mapping["source_id"]

        if other_type not in by_type:
            by_type[other_type] = []

        by_type[other_type].append(
            {
                "id": other_id,
                "confidence": mapping["confidence"],
                "is_derived": mapping.get("is_derived", False),
            }
        )

    # Print results
    logger.info(f"Found mappings to {len(by_type)} different entity types:")
    for type_name, entities in by_type.items():
        logger.info(f"  {type_name}: {len(entities)} entities")
        for i, entity in enumerate(
            sorted(entities, key=lambda e: e["confidence"], reverse=True)
        ):
            if i < 5:  # Limit to 5 examples per type
                derived = " (derived)" if entity["is_derived"] else ""
                logger.info(
                    f"    - {entity['id']} [{entity['confidence']:.2f}]{derived}"
                )

        if len(entities) > 5:
            logger.info(f"    - ... and {len(entities) - 5} more")

    return True


async def main():
    """Main function."""
    # Initialize cache database
    db_dir = os.path.join(os.path.expanduser("~"), ".biomapper", "data")
    os.makedirs(db_dir, exist_ok=True)

    db_manager = get_db_manager(data_dir=db_dir)
    db_manager.init_db(drop_all=False)  # Set to True to reset

    # Populate initial mappings
    if await populate_initial_mappings():
        # Build transitive relationships
        build_transitive_relationships()

        # Demonstrate cached mapper
        await demonstrate_cached_mapper()

        # Show cache statistics
        show_cache_stats()

        # Demonstrate bidirectional lookup with a glucose ChEBI ID
        demonstrate_bidirectional_lookup("CHEBI:17234", "chebi")


if __name__ == "__main__":
    asyncio.run(main())
