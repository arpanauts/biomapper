#!/usr/bin/env python3
"""
Test script for explicit reverse mapping from Arivale_Protein_ID to UniProtKB_AC.

This script directly tests the "Arivale_to_UniProt_Direct" path that already exists
in the database, without relying on the bidirectional path finding mechanism.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import MappingPath, MappingPathStep, MappingResource
from biomapper.utils.config import CONFIG_DB_URL, CACHE_DB_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_reverse")

# Test data - use known Arivale IDs for testing
TEST_ARIVALE_IDS = [
    "INF_P01579",  # Interferon gamma
    "CVD2_P12104",  # Fatty acid-binding protein, intestinal
    "CAM_Q96KN2",  # HHIP-like protein 1
    "DEV_P78552",  # Interleukin-13
    "CAM_O00533",  # Neural cell adhesion molecule L1-like protein
    # Add more test IDs
    "NEX_Q8N474",  # Secreted frizzled-related protein 1
    "CVD2_P08253",  # 72 kDa type IV collagenase
    "IRE_Q92844",  # TRAF family member-associated NF-kappa-B activator
]


async def get_path_info(session: AsyncSession, path_name: str) -> Dict[str, Any]:
    """Get information about a mapping path by name."""
    # Query for mapping path
    path_stmt = select(MappingPath).where(MappingPath.name == path_name)
    path_result = await session.execute(path_stmt)
    path = path_result.scalar_one_or_none()

    if not path:
        logger.error(f"Path not found: {path_name}")
        return {}

    # Get steps
    steps_stmt = (
        select(MappingPathStep)
        .where(MappingPathStep.mapping_path_id == path.id)
        .order_by(MappingPathStep.step_order.asc())
    )
    steps_result = await session.execute(steps_stmt)
    steps = steps_result.scalars().all()

    # For each step, get the mapping resource
    resource_ids = [step.mapping_resource_id for step in steps]
    if resource_ids:
        resources_stmt = select(MappingResource).where(
            MappingResource.id.in_(resource_ids)
        )
        resources_result = await session.execute(resources_stmt)
        resources = resources_result.scalars().all()

        # Map resources by ID for quick lookup
        resource_map = {r.id: r for r in resources}

        # Get resource info
        resource_info = [
            {
                "id": step.mapping_resource_id,
                "name": resource_map[step.mapping_resource_id].name,
                "input_ontology": resource_map[
                    step.mapping_resource_id
                ].input_ontology_term,
                "output_ontology": resource_map[
                    step.mapping_resource_id
                ].output_ontology_term,
                "client_class": resource_map[
                    step.mapping_resource_id
                ].client_class_path,
            }
            for step in steps
            if step.mapping_resource_id in resource_map
        ]
    else:
        resource_info = []

    return {
        "id": path.id,
        "name": path.name,
        "source_type": path.source_type,
        "target_type": path.target_type,
        "description": path.description,
        "priority": path.priority,
        "steps": [
            {
                "step_order": step.step_order,
                "description": step.description,
            }
            for step in steps
        ],
        "resources": resource_info,
    }


async def test_explicit_mapping(
    executor: MappingExecutor,
    source_endpoint: str,
    target_endpoint: str,
    input_ids: List[str],
) -> None:
    """Execute mapping directly between endpoints."""
    logger.info(f"Testing explicit mapping: {source_endpoint} -> {target_endpoint}")
    logger.info(f"Input IDs: {input_ids}")

    # Execute mapping
    results = await executor.execute_mapping(
        source_endpoint_name=source_endpoint,
        target_endpoint_name=target_endpoint,
        input_data=input_ids,
        source_property_name="PrimaryIdentifier",
        target_property_name="PrimaryIdentifier",
        mapping_direction="reverse",  # Explicitly set direction
        try_reverse_mapping=False,  # Don't use bidirectional search
    )

    # Analyze results
    successful = sum(1 for v in results.values() if v is not None)
    logger.info(f"Results: {results}")
    logger.info(f"Summary: {successful}/{len(input_ids)} successful mappings")

    # Check database for metadata
    if successful > 0:
        logger.info("Checking database metadata for successful mappings")
        async with executor.get_cache_session() as cache_session:
            for source_id, target_ids in results.items():
                if target_ids is None or (
                    isinstance(target_ids, list) and not target_ids
                ):
                    continue

                target_id = (
                    target_ids[0] if isinstance(target_ids, list) else target_ids
                )

                from biomapper.db.cache_models import EntityMapping

                stmt = select(EntityMapping).where(
                    EntityMapping.source_id == source_id,
                    EntityMapping.target_id == target_id,
                )
                result = await cache_session.execute(stmt)
                mapping = result.scalar_one_or_none()

                if mapping:
                    logger.info(f"Mapping found for {source_id} -> {target_id}:")
                    logger.info(f"  Direction: {mapping.mapping_direction}")
                    logger.info(f"  Confidence Score: {mapping.confidence_score}")
                    logger.info(f"  Hop Count: {mapping.hop_count}")

                    if mapping.mapping_path_details:
                        try:
                            path_details = (
                                json.loads(mapping.mapping_path_details)
                                if isinstance(mapping.mapping_path_details, str)
                                else mapping.mapping_path_details
                            )
                            logger.info(f"  Path Details: {path_details}")
                        except json.JSONDecodeError:
                            logger.warning(
                                f"  Invalid JSON in mapping_path_details: {mapping.mapping_path_details}"
                            )
                else:
                    logger.warning(
                        f"No mapping found in database for {source_id} -> {target_id}"
                    )


async def main():
    """Main function."""
    logger.info("Testing explicit reverse mapping (Arivale -> UniProt)")

    # Initialize executor
    executor = MappingExecutor(
        metamapper_db_url=CONFIG_DB_URL,
        mapping_cache_db_url=CACHE_DB_URL,
    )

    # Create engine and session for metadata queries
    engine = create_async_engine(CONFIG_DB_URL)
    session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Get information about the reverse mapping path
    async with session_factory() as session:
        path_info = await get_path_info(session, "Arivale_to_UniProt_Direct")
        logger.info(f"Path Info: {json.dumps(path_info, indent=2)}")

    # Test mapping explicitly from Arivale to UniProt
    await test_explicit_mapping(
        executor,
        source_endpoint="Arivale_Protein",  # Source endpoint
        target_endpoint="UKBB_Protein",  # Target endpoint
        input_ids=TEST_ARIVALE_IDS,  # Test Arivale IDs
    )

    logger.info("Explicit reverse mapping test complete")


if __name__ == "__main__":
    asyncio.run(main())
