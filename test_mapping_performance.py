#!/usr/bin/env python3
"""
Minimal test script for profiling MappingExecutor performance.
Uses a small subset of data to isolate performance bottlenecks.
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

async def main():
    """Run a minimal mapping test for performance profiling."""
    logger.info("Starting minimal mapping performance test")
    
    # Get configuration instance
    config = Config.get_instance()
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")
    
    logger.info(f"Using Config DB: {config_db_url}")
    logger.info(f"Using Cache DB: {cache_db_url}")

    # Read test data (just first 5 records)
    data_file = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps_small_test.csv"
    df = pd.read_csv(data_file)
    test_identifiers = df['uniprot'].head(5).tolist()
    logger.info(f"Test identifiers: {test_identifiers}")
    
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
    
    # Execute mapping
    logger.info("Starting mapping execution...")
    start_mapping = time.time()
    
    mapping_result = await executor.execute_mapping(
        source_endpoint_name="UKBB_Protein",
        target_endpoint_name="QIN_Protein", 
        input_identifiers=test_identifiers,
        source_property_name="UniProt",
        target_property_name="gene",
        try_reverse_mapping=False,
        validate_bidirectional=False
    )
    
    mapping_time = time.time() - start_mapping
    logger.info(f"Mapping completed in {mapping_time:.2f} seconds")
    
    # Report results
    success_count = sum(1 for result in mapping_result.values() 
                       if result and result.get("target_identifiers"))
    logger.info(f"Successfully mapped {success_count}/{len(test_identifiers)} identifiers")
    
    return mapping_result

if __name__ == "__main__":
    asyncio.run(main())