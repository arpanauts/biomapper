#!/usr/bin/env python3
"""
Script for mapping UKBB metabolite identifiers to Arivale metabolite identifiers using Biomapper.

This script reads a TSV file containing UKBB metabolite data, maps the identifiers to Arivale 
metabolite identifiers using the MappingExecutor with configurable mapping paths, and 
writes the results to a new TSV file.

Key Features:
- Uses multiple mapping clients (UniChemClient, TranslatorNameResolverClient, UMLSClient) 
- Supports bidirectional validation
- Provides detailed metadata about the mapping process
- Includes confidence scores for each mapping
- Handles one-to-many mappings with expanded rows
- Supports generation of summary reports
"""

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
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.config import Config

# Configure logging with rotating file handler to avoid large log files
import logging.handlers

# Create log directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout for immediate feedback
        logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"metabolite_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)

# --- Constants ---
# Columns for detailed output
CONFIDENCE_SCORE_COLUMN = "mapping_confidence_score"
PATH_DETAILS_COLUMN = "mapping_path_details"
HOP_COUNT_COLUMN = "mapping_hop_count"
MAPPING_DIRECTION_COLUMN = "mapping_direction"
VALIDATION_STATUS_COLUMN = "validation_status"
MAPPING_METHOD_COLUMN = "mapping_method"  # New column to track which client was used

# Source and target property names - these are what the endpoints expose
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"
TARGET_PROPERTY_NAME = "PrimaryIdentifier"


# --- Main Function ---
async def main(
    input_file_path: str, 
    output_file_path: str, 
    try_reverse_mapping_param: bool,
    source_endpoint_name: str,
    target_endpoint_name: str,
    input_id_column_name: str,          # e.g., "HMDB_ID" or "PubChem_CID"
    input_name_column_name: Optional[str], # e.g., "Metabolite_Name" or "Name"
    input_primary_key_column_name: str, # e.g., "Assay" or "name"
    output_mapped_id_column_name: str,  # e.g., "ARIVALE_METABOLITE_ID" or "UKBB_ASSAY_ID"
    source_ontology_name: str,          # e.g., "HMDB" or "PUBCHEM"
    target_ontology_name: str,          # e.g., "ARIVALE_METABOLITE_ID"
    subset_size: int = 0,               # Number of IDs to process, 0 for all
    use_name_resolver: bool = False,    # Whether to use the name resolver as fallback
    use_umls: bool = False              # Whether to use UMLS as fallback
):
    """
    Reads input data, extracts IDs from 'input_id_column_name', maps them using
    MappingExecutor from 'source_endpoint_name' to 'target_endpoint_name',
    and writes the merged results, storing mapped IDs in 'output_mapped_id_column_name'.
    The 'input_primary_key_column_name' is used to ensure all original columns are kept.
    
    If 'input_name_column_name' is provided, it will also be used for name-based mapping as a fallback.
    """
    # --- Logging Configuration Start ---
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Override any existing root logger config
    )
    # Explicitly set level for client loggers
    logging.getLogger("biomapper.mapping.clients.unichem_client").setLevel(log_level)
    logging.getLogger("biomapper.mapping.clients.translator_name_resolver_client").setLevel(log_level)
    logging.getLogger("biomapper.mapping.clients.umls_client").setLevel(log_level)
    
    # Also set the level on the root logger's handlers
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers:
            handler.setLevel(log_level)
    # --- Logging Configuration End ---

    logger = logging.getLogger(__name__)  # Get logger for this script

    # Get configuration instance
    config = Config.get_instance()
    # Fix database paths to point to the correct location 
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")
    
    logger.info(f"Using Config DB: {config_db_url}")
    logger.info(f"Using Cache DB: {cache_db_url}")
    
    # Log fallback options
    logger.info(f"Using Name Resolver fallback: {use_name_resolver}")
    logger.info(f"Using UMLS fallback: {use_umls}")

    # 1. Read input Data
    logger.info(f"Reading input file: {input_file_path}")
    try:
        # Read with pandas, ensure correct separator and engine
        df = pd.read_csv(input_file_path, sep='\t', engine='python', dtype=str, comment='#')
        logger.info(f"Read {len(df)} rows from input file.")

    except FileNotFoundError:
        logger.error(f"Error: Input file not found at {input_file_path}")
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return

    # Verify required columns exist
    if input_id_column_name not in df.columns:
        logger.error(
            f"Error: Input file must contain column '{input_id_column_name}'. Found: {df.columns.tolist()}"
        )
        return
    if input_primary_key_column_name not in df.columns:
        logger.error(
            f"Error: Input file must contain column '{input_primary_key_column_name}'. Found: {df.columns.tolist()}"
        )
        return
    
    # Check name column if provided
    if input_name_column_name and input_name_column_name not in df.columns:
        logger.warning(
            f"Warning: Name column '{input_name_column_name}' not found in input file. Name-based fallback will be disabled."
        )
        input_name_column_name = None

    # Extract unique IDs to map
    identifiers_to_map = df[input_id_column_name].dropna().unique().tolist()
    logger.info(f"Found {len(identifiers_to_map)} unique IDs from column '{input_id_column_name}' to map.")

    # --- SUBSETTING: Process only the first N unique identifiers if specified ---
    if subset_size > 0 and len(identifiers_to_map) > subset_size:
        logger.warning(f"SUBSETTING ENABLED: Processing only the first {subset_size} of {len(identifiers_to_map)} unique IDs.")
        identifiers_to_map = identifiers_to_map[:subset_size]
    # --- END SUBSETTING ---

    if not identifiers_to_map:
        logger.info("No identifiers to map. Exiting.")
        return

    # 2. Execute Mapping
    logger.info("Initializing MappingExecutor...")
    # Let the executor get DB URLs from Config
    start_init_time = time.time()
    # Use the new async factory method to ensure database tables are created
    executor = await MappingExecutor.create(
        # These parameters will use defaults from Config
        metamapper_db_url=config_db_url,
        mapping_cache_db_url=cache_db_url,
        # Use debug level SQL if DEBUG log level is set
        echo_sql=log_level == logging.DEBUG
    )
    logger.info(f"MappingExecutor initialized in {time.time() - start_init_time:.2f} seconds")
    
    # Execute mapping through the MappingExecutor using configured paths
    logger.info(f"Executing mapping from {source_endpoint_name}.{source_ontology_name} to {target_endpoint_name}.{target_ontology_name}...")
    logger.info(f"Mapping {len(identifiers_to_map)} unique IDs with try_reverse_mapping={try_reverse_mapping_param}")
    
    # Setup progress tracking
    start_time = time.time()
    progress_report_interval = 10  # Report status every 10 seconds
    last_report_time = time.time()

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
        # First, try mapping with IDs only
        logger.info(f"Executing primary ID-based mapping...")
        mapping_result = await executor.execute_mapping(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=identifiers_to_map,
            source_property_name=SOURCE_PROPERTY_NAME,
            target_property_name=TARGET_PROPERTY_NAME,
            try_reverse_mapping=try_reverse_mapping_param,
            validate_bidirectional=True,
            progress_callback=None,
        )

        # Process the initial mapping results to identify unmapped IDs
        unmapped_ids = []
        unmapped_names = {}  # Dictionary mapping unmapped IDs to their names

        if input_name_column_name and (use_name_resolver or use_umls):
            # Identify unmapped IDs for fallback name-based mapping
            for id in identifiers_to_map:
                result = mapping_result.get(id, None)
                if not result or not result.get("target_identifiers"):
                    unmapped_ids.append(id)
                    
                    # Find the name for this ID if it exists
                    name_rows = df[df[input_id_column_name] == id]
                    if not name_rows.empty and input_name_column_name in name_rows.columns:
                        name = name_rows.iloc[0][input_name_column_name]
                        if name and pd.notna(name):
                            unmapped_names[id] = name
            
            logger.info(f"Found {len(unmapped_ids)} unmapped IDs, of which {len(unmapped_names)} have names for fallback mapping.")
            
            # Apply fallback mapping if there are unmapped IDs with names
            if unmapped_names:
                # Build a list of names to try mapping
                names_to_map = list(unmapped_names.values())
                name_to_id_map = {name: id for id, name in unmapped_names.items()}
                
                fallback_results = {}
                
                # Try TranslatorNameResolver first if enabled
                if use_name_resolver and names_to_map:
                    logger.info(f"Trying fallback name-based mapping with TranslatorNameResolver for {len(names_to_map)} names...")
                    
                    try:
                        # Import the client - ensure it's registered in MappingExecutor
                        from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient
                        
                        # Configure the client
                        name_resolver_config = {
                            "target_db": target_ontology_name,
                            "match_threshold": 0.5,  # Minimum match score
                        }
                        
                        # Create client instance
                        name_resolver = TranslatorNameResolverClient(name_resolver_config)
                        
                        # Execute name-based mapping
                        name_resolver_results = await name_resolver.map_identifiers(
                            names_to_map, 
                            target_biolink_type="biolink:SmallMolecule"
                        )
                        
                        # Process the results
                        for name, result in name_resolver_results.items():
                            target_ids, confidence = result
                            if target_ids:
                                # Get the original source ID for this name
                                original_id = name_to_id_map.get(name)
                                if original_id:
                                    # Create a result entry similar to MappingExecutor format
                                    fallback_results[original_id] = {
                                        "target_identifiers": target_ids,
                                        "confidence_score": float(confidence) if confidence else 0.6,  # Default if missing
                                        "mapping_path_details": {"hop_count": 1},
                                        "mapping_direction": "forward",
                                        "validation_status": "Successful: NameResolver fallback",
                                        "mapping_method": "NameResolver"
                                    }
                        
                        logger.info(f"Name-based mapping with TranslatorNameResolver found matches for {len(fallback_results)} of {len(names_to_map)} names.")
                        
                        # Clean up
                        await name_resolver.close()
                        
                    except Exception as e:
                        logger.error(f"Error in TranslatorNameResolver fallback: {str(e)}")
                
                # Try UMLS next if enabled and we still have unmapped names
                if use_umls and names_to_map:
                    # Calculate which names are still unmapped
                    mapped_ids = set(fallback_results.keys())
                    still_unmapped_names = {name: id for name, id in name_to_id_map.items() 
                                          if id not in mapped_ids}
                    
                    if still_unmapped_names:
                        names_for_umls = list(still_unmapped_names.keys())
                        logger.info(f"Trying fallback name-based mapping with UMLS for {len(names_for_umls)} remaining unmapped names...")
                        
                        try:
                            # Import the client
                            from biomapper.mapping.clients.umls_client import UMLSClient
                            
                            # Get API key from environment
                            umls_api_key = os.environ.get("UMLS_API_KEY")
                            if not umls_api_key:
                                logger.warning("UMLS_API_KEY not found in environment. UMLS fallback will be skipped.")
                            else:
                                # Configure the client
                                umls_config = {
                                    "api_key": umls_api_key,
                                    "target_db": target_ontology_name,
                                }
                                
                                # Create client instance
                                umls_client = UMLSClient(umls_config)
                                
                                # Execute name-based mapping
                                umls_results = await umls_client.map_identifiers(names_for_umls)
                                
                                # Process the results
                                for name, result in umls_results.items():
                                    target_ids, confidence = result
                                    if target_ids:
                                        # Get the original source ID for this name
                                        original_id = still_unmapped_names.get(name)
                                        if original_id:
                                            # Create a result entry similar to MappingExecutor format
                                            fallback_results[original_id] = {
                                                "target_identifiers": target_ids,
                                                "confidence_score": float(confidence) if confidence else 0.5,  # Default if missing
                                                "mapping_path_details": {"hop_count": 1},
                                                "mapping_direction": "forward",
                                                "validation_status": "Successful: UMLS fallback",
                                                "mapping_method": "UMLS"
                                            }
                                
                                logger.info(f"Name-based mapping with UMLS found matches for {len(fallback_results) - len(mapped_ids)} additional names.")
                                
                                # Clean up
                                await umls_client.close()
                        
                        except Exception as e:
                            logger.error(f"Error in UMLS fallback: {str(e)}")
                
                # Merge fallback results with primary results
                fallback_count = 0
                for id, fallback_result in fallback_results.items():
                    if id not in mapping_result or not mapping_result[id].get("target_identifiers"):
                        mapping_result[id] = fallback_result
                        fallback_count += 1
                
                if fallback_count > 0:
                    logger.info(f"Added {fallback_count} mappings from fallback mechanisms.")
    
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
    
    # Calculate success metrics based on the results
    success_count = 0
    for result in mapping_result.values():
        if result and result.get("target_identifiers"):
            success_count += 1
    
    if success_count > 0:
        # We have some successful mappings
        logger.info(f"Successfully mapped {success_count} out of {len(identifiers_to_map)} identifiers ({success_count/len(identifiers_to_map)*100:.1f}%)")
    else:
        # No successful mappings
        logger.warning("No successful mappings found.")
        
    # Always process results - they'll just be empty for unmapped IDs
    logger.info(f"Mapping returned {len(mapping_result)} results.")

    # 3. Combine Results (even for partial success)
    results_dict = mapping_result
    logger.info(f"Processing {len(results_dict)} mapping results.")

    # Log some sample data to debug
    sample_keys = list(results_dict.keys())[:5]
    logger.info(f"Sample results keys: {sample_keys}")
    for key in sample_keys:
        logger.info(f"Sample result for {key}: {results_dict[key]}")

    # Create a list of rows to properly represent one-to-many relationships
    expanded_rows = []
    mapping_count = 0
    source_id_with_multiple_targets = 0

    # First, make a copy of the original dataframe for rows with no mappings
    df_copy = df.copy()

    # Track source IDs that have mappings to avoid duplicates in the final merged result
    source_ids_with_mappings = set()

    # Process each mapping result and create expanded rows for one-to-many mappings
    for source_id, result_data in results_dict.items():
        if result_data and "target_identifiers" in result_data:
            target_ids = result_data["target_identifiers"]
            if target_ids and len(target_ids) > 0:
                # For each source ID, we may have multiple target IDs
                if len(target_ids) > 1:
                    source_id_with_multiple_targets += 1
                    logger.info(f"Source ID {source_id} maps to {len(target_ids)} targets: {target_ids}")

                # Store for tracking purposes
                source_ids_with_mappings.add(source_id)

                # Get all rows in the original dataframe that have this source ID
                matching_rows = df[df[input_id_column_name] == source_id]
                if len(matching_rows) == 0:
                    logger.warning(f"Source ID {source_id} has mapping results but not found in input DataFrame")
                    continue

                # For each matching row in original dataframe and each target ID, create a new row
                for _, orig_row in matching_rows.iterrows():
                    # Convert the row to a dictionary for easier manipulation
                    row_dict = orig_row.to_dict()

                    # For each target ID, create a new row
                    for target_id in target_ids:
                        # Create a new row based on the original
                        new_row = row_dict.copy()
                        # Add the mapped target ID
                        new_row[output_mapped_id_column_name] = target_id
                        # Add to our list of expanded rows
                        expanded_rows.append(new_row)
                        mapping_count += 1
            else:
                # No target IDs for this source ID
                pass

    logger.info(f"Processed {mapping_count} total mappings from {len(source_ids_with_mappings)} unique source IDs")
    logger.info(f"Found {source_id_with_multiple_targets} source IDs with multiple target mappings")

    # Create a new dataframe from the expanded rows (if any)
    if expanded_rows:
        # Create a dataframe from the expanded rows
        expanded_df = pd.DataFrame(expanded_rows)

        # Remove rows from the original dataframe that have mappings (to avoid duplicates)
        if source_ids_with_mappings:
            df_copy = df_copy[~df_copy[input_id_column_name].isin(source_ids_with_mappings)]

        # Concatenate the expanded rows with the original dataframe rows that don't have mappings
        df = pd.concat([expanded_df, df_copy], ignore_index=True)

        logger.info(f"Created expanded DataFrame with {len(expanded_df)} rows from mappings")
        logger.info(f"Final DataFrame has {len(df)} rows (expanded mappings + unmapped rows)")
    else:
        # No successful mappings, keep original dataframe
        logger.warning("No expanded rows created - no successful mappings found")
        df[output_mapped_id_column_name] = None

    # Generate metadata for the mappings
    if expanded_rows:
        logger.info(f"Generating metadata for expanded rows...")
        metadata_start_time = time.time()

        # Create a dictionary to store metadata for each source_id
        source_metadata = {}

        # Collect metadata for each source ID
        for source_id, result_data in mapping_result.items():
            if result_data:
                # Extract basic metadata
                confidence_score = result_data.get("confidence_score")

                path_details_raw = result_data.get("mapping_path_details")
                path_details_for_json = path_details_raw if isinstance(path_details_raw, dict) else {}

                # Refined hop_count extraction
                hop_count = result_data.get("hop_count")
                if hop_count is None and path_details_for_json:
                    hop_count = path_details_for_json.get("hop_count")
                if hop_count is None:  # Default if still not found
                    hop_count = 1 if path_details_for_json else None

                mapping_direction = result_data.get("mapping_direction", "forward" if path_details_for_json else None)
                validation_status = result_data.get("validation_status", "Unknown")
                mapping_method = result_data.get("mapping_method", "Primary")

                # Store metadata for this source ID
                source_metadata[source_id] = {
                    CONFIDENCE_SCORE_COLUMN: confidence_score,
                    HOP_COUNT_COLUMN: hop_count,
                    PATH_DETAILS_COLUMN: json.dumps(path_details_for_json),
                    MAPPING_DIRECTION_COLUMN: mapping_direction,
                    VALIDATION_STATUS_COLUMN: validation_status,
                    MAPPING_METHOD_COLUMN: mapping_method
                }

                # Log the metadata for debugging
                logger.info(f"Metadata for {source_id}: confidence={confidence_score}, hops={hop_count}, dir={mapping_direction}, status={validation_status}, method={mapping_method}")

        # Now add metadata to each row in our dataframe based on source ID
        # Create new columns for metadata
        for column in [CONFIDENCE_SCORE_COLUMN, HOP_COUNT_COLUMN, PATH_DETAILS_COLUMN, MAPPING_DIRECTION_COLUMN, VALIDATION_STATUS_COLUMN, MAPPING_METHOD_COLUMN]:
            df[column] = None

        # Apply metadata to matching rows
        for idx, row in df.iterrows():
            source_id = row[input_id_column_name]
            if pd.notna(source_id) and source_id in source_metadata:
                metadata = source_metadata[source_id]
                for column, value in metadata.items():
                    df.at[idx, column] = value

        # Log statistics about metadata
        if not df[CONFIDENCE_SCORE_COLUMN].isna().all():
            # Filter to only rows with metadata
            df_with_metadata = df[df[CONFIDENCE_SCORE_COLUMN].notna()]
            num_with_metadata = len(df_with_metadata)

            # Calculate statistics
            avg_confidence = df_with_metadata[CONFIDENCE_SCORE_COLUMN].mean()
            min_confidence = df_with_metadata[CONFIDENCE_SCORE_COLUMN].min()
            max_confidence = df_with_metadata[CONFIDENCE_SCORE_COLUMN].max()
            logger.info(f"Confidence Scores - Avg: {avg_confidence:.3f}, Min: {min_confidence:.3f}, Max: {max_confidence:.3f}")

            # Report metadata processing time
            logger.info(f"Metadata generation completed in {time.time() - metadata_start_time:.2f} seconds for {num_with_metadata} rows")

            # Log distribution of mapping directions
            if MAPPING_DIRECTION_COLUMN in df.columns and not df[MAPPING_DIRECTION_COLUMN].isna().all():
                direction_counts = df[MAPPING_DIRECTION_COLUMN].value_counts()
                logger.info(f"Mapping direction distribution: {dict(direction_counts)}")

            # Log distribution of validation statuses
            if VALIDATION_STATUS_COLUMN in df.columns and not df[VALIDATION_STATUS_COLUMN].isna().all():
                validation_counts = df[VALIDATION_STATUS_COLUMN].value_counts()
                logger.info(f"Validation status distribution: {dict(validation_counts)}")

            # Log distribution of hop counts
            if HOP_COUNT_COLUMN in df.columns and not df[HOP_COUNT_COLUMN].isna().all():
                hop_counts = df[HOP_COUNT_COLUMN].value_counts().to_dict()
                logger.info(f"Hop count distribution: {hop_counts}")
                
            # Log distribution of mapping methods
            if MAPPING_METHOD_COLUMN in df.columns and not df[MAPPING_METHOD_COLUMN].isna().all():
                method_counts = df[MAPPING_METHOD_COLUMN].value_counts()
                logger.info(f"Mapping method distribution: {dict(method_counts)}")
    else:
        logger.info("No successful mappings found, adding empty metadata columns.")
        # Add empty columns if no successful mappings
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        df[MAPPING_DIRECTION_COLUMN] = None
        df[VALIDATION_STATUS_COLUMN] = None
        df[MAPPING_METHOD_COLUMN] = None

    # Log mapping statistics
    # Count successful maps based on non-null values in the *target* ID column
    successful_maps = df[output_mapped_id_column_name].notna().sum()
    total_attempted = df[input_id_column_name].notna().sum()
    logger.info(
        f"Successfully mapped {successful_maps} out of {total_attempted} input IDs."
    )

    # 4. Write Output (for success, partial success, or handled failures)
    logger.info(f"Writing results to {output_file_path}")
    try:
        # Ensure output directory exists
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Track writing time
        write_start_time = time.time()
        df.to_csv(output_file_path, sep="\t", index=False)
        logger.info(f"Output file written successfully in {time.time() - write_start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")


# --- Argument Parsing and Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Map metabolite identifiers from a source endpoint to a target endpoint using Biomapper."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input TSV file containing metabolite identifiers.",
    )
    parser.add_argument(
        "output_file",
        help="Path to write the output TSV file with mapped identifiers.",
    )
    parser.add_argument(
        "--source_endpoint",
        required=True,
        help="Name of the source endpoint (e.g., UKBB_Metabolite)"
    )
    parser.add_argument(
        "--target_endpoint",
        required=True,
        help="Name of the target endpoint (e.g., Arivale_Metabolite)"
    )
    parser.add_argument(
        "--input_id_column_name",
        required=True,
        help="Name of the column in the input file containing IDs to map (e.g., HMDB_ID or PubChem_CID)"
    )
    parser.add_argument(
        "--input_name_column_name",
        help="Name of the column in the input file containing metabolite names for fallback mapping"
    )
    parser.add_argument(
        "--input_primary_key_column_name",
        required=True,
        help="Name of the primary key column in the input file (e.g., Assay or name)"
    )
    parser.add_argument(
        "--output_mapped_id_column_name",
        required=True,
        help="Name for the new column that will store the mapped IDs (e.g., ARIVALE_METABOLITE_ID)"
    )
    parser.add_argument(
        "--source_ontology_name",
        required=True,
        help="Ontology name for the source identifiers (e.g., HMDB or PUBCHEM)"
    )
    parser.add_argument(
        "--target_ontology_name",
        required=True,
        help="Ontology name for the target identifiers (e.g., ARIVALE_METABOLITE_ID)"
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Enable reverse mapping as a fallback if forward mapping fails for an ID (within MappingExecutor)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a summary report of mapping results",
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=0,
        help="Only process the first N unique identifiers (default: 0, process all)",
    )
    parser.add_argument(
        "--use_name_resolver",
        action="store_true",
        help="Use the TranslatorNameResolverClient as a fallback for name-based mapping",
    )
    parser.add_argument(
        "--use_umls",
        action="store_true",
        help="Use the UMLSClient as a fallback for name-based mapping (requires UMLS_API_KEY environment variable)",
    )
    args = parser.parse_args()

    # Basic input validation
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Run the async main function
    asyncio.run(main(
        args.input_file, 
        args.output_file, 
        args.reverse,
        args.source_endpoint,
        args.target_endpoint,
        args.input_id_column_name,
        args.input_name_column_name,
        args.input_primary_key_column_name,
        args.output_mapped_id_column_name,
        args.source_ontology_name,
        args.target_ontology_name,
        args.subset,
        args.use_name_resolver,
        args.use_umls
    ))
    
    # Generate summary report if requested
    if args.summary:
        output_dir = os.path.dirname(args.output_file)
        summary_file = os.path.join(output_dir, f"{Path(args.output_file).stem}_summary_report.txt")
        try:
            # Read the output file
            df_summary = pd.read_csv(args.output_file, sep="\t")
            
            # Generate and write summary
            with open(summary_file, "w") as f:
                f.write(f"# {args.source_endpoint} to {args.target_endpoint} Metabolite Mapping Summary Report\n\n")
                f.write(f"Input File: {args.input_file}\n")
                f.write(f"Output File: {args.output_file}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Overall stats
                total_records = len(df_summary)
                mapped_records = df_summary[args.output_mapped_id_column_name].notna().sum()
                mapping_rate = mapped_records / total_records * 100 if total_records > 0 else 0
                
                f.write(f"## Overall Statistics\n")
                f.write(f"Total records: {total_records}\n")
                f.write(f"Successfully mapped: {mapped_records} ({mapping_rate:.2f}%)\n\n")
                
                # Confidence score distribution
                if CONFIDENCE_SCORE_COLUMN in df_summary.columns and not df_summary[CONFIDENCE_SCORE_COLUMN].isna().all():
                    f.write(f"## Confidence Score Statistics\n")
                    f.write(f"Average confidence: {df_summary[CONFIDENCE_SCORE_COLUMN].mean():.3f}\n")
                    f.write(f"Minimum confidence: {df_summary[CONFIDENCE_SCORE_COLUMN].min():.3f}\n")
                    f.write(f"Maximum confidence: {df_summary[CONFIDENCE_SCORE_COLUMN].max():.3f}\n\n")
                
                # Hop count distribution
                if HOP_COUNT_COLUMN in df_summary.columns and not df_summary[HOP_COUNT_COLUMN].isna().all():
                    hop_counts = df_summary[HOP_COUNT_COLUMN].value_counts().sort_index()
                    f.write(f"## Hop Count Distribution\n")
                    for hop, count in hop_counts.items():
                        f.write(f"{int(hop)} hops: {count} ({count/mapped_records*100:.2f}%)\n")
                    f.write("\n")
                
                # Mapping direction distribution
                if MAPPING_DIRECTION_COLUMN in df_summary.columns and not df_summary[MAPPING_DIRECTION_COLUMN].isna().all():
                    direction_counts = df_summary[MAPPING_DIRECTION_COLUMN].value_counts()
                    f.write(f"## Mapping Direction Distribution\n")
                    for direction, count in direction_counts.items():
                        direction_percentage = count / mapped_records * 100 if mapped_records > 0 else 0
                        f.write(f"{direction}: {count} ({direction_percentage:.2f}%)\n")
                    f.write("\n")
                
                # Validation status distribution
                if VALIDATION_STATUS_COLUMN in df_summary.columns and not df_summary[VALIDATION_STATUS_COLUMN].isna().all():
                    validation_counts = df_summary[VALIDATION_STATUS_COLUMN].value_counts()
                    f.write(f"## Validation Status Distribution\n")
                    for status, count in validation_counts.items():
                        f.write(f"{status}: {count} ({count/mapped_records*100:.2f}%)\n")
                    f.write("\n")
                
                # Mapping method distribution
                if MAPPING_METHOD_COLUMN in df_summary.columns and not df_summary[MAPPING_METHOD_COLUMN].isna().all():
                    method_counts = df_summary[MAPPING_METHOD_COLUMN].value_counts()
                    f.write(f"## Mapping Method Distribution\n")
                    for method, count in method_counts.items():
                        f.write(f"{method}: {count} ({count/mapped_records*100:.2f}%)\n")
            
            print(f"Summary report written to {summary_file}")
        except Exception as e:
            print(f"Error generating summary report: {e}", file=sys.stderr)