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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    logger.info("Using enhanced bidirectional strategy with:")
    logger.info("- Direct UniProt matching (no conversion needed)")
    logger.info("- Composite identifier handling")
    logger.info("- Bidirectional resolution for maximum coverage")
    logger.info("- Context-based tracking throughout")
    logger.info("")
    logger.info("Enhanced features:")
    logger.info(f"- Checkpointing: {'Enabled' if checkpoint_enabled else 'Disabled'}")
    logger.info(f"- Batch size: {batch_size}")
    logger.info(f"- Max retries: {max_retries}")
    logger.info(f"- Progress tracking: {'Enabled' if enable_progress else 'Disabled'}")
    logger.info(f"- Execution ID: {execution_id}")
    logger.info("=" * 80)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    logger.info(f"Output results will be saved to: {OUTPUT_RESULTS_FILE_PATH}")
    
    # Set DATA_DIR environment variable if not already set
    if 'DATA_DIR' not in os.environ:
        os.environ['DATA_DIR'] = DEFAULT_DATA_DIR
        logger.info(f"Set DATA_DIR environment variable to: {DEFAULT_DATA_DIR}")
    
    # Set OUTPUT_DIR environment variable for the strategy
    if 'OUTPUT_DIR' not in os.environ:
        os.environ['OUTPUT_DIR'] = OUTPUT_RESULTS_DIR
        logger.info(f"Set OUTPUT_DIR environment variable to: {OUTPUT_RESULTS_DIR}")
    
    # Initialize variables
    executor = None

    try:
        # Initialize MappingExecutor with robust features
        logger.info("Initializing MappingExecutor with robust features...")
        logger.info(f"Attempting to connect to Metamapper DB at: {settings.metamapper_db_url}")

        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True,
            # Enhanced features
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=CHECKPOINT_DIR,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=2  # 2 second delay between retries
        )
        logger.info("MappingExecutor created successfully with robust features")
        
        # Add progress tracking if enabled
        if enable_progress:
            def progress_callback(progress_data: Dict[str, Any]):
                """Handle progress updates from the executor."""
                if progress_data['type'] == 'batch_complete':
                    logger.info(
                        f"Progress: {progress_data['total_processed']}/{progress_data['total_count']} "
                        f"({progress_data['progress_percent']:.1f}%) - "
                        f"{progress_data['processor']}"
                    )
                elif progress_data['type'] == 'checkpoint_saved':
                    logger.info(f"Checkpoint saved: {progress_data['state_summary']}")
                elif progress_data['type'] == 'retry_attempt':
                    logger.warning(
                        f"Retry {progress_data['attempt']}/{progress_data['max_attempts']} "
                        f"for {progress_data['operation']}"
                    )
            
            executor.add_progress_callback(progress_callback)
            logger.info("Progress tracking enabled")
        
        # Check if strategy exists using new API
        logger.info(f"Checking if strategy '{STRATEGY_NAME}' exists in database...")
        strategy = await executor.get_strategy(STRATEGY_NAME)
        
        if not strategy:
            raise ValueError(
                f"Strategy '{STRATEGY_NAME}' not found in database.\n"
                f"Please run: python scripts/populate_metamapper_db.py"
            )
        
        logger.info(f"Strategy '{STRATEGY_NAME}' found in database")
        
        # Get the source ontology type from the strategy
        source_ontology_type = strategy.default_source_ontology_type
        logger.info(f"Strategy uses source ontology type: {source_ontology_type}")
        logger.info(f"Note: This is UniProt directly - no conversion needed!")
        
        # Loading of identifiers is now handled by the strategy's first step (LoadEndpointIdentifiersAction)
        logger.info(f"Source endpoint '{SOURCE_ENDPOINT_NAME}' will be loaded by the strategy")
        
        # Check for existing checkpoint
        checkpoint_state = await executor.load_checkpoint(execution_id)
        if checkpoint_state:
            logger.info("Found existing checkpoint - attempting to resume execution...")
        
        # Execute mapping strategy with robust features
        logger.info(f"Executing enhanced bidirectional mapping strategy...")
        logger.info("Using robust execution with checkpointing and retry logic...")
        logger.info("This may take some time for large datasets...")
        
        # Set additional environment variables for the actions to use
        os.environ['EXECUTION_ID'] = execution_id
        os.environ['STRATEGY_NAME'] = STRATEGY_NAME
        os.environ['START_TIME'] = start_time.isoformat()
        
        # Set strategy output directory as environment variable for actions to use
        os.environ['STRATEGY_OUTPUT_DIRECTORY'] = OUTPUT_RESULTS_DIR

        result = await executor.execute_yaml_strategy_robust(
            strategy_name=STRATEGY_NAME,
            input_identifiers=[],  # Empty because strategy loads identifiers itself
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            execution_id=execution_id,
            resume_from_checkpoint=checkpoint_enabled,
            use_cache=True  # Enable caching for full runs
        )
        
        logger.info("Mapping execution completed")
        
        # The FormatAndSaveResultsAction now handles all result processing and saving
        # Just extract some basic info for logging
        context = result.get('context', {})
        
        # Check if the action saved the files
        saved_csv_path = context.get('saved_csv_path')
        saved_json_path = context.get('saved_json_summary_path')
        formatted_summary = context.get('formatted_summary', {})
        
        if saved_csv_path:
            logger.info(f"Results saved to CSV: {saved_csv_path}")
        else:
            logger.warning("CSV output path not found in context")
            
        if saved_json_path:
            logger.info(f"Summary saved to JSON: {saved_json_path}")
        else:
            logger.warning("JSON summary path not found in context")
        
        # Log summary from the formatted results if available
        if formatted_summary:
            logger.info("=" * 80)
            logger.info("MAPPING SUMMARY (from FormatAndSaveResultsAction):")
            
            input_analysis = formatted_summary.get('input_analysis', {})
            mapping_results = formatted_summary.get('mapping_results', {})
            
            logger.info(f"Total input identifiers: {input_analysis.get('total_input', 'N/A')}")
            logger.info(f"Composite identifiers: {input_analysis.get('composite_identifiers', 'N/A')}")
            logger.info(f"Direct matches: {mapping_results.get('direct_matches', 'N/A')}")
            logger.info(f"Resolved matches: {mapping_results.get('resolved_matches', 'N/A')}")
            logger.info(f"Total successfully mapped: {mapping_results.get('total_mapped', 'N/A')}")
            logger.info(f"Total unmapped: {mapping_results.get('total_unmapped', 'N/A')}")
            
            # Mapping method breakdown
            mapping_methods = formatted_summary.get('mapping_methods', {})
            if mapping_methods:
                logger.info("\nMapping method breakdown:")
                for method, count in mapping_methods.items():
                    logger.info(f"  {method}: {count}")
            
            # Execution time
            execution_info = formatted_summary.get('execution_info', {})
            duration = execution_info.get('duration_seconds', 0)
            logger.info(f"\nTotal execution time: {duration:.2f} seconds")
            
            # Robust execution features
            robust_features = execution_info.get('robust_features', {})
            logger.info(f"\nRobust execution features:")
            logger.info(f"  Checkpointing: {'Used' if robust_features.get('checkpoint_used') else 'Available' if robust_features.get('checkpoint_enabled') else 'Disabled'}")
            logger.info(f"  Batch processing: {robust_features.get('batch_size', 'N/A')} identifiers per batch")
            logger.info(f"  Retry logic: {robust_features.get('max_retries', 'N/A')} max attempts")
            logger.info(f"  Progress tracking: {'Enabled' if robust_features.get('progress_tracking') else 'Disabled'}")
            
            logger.info("=" * 80)
        
        # Compare with original approach
        logger.info("\nRefactored approach benefits:")
        logger.info("- Strategy now loads identifiers directly (LoadEndpointIdentifiersAction)")
        logger.info("- Results formatting and saving handled by strategy (FormatAndSaveResultsAction)")
        logger.info("- Script simplified to just orchestration and logging")
        logger.info("- All logic now modular and reusable in strategy actions")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except KeyError as e:
        logger.error(f"Column not found error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during mapping: {e}", exc_info=True)
        raise
    finally:
        # Clean up resources
        if executor:
            logger.info("Disposing MappingExecutor...")
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


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