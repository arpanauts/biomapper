#!/usr/bin/env python3
"""
Test script for the bidirectional validation feature.

This script tests the new validate_bidirectional parameter in the MappingExecutor,
which enriches successful mappings with validation status information.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.utils.config import CONFIG_DB_URL, CACHE_DB_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

# Test configuration - adapt these for your specific endpoints
SOURCE_ENDPOINT = "UKBB_Protein"
TARGET_ENDPOINT = "Arivale_Protein" 
SOURCE_PROPERTY = "PrimaryIdentifier"
TARGET_PROPERTY = "PrimaryIdentifier"

# Test data - adapt with real IDs from your database
TEST_IDS = [
    "P01579",  # Should succeed in forward
    "P12104",  # Should succeed in forward
    "Q96KN2",  # Should succeed in forward
    "P78552",  # Should succeed in forward
    "O00533",  # Should succeed in forward
    "Q9Y5C1",  # Might have mixed validation results
]

async def test_bidirectional_validation():
    """Run the bidirectional validation test."""
    logger.info("Starting bidirectional validation test")

    # Initialize executor
    executor = MappingExecutor(
        metamapper_db_url=CONFIG_DB_URL,
        mapping_cache_db_url=CACHE_DB_URL,
    )

    # Make the executor logger more verbose
    exec_logger = logging.getLogger("biomapper.core.mapping_executor")
    old_level = exec_logger.level
    exec_logger.setLevel(logging.DEBUG)

    # Execute mapping with bidirectional validation
    logger.info("Executing mapping with bidirectional validation enabled:")
    logger.info(f"  Input IDs: {TEST_IDS}")

    start_time = datetime.now()
    results = await executor.execute_mapping(
        source_endpoint_name=SOURCE_ENDPOINT,
        target_endpoint_name=TARGET_ENDPOINT,
        input_data=TEST_IDS,
        source_property_name=SOURCE_PROPERTY,
        target_property_name=TARGET_PROPERTY,
        validate_bidirectional=True,  # Enable bidirectional validation
        use_cache=True,
    )
    elapsed = (datetime.now() - start_time).total_seconds()

    # Analyze and report results
    validation_statuses = {}
    for source_id, result in results.items():
        if result is not None:
            status = result.get("validation_status", "Unknown")
            if status not in validation_statuses:
                validation_statuses[status] = []
            validation_statuses[status].append(source_id)
    
    # Log detailed results
    logger.info("\nValidation Results:")
    for status, ids in validation_statuses.items():
        logger.info(f"  {status}: {len(ids)} mappings - {ids}")
    
    # Log specific examples for each status if available
    logger.info("\nExample Results:")
    for status in ["Validated", "UnidirectionalSuccess"]:
        if status in validation_statuses and validation_statuses[status]:
            example_id = validation_statuses[status][0]
            example_result = results[example_id]
            logger.info(f"\n{status} Example ({example_id}):")
            logger.info(json.dumps(example_result, indent=2))

    # Summary
    successful = sum(1 for v in results.values() if v is not None)
    logger.info(f"\nSummary: {successful}/{len(TEST_IDS)} successful mappings in {elapsed:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_bidirectional_validation())