import asyncio
import os
import logging

import aiohttp
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from biomapper.db.models import MappingPath
from biomapper.mapping.relationships.executor import RelationshipMappingExecutor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration
# Example InChIKey for Water
INPUT_INCHIKEY = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
# Example InChIKey for Glucose (D-glucose, alpha-D-Glucopyranose representation)
# INPUT_INCHIKEY = "WQZGKKKJIJFFOK-GASJEMHNSA-N"
TARGET_ONTOLOGY = "CHEBI"  # Target ontology (e.g., CHEBI, PUBCHEM)
PATH_ID_TO_TEST = 30  # The specific mapping path ID to test (INCHIKEY -> CHEBI)


async def main():
    """Tests the execution of a UniChem mapping path."""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logging.error("DATABASE_URL not set in environment variables.")
        return

    engine = create_async_engine(database_url, echo=False)
    AsyncSessionFactory = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with AsyncSessionFactory() as db_session:
        async with aiohttp.ClientSession() as http_session:
            try:
                # Fetch the specific mapping path
                stmt = select(MappingPath).where(MappingPath.id == PATH_ID_TO_TEST)
                result = await db_session.execute(stmt)
                mapping_path: MappingPath = result.scalar_one_or_none()

                if not mapping_path:
                    logging.error(f"MappingPath with ID {PATH_ID_TO_TEST} not found.")
                    return

                if not mapping_path.path_steps:
                    logging.error(f"MappingPath {PATH_ID_TO_TEST} has empty steps.")
                    return

                if mapping_path.source_type.upper() != "INCHIKEY":
                    logging.error(
                        f"Path {PATH_ID_TO_TEST} source type '{mapping_path.source_type}' does not match expected 'INCHIKEY'."
                    )
                    return

                logging.info(
                    f"Testing path ID {PATH_ID_TO_TEST}: {mapping_path.source_type} -> {mapping_path.target_type}"
                )
                logging.info(
                    f"Input Entity ({mapping_path.source_type}): {INPUT_INCHIKEY}"
                )
                logging.info(f"Path Steps: {mapping_path.path_steps}")

                # Instantiate the executor
                executor = RelationshipMappingExecutor(db_session, http_session)

                # Execute the mapping
                output_entity, score = await executor.execute_mapping(
                    input_entity=INPUT_INCHIKEY, mapping_path=mapping_path
                )

                logging.info(f"Execution Result:")
                logging.info(
                    f"  Output Entity ({mapping_path.target_type}): {output_entity}"
                )
                logging.info(f"  Score: {score}")

            except Exception as e:
                logging.exception(f"An error occurred during testing: {e}")
            finally:
                await engine.dispose()  # Clean up the engine connection pool


if __name__ == "__main__":
    asyncio.run(main())
