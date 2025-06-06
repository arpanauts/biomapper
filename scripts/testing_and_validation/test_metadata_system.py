#!/usr/bin/env python
"""
Test script for verifying the Resource Metadata System integration.

This script initializes the metadata system, registers resources,
performs test mappings, and displays performance metrics.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any, Optional

# Ensure biomapper is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from biomapper.metadata.factory import MetadataFactory
from biomapper.metadata.manager import ResourceMetadataManager
from biomapper.metadata.models import (
    ResourceType,
    SupportLevel,
    OperationType,
    OntologyCoverage,
    ResourceMetadata,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("metadata_test")


async def test_resource_registration() -> ResourceMetadataManager:
    """Test resource registration functionality."""
    logger.info("Testing resource registration...")

    # Initialize metadata manager
    metadata_manager = ResourceMetadataManager()

    # Register SQLite cache resource
    cache = metadata_manager.register_resource(
        resource_name="sqlite_cache",
        resource_type=ResourceType.CACHE,
        connection_info={
            "data_dir": "/home/ubuntu/biomapper/data",
            "db_name": "mappings.db",
        },
        priority=10,
    )
    logger.info(f"Registered cache resource: {cache.resource_name} (ID: {cache.id})")

    # Register SPOKE graph resource
    spoke = metadata_manager.register_resource(
        resource_name="spoke_graph",
        resource_type=ResourceType.GRAPH,
        connection_info={"url": "http://spoke-api:4000", "database": "spoke"},
        priority=5,
    )
    logger.info(f"Registered SPOKE resource: {spoke.resource_name} (ID: {spoke.id})")

    # Register ontology coverage
    metabolite_ontologies = ["chebi", "hmdb", "pubchem", "inchikey", "compound_name"]
    for ontology in metabolite_ontologies:
        coverage = metadata_manager.register_ontology_coverage(
            resource_name="sqlite_cache",
            ontology_type=ontology,
            support_level=SupportLevel.FULL,
        )
        logger.info(f"Registered ontology coverage: {ontology} for sqlite_cache")

        coverage = metadata_manager.register_ontology_coverage(
            resource_name="spoke_graph",
            ontology_type=ontology,
            support_level=SupportLevel.PARTIAL,
        )
        logger.info(f"Registered ontology coverage: {ontology} for spoke_graph")

    # List registered resources
    resources = metadata_manager.list_resources()
    logger.info(f"Registered resources: {len(resources)}")
    for resource in resources:
        logger.info(f"  - {resource.resource_name} ({resource.resource_type.value})")

    return metadata_manager


async def test_mapping_dispatcher(factory: MetadataFactory) -> None:
    """Test the mapping dispatcher functionality."""
    logger.info("Testing mapping dispatcher...")

    # Create the complete system
    system = factory.create_complete_system(force_init=False)
    dispatcher = system["dispatcher"]

    # Test mappings
    test_compounds = ["glucose", "adenosine triphosphate", "caffeine", "aspirin"]

    for compound in test_compounds:
        logger.info(f"Testing mapping for '{compound}'...")

        try:
            # Try to map the compound
            result = await dispatcher.map_entity(
                source_id=compound,
                source_type="compound_name",
                target_type="chebi",
                fallback=True,
                timeout=5.0,
            )

            if result:
                resource = (
                    result.metadata.get("resource")
                    if hasattr(result, "metadata")
                    else "unknown"
                )
                response_time = (
                    result.metadata.get("response_time_ms")
                    if hasattr(result, "metadata")
                    else "unknown"
                )
                logger.info(f"  Found mapping using {resource} in {response_time}ms")
                logger.info(f"    Result: {result}")
            else:
                logger.info(f"  No mapping found for {compound}")

        except Exception as e:
            logger.error(f"  Error mapping {compound}: {e}")


async def test_performance_metrics(metadata_manager: ResourceMetadataManager) -> None:
    """Test and display performance metrics."""
    logger.info("Testing performance metrics collection...")

    # Simulate some operations with different response times
    for i in range(5):
        # Simulate success with varying response times
        metadata_manager.log_operation(
            resource_name="sqlite_cache",
            operation_type=OperationType.MAP,
            source_type="compound_name",
            target_type="chebi",
            query=f"test_compound_{i}",
            response_time_ms=50 + (i * 10),  # Varying response times
            status="success",
        )

        # Simulate some errors for SPOKE
        status = "success" if i % 3 != 0 else "error"
        metadata_manager.log_operation(
            resource_name="spoke_graph",
            operation_type=OperationType.MAP,
            source_type="compound_name",
            target_type="chebi",
            query=f"test_compound_{i}",
            response_time_ms=100 + (i * 30),  # Slower than cache
            status=status,
        )

    # Get and display metrics
    metrics = metadata_manager.get_performance_metrics()
    logger.info("Performance metrics:")
    for metric in metrics:
        logger.info(
            f"  {metric.resource.resource_name} - "
            f"{metric.operation_type.value}/{metric.source_type}->{metric.target_type}: "
            f"avg={metric.avg_response_time_ms:.1f}ms, "
            f"success={metric.success_rate:.2f}, "
            f"samples={metric.sample_count}"
        )


async def test_resource_prioritization(
    metadata_manager: ResourceMetadataManager,
) -> None:
    """Test the resource prioritization logic."""
    logger.info("Testing resource prioritization...")

    # Get preferred resource order before performance metrics
    resources_before = metadata_manager.get_preferred_resource_order(
        source_type="compound_name",
        target_type="chebi",
        operation_type=OperationType.MAP,
    )
    logger.info("Resource priority before metrics:")
    for i, resource in enumerate(resources_before):
        logger.info(f"  {i+1}. {resource}")

    # Add more performance data to influence priorities
    for i in range(10):
        # Make SPOKE faster for this specific mapping
        metadata_manager.log_operation(
            resource_name="spoke_graph",
            operation_type=OperationType.MAP,
            source_type="gene_symbol",
            target_type="uniprot",
            query=f"BRCA{i}",
            response_time_ms=20 + (i * 2),  # Very fast
            status="success",
        )

    # Get preferred resource order after performance metrics
    resources_after = metadata_manager.get_preferred_resource_order(
        source_type="gene_symbol",
        target_type="uniprot",
        operation_type=OperationType.MAP,
    )
    logger.info("Resource priority for gene_symbol->uniprot:")
    for i, resource in enumerate(resources_after):
        logger.info(f"  {i+1}. {resource}")


async def main():
    """Main test function."""
    logger.info("=== Starting Resource Metadata System Test ===")
    start_time = time.time()

    # Create factory
    factory = MetadataFactory()

    # Test resource registration
    metadata_manager = await test_resource_registration()

    # Test performance metrics
    await test_performance_metrics(metadata_manager)

    # Test resource prioritization
    await test_resource_prioritization(metadata_manager)

    # Test mapping dispatcher
    await test_mapping_dispatcher(factory)

    elapsed = time.time() - start_time
    logger.info(f"=== Test completed in {elapsed:.2f} seconds ===")


if __name__ == "__main__":
    asyncio.run(main())
