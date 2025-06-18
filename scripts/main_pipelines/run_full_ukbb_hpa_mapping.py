#!/usr/bin/env python
"""
Full UKBB to HPA Protein Mapping Script

This script processes a full UKBB protein dataset through a
mapping strategy (e.g., UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT) using the MappingExecutor
with robust execution features.

Key features of the typical mapping process:
- Direct UniProt matching
- Historical UniProt ID resolution for comprehensive coverage
- Context-based tracking of matched/unmatched identifiers
- Composite identifier handling

Enhanced script features:
- Checkpointing for resumable execution
- Retry logic for external API calls
- Progress tracking and reporting
- Batch processing with configurable sizes

Usage:
    1. Ensure metamapper.db is populated: python scripts/setup_and_configuration/populate_metamapper_db.py
    2. Ensure the biomapper Poetry environment is active
    3. Run: python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py [options]
    
Options:
    --checkpoint: Enable checkpoint saving (default: True)
    --batch-size N: Number of identifiers per batch (default: 250)
    --max-retries N: Maximum retries per operation (default: 3)
    --no-progress: Disable progress reporting
    
The script will automatically:
- Utilize a strategy to load UKBB protein data (UniProt IDs)
- Execute the specified mapping strategy with robust features
- Save comprehensive results to /home/ubuntu/biomapper/data/results/
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Add project root to sys.path for module resolution
BIOMAPPER_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BIOMAPPER_ROOT))

import pandas as pd
from biomapper.core import MappingExecutor
from biomapper.config import settings

# Configure logging
log_dir = BIOMAPPER_ROOT / "logs"
log_dir.mkdir(exist_ok=True)
log_file_name = f"ukbb_hpa_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file_path = log_dir / log_file_name

# Get the root logger and configure it directly for more robustness
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) # Ensure level is set on the root logger

# Remove any existing handlers from the root logger
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
    handler.close() # Close the handler to release resources

# Define a common formatter
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add a StreamHandler for console output
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)
root_logger.addHandler(stream_handler)

# Add a FileHandler for file output
try:
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
except Exception as e:
    # If FileHandler fails, print to stderr and continue with StreamHandler only
    print(f"Critical: Failed to initialize file logger at {log_file_path}: {e}", file=sys.stderr)


logger = logging.getLogger(__name__) # Get a logger for this module (will use root config)
logger.info(f"Logging initialized. Log file: {log_file_path}") # Test message

# ============================================================================
# CONFIGURATION VARIABLES
# ============================================================================

# Output configuration
OUTPUT_RESULTS_DIR = "/home/ubuntu/biomapper/data/results/"
OUTPUT_RESULTS_FILENAME = "full_ukbb_to_hpa_mapping_results.csv"
OUTPUT_RESULTS_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, OUTPUT_RESULTS_FILENAME)

# Summary file for tracking strategy performance
SUMMARY_FILENAME = "full_ukbb_to_hpa_mapping_summary.json"
SUMMARY_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, SUMMARY_FILENAME)

# Default data directory (set as environment variable if not already set)
DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"

# Checkpoint directory for robust execution
CHECKPOINT_DIR = "/home/ubuntu/biomapper/data/checkpoints"

# Strategy name to execute - typically a strategy like UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT
# Note: The OPTIMIZED strategy has a design flaw where it processes ALL unmatched HPA proteins,
# causing timeouts even with small datasets. Use EFFICIENT instead.
STRATEGY_NAME = "UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT"

# Endpoint names as defined in metamapper.db (from protein_config.yaml)
SOURCE_ENDPOINT_NAME = "UKBB_PROTEIN"
TARGET_ENDPOINT_NAME = "HPA_OSP_PROTEIN"

# ============================================================================
# MAIN MAPPING FUNCTION
# ============================================================================


async def run_full_mapping(checkpoint_enabled: bool = True, batch_size: int = 250, 
                          max_retries: int = 3, enable_progress: bool = True):
    """
    Main function to execute the full UKBB to HPA protein mapping using an enhanced strategy.
    
    Args:
        checkpoint_enabled: Enable checkpoint saving for resumable execution
        batch_size: Number of identifiers per batch for processing
        max_retries: Maximum retry attempts for failed operations
        enable_progress: Enable progress reporting callbacks
    """
    start_time = datetime.now()
    execution_id = f"ukbb_hpa_bidirectional_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Starting ENHANCED BIDIRECTIONAL UKBB to HPA protein mapping at {start_time}")
    logger.info("=" * 80)
    logger.info(f"Executing strategy: {STRATEGY_NAME}")
    logger.info("This script orchestrates a strategy that handles all logic internally:")
    logger.info("- Loading initial identifiers")
    logger.info("- Executing forward and reverse mapping paths")
    logger.info("- Reconciling bidirectional results")
    logger.info("- Saving results to CSV and a JSON summary")
    logger.info("")
    logger.info("Script features:")
    logger.info(f"- Checkpointing: {'Enabled' if checkpoint_enabled else 'Disabled'}")
    logger.info(f"- Batch size: {batch_size}")
    logger.info(f"- Max retries: {max_retries}")
    logger.info(f"- Progress tracking: {'Enabled' if enable_progress else 'Disabled'}")
    logger.info(f"- Execution ID: {execution_id}")
    logger.info("=" * 80)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    logger.info(f"Output will be saved in: {OUTPUT_RESULTS_DIR}")
    
    # Set environment variables for the strategy actions to use
    os.environ['STRATEGY_OUTPUT_DIRECTORY'] = OUTPUT_RESULTS_DIR
    os.environ['EXECUTION_ID'] = execution_id
    os.environ['STRATEGY_NAME'] = STRATEGY_NAME
    os.environ['START_TIME'] = start_time.isoformat()
    logger.info(f"Set STRATEGY_OUTPUT_DIRECTORY for actions: {OUTPUT_RESULTS_DIR}")

    executor = None
    try:
        # Initialize MappingExecutor with robust features
        logger.info("Initializing MappingExecutor...")
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True,
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=CHECKPOINT_DIR,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=2
        )
        logger.info("MappingExecutor created successfully.")
        
        # Add progress tracking if enabled
        if enable_progress:
            def progress_callback(progress_data: Dict[str, Any]):
                """Handle progress updates from the executor."""
                if progress_data.get('type') == 'batch_complete':
                    logger.info(
                        f"Progress: {progress_data.get('total_processed', 0)}/"
                        f"{progress_data.get('total_count', 0)} "
                        f"({progress_data.get('progress_percent', 0):.1f}%) - "
                        f"{progress_data.get('processor', 'N/A')}"
                    )
            
            executor.add_progress_callback(progress_callback)
            logger.info("Progress tracking enabled.")
        
        # Execute mapping strategy
        logger.info(f"Executing strategy '{STRATEGY_NAME}'...")
        logger.info("This may take some time for large datasets...")
        
        result = await executor.execute_yaml_strategy_robust(
            strategy_name=STRATEGY_NAME,
            input_identifiers=[],  # Strategy loads its own identifiers
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            execution_id=execution_id,
            resume_from_checkpoint=checkpoint_enabled,
            use_cache=True
        )
        
        logger.info("Strategy execution completed.")
        
        # The SaveBidirectionalResultsAction handles all result saving and summary logging.
        # We just confirm that the output files were created.
        context = result.get('context', {})
        csv_path = context.get('saved_csv_path')
        json_path = context.get('saved_json_path')
        
        if csv_path and json_path:
            logger.info(f"Successfully saved results to:")
            logger.info(f"  - CSV: {csv_path}")
            logger.info(f"  - JSON: {json_path}")
        else:
            logger.warning("Could not confirm that output files were saved. Check logs for details.")

        logger.info("=" * 80)
        logger.info("Refactored script finished successfully.")
        logger.info("All logic is now encapsulated within modular strategy actions.")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"An error occurred during the mapping process: {e}", exc_info=True)
        raise
    finally:
        if executor:
            logger.info("Disposing MappingExecutor...")
            await executor.async_dispose()
            logger.info("MappingExecutor disposed.")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Enhanced UKBB to HPA mapping with robust execution"
    )
    parser.add_argument(
        "--no-checkpoint", 
        action="store_true", 
        help="Disable checkpoint saving"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=250, 
        help="Number of identifiers per batch (default: 250)"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=3, 
        help="Maximum retry attempts for failed operations (default: 3)"
    )
    parser.add_argument(
        "--no-progress", 
        action="store_true", 
        help="Disable progress reporting"
    )
    
    args = parser.parse_args()
    
    try:
        # Run the main async function with parsed arguments
        asyncio.run(run_full_mapping(
            checkpoint_enabled=not args.no_checkpoint,
            batch_size=args.batch_size,
            max_retries=args.max_retries,
            enable_progress=not args.no_progress
        ))
        logger.info("Script completed successfully")
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)