import argparse
import asyncio
import json
import logging
import os
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from biomapper.core.mapping_executor import MappingExecutor, PathExecutionStatus
from biomapper.core.config import Config
from sqlalchemy.future import select
from biomapper.db.cache_models import EntityMapping

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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

# Source and target ontology types for MappingExecutor (Used for logging/info)
SOURCE_ONTOLOGY = "UNIPROTKB_AC"
TARGET_ONTOLOGY = "ARIVALE_PROTEIN_ID"

# Source and target endpoint names (Used for MappingExecutor call)
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "Arivale_Protein"


# --- Main Function ---
async def main(input_file_path: str, output_file_path: str):
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
    if UKBB_ID_COLUMN not in df.columns or UNIPROT_COLUMN not in df.columns:
        logger.error(
            f"Error: Input file must contain columns '{UKBB_ID_COLUMN}' and '{UNIPROT_COLUMN}'. Found: {df.columns.tolist()}"
        )
        return

    # 2. Extract IDs
    # Get unique UniProt IDs to map (handle potential missing values)
    uniprot_ids_to_map = df[UNIPROT_COLUMN].dropna().unique().tolist()
    logger.info(
        f"Found {len(uniprot_ids_to_map)} unique UniProt IDs ({SOURCE_ONTOLOGY}) to map."
    )

    if not uniprot_ids_to_map:
        logger.warning("No valid UniProt IDs found to map. Writing original data.")
        df[ARIVALE_ID_COLUMN] = None  # Add empty column
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        # Ensure output directory exists
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file_path, sep="\t", index=False)
        logger.info(f"Output written to {output_file_path}")
        return

    # 3. Execute Mapping
    logger.info("Initializing MappingExecutor...")
    # Let the executor get DB URLs from Config
    executor = MappingExecutor()
    
    # Execute mapping through the MappingExecutor using configured paths
    # This will:
    # 1. First try the direct path (UKBB_to_Arivale_Protein_via_UniProt)
    # 2. Then try the fallback path with historical resolution if direct path fails
    logger.info(f"Executing mapping from {SOURCE_ENDPOINT_NAME}.{SOURCE_ONTOLOGY} to {TARGET_ENDPOINT_NAME}.{TARGET_ONTOLOGY}...")
    mapping_result = await executor.execute_mapping(
        source_endpoint_name=SOURCE_ENDPOINT_NAME,
        target_endpoint_name=TARGET_ENDPOINT_NAME,
        source_identifiers=uniprot_ids_to_map,
        source_ontology_type=SOURCE_ONTOLOGY,
        target_ontology_type=TARGET_ONTOLOGY,
        # Optional parameters for more control
        max_hop_count=3,  # Maximum number of steps in any path
        min_confidence=0.1,  # Minimum confidence score to accept a result
        allow_reverse_paths=False,  # Don't try reverse mapping in this case
    )

    if mapping_result["status"] == "failure":
        logger.error(
            f"Mapping execution failed: {mapping_result.get('error', 'Unknown error')}"
        )
        # Decide how to handle failure: write partial, write original, or nothing?
        # For now, let's write the original data with empty target/metadata columns
        df[ARIVALE_ID_COLUMN] = None
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        logger.info("Writing original data with empty mapping columns due to mapping failure.")
    elif mapping_result["status"] == "no_path_found":
        logger.error(
            f"Mapping execution failed: No path found. {mapping_result.get('error', '')}"
        )
        df[ARIVALE_ID_COLUMN] = None
        df[CONFIDENCE_SCORE_COLUMN] = None
        df[PATH_DETAILS_COLUMN] = None
        df[HOP_COUNT_COLUMN] = None
        logger.info("Writing original data with empty mapping columns due to no mapping path.")
    else:
        if mapping_result["status"] == "partial_success":
            logger.warning("Mapping execution resulted in partial success.")
        else:  # Success
            logger.info("Mapping execution successful.")

        # 4. Combine Results (even for partial success)
        results_dict = mapping_result.get(
            "results", {}
        )  # {uniprot_id: arivale_id or None}
        logger.info(f"Mapping returned {len(results_dict)} results.")

        # Process the results to extract just the target IDs
        processed_results = {}
        for uniprot_id, result_data in results_dict.items():
            if result_data and "target_identifiers" in result_data:
                target_ids = result_data["target_identifiers"]
                if target_ids and len(target_ids) > 0:
                    # Take the first target ID if there are multiple
                    processed_results[uniprot_id] = target_ids[0]
                else:
                    processed_results[uniprot_id] = None
            else:
                processed_results[uniprot_id] = None
        
        # Create a pandas Series from the processed results for efficient mapping
        map_series = pd.Series(processed_results)
        
        # Map the Arivale IDs back to the original dataframe based on the UniProt column
        # This adds the ARIVALE_ID_COLUMN
        df[ARIVALE_ID_COLUMN] = df[UNIPROT_COLUMN].map(map_series)

        # --- Generate metadata from our simplified mapping results --- #
        successfully_mapped_ids = df[UNIPROT_COLUMN][df[ARIVALE_ID_COLUMN].notna()].unique().tolist()

        if successfully_mapped_ids:
            logger.info(f"Generating metadata for {len(successfully_mapped_ids)} successfully mapped source UniProt IDs...")
            # Add metadata columns directly from our mapping results
            metadata_df = pd.DataFrame([
                {
                    UNIPROT_COLUMN: uniprot_id,
                    CONFIDENCE_SCORE_COLUMN: mapping_result["results"][uniprot_id].get("confidence_score", 0.9),
                    HOP_COUNT_COLUMN: mapping_result["results"][uniprot_id].get("hop_count", 1),
                    PATH_DETAILS_COLUMN: json.dumps(mapping_result["results"][uniprot_id].get("mapping_path_details", {}))
                }
                for uniprot_id in successfully_mapped_ids
                if uniprot_id in mapping_result["results"]
            ])
            
            # Merge metadata back into the main DataFrame if we have any
            if not metadata_df.empty:
                # Use 'left' merge to keep all rows from the original df
                df = pd.merge(df, metadata_df, on=UNIPROT_COLUMN, how="left")
            else:
                logger.warning("No metadata available for mapped identifiers. Adding empty columns.")
                df[CONFIDENCE_SCORE_COLUMN] = None
                df[PATH_DETAILS_COLUMN] = None
                df[HOP_COUNT_COLUMN] = None
        else:
            logger.info("No successful mappings found, skipping metadata generation.")
            # Add empty columns if no successful mappings
            df[CONFIDENCE_SCORE_COLUMN] = None
            df[PATH_DETAILS_COLUMN] = None
            df[HOP_COUNT_COLUMN] = None
        # --- End Metadata Generation --- #

        # Log mapping statistics
        # Count successful maps based on non-null values in the *target* ID column
        successful_maps = df[ARIVALE_ID_COLUMN].notna().sum()
        total_attempted = df[UNIPROT_COLUMN].notna().sum()
        logger.info(
            f"Successfully mapped {successful_maps} out of {total_attempted} input UniProt IDs."
        )

    # 5. Write Output (for success, partial success, or handled failures)
    logger.info(f"Writing results to {output_file_path}")
    try:
        # Ensure output directory exists
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file_path, sep="\t", index=False)
        logger.info("Output file written successfully.")
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
    args = parser.parse_args()

    # Basic input validation
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Run the async main function
    asyncio.run(main(args.input_file, args.output_file))
