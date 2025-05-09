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
# Column names in the input UKBB TSV file
# Assuming these based on EndpointPropertyConfig defined previously
UKBB_ID_COLUMN = "Assay"  # The primary ID in the source file
UNIPROT_COLUMN = "UniProt"  # The column containing UniProt ACs
# Column name for the output mapped Arivale ID
ARIVALE_ID_COLUMN = "ARIVALE_PROTEIN_ID"
# New columns for detailed output
CONFIDENCE_SCORE_COLUMN = "mapping_confidence_score"
PATH_DETAILS_COLUMN = "mapping_path_details"
HOP_COUNT_COLUMN = "mapping_hop_count"
MAPPING_DIRECTION_COLUMN = "mapping_direction"  # Added explicit constant
VALIDATION_STATUS_COLUMN = "validation_status"  # Column for bidirectional validation status

# Column names in Arivale metadata file (for proper mapping lookup)
ARIVALE_UNIPROT_COLUMN = "uniprot"  # The column containing UniProt ACs in the Arivale metadata file
ARIVALE_NAME_COLUMN = "name"  # The column containing Arivale IDs in the Arivale metadata file

# Source and target ontology types for MappingExecutor (Used for logging/info)
SOURCE_ONTOLOGY = "UNIPROTKB_AC"
TARGET_ONTOLOGY = "ARIVALE_PROTEIN_ID"

# Source and target endpoint names (Used for MappingExecutor call)
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "Arivale_Protein"

# Source and target property names - these are what the endpoints expose
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"
TARGET_PROPERTY_NAME = "PrimaryIdentifier"


# --- Main Function ---
async def main(input_file_path: str, output_file_path: str, try_reverse_mapping_param: bool):
    """
    Reads UKBB data, extracts UniProt IDs, maps them to Arivale IDs using
    MappingExecutor, and writes the merged results.
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

    # 1. Read UKBB Data
    logger.info(f"Reading input file: {input_file_path}")
    try:
        # Read with pandas, ensure correct separator and engine
        df = pd.read_csv(input_file_path, sep="\t", engine="python", dtype=str)
        logger.info(f"Read {len(df)} rows from input file.")

    except FileNotFoundError:
        logger.error(f"Error: Input file not found at {input_file_path}")
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return

    # Verify required columns exist
    if UNIPROT_COLUMN not in df.columns:
        logger.error(
            f"Error: Input file must contain column '{UNIPROT_COLUMN}'. Found: {df.columns.tolist()}"
        )
        return

    # Extract unique UniProt IDs to map
    identifiers_to_map = df[UNIPROT_COLUMN].dropna().unique().tolist()
    logger.info(f"Found {len(identifiers_to_map)} unique UniProt IDs to map.")

    # --- MVP SUBSETTING: Process only the first N unique identifiers for initial testing ---
    SUBSET_SIZE = 1000  # Define the subset size
    if len(identifiers_to_map) > SUBSET_SIZE:
        logger.warning(f"SUBSETTING ENABLED: Processing only the first {SUBSET_SIZE} of {len(identifiers_to_map)} unique UniProt IDs.")
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
    logger.info(f"Executing mapping from {SOURCE_ENDPOINT_NAME}.{SOURCE_ONTOLOGY} to {TARGET_ENDPOINT_NAME}.{TARGET_ONTOLOGY}...")
    logger.info(f"Mapping {len(identifiers_to_map)} unique UniProt IDs with try_reverse_mapping={try_reverse_mapping_param}")
    
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
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
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

    # Process the results to extract just the target IDs
    processed_results = {}
    
    # Log some sample data to debug
    sample_keys = list(results_dict.keys())[:5]
    logger.info(f"Sample results keys: {sample_keys}")
    for key in sample_keys:
        logger.info(f"Sample result for {key}: {results_dict[key]}")
    
    # Enhanced result processing with debugging
    mapping_count = 0
    for uniprot_id, result_data in results_dict.items():
        if result_data and "target_identifiers" in result_data:
            target_ids = result_data["target_identifiers"]
            if target_ids and len(target_ids) > 0:
                # Take the first target ID if there are multiple
                processed_results[uniprot_id] = target_ids[0]
                mapping_count += 1
            else:
                processed_results[uniprot_id] = None
        else:
            processed_results[uniprot_id] = None
    
    logger.info(f"Processed {mapping_count} successful mappings from results dictionary")
    
    # Create a pandas Series from the processed results for efficient mapping
    map_series = pd.Series(processed_results)
    
    # Map the Arivale IDs back to the original dataframe based on the UniProt column
    # This adds the ARIVALE_ID_COLUMN
    df[ARIVALE_ID_COLUMN] = df[UNIPROT_COLUMN].map(map_series)

    # --- Generate metadata from our mapping results with enhanced processing --- #
    
    # Initialize metadata collection
    metadata_entries = []
    ids_for_metadata_generation = []

    for uniprot_id, result_data in mapping_result.items():
        if result_data: # Ensure there's result_data for this ID
            # Consider an entry active if it has target_identifiers, or a meaningful validation_status, or path_details
            has_targets = bool(result_data.get("target_identifiers"))
            validation_status = result_data.get("validation_status", "Unknown")
            has_path_details = bool(result_data.get("mapping_path_details"))
            # Define what counts as a non-default or informative validation status
            is_informative_status = validation_status not in ["Unknown", "NotApplicable", "NoMappingFound"]

            # Log the status for all entries being checked
            logger.info(f"DEBUG_METADATA_CHECK: ID: {uniprot_id}, HasTargets: {has_targets}, ValidationStatus: '{validation_status}', HasPathDetails: {has_path_details}, IsInformativeStatus: {is_informative_status}")

            if has_targets or is_informative_status or has_path_details:
                ids_for_metadata_generation.append(uniprot_id)

    if ids_for_metadata_generation:
        logger.info(f"Generating metadata for {len(ids_for_metadata_generation)} source UniProt IDs with mapping activity...")
        metadata_start_time = time.time()
        
        for uniprot_id in ids_for_metadata_generation:
            result_data = mapping_result[uniprot_id] # We know this exists
            
            # Extract metadata with appropriate defaults and validation
            confidence_score = result_data.get("confidence_score")
            
            path_details_raw = result_data.get("mapping_path_details")
            path_details_for_json = path_details_raw if isinstance(path_details_raw, dict) else {}

            # Refined hop_count extraction
            hop_count = result_data.get("hop_count")
            if hop_count is None and path_details_for_json:
                hop_count = path_details_for_json.get("hop_count")
            if hop_count is None: # Default if still not found
                hop_count = 1 if path_details_for_json else None
            
            mapping_direction = result_data.get("mapping_direction", "forward" if path_details_for_json else None)
            validation_status = result_data.get("validation_status", "Unknown") # Already fetched, but good to re-get for clarity
            
            metadata_entries.append({
                UNIPROT_COLUMN: uniprot_id,
                CONFIDENCE_SCORE_COLUMN: confidence_score,
                HOP_COUNT_COLUMN: hop_count,
                PATH_DETAILS_COLUMN: json.dumps(path_details_for_json),
                MAPPING_DIRECTION_COLUMN: mapping_direction,
                VALIDATION_STATUS_COLUMN: validation_status
            })
    
        # Create metadata DataFrame with all validated entries
        metadata_df = pd.DataFrame(metadata_entries) if metadata_entries else None
        
        # Calculate and log metadata statistics if available
        if metadata_df is not None and not metadata_df.empty:
            # Log statistics about confidence scores
            if CONFIDENCE_SCORE_COLUMN in metadata_df.columns and not metadata_df[CONFIDENCE_SCORE_COLUMN].isna().all():
                avg_confidence = metadata_df[CONFIDENCE_SCORE_COLUMN].mean()
                min_confidence = metadata_df[CONFIDENCE_SCORE_COLUMN].min()
                max_confidence = metadata_df[CONFIDENCE_SCORE_COLUMN].max()
                logger.info(f"Confidence Scores - Avg: {avg_confidence:.3f}, Min: {min_confidence:.3f}, Max: {max_confidence:.3f}")
            
            # Report metadata processing time
            logger.info(f"Metadata generation completed in {time.time() - metadata_start_time:.2f} seconds")
            
            # Log distribution of mapping directions if available
            if MAPPING_DIRECTION_COLUMN in metadata_df.columns and not metadata_df[MAPPING_DIRECTION_COLUMN].isna().all():
                direction_counts = metadata_df[MAPPING_DIRECTION_COLUMN].value_counts()
                logger.info(f"Mapping direction distribution: {dict(direction_counts)}")
                
            # Log distribution of validation statuses if available
            if VALIDATION_STATUS_COLUMN in metadata_df.columns and not metadata_df[VALIDATION_STATUS_COLUMN].isna().all():
                validation_counts = metadata_df[VALIDATION_STATUS_COLUMN].value_counts()
                logger.info(f"Validation status distribution: {dict(validation_counts)}")
            
            # Log distribution of hop counts if available
            if HOP_COUNT_COLUMN in metadata_df.columns and not metadata_df[HOP_COUNT_COLUMN].isna().all():
                hop_counts = metadata_df[HOP_COUNT_COLUMN].value_counts().to_dict()
                logger.info(f"Hop count distribution: {hop_counts}")
            
            # Log statistics about hop counts
            if HOP_COUNT_COLUMN in metadata_df.columns and not metadata_df[HOP_COUNT_COLUMN].isna().all():
                hop_counts = metadata_df[HOP_COUNT_COLUMN].value_counts().to_dict()
                logger.info(f"Hop Count Distribution: {hop_counts}")
            
            # Merge metadata with detailed logging
            logger.info(f"Merging metadata for {len(metadata_df)} mappings into output DataFrame")
            df = pd.merge(df, metadata_df, on=UNIPROT_COLUMN, how="left", validate="many_to_one")
            
            # Check for potential join issues
            null_metadata_count = df[CONFIDENCE_SCORE_COLUMN].isna().sum()
            if null_metadata_count > 0:
                logger.warning(f"Found {null_metadata_count} rows with missing metadata after merge")
        else:
            logger.warning("No valid metadata available for mapped identifiers. Adding empty columns.")
            df[CONFIDENCE_SCORE_COLUMN] = None
            df[PATH_DETAILS_COLUMN] = None
            df[HOP_COUNT_COLUMN] = None
            df[MAPPING_DIRECTION_COLUMN] = None
            df[VALIDATION_STATUS_COLUMN] = None
    else:
        logger.info("No successful mappings found, skipping metadata generation.")
        # Add empty columns if no successful mappings
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        df[MAPPING_DIRECTION_COLUMN] = None
        df[VALIDATION_STATUS_COLUMN] = None
        # --- End Enhanced Metadata Generation --- #

        # Log mapping statistics
        # Count successful maps based on non-null values in the *target* ID column
        successful_maps = df[ARIVALE_ID_COLUMN].notna().sum()
        total_attempted = df[UNIPROT_COLUMN].notna().sum()
        logger.info(
            f"Successfully mapped {successful_maps} out of {total_attempted} input UniProt IDs."
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
        description=f"Map {UKBB_ID_COLUMN} to {ARIVALE_ID_COLUMN} via {UNIPROT_COLUMN}."
    )
    parser.add_argument(
        "input_file",
        help=f"Path to the input TSV file containing {UKBB_ID_COLUMN} and {UNIPROT_COLUMN}.",
    )
    parser.add_argument(
        "output_file",
        help=f"Path to write the output TSV file with mapped {ARIVALE_ID_COLUMN}.",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Enable reverse mapping when forward mapping fails",
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
    asyncio.run(main(args.input_file, args.output_file, args.reverse))
    
    # Generate summary report if requested
    if args.summary:
        output_dir = os.path.dirname(args.output_file)
        summary_file = os.path.join(output_dir, "mapping_summary_report.txt")
        try:
            # Read the output file
            df = pd.read_csv(args.output_file, sep="\t")
            
            # Generate and write summary
            with open(summary_file, "w") as f:
                f.write("# UKBB to Arivale Mapping Summary Report\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Overall stats
                total_records = len(df)
                mapped_records = df[ARIVALE_ID_COLUMN].notna().sum()
                mapping_rate = mapped_records / total_records * 100 if total_records > 0 else 0
                
                f.write(f"## Overall Statistics\n")
                f.write(f"Total records: {total_records}\n")
                f.write(f"Successfully mapped: {mapped_records} ({mapping_rate:.2f}%)\n\n")
                
                # Confidence score distribution
                if CONFIDENCE_SCORE_COLUMN in df.columns and not df[CONFIDENCE_SCORE_COLUMN].isna().all():
                    f.write(f"## Confidence Score Statistics\n")
                    f.write(f"Average confidence: {df[CONFIDENCE_SCORE_COLUMN].mean():.3f}\n")
                    f.write(f"Minimum confidence: {df[CONFIDENCE_SCORE_COLUMN].min():.3f}\n")
                    f.write(f"Maximum confidence: {df[CONFIDENCE_SCORE_COLUMN].max():.3f}\n\n")
                
                # Hop count distribution
                if HOP_COUNT_COLUMN in df.columns and not df[HOP_COUNT_COLUMN].isna().all():
                    hop_counts = df[HOP_COUNT_COLUMN].value_counts().sort_index()
                    f.write(f"## Hop Count Distribution\n")
                    for hop, count in hop_counts.items():
                        f.write(f"{int(hop)} hops: {count} ({count/mapped_records*100:.2f}%)\n")
                    f.write("\n")
                
                # Mapping direction distribution
                if MAPPING_DIRECTION_COLUMN in df.columns and not df[MAPPING_DIRECTION_COLUMN].isna().all():
                    direction_counts = df[MAPPING_DIRECTION_COLUMN].value_counts()
                    f.write(f"## Mapping Direction Distribution\n")
                    for direction, count in direction_counts.items():
                        f.write(f"{direction}: {count} ({count/mapped_records*100:.2f}%)\n")
                
                # Validation status distribution
                if VALIDATION_STATUS_COLUMN in df.columns and not df[VALIDATION_STATUS_COLUMN].isna().all():
                    validation_counts = df[VALIDATION_STATUS_COLUMN].value_counts()
                    f.write(f"\n## Validation Status Distribution\n")
                    for status, count in validation_counts.items():
                        f.write(f"{status}: {count} ({count/mapped_records*100:.2f}%)\n")
            
            print(f"Summary report written to {summary_file}")
        except Exception as e:
            print(f"Error generating summary report: {e}", file=sys.stderr)
