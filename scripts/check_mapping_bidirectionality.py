import asyncio
import csv
import json
import logging
import os
import argparse
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Tuple, Set
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import (
    Endpoint,
    EndpointPropertyConfig,
    PropertyExtractionConfig,
)
from biomapper.db.cache_models import (
    PathExecutionStatus,
    PathExecutionLog,
    PathLogMappingAssociation,
    EntityMapping,
)
from biomapper.utils.config import CONFIG_DB_URL

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "Arivale_Protein"
OUTPUT_FILE = Path(__file__).parent / "ukbb_arivale_comprehensive_mapping.csv"
ARIVALE_TSV_PATH = Path(
    "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"
)


async def get_identifier_column_from_config(
    session: AsyncSession, endpoint_id: int
) -> str | None:
    """Fetch the identifier column name from property configuration tables."""
    property_name_to_find = "PrimaryIdentifier"
    stmt = (
        select(PropertyExtractionConfig.extraction_pattern)
        .join(
            EndpointPropertyConfig,
            PropertyExtractionConfig.id
            == EndpointPropertyConfig.property_extraction_config_id,
        )
        .where(
            EndpointPropertyConfig.endpoint_id == endpoint_id,
            EndpointPropertyConfig.property_name == property_name_to_find,
            PropertyExtractionConfig.extraction_method
            == "column",  # Ensure it's column extraction
        )
    )
    result = await session.execute(stmt)
    extraction_pattern_json = result.scalar_one_or_none()

    if not extraction_pattern_json:
        logger.error(
            f"No 'column' PropertyExtractionConfig found for endpoint ID {endpoint_id} and property '{property_name_to_find}'."
        )
        return None

    try:
        extraction_details = json.loads(extraction_pattern_json)
        column_name = extraction_details.get("column_name")
        if not column_name:
            logger.error(
                f"'column_name' not found in extraction_pattern JSON: {extraction_pattern_json}"
            )
            return None
        return column_name
    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse extraction_pattern JSON: {extraction_pattern_json}"
        )
        return None


async def load_identifiers_from_endpoint(
    session: AsyncSession, endpoint_name: str
) -> Tuple[str, Path, List[str], pd.DataFrame]:
    """
    Load identifiers using connection details for path and config tables for column.

    Returns:
        Tuple containing:
        - identifier_col: The name of the identifier column
        - file_path: Path to the data file
        - identifiers: List of unique identifiers
        - df: The full dataframe containing all columns
    """
    logger.info(f"Loading identifiers for endpoint: {endpoint_name}")
    # Fetch Endpoint
    stmt_endpoint = select(Endpoint).where(Endpoint.name == endpoint_name)
    result_endpoint = await session.execute(stmt_endpoint)
    endpoint = result_endpoint.scalar_one_or_none()

    if not endpoint:
        logger.error(f"Endpoint '{endpoint_name}' not found.")
        return "", Path(""), [], pd.DataFrame()

    # Get file path from connection_details
    file_path_str = None
    try:
        if endpoint.connection_details:
            conn_details = json.loads(endpoint.connection_details)
            file_path_str = conn_details.get("path")
        if not file_path_str:
            logger.error(f"'path' not found in connection details for {endpoint_name}.")
            return "", Path(""), [], pd.DataFrame()
    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse connection_details JSON for {endpoint_name}: {endpoint.connection_details}"
        )
        return "", Path(""), [], pd.DataFrame()

    # Get identifier column name from config tables
    identifier_col = await get_identifier_column_from_config(session, endpoint.id)
    if not identifier_col:
        # Error already logged in helper function
        return "", Path(""), [], pd.DataFrame()

    # Load identifiers from file
    try:
        file_path = Path(file_path_str)
        if not file_path.is_file():
            logger.error(f"Input file not found at path: {file_path}")
            return "", Path(""), [], pd.DataFrame()

        # Use pandas to read the TSV file, reading all columns
        df = pd.read_csv(file_path, sep="\t", comment="#", dtype=str)

        # Check if the required column exists
        if identifier_col not in df.columns:
            logger.error(
                f"Identifier column '{identifier_col}' not found in DataFrame from {file_path}. Available columns: {df.columns.tolist()}"
            )
            return "", Path(""), [], pd.DataFrame()

        # Extract, strip, filter NaNs/empty, and get unique identifiers
        identifiers = set(df[identifier_col].dropna().astype(str).str.strip())
        # Remove any potential empty strings after stripping
        identifiers.discard("")

        logger.info(
            f"Loaded {len(identifiers)} unique identifiers from {file_path} using pandas"
        )
        logger.info(
            f"Full dataframe has {len(df)} rows and {len(df.columns)} columns: {df.columns.tolist()}"
        )
        return identifier_col, file_path, list(identifiers), df

    except FileNotFoundError:
        logger.error(f"Input file not found at path: {file_path}")
        return "", Path(""), [], pd.DataFrame()
    except pd.errors.EmptyDataError:
        logger.error(f"Pandas Error: File {file_path} is empty.")
        return "", Path(""), [], pd.DataFrame()
    except ValueError as e:
        # Catch potential errors if identifier_col isn't in the file (though usecols should handle this)
        logger.error(
            f"Pandas/ValueError reading {file_path} with column '{identifier_col}': {e}"
        )
        return "", Path(""), [], pd.DataFrame()
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while loading identifiers for {endpoint_name}: {e}",
            exc_info=True,
        )
        return "", Path(""), [], pd.DataFrame()


async def get_failure_details(
    session: AsyncSession, failed_source_ids: Set[str]
) -> Dict[str, str]:
    """Query cache logs for details on why mappings failed for specific identifiers."""
    if not failed_source_ids:
        return {}

    # Query PathLogMappingAssociation joined with PathExecutionLog
    # Filter by input identifiers and non-successful status
    stmt = (
        select(
            PathLogMappingAssociation.input_identifier,
            PathExecutionLog.path_name,
            PathLogMappingAssociation.status,
            PathLogMappingAssociation.error_message,
            PathExecutionLog.log_timestamp,  # For ordering attempts
        )
        .join(
            PathExecutionLog,
            PathLogMappingAssociation.path_execution_log_id == PathExecutionLog.id,
        )
        .where(
            PathLogMappingAssociation.input_identifier.in_(failed_source_ids),
            PathLogMappingAssociation.status != PathExecutionStatus.SUCCESS,
        )
        .order_by(
            PathLogMappingAssociation.input_identifier,
            PathExecutionLog.log_timestamp,  # Show attempts in chronological order
        )
    )

    result = await session.execute(stmt)
    rows = result.fetchall()

    failure_details: Dict[str, List[str]] = {sid: [] for sid in failed_source_ids}
    for row in rows:
        input_id, path_name, status, error_msg, _ = row
        reason = f"Path '{path_name}': {status.name}"
        if error_msg:
            reason += f" ({error_msg})"
        if input_id in failure_details:
            failure_details[input_id].append(reason)

    # Format into single string per identifier
    formatted_details = {
        sid: "; ".join(reasons) for sid, reasons in failure_details.items() if reasons
    }
    return formatted_details


async def main(log_level_str: str):
    # Optional: Set logger level specifically if needed inside main too
    # numeric_level = getattr(logging, log_level_str.upper(), None)
    # if isinstance(numeric_level, int):
    #     logger.setLevel(numeric_level)

    logger.info(
        f"Starting mapping process: {SOURCE_ENDPOINT_NAME} -> {TARGET_ENDPOINT_NAME}"
    )

    # Create Executor
    # Ensure executor uses the correct DB URL if it reads config itself
    executor = MappingExecutor(metamapper_db_url=CONFIG_DB_URL)

    # Create DB session for loading identifiers
    engine = create_async_engine(CONFIG_DB_URL)
    async_session_factory = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # Variables to store data for both endpoints
    source_identifiers = []
    source_df = pd.DataFrame()
    source_id_column = ""
    target_identifiers = []
    target_df = pd.DataFrame()
    target_id_column = ""

    async with async_session_factory() as meta_session:
        # --- Load Source Identifiers ---
        (
            source_id_column,
            source_file_path,
            source_identifiers,
            source_df,
        ) = await load_identifiers_from_endpoint(meta_session, SOURCE_ENDPOINT_NAME)
        if not source_identifiers:
            logger.error("Failed to load source identifiers. Exiting.")
            return
        logger.info(
            f"Successfully loaded source data: {len(source_identifiers)} identifiers"
        )

        # --- Load Target Identifiers (for joining later) ---
        (
            target_id_column,
            target_file_path,
            target_ids,
            target_df,
        ) = await load_identifiers_from_endpoint(meta_session, TARGET_ENDPOINT_NAME)
        if not target_ids:
            logger.warning(
                "Failed to load target identifiers. Reverse mapping will be skipped."
            )
            # Handle the case where target_df might be empty if needed
            target_df = pd.DataFrame(columns=[target_id_column])
            # Set target_ids to empty list explicitly if load failed but we continue
            target_ids = []
        else:
            logger.info(
                f"Successfully loaded target data: {len(target_ids)} identifiers"
            )

        # --- Execute Reverse Mapping ---
        if target_ids:
            logger.info(
                f"\nExecuting REVERSE mapping: {TARGET_ENDPOINT_NAME} -> {SOURCE_ENDPOINT_NAME}..."
            )
            # We need the executor here, which is defined outside.
            # The execute_mapping itself handles sessions internally.
            reverse_mapping_results = await executor.execute_mapping(
                source_endpoint_name=TARGET_ENDPOINT_NAME,
                target_endpoint_name=SOURCE_ENDPOINT_NAME,
                input_data=target_ids,
                use_cache=True,
                max_cache_age_days=None,
                mapping_direction="reverse",
                try_reverse_mapping=True,  # Enable bidirectional search for reverse mapping
            )
            logger.info(
                f"Got REVERSE mapping response with {len(reverse_mapping_results)} entries"
            )
            reverse_successful = sum(
                1
                for v in reverse_mapping_results.values()
                if v and v != "NO_MAPPING_FOUND"
            )
            logger.info(
                f"Reverse mapping finished. Successfully mapped {reverse_successful} / {len(target_ids)} target identifiers."
            )
        else:
            logger.info(
                "Skipping reverse mapping as no target identifiers were loaded."
            )

    # Check if source_ids were actually loaded before proceeding
    if not source_identifiers:
        logger.error(
            "Source identifiers were not loaded, cannot proceed with forward mapping."
        )
        return

    # --- Execute Forward Mapping ---
    logger.info(
        f"Executing end-to-end mapping: {SOURCE_ENDPOINT_NAME} -> {TARGET_ENDPOINT_NAME}..."
    )
    try:
        # Execute the full mapping using the executor
        mapping_response = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            input_identifiers=source_identifiers,
            source_property_name="PrimaryIdentifier",
            target_property_name="PrimaryIdentifier",
            mapping_direction="forward",
            try_reverse_mapping=True,  # Enable bidirectional search for forward mapping
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
        logger.error(
            f"Mapping execution returned unexpected type: {type(mapping_response)}. Expected dict."
        )
        return

    # Use the mapping_response directly as our mapping_results
    mapping_results = mapping_response

    logger.info(f"Got mapping response with {len(mapping_results)} entries")

    # Process mapping results and count statistics
    if mapping_results:
        logger.info("Processing mapping results...")
        # Count successful mappings (where value is not None)
        successfully_mapped_count = sum(
            1 for v in mapping_results.values() if v is not None
        )
        failed_count = len(source_identifiers) - successfully_mapped_count
        logger.info(
            f"Successfully mapped {successfully_mapped_count} out of {len(source_identifiers)} identifiers."
        )
        if failed_count > 0:
            logger.warning(
                f"{failed_count} source identifiers could not be fully mapped to a target identifier."
            )

        # --- Start Metadata Retrieval --- #
        # Prepare the dataframes for outer join
        # 1. Create a mapping results dataframe from the main execution
        mapping_df = pd.DataFrame.from_dict(
            mapping_results, orient="index", columns=["target_id"]
        )
        mapping_df.index.name = "source_id"
        mapping_df = mapping_df.reset_index()

        # 2. Add mapping status
        mapping_df["mapping_status"] = mapping_df["target_id"].apply(
            lambda x: "SUCCESS" if pd.notna(x) else "FAILED"
        )

        # 3. Fetch metadata for successful mappings directly from EntityMapping
        mapping_metadata_dict = {}
        successful_mappings = mapping_df[mapping_df["mapping_status"] == "SUCCESS"]

        if not successful_mappings.empty:
            # Use the cache database URL from the config
            cache_db_url = CONFIG_DB_URL.replace("metamapper.db", "mapping_cache.db")
            logger.info(f"Using cache database URL: {cache_db_url}")
            cache_engine = create_async_engine(cache_db_url)

            # Log what we're looking for
            logger.info(
                f"Searching for mappings in entity_mappings table with source_type=UNIPROTKB_AC and target_type=ARIVALE_PROTEIN_ID"
            )
            async with AsyncSession(cache_engine) as cache_session:
                logger.info(
                    f"Retrieving metadata for {len(successful_mappings)} successful mappings..."
                )
                for _, row in successful_mappings.iterrows():
                    source_id = row["source_id"]
                    target_id = row["target_id"]
                    mapping_entry = None  # Initialize mapping_entry

                    # Attempt 1: Query using the original source_id
                    stmt = (
                        select(EntityMapping)
                        .where(
                            EntityMapping.source_id == source_id,
                            EntityMapping.target_id == target_id,
                            EntityMapping.source_type == "UNIPROTKB_AC",
                            EntityMapping.target_type == "ARIVALE_PROTEIN_ID",
                        )
                        .order_by(EntityMapping.last_updated.desc())
                    )
                    result = await cache_session.execute(stmt)
                    mapping_entry = result.scalars().first()

                    # Attempt 2: If Attempt 1 failed and source_id is composite, try components
                    if not mapping_entry and ("_" in source_id or "," in source_id):
                        logger.debug(
                            f"Metadata lookup failed for composite ID '{source_id}', trying components..."
                        )
                        components = re.split("[_,]", source_id)
                        for component in components:
                            component_stripped = component.strip()
                            if not component_stripped:
                                continue  # Skip empty strings

                            stmt_comp = (
                                select(EntityMapping)
                                .where(
                                    EntityMapping.source_id == component_stripped,
                                    EntityMapping.target_id == target_id,
                                    EntityMapping.source_type == "UNIPROTKB_AC",
                                    EntityMapping.target_type == "ARIVALE_PROTEIN_ID",
                                )
                                .order_by(EntityMapping.last_updated.desc())
                            )
                            result_comp = await cache_session.execute(stmt_comp)
                            component_mapping_entry = result_comp.scalars().first()
                            if component_mapping_entry:
                                logger.debug(
                                    f"Found metadata for '{source_id}' via component '{component_stripped}'"
                                )
                                mapping_entry = (
                                    component_mapping_entry  # Use the found entry
                                )
                                break  # Stop after finding the first matching component

                    # Process the final result (either from Attempt 1 or Attempt 2)
                    if mapping_entry:
                        # Log detailed information about each found mapping
                        logger.debug(
                            f"Found mapping: {source_id} -> {target_id} "
                            f"(Source used for lookup: {mapping_entry.source_id}, "  # Log which source ID was ultimately used
                            f"Direction: {mapping_entry.mapping_direction}, "
                            f"Confidence: {mapping_entry.confidence_score}, "
                            f"Hop Count: {mapping_entry.hop_count})"
                        )
                        mapping_metadata_dict[
                            source_id
                        ] = mapping_entry  # Keyed by original source_id
                    else:
                        # Log warning only if both attempts failed
                        logger.warning(
                            f"Could not find EntityMapping metadata for SUCCESSFUL mapping: {source_id} -> {target_id}"
                        )

                # Summarize what we found by direction
                forward_count = sum(
                    1
                    for m in mapping_metadata_dict.values()
                    if m.mapping_direction == "forward"
                )
                reverse_count = sum(
                    1
                    for m in mapping_metadata_dict.values()
                    if m.mapping_direction == "reverse"
                )
                null_count = sum(
                    1
                    for m in mapping_metadata_dict.values()
                    if m.mapping_direction is None
                )
                logger.info(
                    f"Found metadata for {len(mapping_metadata_dict)} mappings: "
                    f"{forward_count} forward, {reverse_count} reverse, {null_count} null direction."
                )

        # 4. Add enhanced metadata fields where available using the fetched data
        mapping_df["confidence"] = mapping_df["source_id"].apply(
            lambda x: mapping_metadata_dict.get(x).confidence
            if x in mapping_metadata_dict
            else None
        )
        mapping_df["confidence_score"] = mapping_df["source_id"].apply(
            lambda x: mapping_metadata_dict.get(x).confidence_score
            if x in mapping_metadata_dict
            else None
        )
        mapping_df["mapping_path_details"] = mapping_df["source_id"].apply(
            lambda x: json.dumps(mapping_metadata_dict.get(x).mapping_path_details)
            if x in mapping_metadata_dict
            and mapping_metadata_dict.get(x).mapping_path_details
            else None
        )
        mapping_df["hop_count"] = mapping_df["source_id"].apply(
            lambda x: mapping_metadata_dict.get(x).hop_count
            if x in mapping_metadata_dict
            else None
        )
        mapping_df["mapping_direction"] = mapping_df["source_id"].apply(
            lambda x: mapping_metadata_dict.get(x).mapping_direction
            if x in mapping_metadata_dict
            else None  # Should be 'forward' for these
        )

        # 5. Prepare source dataframe with meaningful column names
        source_df_processed = source_df.rename(columns={source_id_column: "source_id"})
        # Add prefix to avoid column name conflicts
        source_cols = [col for col in source_df_processed.columns if col != "source_id"]
        for col in source_cols:
            source_df_processed = source_df_processed.rename(
                columns={col: f"source_{col}"}
            )

        # 6. Prepare target dataframe with meaningful column names
        target_df_processed = target_df.rename(columns={target_id_column: "target_id"})
        # Add prefix to avoid column name conflicts
        target_cols = [col for col in target_df_processed.columns if col != "target_id"]
        for col in target_cols:
            target_df_processed = target_df_processed.rename(
                columns={col: f"target_{col}"}
            )

        # 7. Perform outer join between source data and mapping results
        join_df = pd.merge(source_df_processed, mapping_df, on="source_id", how="left")

        # Fill in mapping_status for any rows without a status
        join_df["mapping_status"] = join_df["mapping_status"].fillna("FAILED")

        # Identify source IDs that did not map successfully
        all_source_ids = set(source_df[source_id_column].unique())
        successful_source_ids = set(mapping_df["source_id"].unique())
        failed_source_ids = all_source_ids - successful_source_ids

        # --- New Step: Query failure details ---
        failure_details_dict = {}
        if failed_source_ids:
            logger.info(
                f"Querying failure details for {len(failed_source_ids)} identifiers..."
            )
            failure_details_dict = await get_failure_details(
                cache_session, failed_source_ids
            )
            logger.info(
                f"Retrieved failure details for {len(failure_details_dict)} identifiers."
            )

        # --- New Step: Add failure reason column ---
        join_df["failure_reason"] = (
            join_df["source_id"].map(failure_details_dict).fillna("")
        )

        # 8. Perform outer join with target data
        final_df = pd.merge(join_df, target_df_processed, on="target_id", how="outer")

        # 9. Refine mapping_status based on joins and failure details
        final_df["mapping_status"] = final_df.apply(
            lambda row: "SUCCESS"
            if pd.notna(row["target_id"]) and pd.notna(row["source_id"])
            else "TARGET_ONLY"
            if pd.isna(row["source_id"])
            else "FAILED"
            if row["failure_reason"] != ""
            else "SOURCE_ONLY",  # Source exists, no target match, no specific failure logged
            axis=1,
        )

        # Clear failure reason for non-failed statuses
        final_df.loc[final_df["mapping_status"] != "FAILED", "failure_reason"] = ""

        # Ensure all rows have a mapping status (should be covered by apply now)
        # final_df["mapping_status"] = final_df["mapping_status"].fillna("UNKNOWN")

        # 10. Calculate statistics for the final joined result
        total_rows = len(final_df)
        source_only_count = sum(
            (final_df["source_id"].notna()) & (final_df["target_id"].isna())
        )
        target_only_count = sum(
            (final_df["source_id"].isna()) & (final_df["target_id"].notna())
        )
        matched_count = sum(
            (final_df["source_id"].notna()) & (final_df["target_id"].notna())
        )

        logger.info(f"Joined results: {total_rows} total rows")
        logger.info(f"  - {matched_count} matched pairs")
        logger.info(f"  - {source_only_count} source-only entries")
        logger.info(f"  - {target_only_count} target-only entries")

        # Output to CSV
        logger.info(f"Writing {len(final_df)} joined results to {OUTPUT_FILE}")
        final_df.to_csv(OUTPUT_FILE, index=False)

        logger.info(f"Mapping complete. Comprehensive results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Map UKBB Protein identifiers to Arivale Protein identifiers."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    args = parser.parse_args()

    # Configure logging based on parsed argument
    log_level_numeric = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level_numeric,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get the root logger and set its level (optional but good practice)
    # root_logger = logging.getLogger()
    # root_logger.setLevel(log_level_numeric)

    # Explicitly set the level for the mapping_executor logger
    executor_logger = logging.getLogger("biomapper.core.mapping_executor")
    executor_logger.setLevel(log_level_numeric)

    # Run the main async function
    asyncio.run(main(args.log_level))
