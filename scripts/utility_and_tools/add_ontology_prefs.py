import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from biomapper.db.models import Base, Endpoint, OntologyPreference
from biomapper.utils.config import CONFIG_DB_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PREFERENCES_TO_ADD = [
    {
        "endpoint_name": "UKBB_Protein",
        "endpoint_id": 3,
        "ontology_name": "UNIPROT_NAME",  # UKBB uses protein names as primary ID
        "priority": 0,
    },
    {
        "endpoint_name": "Arivale_Protein",
        "endpoint_id": 4,
        "ontology_name": "UNIPROTKB_AC",  # Arivale uses UniProt AC as primary ID
        "priority": 0,
    },
]


async def add_ontology_preferences():
    """Adds predefined OntologyPreference entries to the database."""
    engine = create_async_engine(CONFIG_DB_URL, echo=False)
    async_session_factory = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session_factory() as session:
        async with session.begin():
            added_count = 0
            skipped_count = 0
            error_count = 0

            for pref_data in PREFERENCES_TO_ADD:
                endpoint_id = pref_data["endpoint_id"]
                ontology_name = pref_data["ontology_name"]
                endpoint_name = pref_data["endpoint_name"]

                # Check if endpoint exists (optional but good practice)
                endpoint_check = await session.get(Endpoint, endpoint_id)
                if not endpoint_check or endpoint_check.name != endpoint_name:
                    logger.error(
                        f"Endpoint mismatch or not found: ID {endpoint_id}, Expected Name '{endpoint_name}'. Skipping preference."
                    )
                    error_count += 1
                    continue

                # Check if preference already exists for the endpoint
                stmt = (
                    select(OntologyPreference)
                    .where(OntologyPreference.endpoint_id == endpoint_id)
                    .order_by(OntologyPreference.priority.asc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                existing_pref = result.scalar_one_or_none()

                if existing_pref:
                    if existing_pref.ontology_name == ontology_name:
                        logger.info(
                            f"Preference already exists for {endpoint_name} -> {ontology_name}. Skipping."
                        )
                        skipped_count += 1
                    else:
                        logger.warning(
                            f"Existing preference found for {endpoint_name} but with different ontology: {existing_pref.ontology_name}. Consider manual review."
                        )
                        # Decide whether to update or skip based on requirements
                        skipped_count += 1  # Skipping for now
                else:
                    # Create and add new preference
                    new_pref = OntologyPreference(
                        endpoint_id=endpoint_id,
                        ontology_name=ontology_name,
                        priority=pref_data["priority"],
                    )
                    session.add(new_pref)
                    added_count += 1
                    logger.info(
                        f"Adding preference: {endpoint_name} -> {ontology_name}"
                    )

        logger.info(
            f"Finished adding preferences. Added: {added_count}, Skipped: {skipped_count}, Errors: {error_count}"
        )


async def main():
    await add_ontology_preferences()


if __name__ == "__main__":
    asyncio.run(main())
