"""
Example usage of the Resource Metadata System.

This example demonstrates how to initialize the metadata system,
register resources, and use the MappingDispatcher for efficient
mapping operations.
"""

import asyncio
import os
import logging
from typing import Dict, List, Any

from biomapper.mapping.metadata.initialize import (
    initialize_metadata_system,
    get_metadata_db_path,
)
from biomapper.mapping.metadata.manager import ResourceMetadataManager
from biomapper.mapping.metadata.dispatcher import MappingDispatcher
from biomapper.mapping.adapters.cache_adapter import CacheResourceAdapter
from biomapper.mapping.adapters.spoke_adapter import SpokeResourceAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the example."""
    # Initialize the metadata system
    db_path = get_metadata_db_path()
    if not os.path.exists(db_path):
        logger.info(f"Initializing metadata system at {db_path}")
        initialize_metadata_system(db_path)

    # Create the resource metadata manager
    metadata_manager = ResourceMetadataManager(db_path)

    # Register resources
    with metadata_manager:
        # Register SQLite cache
        cache_id = metadata_manager.register_resource(
            name="sqlite_cache",
            resource_type="cache",
            connection_info={"db_path": "/home/ubuntu/.biomapper/mappings.db"},
            priority=10,  # Highest priority
        )

        # Register ontology coverage for cache
        metadata_manager.register_ontology_coverage(
            resource_name="sqlite_cache", ontology_type="chebi", support_level="full"
        )
        metadata_manager.register_ontology_coverage(
            resource_name="sqlite_cache", ontology_type="hmdb", support_level="full"
        )
        metadata_manager.register_ontology_coverage(
            resource_name="sqlite_cache", ontology_type="pubchem", support_level="full"
        )

        # Register SPOKE knowledge graph
        spoke_id = metadata_manager.register_resource(
            name="spoke_graph",
            resource_type="graph",
            connection_info={
                "host": "localhost",
                "port": 8529,
                "db_name": "spoke",
                "username": "spoke",
                "password": "spoke_password",
            },
            priority=5,  # Medium priority
        )

        # Register ontology coverage for SPOKE
        metadata_manager.register_ontology_coverage(
            resource_name="spoke_graph",
            ontology_type="chebi",
            support_level="partial",
            entity_count=12000,
        )
        metadata_manager.register_ontology_coverage(
            resource_name="spoke_graph",
            ontology_type="hmdb",
            support_level="partial",
            entity_count=5000,
        )
        metadata_manager.register_ontology_coverage(
            resource_name="spoke_graph",
            ontology_type="uniprot",
            support_level="full",
            entity_count=20000,
        )

    # Create the mapping dispatcher
    dispatcher = MappingDispatcher(metadata_manager)

    # Add resource adapters
    # Note: In a real implementation, you would check if the resources
    # are actually available before adding them

    # Add SQLite cache adapter
    cache_config = {"db_path": "/home/ubuntu/.biomapper/mappings.db"}
    cache_adapter = CacheResourceAdapter(cache_config, "sqlite_cache")
    await dispatcher.add_resource_adapter("sqlite_cache", cache_adapter)

    # Add SPOKE adapter
    # Note: This is just for demonstration, in practice you would
    # need a real SPOKE instance to connect to
    spoke_config = {
        "host": "localhost",
        "port": 8529,
        "db_name": "spoke",
        "username": "spoke",
        "password": "spoke_password",
    }
    spoke_adapter = SpokeResourceAdapter(spoke_config, "spoke_graph")
    # In a real implementation, this would connect to SPOKE
    # await dispatcher.add_resource_adapter("spoke_graph", spoke_adapter)

    # Example mapping operation
    # This simulation just shows how the dispatcher would be used
    logger.info("Simulating mapping 'glucose' to ChEBI ID...")
    logger.info(
        "In a real implementation, this would use the adapters to query resources."
    )

    # This is how you would use the dispatcher:
    # results = await dispatcher.map_entity(
    #     source_id="glucose",
    #     source_type="compound_name",
    #     target_type="chebi"
    # )

    # Simulate results
    results = [
        {"target_id": "CHEBI:17234", "confidence": 0.95, "source": "sqlite_cache"}
    ]

    logger.info(f"Mapping results: {results}")

    # Show resource priorities
    with metadata_manager:
        resources = metadata_manager.get_resources_by_priority("compound_name", "chebi")
        logger.info("Resources prioritized for this mapping:")
        for resource in resources:
            logger.info(f"  {resource['name']} (Priority: {resource['priority']})")


if __name__ == "__main__":
    asyncio.run(main())
