import asyncio
import aiohttp
import csv
from pathlib import Path
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Assuming RelationshipMappingExecutor and database setup are accessible
# Adjust imports based on your project structure
from biomapper.mapping.relationships.executor import RelationshipMappingExecutor

# --- Configuration ---
DATABASE_URL = "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db"
ARIVALE_METADOLOMICS_FILE = Path(
    "/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv"
)
RELATIONSHIP_ID_TO_TEST = 1
SOURCE_ONTOLOGY = "PUBCHEM"
MAX_ROWS_TO_TEST = 5  # Limit the number of rows processed for this MVP test
# -------------------


async def main():
    # Configure logging
    # Set level to DEBUG to see detailed logs from executor
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Force the specific executor logger to DEBUG level
    logging.getLogger("biomapper.mapping.relationships.executor").setLevel(
        logging.DEBUG
    )

    logging.info(
        f"Starting mapping test for relationship ID: {RELATIONSHIP_ID_TO_TEST}"
    )
    logging.info(f"Source ontology: {SOURCE_ONTOLOGY}")
    logging.info(f"Target: UKBB Metabolites (via NAME)")
    logging.info(
        f"Processing max {MAX_ROWS_TO_TEST} rows from {ARIVALE_METADOLOMICS_FILE}"
    )

    if not ARIVALE_METADOLOMICS_FILE.exists():
        logging.error(f"Source file not found: {ARIVALE_METADOLOMICS_FILE}")
        return

    # We need a specific session for the config DB (metamapper.db) for the executor
    config_engine = create_async_engine(DATABASE_URL, echo=False)
    ConfigSessionLocal = async_sessionmaker(
        bind=config_engine, expire_on_commit=False, class_=AsyncSession
    )

    processed_rows = 0

    try:
        async with aiohttp.ClientSession() as http_session:
            # Create a session for the configuration database
            async with ConfigSessionLocal() as config_db_session:
                executor = RelationshipMappingExecutor(config_db_session, http_session)

                with open(ARIVALE_METADOLOMICS_FILE, "r", newline="") as csvfile:
                    # Skip header lines until we find the actual header row
                    for _ in range(
                        13
                    ):  # Based on the file view, header is line 14 (0-indexed 13)
                        next(csvfile)

                    reader = csv.DictReader(csvfile, delimiter="\t")
                    logging.info(f"CSV Headers: {reader.fieldnames}")

                    if SOURCE_ONTOLOGY not in reader.fieldnames:
                        logging.error(
                            f"Source ontology column '{SOURCE_ONTOLOGY}' not found in CSV headers."
                        )
                        return

                    for row in reader:
                        if processed_rows >= MAX_ROWS_TO_TEST:
                            logging.info(
                                f"Reached max rows to test ({MAX_ROWS_TO_TEST}). Stopping."
                            )
                            break

                        source_entity_value = row.get(SOURCE_ONTOLOGY)

                        # Check if source_entity_value is not None, not empty, and potentially filter out multi-values if needed
                        if source_entity_value and ";" not in source_entity_value:
                            logging.info(
                                f"\nProcessing row {reader.line_num}: {SOURCE_ONTOLOGY}={source_entity_value}"
                            )
                            try:
                                mapping_results = await executor.map_entity(
                                    relationship_id=RELATIONSHIP_ID_TO_TEST,
                                    source_entity=source_entity_value,
                                    source_ontology=SOURCE_ONTOLOGY,
                                )
                                logging.info(f" -> Mapping Result: {mapping_results}")

                                if not mapping_results:
                                    logging.warning(
                                        f"   No mapping found for {SOURCE_ONTOLOGY} {source_entity_value}."
                                    )
                                else:
                                    # Check cache (optional, for verification)
                                    # cache_entry = await executor.check_cache(...)
                                    # logging.info(f"   Cache check shows: {cache_entry}")
                                    pass

                            except Exception as e:
                                logging.error(
                                    f"   Error mapping {source_entity_value}: {e}",
                                    exc_info=True,
                                )

                            processed_rows += 1
                        elif source_entity_value and ";" in source_entity_value:
                            logging.warning(
                                f"Skipping row {reader.line_num}: Multiple {SOURCE_ONTOLOGY} IDs found ('{source_entity_value}'). Simple MVP handles single IDs."
                            )
                        # else: # No Pubchem ID or empty
                        #     # logging.debug(f"Skipping row {reader.line_num}: No {SOURCE_ONTOLOGY} ID found.")
                        #     pass

    except FileNotFoundError:
        logging.error(f"Source file not found: {ARIVALE_METADOLOMICS_FILE}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        logging.info("Database session implicitly closed if opened.")
        logging.info("Mapping test script finished.")


if __name__ == "__main__":
    # Ensure the script is run from the project root or adjust paths accordingly
    # Example: Run from /home/ubuntu/biomapper using `python scripts/test_ukbb_mapping.py`

    # Hacky way to adjust Python path if running script directly
    import sys

    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    asyncio.run(main())
