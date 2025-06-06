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
            os.path.join(log_dir, f"mapping_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
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
MAPPING_DIRECTION_COLUMN = "mapping_direction"  # Added explicit constant
VALIDATION_STATUS_COLUMN = "validation_status"  # Column for bidirectional validation status

# Source and target property names - these are what the endpoints expose
# These are assumed to be 'PrimaryIdentifier' for now, but could be made configurable if needed.
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"
TARGET_PROPERTY_NAME = "PrimaryIdentifier"


# --- Main Function ---
async def main(
    input_file_path: str, 
    output_file_path: str, 
    try_reverse_mapping_param: bool,
    source_endpoint_name: str,
    target_endpoint_name: str,
    input_id_column_name: str,        # e.g., "UniProt" or "uniprot"
    input_primary_key_column_name: str, # e.g., "Assay" or "name"
    output_mapped_id_column_name: str, # e.g., "ARIVALE_PROTEIN_ID" or "UKBB_ASSAY_ID"
    source_ontology_name: str,        # e.g., "UNIPROTKB_AC"
    target_ontology_name: str         # e.g., "ARIVALE_PROTEIN_ID"
):
    """
    Reads input data, extracts IDs from 'input_id_column_name', maps them using
    MappingExecutor from 'source_endpoint_name' to 'target_endpoint_name',
    and writes the merged results, storing mapped IDs in 'output_mapped_id_column_name'.
    The 'input_primary_key_column_name' is used to ensure all original columns are kept.
    """
    # --- Logging Configuration Start ---
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Override any existing root logger config
    )
    # Explicitly set level for the client logger we are debugging
    logging.getLogger("biomapper.mapping.clients.arivale_lookup_client").setLevel(
        log_level
    )
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

    # 1. Read input Data
    logger.info(f"Reading input file: {input_file_path}")
    try:
        # Read with pandas, ensure correct separator and engine
        df = pd.read_csv(input_file_path, sep='\t', engine='python', dtype=str, comment='#') # Use python engine, explicit tab sep, dtype=str, and skip comments
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

    # Extract unique IDs to map
    identifiers_to_map = df[input_id_column_name].dropna().unique().tolist()
    logger.info(f"Found {len(identifiers_to_map)} unique IDs from column '{input_id_column_name}' to map.")

    # --- MVP SUBSETTING: Process only the first N unique identifiers for initial testing ---
    SUBSET_SIZE = 1000  # Define the subset size
    if len(identifiers_to_map) > SUBSET_SIZE:
        logger.warning(f"SUBSETTING ENABLED: Processing only the first {SUBSET_SIZE} of {len(identifiers_to_map)} unique IDs.")
        identifiers_to_map = identifiers_to_map[:SUBSET_SIZE]
    # --- END MVP SUBSETTING ---

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
    # This will:
    # 1. First try the direct path (UKBB_to_Arivale_Protein_via_UniProt)
    # 2. Then try the fallback path with historical resolution if direct path fails
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
        mapping_result = await executor.execute_mapping(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=identifiers_to_map,
            source_property_name=SOURCE_PROPERTY_NAME, # Property name (PrimaryIdentifier), not the ontology type
            target_property_name=TARGET_PROPERTY_NAME, # Property name (PrimaryIdentifier), not the ontology type
            try_reverse_mapping=try_reverse_mapping_param,
            validate_bidirectional=True, # Enable bidirectional validation
            progress_callback=None, # Can be enhanced later if a GUI/detailed CLI progress is needed
            # batch_size and other parameters will use defaults from MappingExecutor constructor or its method defaults
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
    
    # The mapping_result is now just a dictionary of results, not a status-wrapped object
    # Calculate success metrics based on the results directly
    logger.info(f"DEBUG: Type of mapping_result: {type(mapping_result)}")
    if isinstance(mapping_result, dict):
        logger.info(f"DEBUG: Number of items in mapping_result: {len(mapping_result)}")
        # Log the first few items (values) from mapping_result to inspect their structure
        for i, (item_key, item_value) in enumerate(mapping_result.items()):
            if i < 5: # Log first 5 items
                logger.info(f"DEBUG: Item {i} - Key: {item_key}, Value: {item_value}")
                if isinstance(item_value, dict):
                    logger.info(f"DEBUG: Item {i} - target_identifiers: {item_value.get('target_identifiers')}")
                    logger.info(f"DEBUG: Item {i} - validation_status: {item_value.get('validation_status')}")
                else:
                    logger.info(f"DEBUG: Item {i} - Value is not a dict: {type(item_value)}")    
            else:
                break

    success_count = 0
    for result_idx, result in enumerate(mapping_result.values()):
        if result_idx < 10: # Log checks for the first 10 results
            is_valid_result = bool(result)
            has_target_ids = False
            target_ids_val = None
            if is_valid_result and isinstance(result, dict):
                target_ids_val = result.get("target_identifiers")
                has_target_ids = bool(target_ids_val) # True if list is not None and not empty
            logger.info(f"DEBUG loop idx {result_idx}: ValidResult={is_valid_result}, TargetIdsVal='{target_ids_val}', HasTargetIds={has_target_ids}")

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
    results_dict = mapping_result  # Now mapping_result is directly the results dict
    logger.info(f"Processing {len(results_dict)} mapping results.")

    # Log some sample data to debug
    sample_keys = list(results_dict.keys())[:5]
    logger.info(f"Sample results keys: {sample_keys}")
    for key in sample_keys:
        logger.info(f"Sample result for {key}: {results_dict[key]}")

    # CHANGE: Instead of creating a single mapping per source ID, we'll create a list of rows
    # to properly represent one-to-many relationships
    expanded_rows = []
    mapping_count = 0
    source_id_with_multiple_targets = 0

    # First, make a copy of the original dataframe for rows with no mappings
    # This ensures we keep all original rows even if they don't map to anything
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

    # --- MODIFIED: Generate metadata directly in the expanded rows approach --- #

    # If we have successful mappings
    if expanded_rows:
        logger.info(f"Generating metadata for expanded rows...")
        metadata_start_time = time.time()

        # Process expanded rows as a completed batch
        # We've already created the expanded rows with source_id -> target_id pairs

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

                # Store metadata for this source ID
                source_metadata[source_id] = {
                    CONFIDENCE_SCORE_COLUMN: confidence_score,
                    HOP_COUNT_COLUMN: hop_count,
                    PATH_DETAILS_COLUMN: json.dumps(path_details_for_json),
                    MAPPING_DIRECTION_COLUMN: mapping_direction,
                    VALIDATION_STATUS_COLUMN: validation_status
                }

                # Log the metadata for debugging
                logger.info(f"Metadata for {source_id}: confidence={confidence_score}, hops={hop_count}, dir={mapping_direction}, status={validation_status}")

        # Now add metadata to each row in our dataframe based on source ID
        # Create new columns for metadata
        for column in [CONFIDENCE_SCORE_COLUMN, HOP_COUNT_COLUMN, PATH_DETAILS_COLUMN, MAPPING_DIRECTION_COLUMN, VALIDATION_STATUS_COLUMN]:
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
    else:
        logger.info("No successful mappings found, adding empty metadata columns.")
        # Add empty columns if no successful mappings
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        df[MAPPING_DIRECTION_COLUMN] = None
        df[VALIDATION_STATUS_COLUMN] = None
    # --- End Modified Metadata Generation --- #

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
        description="Map identifiers from a source endpoint to a target endpoint using Biomapper."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input TSV file.",
    )
    parser.add_argument(
        "output_file",
        help="Path to write the output TSV file with mapped identifiers.",
    )
    parser.add_argument(
        "--source_endpoint",
        required=True,
        help="Name of the source endpoint (e.g., UKBB_Protein)"
    )
    parser.add_argument(
        "--target_endpoint",
        required=True,
        help="Name of the target endpoint (e.g., Arivale_Protein)"
    )
    parser.add_argument(
        "--input_id_column_name",
        required=True,
        help="Name of the column in the input file containing IDs to map (e.g., UniProt or uniprot)"
    )
    parser.add_argument(
        "--input_primary_key_column_name",
        required=True,
        help="Name of the primary key column in the input file (e.g., Assay or name)"
    )
    parser.add_argument(
        "--output_mapped_id_column_name",
        required=True,
        help="Name for the new column that will store the mapped IDs (e.g., ARIVALE_PROTEIN_ID or UKBB_ASSAY_ID)"
    )
    parser.add_argument(
        "--source_ontology_name",
        required=True,
        help="Ontology name for the source identifiers (e.g., UNIPROTKB_AC)"
    )
    parser.add_argument(
        "--target_ontology_name",
        required=True,
        help="Ontology name for the target identifiers (e.g., ARIVALE_PROTEIN_ID)"
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
        args.input_primary_key_column_name,
        args.output_mapped_id_column_name,
        args.source_ontology_name,
        args.target_ontology_name
    ))
    
    # Generate summary report if requested
    if args.summary:
        output_dir = os.path.dirname(args.output_file)
        summary_file = os.path.join(output_dir, f"{Path(args.output_file).stem}_summary_report.txt") # Make summary filename based on outputfile
        try:
            # Read the output file
            df_summary = pd.read_csv(args.output_file, sep="\t")
            
            # Generate and write summary
            with open(summary_file, "w") as f:
                f.write(f"# {args.source_endpoint} to {args.target_endpoint} Mapping Summary Report\n\n")
                f.write(f"Input File: {args.input_file}\n")
                f.write(f"Output File: {args.output_file}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Overall stats
                total_records = len(df_summary)
                # Use the dynamic output_mapped_id_column_name for checking mapped records
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
                        # Check if mapped_records is zero to avoid division by zero
                        direction_percentage = count / mapped_records * 100 if mapped_records > 0 else 0
                        f.write(f"{direction}: {count} ({direction_percentage:.2f}%)\n")
                
                # Validation status distribution
                if VALIDATION_STATUS_COLUMN in df_summary.columns and not df_summary[VALIDATION_STATUS_COLUMN].isna().all():
                    validation_counts = df_summary[VALIDATION_STATUS_COLUMN].value_counts()
                    f.write(f"\n## Validation Status Distribution\n")
                    for status, count in validation_counts.items():
                        f.write(f"{status}: {count} ({count/mapped_records*100:.2f}%)\n")
            
            print(f"Summary report written to {summary_file}")
        except Exception as e:
            print(f"Error generating summary report: {e}", file=sys.stderr)
