#!/usr/bin/env python
"""
Test efficient mapping with a small subset of data to verify reporting functionality.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
STRATEGY_NAME = "UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT"
SOURCE_ENDPOINT_NAME = "UKBB_PROTEIN"
TARGET_ENDPOINT_NAME = "HPA_OSP_PROTEIN"
OUTPUT_DIR = "/home/ubuntu/biomapper/data/results"
DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"
TEST_LIMIT = 100  # Test with only 100 identifiers


async def test_efficient_mapping():
    """Test the efficient mapping with a small subset."""
    start_time = datetime.now()
    logger.info(f"Starting TEST efficient mapping at {start_time}")
    logger.info(f"Testing with {TEST_LIMIT} identifiers")
    logger.info("=" * 80)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    executor = None
    
    try:
        # Initialize MappingExecutor
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        logger.info("MappingExecutor created successfully")
        
        # Get strategy
        strategy = await executor.get_strategy(STRATEGY_NAME)
        if not strategy:
            raise ValueError(f"Strategy '{STRATEGY_NAME}' not found in database.")
        
        # Load input identifiers (limited subset)
        source_ontology_type = strategy.default_source_ontology_type
        logger.info(f"Loading identifiers from '{SOURCE_ENDPOINT_NAME}'...")
        
        all_identifiers = await executor.load_endpoint_identifiers(
            endpoint_name=SOURCE_ENDPOINT_NAME,
            ontology_type=source_ontology_type
        )
        
        # Take a subset for testing
        input_identifiers = all_identifiers[:TEST_LIMIT]
        
        logger.info(f"Testing with {len(input_identifiers)} identifiers (out of {len(all_identifiers)} total)")
        
        # Execute mapping strategy
        logger.info("Executing efficient strategy...")
        
        result = await executor.execute_yaml_strategy(
            strategy_name=STRATEGY_NAME,
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            input_identifiers=input_identifiers,
            use_cache=True,
            progress_callback=lambda curr, total, status: logger.info(
                f"Progress: {curr}/{total} - {status}"
            )
        )
        
        logger.info("Strategy execution completed!")
        
        # Check if reporting files were created
        report_files = [
            f"{OUTPUT_DIR}/ukbb_to_hpa_mapping_results_efficient.csv",
            f"{OUTPUT_DIR}/ukbb_to_hpa_detailed_report_efficient.md",
            f"{OUTPUT_DIR}/ukbb_to_hpa_flow_efficient.json"
        ]
        
        logger.info("\nChecking report files:")
        for file_path in report_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                logger.info(f"✓ {file_path} ({size} bytes)")
            else:
                logger.error(f"✗ {file_path} NOT FOUND")
        
        # Log summary from result
        if 'summary' in result:
            summary = result['summary']
            logger.info(f"\nMapping Summary:")
            logger.info(f"- Total input: {summary.get('total_input', 0)}")
            logger.info(f"- Total output: {summary.get('total_output', 0)}")
            logger.info(f"- Success rate: {summary.get('success_rate', 0):.1f}%")
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nTest completed in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        raise
    finally:
        if executor:
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


if __name__ == "__main__":
    try:
        asyncio.run(test_efficient_mapping())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)