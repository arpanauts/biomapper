import asyncio
import csv
import json
import logging
import os
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

        identifiers = set()
        logger.info(f"Reading identifiers from '{identifier_col}' column in {file_path}")
        with open(file_path, 'r', newline='', encoding='utf-8') as tsvfile:
            dialect = csv.Sniffer().sniff(tsvfile.read(1024))
            tsvfile.seek(0)
            reader = csv.DictReader(tsvfile, dialect=dialect)

            if identifier_col not in reader.fieldnames:
                logger.error(f"Identifier column '{identifier_col}' (from config) not found in file {file_path}. Available columns: {reader.fieldnames}")
                return "", Path(""), []

            for row in reader:
                identifier = row.get(identifier_col)
                if identifier:
                    identifiers.add(identifier.strip())

        logger.info(f"Loaded {len(identifiers)} unique identifiers from {file_path}")
        return identifier_col, file_path, list(identifiers)

    except FileNotFoundError:
        logger.error(f"Input file not found at path: {file_path}")
        return "", Path(""), []
    except KeyError:
        logger.error(f"Identifier column '{identifier_col}' (from config) caused KeyError in file {file_path}.")
        return "", Path(""), []
    except csv.Error as e:
        logger.error(f"Error reading CSV/TSV file {file_path}: {e}")
        return "", Path(""), []
    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading identifiers for {endpoint_name}: {e}", exc_info=True)
        return "", Path(""), []

def load_arivale_mapping_lookup(arivale_tsv_path: Path) -> Dict[str, str]:
    """Loads the Arivale metadata and creates a UniProt AC -> Arivale Name lookup.

    Args:
        arivale_tsv_path: Path to the Arivale proteomics_metadata.tsv file.

    Returns:
        A dictionary mapping UniProt Accession IDs to Arivale 'name' identifiers.
    """
    logger.info(f"Loading Arivale mapping lookup from {arivale_tsv_path}...")
    try:
        # Skip comment lines starting with '#' and use tab separator
        df_arivale = pd.read_csv(arivale_tsv_path, sep='\t', comment='#')
        # Ensure required columns exist
        if 'uniprot' not in df_arivale.columns or 'name' not in df_arivale.columns:
            raise ValueError("Arivale TSV missing required columns: 'uniprot' and/or 'name'")

        # Drop rows where 'uniprot' is missing, as they can't be used for mapping
        df_arivale.dropna(subset=['uniprot'], inplace=True)

        # Handle potential duplicate UniProt IDs - keep the first occurrence
        # Log a warning if duplicates are found
        if df_arivale['uniprot'].duplicated().any():
            duplicates = df_arivale[df_arivale['uniprot'].duplicated()]['uniprot'].unique()
            logger.warning(f"Duplicate UniProt IDs found in Arivale data. Keeping first occurrence. Duplicates: {list(duplicates)}")
            df_arivale.drop_duplicates(subset=['uniprot'], keep='first', inplace=True)

        # Create the lookup dictionary
        lookup = pd.Series(df_arivale['name'].values, index=df_arivale['uniprot']).to_dict()
        logger.info(f"Created Arivale lookup with {len(lookup)} UniProt entries.")
        return lookup

    except FileNotFoundError:
        logger.error(f"Arivale TSV file not found at: {arivale_tsv_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading or processing Arivale TSV: {e}", exc_info=True)
        raise

async def main():
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

    logger.info(f"Executing Step 1: Mapping UKBB Identifiers ({SOURCE_ENDPOINT_NAME}) to UniProtKB ACs...")
    try:
        # Step 1: UKBB Identifier -> UniProtKB AC
        # Note: The execute_mapping currently seems hardcoded to find the path
        # between the source and target endpoints and use the appropriate client.
        # For UKBB->Arivale (Protein), it should find the UniProtNameClient.
        mapping_response = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME, # Used internally by executor to find path/client
            input_identifiers=identifiers_to_map, # Use updated parameter name
            source_property_name="PrimaryIdentifier", # Specify source property
            target_property_name="PrimaryIdentifier"  # Specify target property
        )

    except Exception as e:
        logger.error(f"Mapping execution failed during Step 1: {e}", exc_info=True)
        return

    # Handle potential None or error dict from executor
    if mapping_response is None:
        logger.error("Mapping execution returned None.")
        return
    # Only treat as error if 'error' key exists AND is not None
    if isinstance(mapping_response, dict) and "error" in mapping_response and mapping_response["error"] is not None:
        logger.error(f"Mapping execution failed: {mapping_response['error']}")
        return
    if not isinstance(mapping_response, dict):
        logger.error(f"Mapping execution returned unexpected type: {type(mapping_response)}. Expected dict.")
        return
    if mapping_response.get("status") == PathExecutionStatus.FAILURE.value:
        logger.error(f"Mapping execution failed with status FAILURE. Error: {mapping_response.get('error')}")
        return
    if mapping_response.get("status") == PathExecutionStatus.NO_PATH_FOUND.value:
        logger.error(f"Mapping execution failed: No path found. Error: {mapping_response.get('error')}")
        return

    # Extract the actual results from the response dictionary
    mapping_results = mapping_response.get("results", {})
    if not mapping_results:
        logger.warning("Mapping execution returned no results.")

    # Load Arivale UniProt -> Arivale Name lookup
    try:
        arivale_lookup = load_arivale_mapping_lookup(ARIVALE_TSV_PATH)
    except Exception:
        # Error already logged in load_arivale_mapping_lookup
        logger.error("Failed to load Arivale mapping data. Exiting.")
        return

    # Perform UniProt -> Arivale mapping and combine results
    final_results = []
    unmapped_count_step1 = 0
    unmapped_count_step2 = 0

    logger.info(f"Combining results and mapping UniProt IDs to Arivale Names...")
    for ukbb_id in identifiers_to_map: # Iterate in original order
        # mapping_results contains {ukbb_id: [list_of_uniprot_ids]} or {ukbb_id: None}
        uniprot_id_list = mapping_results.get(ukbb_id)
        # Extract the first ID if the list is not empty, otherwise None
        uniprot_id = uniprot_id_list[0] if uniprot_id_list else None
        arivale_name = None

        if uniprot_id:
            # Lookup UniProt ID in Arivale data
            arivale_name = arivale_lookup.get(uniprot_id)
            if not arivale_name:
                unmapped_count_step2 += 1
                logger.info(f"UniProt ID '{uniprot_id}' (from UKBB ID '{ukbb_id}') not found in Arivale lookup.")
        else:
            unmapped_count_step1 += 1
            logger.info(f"UKBB ID '{ukbb_id}' did not map to a UniProt ID.")

        final_results.append({
            'ukbb_identifier': ukbb_id,
            'uniprot_id': uniprot_id,
            'arivale_name': arivale_name
        })

    # Write results to output CSV
    try:
        df_results = pd.DataFrame(final_results)
        logger.info(f"Writing {len(df_results)} mapping results to {OUTPUT_FILE}")
        df_results.to_csv(OUTPUT_FILE, index=False)

        if unmapped_count_step1 > 0:
            logger.info(f"{unmapped_count_step1} identifiers could not be mapped to UniProt IDs.")
        if unmapped_count_step2 > 0:
            logger.info(f"{unmapped_count_step2} UniProt IDs could not be mapped to an Arivale Name.")

        logger.info(f"Mapping complete. Results written to {OUTPUT_FILE}")

    except Exception as e:
        logger.error(f"Failed to write output CSV. Exception Type: {type(e).__name__}, Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
