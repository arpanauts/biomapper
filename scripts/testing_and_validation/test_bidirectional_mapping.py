#!/usr/bin/env python3
"""
Test script for bidirectional mapping implementation.

This script tests the bidirectional mapping functionality in the MappingExecutor,
verifying both forward, reverse, and bidirectional (fallback) mapping scenarios.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.cache_models import EntityMapping, PathExecutionLog
from biomapper.utils.config import CONFIG_DB_URL, CACHE_DB_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

# Test configuration
SOURCE_ENDPOINT = "UKBB_Protein"
TARGET_ENDPOINT = "Arivale_Protein"
SOURCE_PROPERTY = "PrimaryIdentifier"
TARGET_PROPERTY = "PrimaryIdentifier"

# Test data - a mix of IDs to test different scenarios
# Using real IDs from the database that we know exist
FORWARD_TEST_IDS = [
    "P01579",
    "P12104",
    "Q96KN2",
    "P78552",
    "O00533",
]  # Should succeed in forward

# Use existing Arivale IDs that should be reverse mappable
REVERSE_TEST_IDS = [
    "INF_P01579",
    "CVD2_P12104",
    "CAM_Q96KN2",
    "DEV_P78552",
    "CAM_O00533",
]

# These IDs should try forward first, then fall back to reverse if needed
BIDIRECTIONAL_TEST_IDS = ["Q9Y5C1", "CAM_Q9Y5C1", "NO_MAPPING_AT_ALL"]


async def perform_mapping_test(
    executor: MappingExecutor,
    direction: str,
    source_endpoint: str,
    target_endpoint: str,
    input_ids: List[str],
    try_reverse: bool = False,
) -> Dict[str, Any]:
    """Perform a mapping test and log the results."""
    logger.info(f"Executing {direction} mapping test with try_reverse={try_reverse}:")
    logger.info(f"  Input IDs: {input_ids}")

    # Determine which direction to use based on test type
    mapping_direction = "forward"
    if direction == "reverse":
        # For explicit reverse test, swap endpoints
        source_endpoint, target_endpoint = target_endpoint, source_endpoint
        mapping_direction = "reverse"

    # Enable more verbose logging for bidirectional test
    if try_reverse:
        # Make executor logger more verbose
        exec_logger = logging.getLogger("biomapper.core.mapping_executor")
        old_level = exec_logger.level
        exec_logger.setLevel(logging.DEBUG)

    # Execute mapping
    start_time = datetime.now()
    results = await executor.execute_mapping(
        source_endpoint_name=source_endpoint,
        target_endpoint_name=target_endpoint,
        input_data=input_ids,
        source_property_name=SOURCE_PROPERTY,
        target_property_name=TARGET_PROPERTY,
        mapping_direction=mapping_direction,
        try_reverse_mapping=try_reverse,  # Only use reverse when testing bidirectional
    )

    # Restore log level
    if try_reverse:
        exec_logger.setLevel(old_level)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Log results
    successful = sum(1 for v in results.values() if v is not None)
    logger.info(f"  Results: {results}")
    logger.info(
        f"  Summary: {successful}/{len(input_ids)} successful mappings in {elapsed:.2f} seconds\n"
    )

    return results


async def check_db_metadata(
    executor: MappingExecutor,
    source_ontology: str,
    target_ontology: str,
    mapped_ids: Dict[str, Optional[List[str]]],
) -> None:
    """Check database for metadata fields associated with the mappings."""
    logger.info(f"Checking database metadata for {len(mapped_ids)} mappings:")

    # Only check successful mappings
    successful_mappings = {k: v for k, v in mapped_ids.items() if v is not None}
    if not successful_mappings:
        logger.info("  No successful mappings to check.")
        return

    # Connect to cache database
    async with executor.get_cache_session() as cache_session:
        for source_id, target_ids in successful_mappings.items():
            target_id = target_ids[0] if isinstance(target_ids, list) else target_ids

            stmt = select(EntityMapping).where(
                EntityMapping.source_id == source_id,
                EntityMapping.target_id == target_id,
            )
            result = await cache_session.execute(stmt)
            mapping = result.scalar_one_or_none()

            if mapping:
                logger.info(f"  Mapping found for {source_id} -> {target_id}:")
                logger.info(f"    Direction: {mapping.mapping_direction}")
                logger.info(f"    Confidence Score: {mapping.confidence_score}")
                logger.info(f"    Hop Count: {mapping.hop_count}")

                if mapping.mapping_path_details:
                    path_details = mapping.mapping_path_details
                    if isinstance(path_details, str):
                        try:
                            path_details = json.loads(path_details)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"    Invalid JSON in mapping_path_details: {path_details}"
                            )

                    logger.info(f"    Path Details: {path_details}")
                else:
                    logger.info("    Path Details: None")
                logger.info("")
            else:
                logger.warning(
                    f"  No mapping found in database for {source_id} -> {target_id}"
                )


async def main():
    """Run the bidirectional mapping tests."""
    logger.info("Starting bidirectional mapping test")

    # Initialize executor
    executor = MappingExecutor(
        metamapper_db_url=CONFIG_DB_URL,
        mapping_cache_db_url=CACHE_DB_URL,
    )

    # Determine source and target ontology types
    async with executor.async_session() as meta_session:
        source_ontology = await executor._get_ontology_type(
            meta_session, SOURCE_ENDPOINT, SOURCE_PROPERTY
        )
        target_ontology = await executor._get_ontology_type(
            meta_session, TARGET_ENDPOINT, TARGET_PROPERTY
        )

        if not source_ontology or not target_ontology:
            logger.error(
                f"Could not determine ontology types for {SOURCE_ENDPOINT} and {TARGET_ENDPOINT}"
            )
            return

        logger.info(
            f"Source ontology: {source_ontology}, Target ontology: {target_ontology}"
        )

    # Test 1: Forward Mapping
    forward_results = await perform_mapping_test(
        executor,
        "forward",
        SOURCE_ENDPOINT,
        TARGET_ENDPOINT,
        FORWARD_TEST_IDS,
        try_reverse=False,
    )

    # Test 2: Reverse Mapping
    reverse_results = await perform_mapping_test(
        executor,
        "reverse",
        TARGET_ENDPOINT,
        SOURCE_ENDPOINT,
        REVERSE_TEST_IDS,
        try_reverse=False,
    )

    # Test 3: Bidirectional Mapping with Fallback
    bidirectional_results = await perform_mapping_test(
        executor,
        "forward",
        SOURCE_ENDPOINT,
        TARGET_ENDPOINT,
        BIDIRECTIONAL_TEST_IDS,
        try_reverse=True,
    )

    # Check metadata in database
    logger.info("\nChecking database metadata:")

    # Forward mappings
    logger.info("\nFORWARD MAPPINGS METADATA:")
    await check_db_metadata(executor, source_ontology, target_ontology, forward_results)

    # Reverse mappings
    logger.info("\nREVERSE MAPPINGS METADATA:")
    # For reverse, swap source/target ontology
    await check_db_metadata(executor, target_ontology, source_ontology, reverse_results)

    # Bidirectional mappings
    logger.info("\nBIDIRECTIONAL MAPPINGS METADATA:")
    await check_db_metadata(
        executor, source_ontology, target_ontology, bidirectional_results
    )


if __name__ == "__main__":
    asyncio.run(main())
