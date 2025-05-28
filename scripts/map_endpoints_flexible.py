#!/usr/bin/env python3
"""Flexible endpoint mapping script that accepts property names as parameters"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from biomapper.core.mapping_executor import MappingExecutor, PathExecutionStatus
from biomapper.core.config import Config
from sqlalchemy.future import select
from biomapper.db.cache_models import EntityMapping

# Configure logging
import logging.handlers

# Create log directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"flexible_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)

# --- Constants ---
# New columns for detailed output
CONFIDENCE_SCORE_COLUMN = "mapping_confidence_score"
PATH_DETAILS_COLUMN = "mapping_path_details"
HOP_COUNT_COLUMN = "mapping_hop_count"
MAPPING_DIRECTION_COLUMN = "mapping_direction"
VALIDATION_STATUS_COLUMN = "validation_status"

# --- Main Function ---
async def main(
    input_file_path: str,
    output_file_path: str,
    source_endpoint_name: str,
    target_endpoint_name: str,
    input_id_column_name: str,
    input_primary_key_column_name: str,
    output_mapped_id_column_name: str,
    source_property_name: str,
    target_property_name: str,
    source_ontology_name: str, # Not used by executor, but kept for compatibility
    target_ontology_name: str, # Not used by executor, but kept for compatibility
    try_reverse_mapping_param: bool = False,
    summary_param: bool = False
):
    logger = logging.getLogger(__name__)
    
    # Get configuration instance
    config = Config.get_instance()
    # Fix database paths to point to the correct location 
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")
    
    logger.info(f"Using Config DB: {config_db_url}")
    logger.info(f"Using Cache DB: {cache_db_url}")
    
    # 1. Read Input File
    logger.info(f"Reading input file: {input_file_path}")
    try:
        # Read with pandas, ensure correct separator and engine
        df_input = pd.read_csv(input_file_path, sep="\t", low_memory=False)
        logger.info(f"Processing data from {input_file_path}")
    except FileNotFoundError:
        logger.error(f"Error: Input file not found at {input_file_path}")
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return
    
    # Check required columns exist
    if input_id_column_name not in df_input.columns:
        logger.error(f"Error: Column '{input_id_column_name}' not found in input file. Available columns: {df_input.columns.tolist()}")
        return
    
    if input_primary_key_column_name not in df_input.columns:
        logger.error(f"Error: Column '{input_primary_key_column_name}' not found in input file. Available columns: {df_input.columns.tolist()}")
        return
    
    # Extract unique IDs to map
    identifiers_to_map = df_input[input_id_column_name].dropna().unique().tolist()
    logger.info(f"Found {len(identifiers_to_map)} unique IDs from column '{input_id_column_name}' to map.")
    
    if not identifiers_to_map:
        logger.info("No identifiers to map. Exiting.")
        return
    
    # 2. Execute Mapping
    logger.info("Initializing MappingExecutor...")
    start_init_time = time.time()
    executor = await MappingExecutor.create(
        config_db_url,
        cache_db_url
    )
    logger.info(f"MappingExecutor initialized in {time.time() - start_init_time:.2f} seconds")
    
    logger.info(f"Executing mapping from {source_endpoint_name}.{source_property_name} to {target_endpoint_name}.{target_property_name}...")
    logger.info(f"Mapping {len(identifiers_to_map)} unique IDs with try_reverse_mapping={try_reverse_mapping_param}")
    
    # Progress tracking variables
    start_time = time.time()
    last_report_time = start_time
    progress_report_interval = 10  # Report progress every 10 seconds
    
    # Create an async task to periodically report progress
    async def report_progress():
        nonlocal last_report_time
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                current_time = time.time()
                if current_time - last_report_time >= progress_report_interval:
                    elapsed = current_time - start_time
                    logger.info(f"Mapping in progress... Elapsed time: {elapsed:.1f}s")
                    last_report_time = current_time
            except asyncio.CancelledError:
                break
    
    # Start progress reporting task
    progress_task = asyncio.create_task(report_progress())
    
    try:
        mapping_result = await executor.execute_mapping(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=identifiers_to_map,
            source_property_name=source_property_name,
            target_property_name=target_property_name,
            try_reverse_mapping=try_reverse_mapping_param,
            validate_bidirectional=True,
            progress_callback=None,
        )
    finally:
        # Cancel the progress reporting task when mapping is done
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass
    
    # Report mapping completion time
    mapping_time = time.time() - start_time
    logger.info(f"Mapping execution completed in {mapping_time:.2f} seconds")
    
    # Debug the mapping result structure
    logger.info(f"DEBUG: Type of mapping_result: {type(mapping_result)}")
    logger.info(f"DEBUG: Number of items in mapping_result: {len(mapping_result)}")
    
    # Show first 5 results for debugging
    debug_items = list(mapping_result.items())[:5]
    for idx, (key, value) in enumerate(debug_items):
        logger.info(f"DEBUG: Item {idx} - Key: {key}, Value: {value}")
        if isinstance(value, dict):
            logger.info(f"DEBUG: Item {idx} - target_identifiers: {value.get('target_identifiers')}")
            logger.info(f"DEBUG: Item {idx} - validation_status: {value.get('validation_status')}")
    
    # 3. Process Results
    if not mapping_result:
        logger.warning("No successful mappings found.")
        mapping_result = {}
    
    logger.info(f"Mapping returned {len(mapping_result)} results.")
    
    # Convert mapping results to structured format
    expanded_rows = []
    
    # Create a mapping of input IDs to their rows
    id_to_rows = {}
    for idx, row in df_input.iterrows():
        input_id = row[input_id_column_name]
        if pd.notna(input_id):
            if input_id not in id_to_rows:
                id_to_rows[input_id] = []
            id_to_rows[input_id].append(row)
    
    # Process mapping results
    logger.info(f"Processing {len(mapping_result)} mapping results.")
    
    # Debug: Show sample keys and results
    sample_keys = list(mapping_result.keys())[:5]
    logger.info(f"Sample results keys: {sample_keys}")
    for key in sample_keys:
        logger.info(f"Sample result for {key}: {mapping_result[key]}")
    
    total_mappings = 0
    mapped_source_ids = set()
    multi_mapping_count = 0
    
    # Check for all rows to process
    row_count = 0
    for idx, row in df_input.iterrows():
        row_count += 1
        input_id = row[input_id_column_name]
        
        # Debug first 10 rows
        if row_count <= 10:
            valid_result = pd.notna(input_id) and input_id in mapping_result
            target_ids_val = 'None'
            has_target_ids = False
            if valid_result:
                result = mapping_result[input_id]
                target_ids_val = str(result.get('target_identifiers', 'None'))
                has_target_ids = result.get('target_identifiers') is not None
            logger.info(f"DEBUG loop idx {idx}: ValidResult={valid_result}, TargetIdsVal='{target_ids_val}', HasTargetIds={has_target_ids}")
        
        if pd.notna(input_id) and input_id in mapping_result:
            result = mapping_result[input_id]
            
            # Handle case where result might have target_identifiers
            if isinstance(result, dict) and result.get('target_identifiers'):
                target_ids = result['target_identifiers']
                if not isinstance(target_ids, list):
                    target_ids = [target_ids]
                
                # Track multi-mappings
                if len(target_ids) > 1:
                    multi_mapping_count += 1
                
                # Create a row for each target ID (handling one-to-many)
                for target_id in target_ids:
                    new_row = row.copy()
                    new_row[output_mapped_id_column_name] = target_id
                    new_row[CONFIDENCE_SCORE_COLUMN] = result.get('confidence_score', 1.0)
                    new_row[PATH_DETAILS_COLUMN] = result.get('mapping_path_details', '')
                    new_row[HOP_COUNT_COLUMN] = result.get('hop_count', 0)
                    new_row[MAPPING_DIRECTION_COLUMN] = result.get('mapping_direction', 'forward')
                    new_row[VALIDATION_STATUS_COLUMN] = result.get('validation_status', '')
                    expanded_rows.append(new_row)
                    total_mappings += 1
                
                mapped_source_ids.add(input_id)
            else:
                # No mapping found - add row with empty mapping columns
                new_row = row.copy()
                new_row[output_mapped_id_column_name] = ''
                new_row[CONFIDENCE_SCORE_COLUMN] = ''
                new_row[PATH_DETAILS_COLUMN] = ''
                new_row[HOP_COUNT_COLUMN] = ''
                new_row[MAPPING_DIRECTION_COLUMN] = ''
                new_row[VALIDATION_STATUS_COLUMN] = ''
                expanded_rows.append(new_row)
        else:
            # ID not in mapping results - add row with empty mapping columns
            new_row = row.copy()
            new_row[output_mapped_id_column_name] = ''
            new_row[CONFIDENCE_SCORE_COLUMN] = ''
            new_row[PATH_DETAILS_COLUMN] = ''
            new_row[HOP_COUNT_COLUMN] = ''
            new_row[MAPPING_DIRECTION_COLUMN] = ''
            new_row[VALIDATION_STATUS_COLUMN] = ''
            expanded_rows.append(new_row)
    
    logger.info(f"Processed {total_mappings} total mappings from {len(mapped_source_ids)} unique source IDs")
    logger.info(f"Found {multi_mapping_count} source IDs with multiple target mappings")
    
    # Create output dataframe
    if expanded_rows:
        df_output = pd.DataFrame(expanded_rows)
        logger.info(f"Created output dataframe with {len(df_output)} rows (expanded from {len(df_input)} input rows)")
    else:
        logger.warning("No expanded rows created - no successful mappings found")
        # Create output with same structure as input plus empty mapping columns
        df_output = df_input.copy()
        df_output[output_mapped_id_column_name] = ''
        df_output[CONFIDENCE_SCORE_COLUMN] = ''
        df_output[PATH_DETAILS_COLUMN] = ''
        df_output[HOP_COUNT_COLUMN] = ''
        df_output[MAPPING_DIRECTION_COLUMN] = ''
        df_output[VALIDATION_STATUS_COLUMN] = ''
        logger.info("No successful mappings found, adding empty metadata columns.")
    
    logger.info(f"Successfully mapped {len(mapped_source_ids)} out of {len(identifiers_to_map)} input IDs.")
    
    # 4. Write Output
    os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
    logger.info(f"Ensured output directory exists: {os.path.dirname(os.path.abspath(output_file_path))}")
    
    logger.info(f"Writing results to {output_file_path}")
    start_write_time = time.time()
    df_output.to_csv(output_file_path, sep="\t", index=False)
    logger.info(f"Output file written successfully in {time.time() - start_write_time:.2f} seconds.")
    
    # 5. Generate Summary Report (if requested)
    if summary_param:
        summary_file_path = output_file_path.replace('.tsv', '_summary_report.txt')
        
        with open(summary_file_path, 'w') as f:
            f.write(f"# {source_endpoint_name} to {target_endpoint_name} Mapping Summary Report\n\n")
            f.write(f"Input File: {input_file_path}\n")
            f.write(f"Output File: {output_file_path}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Overall Statistics\n")
            f.write(f"Total records: {len(df_input)}\n")
            f.write(f"Successfully mapped: {len(mapped_source_ids)} ({len(mapped_source_ids)/len(identifiers_to_map)*100:.2f}%)\n")
            
            if multi_mapping_count > 0:
                f.write(f"\n## One-to-Many Mappings\n")
                f.write(f"Source IDs with multiple targets: {multi_mapping_count}\n")
                f.write(f"Total mappings: {total_mappings}\n")
                f.write(f"Average targets per mapped source: {total_mappings/len(mapped_source_ids):.2f}\n")
        
        print(f"Summary report written to {summary_file_path}")
    
    # Clean up
    await executor.close()

# --- Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute flexible endpoint mapping")
    parser.add_argument("input_file", help="Input TSV file path")
    parser.add_argument("output_file", help="Output TSV file path")
    parser.add_argument("--source_endpoint", required=True, help="Source endpoint name")
    parser.add_argument("--target_endpoint", required=True, help="Target endpoint name")
    parser.add_argument("--input_id_column_name", required=True, help="Column name containing identifiers to map")
    parser.add_argument("--input_primary_key_column_name", required=True, help="Column name for primary key")
    parser.add_argument("--output_mapped_id_column_name", required=True, help="Column name for mapped identifiers")
    parser.add_argument("--source_property_name", required=True, help="Source property name (e.g., PrimaryIdentifier)")
    parser.add_argument("--target_property_name", required=True, help="Target property name (e.g., UniProtAccession)")
    parser.add_argument("--source_ontology_name", required=True, help="Source ontology name (kept for compatibility)")
    parser.add_argument("--target_ontology_name", required=True, help="Target ontology name (kept for compatibility)")
    parser.add_argument("--reverse", action="store_true", help="Also try reverse mapping")
    parser.add_argument("--summary", action="store_true", help="Generate summary report")
    
    args = parser.parse_args()
    
    # Run the async main function
    asyncio.run(main(
        input_file_path=args.input_file,
        output_file_path=args.output_file,
        source_endpoint_name=args.source_endpoint,
        target_endpoint_name=args.target_endpoint,
        input_id_column_name=args.input_id_column_name,
        input_primary_key_column_name=args.input_primary_key_column_name,
        output_mapped_id_column_name=args.output_mapped_id_column_name,
        source_property_name=args.source_property_name,
        target_property_name=args.target_property_name,
        source_ontology_name=args.source_ontology_name,
        target_ontology_name=args.target_ontology_name,
        try_reverse_mapping_param=args.reverse,
        summary_param=args.summary
    ))