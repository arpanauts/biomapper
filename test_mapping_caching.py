#!/usr/bin/env python3
"""
Test script to verify client caching performance improvements.
Runs multiple mapping operations to see caching benefits.
"""
import asyncio
import logging
import pandas as pd
import time
from datetime import datetime
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.config import Config

# Configure minimal logging for testing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_mapping_test(test_name: str, executor: MappingExecutor, identifiers: list):
    """Run a single mapping test and return timing data."""
    logger.info(f"=== {test_name} ===")
    start_time = time.time()
    
    try:
        result = await executor.execute_mapping(
            source_endpoint_name="UKBB_Protein",
            target_endpoint_name="QIN_Protein", 
            input_identifiers=identifiers,
            source_property_name="UniProt",
            target_property_name="gene",
            try_reverse_mapping=False,
            validate_bidirectional=False
        )
        
        execution_time = time.time() - start_time
        success_count = sum(1 for r in result.values() if r and r.get("target_identifiers"))
        
        logger.info(f"{test_name} completed in {execution_time:.2f}s: {success_count}/{len(identifiers)} mapped")
        return execution_time, success_count
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"{test_name} failed after {execution_time:.2f}s: {e}")
        return execution_time, 0

async def main():
    """Run multiple mapping tests to demonstrate caching benefits."""
    logger.info("Starting client caching performance test")
    
    # Get configuration instance
    config = Config.get_instance()
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")
    
    logger.info(f"Using Config DB: {config_db_url}")
    logger.info(f"Using Cache DB: {cache_db_url}")

    # Read test data 
    data_file = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps_small_test.csv"
    df = pd.read_csv(data_file)
    all_identifiers = df['uniprot'].tolist()
    
    # Create different test batches
    batch1 = all_identifiers[:3]  # First 3
    batch2 = all_identifiers[2:5]  # Overlapping batch
    batch3 = all_identifiers[1:4]  # Another overlapping batch
    
    logger.info(f"Test batches:")
    logger.info(f"  Batch 1: {batch1}")
    logger.info(f"  Batch 2: {batch2}")
    logger.info(f"  Batch 3: {batch3}")
    
    # Initialize MappingExecutor
    logger.info("Initializing MappingExecutor...")
    start_init = time.time()
    
    executor = await MappingExecutor.create(
        metamapper_db_url=config_db_url,
        mapping_cache_db_url=cache_db_url,
        echo_sql=False
    )
    
    init_time = time.time() - start_init
    logger.info(f"MappingExecutor initialized in {init_time:.2f} seconds")
    
    # Run multiple mapping tests
    total_start = time.time()
    
    times = []
    times.append(await run_mapping_test("Test 1 (First run - CSV loading)", executor, batch1))
    times.append(await run_mapping_test("Test 2 (Should use cached client)", executor, batch2))
    times.append(await run_mapping_test("Test 3 (Should use cached client)", executor, batch3))
    
    total_time = time.time() - total_start
    
    # Report results
    logger.info("\n=== PERFORMANCE SUMMARY ===")
    logger.info(f"Total execution time: {total_time:.2f}s")
    for i, (exec_time, success) in enumerate(times, 1):
        logger.info(f"Test {i}: {exec_time:.2f}s ({success} successes)")
    
    # Calculate improvement
    first_run_time = times[0][0]
    subsequent_avg = sum(t[0] for t in times[1:]) / len(times[1:])
    improvement = ((first_run_time - subsequent_avg) / first_run_time) * 100
    
    logger.info(f"\nFirst run: {first_run_time:.2f}s")
    logger.info(f"Subsequent avg: {subsequent_avg:.2f}s")
    logger.info(f"Performance improvement: {improvement:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())