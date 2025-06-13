#!/usr/bin/env python
"""
Full UKBB to HPA Protein Mapping Script

This script processes a full UKBB protein dataset through the UKBB_TO_HPA_PROTEIN_PIPELINE
strategy using the MappingExecutor, and saves comprehensive mapping results to a CSV file.

The script uses the configuration-driven approach:
- Data file paths are loaded from metamapper.db (populated from protein_config.yaml)
- No hardcoded file paths are needed
- Only endpoint names and strategy name need to be specified

Usage:
    1. Ensure metamapper.db is populated: python scripts/populate_metamapper_db.py
    2. Ensure the biomapper Poetry environment is active
    3. Run: python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
    
The script will automatically:
- Load UKBB protein data from the configured endpoint
- Execute the UKBB_TO_HPA_PROTEIN_PIPELINE strategy
- Save results to /home/ubuntu/biomapper/data/results/
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
from biomapper.db.models import PropertyExtractionConfig
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
# CONFIGURATION VARIABLES
# ============================================================================

# Output configuration
OUTPUT_RESULTS_DIR = "/home/ubuntu/biomapper/data/results/"
OUTPUT_RESULTS_FILENAME = "full_ukbb_to_hpa_mapping_results.csv"
OUTPUT_RESULTS_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, OUTPUT_RESULTS_FILENAME)

# Default data directory (set as environment variable if not already set)
DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"

# Strategy name to execute
STRATEGY_NAME = "UKBB_TO_HPA_PROTEIN_PIPELINE"

# Endpoint names as defined in metamapper.db (from protein_config.yaml)
SOURCE_ENDPOINT_NAME = "UKBB_PROTEIN"
TARGET_ENDPOINT_NAME = "HPA_OSP_PROTEIN"

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

async def get_column_for_ontology_type(executor: MappingExecutor, endpoint_name: str, ontology_type: str) -> str:
    """
    Get the column name for a given ontology type from an endpoint's property configuration.
    
    Args:
        executor: MappingExecutor instance
        endpoint_name: Name of the endpoint
        ontology_type: Ontology type to look up
        
    Returns:
        Column name for the ontology type
    """
    async with executor.async_metamapper_session() as session:
        from biomapper.db.models import Endpoint, EndpointPropertyConfig
        
        # Get the endpoint
        stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
        result = await session.execute(stmt)
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found in database")
        
        # Get the property config for the ontology type
        stmt = select(EndpointPropertyConfig).where(
            EndpointPropertyConfig.endpoint_id == endpoint.id,
            EndpointPropertyConfig.ontology_type == ontology_type
        )
        result = await session.execute(stmt)
        property_config = result.scalar_one_or_none()
        
        if not property_config:
            raise ValueError(f"No property configuration found for ontology type '{ontology_type}' in endpoint '{endpoint_name}'")
        
        # Get the extraction config to find the column name
        stmt = select(PropertyExtractionConfig).where(
            PropertyExtractionConfig.id == property_config.property_extraction_config_id
        )
        result = await session.execute(stmt)
        extraction_config = result.scalar_one_or_none()
        
        if not extraction_config:
            raise ValueError(f"No extraction configuration found for property config ID {property_config.property_extraction_config_id}")
        
        # Parse the extraction pattern to get the column name
        # The extraction_pattern is a JSON string like '{"column": "UniProt"}'
        import json
        try:
            pattern_data = json.loads(extraction_config.extraction_pattern)
            column_name = pattern_data.get('column')
            if not column_name:
                raise ValueError(f"No 'column' field found in extraction pattern: {extraction_config.extraction_pattern}")
            return column_name
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in extraction pattern: {extraction_config.extraction_pattern}")


async def load_identifiers_from_endpoint(executor: MappingExecutor, endpoint_name: str, ontology_type: str) -> List[str]:
    """
    Load identifiers from an endpoint using its configuration in metamapper.db.
    
    Args:
        executor: MappingExecutor instance
        endpoint_name: Name of the endpoint to load from
        ontology_type: Ontology type of the identifiers to load
        
    Returns:
        List of unique identifiers
    """
    try:
        # First get the column name for the ontology type
        column_name = await get_column_for_ontology_type(executor, endpoint_name, ontology_type)
        logger.info(f"Ontology type '{ontology_type}' maps to column '{column_name}'")
        
        # Get endpoint configuration from metamapper.db
        async with executor.async_metamapper_session() as session:
            from biomapper.db.models import Endpoint
            
            stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
            result = await session.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                raise ValueError(f"Endpoint '{endpoint_name}' not found in database")
            
            # Parse connection details (it's a JSON string)
            import json
            connection_details = json.loads(endpoint.connection_details)
            file_path = connection_details.get('file_path', '')
            delimiter = connection_details.get('delimiter', ',')
            
            # Handle environment variable substitution
            if '${DATA_DIR}' in file_path:
                data_dir = os.environ.get('DATA_DIR', DEFAULT_DATA_DIR)
                file_path = file_path.replace('${DATA_DIR}', data_dir)
            
            logger.info(f"Loading identifiers from endpoint '{endpoint_name}'")
            logger.info(f"File path: {file_path}")
            
            # Load the file
            if endpoint.type == 'file_tsv':
                df = pd.read_csv(file_path, sep=delimiter)
            elif endpoint.type == 'file_csv':
                df = pd.read_csv(file_path, sep=delimiter)
            else:
                raise ValueError(f"Unsupported endpoint type: {endpoint.type}")
            
            logger.info(f"Loaded dataframe with shape: {df.shape}")
            
            # Extract unique identifiers
            if column_name not in df.columns:
                raise KeyError(
                    f"Column '{column_name}' not found in {endpoint_name} data.\n"
                    f"Available columns: {list(df.columns)}"
                )
            
            identifiers = df[column_name].dropna().unique().tolist()
            logger.info(f"Found {len(identifiers)} unique identifiers in column '{column_name}'")
            
            return identifiers
            
    except Exception as e:
        logger.error(f"Error loading identifiers from endpoint {endpoint_name}: {e}")
        raise


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
        
        # Get the source ontology type from the strategy configuration
        async with executor.async_metamapper_session() as session:
            stmt = select(MappingStrategy).where(MappingStrategy.name == STRATEGY_NAME)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            
            if not strategy or not strategy.default_source_ontology_type:
                raise ValueError(f"Strategy '{STRATEGY_NAME}' does not have a default_source_ontology_type defined")
            
            source_ontology_type = strategy.default_source_ontology_type
            logger.info(f"Strategy uses source ontology type: {source_ontology_type}")
        
        # Load input identifiers from the source endpoint
        logger.info(f"Loading identifiers from source endpoint '{SOURCE_ENDPOINT_NAME}'...")
        input_identifiers = await load_identifiers_from_endpoint(
            executor=executor,
            endpoint_name=SOURCE_ENDPOINT_NAME,
            ontology_type=source_ontology_type
        )
        
        if not input_identifiers:
            logger.warning("No identifiers found in the source endpoint. Exiting.")
            return
        
        # Execute mapping strategy
        logger.info(f"Executing mapping strategy on {len(input_identifiers)} identifiers...")
        logger.info("This may take some time for large datasets...")
        
        result = await executor.execute_yaml_strategy(
            strategy_name=STRATEGY_NAME,
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
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
        
        # The execute_yaml_strategy returns results in 'results' key
        results_dict = result.get('results', {})
        final_identifiers = set(result.get('final_identifiers', []))
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
                all_mapped_values = mapping_result.get('all_mapped_values', [])
                
                # Check if this identifier made it to the final set
                # The last value in all_mapped_values should be the final HPA gene if it passed all steps
                if all_mapped_values and len(all_mapped_values) > 0:
                    # Check if any of the mapped values are in the final identifiers
                    made_it_through = any(val in final_identifiers for val in all_mapped_values)
                    
                    if made_it_through and len(all_mapped_values) > 1:
                        # Successfully mapped through all steps
                        final_mapped_id = all_mapped_values[-1]  # Last value is the HPA gene
                        mapping_status = 'MAPPED'
                        final_step_reached = 'S4_HPA_UNIPROT_TO_NATIVE'
                    else:
                        # Filtered out somewhere
                        final_mapped_id = None
                        mapping_status = 'FILTERED_OUT'
                        # Find where it was filtered
                        for step in step_results:
                            if (step.get('action_type') == 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE' or
                                step.get('action_type') == 'FILTER_BY_TARGET_PRESENCE'):
                                final_step_reached = step.get('step_id', 'S3_FILTER_BY_HPA_PRESENCE')
                                break
                else:
                    # No mapping found
                    mapping_status = 'UNMAPPED'
                    final_mapped_id = None
                
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
    try:
        # Run the main async function
        asyncio.run(run_full_mapping())
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)