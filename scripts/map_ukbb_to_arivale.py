import asyncio
import csv
import json
import logging
import os
import argparse
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig
from biomapper.db.cache_models import PathExecutionStatus # Corrected import path
from biomapper.utils.config import CONFIG_DB_URL

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "Arivale_Protein"
OUTPUT_FILE = Path(__file__).parent / "ukbb_arivale_mapping_output.csv"
ARIVALE_TSV_PATH = Path("/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv")

async def get_identifier_column_from_config(session: AsyncSession, endpoint_id: int) -> str | None:
    """Fetch the identifier column name from property configuration tables."""
    property_name_to_find = "PrimaryIdentifier"
    stmt = (
        select(PropertyExtractionConfig.extraction_pattern)
        .join(EndpointPropertyConfig, PropertyExtractionConfig.id == EndpointPropertyConfig.property_extraction_config_id)
        .where(
            EndpointPropertyConfig.endpoint_id == endpoint_id,
            EndpointPropertyConfig.property_name == property_name_to_find,
            PropertyExtractionConfig.extraction_method == 'column' # Ensure it's column extraction
        )
    )
    result = await session.execute(stmt)
    extraction_pattern_json = result.scalar_one_or_none()

    if not extraction_pattern_json:
        logger.error(f"No 'column' PropertyExtractionConfig found for endpoint ID {endpoint_id} and property '{property_name_to_find}'.")
        return None

    try:
        extraction_details = json.loads(extraction_pattern_json)
        column_name = extraction_details.get("column_name")
        if not column_name:
            logger.error(f"'column_name' not found in extraction_pattern JSON: {extraction_pattern_json}")
            return None
        return column_name
    except json.JSONDecodeError:
        logger.error(f"Failed to parse extraction_pattern JSON: {extraction_pattern_json}")
        return None

async def load_identifiers_from_endpoint(session: AsyncSession, endpoint_name: str) -> Tuple[str, Path, List[str]]:
    """Load identifiers using connection details for path and config tables for column."""
    logger.info(f"Loading identifiers for endpoint: {endpoint_name}")
    # Fetch Endpoint
    stmt_endpoint = select(Endpoint).where(Endpoint.name == endpoint_name)
    result_endpoint = await session.execute(stmt_endpoint)
    endpoint = result_endpoint.scalar_one_or_none()

    if not endpoint:
        logger.error(f"Endpoint '{endpoint_name}' not found.")
        return "", Path(""), []

    # Get file path from connection_details
    file_path_str = None
    try:
        if endpoint.connection_details:
            conn_details = json.loads(endpoint.connection_details)
            file_path_str = conn_details.get("path")
        if not file_path_str:
            logger.error(f"'path' not found in connection details for {endpoint_name}.")
            return "", Path(""), []
    except json.JSONDecodeError:
        logger.error(f"Failed to parse connection_details JSON for {endpoint_name}: {endpoint.connection_details}")
        return "", Path(""), []

    # Get identifier column name from config tables
    identifier_col = await get_identifier_column_from_config(session, endpoint.id)
    if not identifier_col:
        # Error already logged in helper function
        return "", Path(""), []

    # Load identifiers from file
    try:
        file_path = Path(file_path_str)
        if not file_path.is_file():
            logger.error(f"Input file not found at path: {file_path}")
            return "", Path(""), []

        # Use pandas to read the TSV file, similar to check_uniprot_overlap.py
        df = pd.read_csv(file_path, sep='\t', comment='#', usecols=[identifier_col], dtype=str)
        
        # Check if the required column exists (pandas handles this implicitly during load if usecols is specific)
        # However, an explicit check after load is good practice if usecols wasn't used or column name might be wrong
        if identifier_col not in df.columns:
             logger.error(f"Identifier column '{identifier_col}' not found in DataFrame from {file_path}. Available columns: {df.columns.tolist()}")
             return "", Path(""), []
        
        # Extract, strip, filter NaNs/empty, and get unique identifiers
        identifiers = set(df[identifier_col].dropna().astype(str).str.strip())
        # Remove any potential empty strings after stripping
        identifiers.discard('') 

        logger.info(f"Loaded {len(identifiers)} unique identifiers from {file_path} using pandas")
        return identifier_col, file_path, list(identifiers)

    except FileNotFoundError:
        logger.error(f"Input file not found at path: {file_path}")
    except pd.errors.EmptyDataError:
        logger.error(f"Pandas Error: File {file_path} is empty.")
        return "", Path(""), []
    except ValueError as e:
        # Catch potential errors if identifier_col isn't in the file (though usecols should handle this)
        logger.error(f"Pandas/ValueError reading {file_path} with column '{identifier_col}': {e}")
        return "", Path(""), []
    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading identifiers for {endpoint_name}: {e}", exc_info=True)
        return "", Path(""), []

async def main(log_level_str: str): # Pass log level to main
    # Optional: Set logger level specifically if needed inside main too
    # numeric_level = getattr(logging, log_level_str.upper(), None)
    # if isinstance(numeric_level, int):
    #     logger.setLevel(numeric_level)
        
    logger.info(f"Starting mapping process: {SOURCE_ENDPOINT_NAME} -> {TARGET_ENDPOINT_NAME}")

    # Create Executor
    # Ensure executor uses the correct DB URL if it reads config itself
    executor = MappingExecutor(metamapper_db_url=CONFIG_DB_URL)

    # Create DB session for loading identifiers
    engine = create_async_engine(CONFIG_DB_URL)
    async_session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    identifiers_to_map = []
    ukbb_id_column = ""
    ukbb_file_path = Path("")
    async with async_session_factory() as session:
        ukbb_id_column, ukbb_file_path, identifiers_to_map = await load_identifiers_from_endpoint(session, SOURCE_ENDPOINT_NAME)

    if not identifiers_to_map or not ukbb_id_column or not ukbb_file_path:
        logger.error("Could not retrieve source identifiers, column name, or file path. Exiting.")
        return

    logger.info(f"Executing end-to-end mapping: {SOURCE_ENDPOINT_NAME} -> {TARGET_ENDPOINT_NAME}...")
    try:
        # Execute the full mapping using the executor
        mapping_response = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME, # Executor finds the path
            input_identifiers=identifiers_to_map,
            source_property_name="PrimaryIdentifier", # Source property
            target_property_name="PrimaryIdentifier",  # Target property
        )

    except Exception as e:
        logger.error(f"Mapping execution failed: {e}", exc_info=True)
        return

    # Handle potential errors in mapping_response
    if mapping_response is None:
        logger.error("Mapping execution returned None.")
        return
    
    # Check if response is an error dictionary (has 'error' key)
    if isinstance(mapping_response, dict) and "error" in mapping_response:
        logger.error(f"Mapping execution failed: {mapping_response['error']}")
        return
    
    # Ensure response is a dictionary
    if not isinstance(mapping_response, dict):
        logger.error(f"Mapping execution returned unexpected type: {type(mapping_response)}. Expected dict.")
        return
    
    # Use the mapping_response directly as our mapping_results
    # The updated execute_mapping method returns the results directly
    mapping_results = mapping_response
    
    logger.info(f"Got mapping response with {len(mapping_results)} entries")
    
    # Combine results - the executor gives final mapping now
    if mapping_results:
        logger.info("Processing mapping results...")
        # Count successful mappings (where value is not None)
        successful_mappings = sum(1 for v in mapping_results.values() if v is not None)
        total_inputs = len(identifiers_to_map)
        failed_mappings = total_inputs - successful_mappings
        logger.info(f"Successfully mapped {successful_mappings} out of {total_inputs} identifiers.")
        if failed_mappings > 0:
            logger.warning(f"{failed_mappings} source identifiers could not be fully mapped to a target identifier.")

        # Convert results to DataFrame with more descriptive column names
        mapping_df = pd.DataFrame.from_dict(mapping_results, orient='index', columns=['Arivale_Protein_ID'])
    else:
        logger.warning("Mapping execution returned no results.")
        # Create an empty DataFrame or handle as appropriate
        mapping_df = pd.DataFrame(index=identifiers_to_map, columns=['Arivale_Protein_ID'])
        mapping_df.index.name = 'UKBB_UniProtKB_AC'
        failed_mappings = len(identifiers_to_map)
        logger.warning(f"{failed_mappings} source identifiers could not be mapped.")

    # Prepare DataFrame for output with more descriptive column names
    mapping_df.index.name = 'UKBB_UniProtKB_AC'
    mapping_df = mapping_df.reset_index()

    # Output to CSV
    logger.info(f"Writing {len(mapping_df)} mapping results to {OUTPUT_FILE}")
    mapping_df.to_csv(OUTPUT_FILE, index=False)

    # Log summary of failures again for clarity
    if failed_mappings > 0:
        logger.info(f"{failed_mappings} source identifiers ended with no successful mapping in the output file.")

    logger.info(f"Mapping complete. Results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Map UKBB Protein identifiers to Arivale Protein identifiers.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    args = parser.parse_args()

    # Configure logging based on parsed argument
    log_level_numeric = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level_numeric, # Use the numeric level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get the root logger and set its level (optional but good practice)
    # root_logger = logging.getLogger()
    # root_logger.setLevel(log_level_numeric)

    # Explicitly set the level for the mapping_executor logger
    executor_logger = logging.getLogger('biomapper.core.mapping_executor')
    executor_logger.setLevel(log_level_numeric)

    # Run the main async function
    asyncio.run(main(args.log_level)) # Pass log level string if needed by main
