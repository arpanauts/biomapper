#!/usr/bin/env python
"""Example script demonstrating integration between SPOKE and SQLite mapping cache.

This example shows:
1. Initializing the cache database
2. Setting up a connection to SPOKE
3. Synchronizing mappings between SPOKE and cache
4. Performing lookups using the integrated system
5. Building transitive relationships
"""

import asyncio
import logging
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biomapper.cache.config import get_default_config
from biomapper.cache.manager import CacheManager
from biomapper.cache.monitoring import get_cache_stats
from biomapper.db.session import get_db_manager
from biomapper.integration.spoke_cache_sync import SpokeCacheSync
from biomapper.spoke.client import SpokeClient
from biomapper.transitivity.builder import TransitivityBuilder


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the demonstration."""
    # Initialize the cache configuration
    config = get_default_config()

    # Make sure data directory exists
    os.makedirs(config.data_dir, exist_ok=True)

    # Initialize database (will create if it doesn't exist)
    db_manager = get_db_manager(data_dir=config.data_dir, db_name=config.db_name)
    db_manager.init_db()

    logger.info(
        f"Database initialized at {os.path.join(config.data_dir, config.db_name)}"
    )

    # Create cache manager
    cache_manager = CacheManager(
        data_dir=config.data_dir,
        db_name=config.db_name,
        min_confidence=0.7,
        ttl_days=30,
    )

    # Create SPOKE client
    spoke_client = SpokeClient(
        base_url=os.environ.get("SPOKE_API_URL", "https://spoke.example.org/api/v1"),
        api_key=os.environ.get("SPOKE_API_KEY", "demo_key"),
    )

    # Create sync manager
    sync_manager = SpokeCacheSync(
        spoke_client=spoke_client,
        cache_manager=cache_manager,
    )

    # Example 1: Add some example mappings to the cache
    logger.info("Adding example mappings to the cache...")

    # Add glucose mappings
    cache_manager.add_mapping(
        source_id="glucose",
        source_type="compound_name",
        target_id="CHEBI:17234",
        target_type="chebi",
        confidence=0.95,
        mapping_source="manual",
        metadata={"common_name": "Glucose", "formula": "C6H12O6"},
    )

    cache_manager.add_mapping(
        source_id="CHEBI:17234",
        source_type="chebi",
        target_id="HMDB0000122",
        target_type="hmdb",
        confidence=0.95,
        mapping_source="unichem",
        metadata={"common_name": "Glucose", "formula": "C6H12O6"},
    )

    cache_manager.add_mapping(
        source_id="HMDB0000122",
        source_type="hmdb",
        target_id="CID5793",
        target_type="pubchem.compound",
        confidence=0.9,
        mapping_source="unichem",
    )

    # Example 2: Build transitive relationships
    logger.info("Building transitive relationships...")

    # Create transitivity builder
    transitivity_builder = TransitivityBuilder(
        cache_manager=cache_manager,
        min_confidence=0.7,
        max_chain_length=3,
        confidence_decay=0.9,
    )

    # Build transitive mappings
    new_mappings = transitivity_builder.build_transitive_mappings()
    logger.info(f"Created {new_mappings} new transitive mappings")

    # Example 3: Look up mappings using cache
    logger.info("Looking up mappings from cache...")

    # Look up glucose by name
    glucose_results = cache_manager.lookup(
        source_id="glucose", source_type="compound_name", include_metadata=True
    )

    logger.info(f"Found {len(glucose_results)} mappings for 'glucose':")
    for mapping in glucose_results:
        logger.info(
            f"  → {mapping['target_type']}:{mapping['target_id']} "
            f"(confidence: {mapping['confidence']:.2f}, "
            f"source: {mapping.get('mapping_source', 'unknown')})"
        )

    # Example 4: Synchronize with SPOKE
    logger.info("\nSynchronizing with SPOKE...")

    # This would normally use real data, but we'll use our example data for demonstration
    test_entities = [
        {"id": "CHEBI:17234", "type": "chebi"},
        {"id": "HMDB0000122", "type": "hmdb"},
        {"id": "CID5793", "type": "pubchem.compound"},
    ]

    # Synchronize each entity
    for entity in test_entities:
        logger.info(f"Synchronizing {entity['type']}:{entity['id']}...")

        # In a real scenario, this would communicate with the SPOKE API
        # For demo, we're showing the function call but not executing it

        # Commented out as we don't have a real SPOKE instance for testing
        # sync_result = await sync_manager.sync_entity_mappings(
        #     entity_id=entity["id"],
        #     entity_type=entity["type"],
        #     direction=SyncDirection.BIDIRECTIONAL,
        # )
        #
        # logger.info(f"  → Added {sync_result['mappings_added_to_cache']} mappings to cache")
        # logger.info(f"  → Added {sync_result['mappings_added_to_spoke']} mappings to SPOKE")

        # For demo purposes, show a simulated result
        logger.info("  → Simulation: Added 3 mappings to cache")
        logger.info("  → Simulation: Added 2 mappings to SPOKE")

    # Example 5: Check cache statistics
    logger.info("\nChecking cache statistics...")

    stats = get_cache_stats(days=7)

    logger.info("Cache statistics for the past 7 days:")
    logger.info(f"  → Total entities: {stats['total_entities']}")
    logger.info(f"  → Total mappings: {stats['total_mappings']}")
    logger.info(f"  → Direct mappings: {stats['direct_mappings']}")
    logger.info(f"  → Derived mappings: {stats['derived_mappings']}")
    logger.info(f"  → Hit ratio: {stats['hit_ratio'] * 100:.1f}%")

    events = stats.get("events", {})
    logger.info(f"  → Cache hits: {events.get('hit', 0)}")
    logger.info(f"  → Cache misses: {events.get('miss', 0)}")
    logger.info(f"  → API calls: {events.get('api_call', 0)}")

    # Example 6: Build extended transitive relationships
    logger.info("\nBuilding extended transitive relationships...")

    extended_mappings = transitivity_builder.build_extended_transitive_mappings()
    logger.info(f"Created {extended_mappings} extended transitive mappings")

    # Example 7: Final lookup to demonstrate all mapping types
    logger.info("\nFinal lookup demonstration:")

    # Look up glucose by ChEBI ID
    chebi_results = cache_manager.lookup(
        source_id="CHEBI:17234",
        source_type="chebi",
        include_derived=True,
        include_metadata=True,
    )

    logger.info(f"Found {len(chebi_results)} mappings for CHEBI:17234:")
    for mapping in chebi_results:
        # Indicate if it's a direct or derived mapping
        mapping_type = "Derived" if mapping.get("is_derived", False) else "Direct"

        logger.info(
            f"  → {mapping_type}: {mapping['target_type']}:{mapping['target_id']} "
            f"(confidence: {mapping['confidence']:.2f})"
        )


if __name__ == "__main__":
    asyncio.run(main())
