"""
A test script to debug the metadata fields in entity mappings.
"""

import asyncio
import json
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from biomapper.db.cache_models import EntityMapping

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Create a test entry directly
    engine = create_async_engine(
        "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db"
    )
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # 1. First delete any test entries
    async with async_session() as session:
        await session.execute(
            text('DELETE FROM entity_mappings WHERE source_id = "TEST123"')
        )
        await session.commit()

    # 2. Create a test entry with metadata fields
    async with async_session() as session:
        test_mapping = EntityMapping(
            source_id="TEST123",
            source_type="UNIPROTKB_AC",
            target_id="TEST_TARGET",
            target_type="ARIVALE_PROTEIN_ID",
            confidence_score=0.95,
            hop_count=2,
            mapping_direction="forward",
            mapping_path_details=json.dumps({"path_id": 7, "path_log_id": 25}),
        )
        session.add(test_mapping)
        await session.commit()
        logger.info("Created test mapping with metadata fields")

    # 3. Verify the entry was created with metadata
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT id, source_id, target_id, confidence_score, hop_count, mapping_direction, mapping_path_details "
                'FROM entity_mappings WHERE source_id = "TEST123"'
            )
        )
        row = result.fetchone()
        if row:
            (
                id,
                source_id,
                target_id,
                confidence_score,
                hop_count,
                mapping_direction,
                mapping_path_details,
            ) = row
            logger.info(
                f"Retrieved test mapping: ID={id}, Source={source_id}, Target={target_id}"
            )
            logger.info(f"  Confidence Score: {confidence_score}")
            logger.info(f"  Hop Count: {hop_count}")
            logger.info(f"  Direction: {mapping_direction}")
            logger.info(f"  Path Details: {mapping_path_details}")
        else:
            logger.error("Test mapping not found!")

    # 4. Now try with the MappingExecutor (but we need to mock the client)
    # This would require more extensive changes to the code

    # 5. Check all metadata entries
    import sqlite3

    conn = sqlite3.connect("data/mapping_cache.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM entity_mappings WHERE confidence_score IS NOT NULL OR hop_count IS NOT NULL OR mapping_direction IS NOT NULL OR mapping_path_details IS NOT NULL"
    )
    count = cursor.fetchone()[0]
    logger.info(f"Entries with metadata: {count}")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
