# scripts/check_unichem_paths.py
import asyncio
import json
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Add project root to path to allow importing biomapper modules
import sys

# Assuming the script is run from the project root or the scripts directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from biomapper.db.models import MappingPath, Base  # noqa: E402


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load .env file and get DATABASE_URL from environment
load_dotenv()  # Load .env file if present
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable not set or .env file not found."
    )

# Database session management
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionFactory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_paths():
    """
    Queries the database for MappingPaths and checks if any use UniChem (resource_id 10).
    """
    db_url = DATABASE_URL
    logger.info(f"Connecting to database: {db_url}")
    engine = create_async_engine(db_url)
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        logger.info("Querying all MappingPaths...")
        stmt = select(MappingPath)
        result = await session.execute(stmt)
        all_paths = result.scalars().all()
        logger.info(f"Found {len(all_paths)} total mapping paths.")

        valid_paths_details = []  # List to store details of valid paths

        for path in all_paths:
            try:
                # Use the steps property which includes JSON decoding and basic validation
                steps = path.steps
                if steps:  # Check if steps list is not empty after decoding
                    valid_paths_details.append(
                        {
                            "id": path.id,
                            "source_type": path.source_type,
                            "target_type": path.target_type,
                            "steps": steps,  # Store the decoded steps
                        }
                    )
                else:
                    logger.warning(
                        f"Path ID {path.id} has empty 'steps' list after decoding. Skipping."
                    )
            except Exception as e:  # Catch potential errors during access/decoding
                logger.warning(
                    f"Path ID {path.id} encountered error accessing/decoding 'steps': {e}. Skipping."
                )

    # Log the details of all valid paths found
    if valid_paths_details:
        logger.info("\n--- Valid Mapping Paths Found ---")
        for p in valid_paths_details:
            steps_str = json.dumps(
                p["steps"]
            )  # Convert steps back to JSON string for logging
            logger.info(
                f"  ID: {p['id']}, Source: {p['source_type']}, Target: {p['target_type']}, Steps: {steps_str}"
            )
        logger.info("---------------------------------")
    else:
        logger.info("\n--- No valid mapping paths found ---")


async def main():
    # Optional: Initialize DB if needed (usually done elsewhere)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    await check_paths()


if __name__ == "__main__":
    asyncio.run(main())
