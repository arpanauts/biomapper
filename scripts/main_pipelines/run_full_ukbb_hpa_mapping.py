#!/usr/bin/env python
"""
Full UKBB to HPA Protein Mapping Script

This script processes a full UKBB protein dataset through the UKBB_TO_HPA_PROTEIN_PIPELINE
strategy using the MappingExecutor, and saves comprehensive mapping results to a CSV file.

Usage:
    1. Update FULL_UKBB_DATA_FILE_PATH to point to your UKBB protein data TSV file
    2. Ensure the biomapper Poetry environment is active
    3. Run: python scripts/run_full_ukbb_hpa_mapping.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to sys.path for module resolution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from biomapper.db.models import MappingStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION VARIABLES - UPDATE THESE FOR YOUR DATA
# ============================================================================

# IMPORTANT: User must change this path to their actual full UKBB protein data TSV file
FULL_UKBB_DATA_FILE_PATH = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"

# Column name containing UKBB Protein Assay IDs in the input file
UKBB_ID_COLUMN_NAME = "Assay"

# Confirm this is the correct HPA dataset for the full run
HPA_DATA_FILE_PATH_CONFIRMATION = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv"

# Output configuration
OUTPUT_RESULTS_DIR = "/home/ubuntu/biomapper/data/results/"
OUTPUT_RESULTS_FILENAME = "full_ukbb_to_hpa_mapping_results.csv"
OUTPUT_RESULTS_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, OUTPUT_RESULTS_FILENAME)

# Default data directory (set as environment variable if not already set)
DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"

# Strategy name to execute
STRATEGY_NAME = "UKBB_TO_HPA_PROTEIN_PIPELINE"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_strategy_exists(executor: MappingExecutor, strategy_name: str) -> bool:
    """
    Check if a strategy exists in the metamapper database.
    
    Args:
        executor: MappingExecutor instance
        strategy_name: Name of the strategy to check
        
    Returns:
        True if strategy exists, False otherwise
    """
    try:
        async with executor.async_metamapper_session() as session:
            stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_name)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            return strategy is not None
    except Exception as e:
        logger.error(f"Error checking for strategy {strategy_name}: {e}")
        return False




# ============================================================================
# MAIN MAPPING FUNCTION
# ============================================================================

async def run_full_mapping():
    """
    Main function to execute the full UKBB to HPA protein mapping.
    """
    start_time = datetime.now()
    logger.info(f"Starting full UKBB to HPA protein mapping at {start_time}")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    logger.info(f"Output results will be saved to: {OUTPUT_RESULTS_FILE_PATH}")
    
    # Set DATA_DIR environment variable if not already set
    if 'DATA_DIR' not in os.environ:
        os.environ['DATA_DIR'] = DEFAULT_DATA_DIR
        logger.info(f"Set DATA_DIR environment variable to: {DEFAULT_DATA_DIR}")
    
    # Initialize variables
    executor = None
    input_identifiers = []
    
    try:
        # Load input UKBB IDs
        logger.info(f"Loading UKBB identifiers from: {FULL_UKBB_DATA_FILE_PATH}")
        
        if not os.path.exists(FULL_UKBB_DATA_FILE_PATH):
            raise FileNotFoundError(
                f"Input file not found: {FULL_UKBB_DATA_FILE_PATH}\n"
                f"Please update FULL_UKBB_DATA_FILE_PATH to point to your UKBB protein data file."
            )
        
        # Load the TSV file
        df = pd.read_csv(FULL_UKBB_DATA_FILE_PATH, sep='\t')
        logger.info(f"Loaded dataframe with shape: {df.shape}")
        
        # Extract unique identifiers
        if UKBB_ID_COLUMN_NAME not in df.columns:
            raise KeyError(
                f"Column '{UKBB_ID_COLUMN_NAME}' not found in input file.\n"
                f"Available columns: {list(df.columns)}"
            )
        
        input_identifiers = df[UKBB_ID_COLUMN_NAME].dropna().unique().tolist()
        logger.info(f"Found {len(input_identifiers)} unique UKBB Protein Assay IDs")
        
        if not input_identifiers:
            logger.warning("No identifiers found in the input file. Exiting.")
            return
        
        # Initialize MappingExecutor
        logger.info("Initializing MappingExecutor...")
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        logger.info("MappingExecutor created successfully")
        
        # Check if strategy exists
        logger.info(f"Checking if strategy '{STRATEGY_NAME}' exists in database...")
        strategy_exists = await check_strategy_exists(executor, STRATEGY_NAME)
        
        if not strategy_exists:
            raise ValueError(
                f"Strategy '{STRATEGY_NAME}' not found in database.\n"
                f"Please run: python scripts/populate_metamapper_db.py"
            )
        
        logger.info(f"Strategy '{STRATEGY_NAME}' found in database")
        
        # Execute mapping strategy
        logger.info(f"Executing mapping strategy on {len(input_identifiers)} identifiers...")
        logger.info("This may take some time for large datasets...")
        
        result = await executor.execute_yaml_strategy(
            strategy_name=STRATEGY_NAME,
            source_endpoint_name="UKBB_PROTEIN",
            target_endpoint_name="HPA_OSP_PROTEIN",
            input_identifiers=input_identifiers,
            use_cache=True,  # Enable caching for full runs
            progress_callback=lambda curr, total, status: logger.info(
                f"Progress: {curr}/{total} - {status}"
            )
        )
        
        logger.info("Mapping execution completed")
        
        # Process and save results
        logger.info("Processing mapping results...")
        
        # Debug: log the structure of the result
        logger.info(f"Result keys: {list(result.keys())}")
        
        # The execute_yaml_strategy returns results in 'results' key, not 'mapped_data'
        results_dict = result.get('results', {})
        output_rows = []
        
        # Get step results for parsing
        step_results = result.get('summary', {}).get('step_results', [])
        
        # Process each input identifier
        for input_id in input_identifiers:
            # Default values
            final_mapped_id = None
            mapping_status = 'UNMAPPED'
            final_step_reached = 'Unknown'
            error_message = None
            
            # Check if this ID has results
            if input_id in results_dict:
                mapping_result = results_dict[input_id]
                final_mapped_id = mapping_result.get('mapped_value')
                
                if final_mapped_id:
                    mapping_status = 'MAPPED'
                    # Get the last successful step from summary
                    for step in reversed(step_results):
                        if step.get('success') and step.get('output_count', 0) > 0:
                            final_step_reached = step.get('step_id', 'Unknown')
                            break
                else:
                    # ID was filtered out or lost
                    mapping_status = 'FILTERED_OUT'
                    # Find where it was filtered
                    for step in step_results:
                        if (step.get('action_type') == 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE' or
                            step.get('action_type') == 'FILTER_BY_TARGET_PRESENCE'):
                            final_step_reached = step.get('step_id', 'S3_FILTER_BY_HPA_PRESENCE')
                            break
                
                # Check for any error in mapping result
                if mapping_result.get('status') == 'error':
                    mapping_status = 'ERROR_DURING_PIPELINE'
                    error_message = mapping_result.get('message', 'Unknown error')
            else:
                # ID was not in final results - it was lost or filtered
                # Check if it made it through any steps by looking at step outputs
                last_successful_step = None
                for step in step_results:
                    if step.get('success'):
                        step_output = step.get('output_data', [])
                        if not isinstance(step_output, list):
                            continue
                        # Check if this ID appears in any intermediate output
                        # Note: This is a simplified check - in reality we'd need to track ID transformations
                        last_successful_step = step.get('step_id')
                        
                        # If this is a filter step and output < input, it was filtered here
                        if (step.get('action_type') == 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE' and 
                            step.get('output_count', 0) < step.get('input_count', 0)):
                            mapping_status = 'FILTERED_OUT'
                            final_step_reached = step.get('step_id', 'S3_FILTER_BY_HPA_PRESENCE')
                            break
                
                if final_step_reached == 'Unknown' and last_successful_step:
                    final_step_reached = last_successful_step
            
            output_rows.append({
                'Input_UKBB_Assay_ID': input_id,
                'Final_Mapped_HPA_ID': final_mapped_id,
                'Mapping_Status': mapping_status,
                'Final_Step_ID_Reached': final_step_reached,
                'Error_Message': error_message
            })
        
        # Create DataFrame and save to CSV
        output_df = pd.DataFrame(output_rows)
        output_df.to_csv(OUTPUT_RESULTS_FILE_PATH, index=False)
        logger.info(f"Results saved to: {OUTPUT_RESULTS_FILE_PATH}")
        
        # Log summary statistics
        summary = result.get('summary', {})
        logger.info("=" * 60)
        logger.info("MAPPING SUMMARY:")
        logger.info(f"Total input identifiers: {summary.get('total_input', 0)}")
        logger.info(f"Successfully mapped: {summary.get('successful_mappings', 0)}")
        logger.info(f"Failed mappings: {summary.get('failed_mappings', 0)}")
        logger.info(f"Lost during processing: {summary.get('lost_during_processing', 0)}")
        
        # Additional statistics from output DataFrame
        if not output_df.empty and 'Mapping_Status' in output_df.columns:
            status_counts = output_df['Mapping_Status'].value_counts()
            logger.info("\nDetailed status breakdown:")
            for status, count in status_counts.items():
                logger.info(f"  {status}: {count}")
        else:
            logger.warning("No mapping results to analyze")
        
        # Calculate execution time
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"\nTotal execution time: {duration}")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}")
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
    try:
        # Run the main async function
        asyncio.run(run_full_mapping())
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)