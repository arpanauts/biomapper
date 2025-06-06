#!/usr/bin/env python
"""
Test script for UKBB to HPA protein mapping pipeline with cache bypass.
This script tests the mapping with cache disabled to help diagnose issues.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import MappingStrategyStep
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get DATA_DIR from environment
DATA_DIR = os.environ.get('DATA_DIR', '/home/ubuntu/biomapper/data')
logger.info(f"Using DATA_DIR: {DATA_DIR}")


async def test_pipeline_with_cache_bypass():
    """Test the UKBB to HPA protein mapping pipeline with cache bypassed."""
    
    # Database URLs
    metamapper_url = f"sqlite+aiosqlite:///{DATA_DIR}/metamapper.db"
    cache_url = f"sqlite+aiosqlite:///{DATA_DIR}/mapping_cache.db"
    
    # Create engines
    metamapper_engine = create_async_engine(metamapper_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        metamapper_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Initialize mapping executor
    executor = MappingExecutor(
        metamapper_db_url=metamapper_url,
        mapping_cache_db_url=cache_url,
        enable_metrics=False
    )
    
    # Test data - using UniProt IDs known to be in HPA
    test_ids = [
        "Q86V81",  # ALS2 - should be in HPA
        "P05067",  # APP - should be in HPA
        "P10636",  # MAPT/TAU - should be in HPA
        "Q9NZC2",  # TREM2 - should be in HPA
        "O00555",  # CACNA1A - should be in HPA
    ]
    
    logger.info(f"Testing with {len(test_ids)} UniProt IDs: {test_ids}")
    
    # Get the strategy steps
    async with AsyncSessionLocal() as session:
        # Load the UKBB_TO_HPA_PROTEIN_PIPELINE strategy
        stmt = select(MappingStrategyStep).where(
            MappingStrategyStep.strategy_name == "UKBB_TO_HPA_PROTEIN_PIPELINE"
        ).order_by(MappingStrategyStep.step_order)
        
        result = await session.execute(stmt)
        steps = result.scalars().all()
        
        if not steps:
            logger.error("No strategy steps found for UKBB_TO_HPA_PROTEIN_PIPELINE")
            return
        
        logger.info(f"Found {len(steps)} steps in the strategy")
        
        # Execute each step
        current_ids = test_ids
        current_ontology = "UniProt"
        
        for step in steps:
            logger.info(f"\n{'='*60}")
            logger.info(f"Executing step {step.step_order}: {step.step_name}")
            logger.info(f"Action: {step.action_type}")
            logger.info(f"Input count: {len(current_ids)}")
            
            if step.action_type == "EXECUTE_MAPPING_PATH":
                # For the RESOLVE_UNIPROT_HISTORY step, add cache bypass
                if step.step_name == "S2_RESOLVE_UNIPROT_HISTORY":
                    logger.info("*** BYPASSING CACHE for UniProtHistoricalResolverClient ***")
                    # We need to modify the executor to pass config to the client
                    # For now, let's add a temporary hack to the executor
                    
                # Get the action handler
                from biomapper.core.strategy_actions.execute_mapping_path import ExecuteMappingPathAction
                action = ExecuteMappingPathAction(session)
                
                # Create context with mapping executor
                context = {
                    'mapping_executor': executor,
                    'batch_size': 250,
                    'min_confidence': 0.0
                }
                
                # If this is the RESOLVE_UNIPROT_HISTORY step, we need to pass the bypass_cache config
                # This requires modifying the executor to accept and pass through client config
                if step.step_name == "S2_RESOLVE_UNIPROT_HISTORY":
                    # Temporary solution: directly modify the client's behavior
                    # We'll need to implement a proper solution to pass config through
                    logger.warning("Cache bypass not fully implemented - results may still come from cache")
                
                # Execute the action
                result = await action.execute(
                    current_identifiers=current_ids,
                    current_ontology_type=current_ontology,
                    action_params=step.parameters,
                    source_endpoint=None,  # Not used in this action
                    target_endpoint=None,  # Not used in this action
                    context=context
                )
                
                # Update current state
                current_ids = result.get('output_identifiers', [])
                current_ontology = result.get('output_ontology_type', current_ontology)
                
                logger.info(f"Output count: {len(current_ids)}")
                logger.info(f"Output ontology: {current_ontology}")
                
                # Log details
                details = result.get('details', {})
                logger.info(f"Total mapped: {details.get('total_mapped', 0)}")
                logger.info(f"Total unmapped: {details.get('total_unmapped', 0)}")
                
            elif step.action_type == "FILTER_BY_TARGET_PRESENCE":
                # Get the action handler
                from biomapper.core.strategy_actions.filter_by_target_presence import FilterByTargetPresenceAction
                action = FilterByTargetPresenceAction(session)
                
                # Execute the action
                result = await action.execute(
                    current_identifiers=current_ids,
                    current_ontology_type=current_ontology,
                    action_params=step.parameters,
                    source_endpoint=None,
                    target_endpoint=None,
                    context={}
                )
                
                # Update current state
                current_ids = result.get('output_identifiers', [])
                
                logger.info(f"Output count: {len(current_ids)}")
                logger.info(f"Filtered out: {len(test_ids) - len(current_ids)} identifiers")
        
        logger.info(f"\n{'='*60}")
        logger.info("Pipeline execution complete")
        logger.info(f"Final output count: {len(current_ids)}")
        if current_ids:
            logger.info(f"Final mapped IDs: {current_ids[:10]}...")  # Show first 10


async def main():
    """Main entry point."""
    try:
        await test_pipeline_with_cache_bypass()
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())