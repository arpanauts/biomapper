#!/usr/bin/env python3
"""
Script to update existing records in entity_mappings table with proper metadata.

This script will:
1. Find all records in entity_mappings that have null values for the new metadata fields
2. Determine appropriate values for confidence_score, hop_count, mapping_direction, and mapping_path_details
3. Update the records in the database
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import sqlalchemy as sa
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from biomapper.db.cache_models import EntityMapping
from biomapper.db.models import MappingPath, MappingPathStep, MappingResource
from biomapper.utils.config import CONFIG_DB_URL, CACHE_DB_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("update_metadata")

# Constants
DEFAULT_CONFIDENCE = 0.8
DEFAULT_HOP_COUNT = 1


async def get_mapping_path_details(
    meta_session: AsyncSession, source_type: str, target_type: str
) -> Dict[str, Any]:
    """
    Find the mapping path for the given source and target types.

    Args:
        meta_session: SQLAlchemy session for the metamapper database
        source_type: Source ontology type
        target_type: Target ontology type

    Returns:
        Dictionary with path details
    """
    # Query for mapping path
    path_stmt = (
        select(MappingPath)
        .where(
            MappingPath.source_type == source_type,
            MappingPath.target_type == target_type,
        )
        .order_by(MappingPath.priority.asc())
        .limit(1)
    )
    path_result = await meta_session.execute(path_stmt)
    path = path_result.scalar_one_or_none()

    if not path:
        logger.warning(f"No mapping path found for {source_type} -> {target_type}")
        return {
            "hop_count": DEFAULT_HOP_COUNT,
            "path_id": None,
            "path_name": "unknown",
            "resource_types": [],
            "client_identifiers": [],
        }

    # Get steps
    steps_stmt = (
        select(MappingPathStep)
        .where(MappingPathStep.mapping_path_id == path.id)
        .order_by(MappingPathStep.step_order.asc())
    )
    steps_result = await meta_session.execute(steps_stmt)
    steps = steps_result.scalars().all()

    hop_count = len(steps)

    # For each step, get the mapping resource
    resource_ids = [step.mapping_resource_id for step in steps]
    if resource_ids:
        resources_stmt = select(MappingResource).where(
            MappingResource.id.in_(resource_ids)
        )
        resources_result = await meta_session.execute(resources_stmt)
        resources = resources_result.scalars().all()

        # Map resources by ID for quick lookup
        resource_map = {r.id: r for r in resources}

        # Extract resource types and client identifiers
        resource_types = [
            resource_map[step.mapping_resource_id].resource_type
            for step in steps
            if step.mapping_resource_id in resource_map
        ]
        client_identifiers = [
            resource_map[step.mapping_resource_id].name
            for step in steps
            if step.mapping_resource_id in resource_map
        ]
    else:
        resource_types = []
        client_identifiers = []

    return {
        "hop_count": hop_count,
        "path_id": path.id,
        "path_name": path.name,
        "resource_types": resource_types,
        "client_identifiers": client_identifiers,
    }


async def get_mapping_direction(
    meta_session: AsyncSession, source_type: str, target_type: str
) -> str:
    """
    Determine the mapping direction based on the source and target types.

    Args:
        meta_session: SQLAlchemy session for the metamapper database
        source_type: Source ontology type
        target_type: Target ontology type

    Returns:
        "forward" or "reverse"
    """
    # Check if there's a direct path (forward)
    forward_path_stmt = (
        select(MappingPath)
        .where(
            MappingPath.source_type == source_type,
            MappingPath.target_type == target_type,
        )
        .limit(1)
    )
    forward_result = await meta_session.execute(forward_path_stmt)
    forward_path = forward_result.scalar_one_or_none()

    if forward_path:
        return "forward"

    # Check if there's a reverse path
    reverse_path_stmt = (
        select(MappingPath)
        .where(
            MappingPath.source_type == target_type,
            MappingPath.target_type == source_type,
        )
        .limit(1)
    )
    reverse_result = await meta_session.execute(reverse_path_stmt)
    reverse_path = reverse_result.scalar_one_or_none()

    if reverse_path:
        return "reverse"

    # If neither found, assume forward
    return "forward"


async def update_entity_mapping_metadata(
    cache_db_url: str, metamapper_db_url: str
) -> None:
    """
    Update entity_mappings records with proper metadata values.

    Args:
        cache_db_url: URL for the cache database
        metamapper_db_url: URL for the metamapper database
    """
    # Create database connections
    meta_engine = create_async_engine(metamapper_db_url)
    meta_session_factory = sessionmaker(
        meta_engine, expire_on_commit=False, class_=AsyncSession
    )

    cache_engine = create_async_engine(cache_db_url)
    cache_session_factory = sessionmaker(
        cache_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Find all records with null metadata fields
    async with cache_session_factory() as cache_session:
        query = select(EntityMapping).where(
            sa.or_(
                EntityMapping.confidence_score.is_(None),
                EntityMapping.hop_count.is_(None),
                EntityMapping.mapping_direction.is_(None),
                EntityMapping.mapping_path_details.is_(None),
            )
        )
        result = await cache_session.execute(query)
        records = result.scalars().all()

        logger.info(f"Found {len(records)} records with missing metadata")

        if not records:
            logger.info("No records need updating.")
            return

        # Process records in batches
        batch_size = 100
        updated_count = 0

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            async with meta_session_factory() as meta_session:
                for record in batch:
                    # Determine mapping direction
                    direction = await get_mapping_direction(
                        meta_session, record.source_type, record.target_type
                    )

                    # Get path details
                    source_type = record.source_type
                    target_type = record.target_type

                    if direction == "reverse":
                        # For reverse mapping, swap source and target for path lookup
                        source_type, target_type = target_type, source_type

                    path_details = await get_mapping_path_details(
                        meta_session, source_type, target_type
                    )

                    # Set confidence score
                    # - Base score (0.7-0.8)
                    # - Higher for direct paths (fewer hops)
                    # - Small penalty for reverse mappings
                    hop_count = path_details.get("hop_count", DEFAULT_HOP_COUNT)

                    confidence_score = 0.8  # Base score

                    # Adjust for hop count
                    if hop_count <= 1:
                        confidence_score += 0.1  # Direct mapping bonus
                    elif hop_count == 2:
                        confidence_score += 0.05  # Small bonus for 2-hop
                    else:
                        # Increasing penalty for longer paths
                        confidence_score -= 0.05 * (hop_count - 2)

                    # Small penalty for reverse mappings
                    if direction == "reverse":
                        confidence_score -= 0.05

                    # Ensure within bounds
                    confidence_score = min(1.0, max(0.1, confidence_score))

                    # Create mapping_path_details JSON
                    mapping_path_details = {
                        "confidence_score": confidence_score,
                        "hop_count": hop_count,
                        "mapping_direction": direction,
                        "path_details": path_details,
                    }

                    # Update the record
                    record.confidence_score = confidence_score
                    record.hop_count = hop_count
                    record.mapping_direction = direction
                    record.mapping_path_details = json.dumps(mapping_path_details)
                    record.last_updated = datetime.now(timezone.utc)

                    updated_count += 1

                    if updated_count % 100 == 0:
                        logger.info(f"Updated {updated_count} records")

            # Commit the batch
            await cache_session.commit()

        logger.info(f"Updated {updated_count} records in total")


async def main():
    """Main function."""
    logger.info("Starting metadata update")

    # Get database URLs
    cache_db_url = CACHE_DB_URL
    metamapper_db_url = CONFIG_DB_URL

    logger.info(f"Cache DB URL: {cache_db_url}")
    logger.info(f"Metamapper DB URL: {metamapper_db_url}")

    # Update metadata
    await update_entity_mapping_metadata(cache_db_url, metamapper_db_url)

    logger.info("Metadata update complete")


if __name__ == "__main__":
    asyncio.run(main())
