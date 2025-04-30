"""
A simplified test to debug issues with the mapping executor's caching of metadata fields.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from biomapper.db.cache_models import (
    EntityMapping,
    PathExecutionLog,
    PathExecutionStatus,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Set up database connection
    engine = create_async_engine(
        "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db"
    )
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Create a test path execution log
    async with async_session() as session:
        # Create a path execution log
        path_log = PathExecutionLog(
            relationship_mapping_path_id=7,  # Using an existing path ID
            source_entity_id="TEST_SOURCE",
            source_entity_type="UNIPROTKB_AC",
            start_time=datetime.now(timezone.utc),
            status=PathExecutionStatus.PENDING,
        )
        session.add(path_log)
        await session.flush()
        path_log_id = path_log.id
        logger.info(f"Created path execution log with ID: {path_log_id}")

        # Now pretend we're in the _cache_results method
        now = datetime.now(timezone.utc)
        source_id = "TEST_SOURCE2"
        source_ontology = "UNIPROTKB_AC"
        target_ontology = "ARIVALE_PROTEIN_ID"
        target_id_str = "TEST_TARGET2"
        processed_target_ids = ["TEST_TARGET2"]

        # First, delete any existing mappings for this test
        await session.execute(
            text('DELETE FROM entity_mappings WHERE source_id = "TEST_SOURCE2"')
        )

        # Create a new mapping with all metadata fields
        mapping = EntityMapping(
            source_id=source_id,
            source_type=source_ontology,
            target_id=target_id_str,
            target_type=target_ontology,
            last_updated=now,
            # Add new metadata fields explicitly
            confidence_score=1.0
            if len(processed_target_ids) == 1
            else 0.8,  # Default confidence
            hop_count=path_log.relationship_mapping_path_id,  # This is the path ID
            mapping_path_details=json.dumps(
                {
                    "path_log_id": path_log.id,
                    "path_id": path_log.relationship_mapping_path_id,
                }
            ),
            mapping_direction="forward",  # Default direction
        )

        # Add the mapping to the session
        session.add(mapping)
        await session.commit()
        logger.info("Created test mapping with metadata fields")

    # Verify the mapping was created with metadata
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT id, source_id, target_id, confidence_score, hop_count, mapping_direction, mapping_path_details "
                'FROM entity_mappings WHERE source_id = "TEST_SOURCE2"'
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

    # Check all metadata entries
    import sqlite3

    conn = sqlite3.connect("data/mapping_cache.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM entity_mappings WHERE confidence_score IS NOT NULL OR hop_count IS NOT NULL OR mapping_direction IS NOT NULL OR mapping_path_details IS NOT NULL"
    )
    count = cursor.fetchone()[0]
    logger.info(f"Total entries with metadata: {count}")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
