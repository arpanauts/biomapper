"""
Script to test the UKBB to HPA protein mapping using YAML-defined strategy.

This script demonstrates:
1. Populating the metamapper database with protein configurations
2. Executing the UKBB_TO_HPA_PROTEIN_PIPELINE strategy
3. Displaying the results
"""

import asyncio
import logging
import traceback
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_yaml_strategy():
    """Test the YAML-based mapping strategy."""
    
    executor = None  # Initialize to None for finally block
    
    try:
        # Create MappingExecutor using the async factory method
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        logger.info("MappingExecutor created successfully")
        
        # Test UKBB protein assay IDs
        test_identifiers = [
            "ADAMTS13",   # ADAM metallopeptidase with thrombospondin type 1 motif 13
            "ALB",        # Albumin
            "APOA1",      # Apolipoprotein A1
            "C3",         # Complement C3
            "CRP",        # C-reactive protein
            "IL6",        # Interleukin 6
            "TNF",        # Tumor necrosis factor
            "VEGFA"       # Vascular endothelial growth factor A
        ]
        
        logger.info(f"Testing with {len(test_identifiers)} UKBB protein identifiers")
        
        # Execute the YAML strategy
        result = await executor.execute_yaml_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            source_endpoint_name="UKBB_PROTEIN",
            target_endpoint_name="HPA_OSP_PROTEIN",
            input_identifiers=test_identifiers,
            use_cache=False,
            progress_callback=lambda curr, total, status: logger.info(f"Progress: {curr}/{total} - {status}")
        )
        
        # Display results
        logger.info("\n=== YAML Strategy Execution Results ===")
        
        summary = result.get("summary", {})
        logger.info(f"Strategy: {summary.get('strategy_name')}")
        logger.info(f"Total input: {summary.get('total_input')}")
        logger.info(f"Total mapped: {summary.get('total_mapped')}")
        logger.info(f"Total unmapped: {summary.get('total_unmapped')}")
        logger.info(f"Steps executed: {summary.get('steps_executed')}")
        
        # Display step results
        logger.info("\n=== Step Results ===")
        for step in summary.get("step_results", []):
            logger.info(f"\nStep: {step.get('step_id')}")
            logger.info(f"  Action: {step.get('action_type')}")
            logger.info(f"  Success: {step.get('success')}")
            logger.info(f"  Input count: {step.get('input_count')}")
            logger.info(f"  Output count: {step.get('output_count')}")
            if step.get('details'):
                logger.info(f"  Details: {step.get('details')}")
            if step.get('error'):
                logger.error(f"  Error: {step.get('error')}")
        
        # Display individual mapping results
        logger.info("\n=== Individual Mapping Results ===")
        results = result.get("results", {})
        for source_id, mapping in results.items():
            mapped_value = mapping.get('mapped_value', 'None')
            confidence = mapping.get('confidence', 0.0)
            error = mapping.get('error', '')
            
            if mapped_value and mapped_value != 'None':
                logger.info(f"{source_id} -> {mapped_value} (confidence: {confidence:.2f})")
            else:
                logger.warning(f"{source_id} -> No mapping found. {error}")
        
        # Test with non-existent strategy (should fail)
        logger.info("\n=== Testing error handling ===")
        try:
            await executor.execute_yaml_strategy(
                strategy_name="NON_EXISTENT_STRATEGY",
                source_endpoint_name="UKBB_PROTEIN",
                target_endpoint_name="HPA_OSP_PROTEIN",
                input_identifiers=["TEST"],
                use_cache=False
            )
        except Exception as e:
            logger.info(f"Expected error caught: {e}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        logger.error(traceback.format_exc())
    finally:
        if executor:
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


async def check_database_state():
    """Check if the strategy is properly loaded in the database."""
    from biomapper.db.session import get_db_manager
    from biomapper.config import settings
    from biomapper.db.models import MappingStrategy, MappingStrategyStep
    from sqlalchemy import select
    
    db_manager = get_db_manager(db_url=settings.metamapper_db_url)
    
    async with await db_manager.create_async_session() as session:
        # Check if strategy exists
        stmt = select(MappingStrategy).where(
            MappingStrategy.name == "UKBB_TO_HPA_PROTEIN_PIPELINE"
        )
        result = await session.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if strategy:
            logger.info(f"Strategy found: {strategy.name}")
            logger.info(f"  Entity type: {strategy.entity_type}")
            logger.info(f"  Description: {strategy.description}")
            logger.info(f"  Source ontology: {strategy.default_source_ontology_type}")
            logger.info(f"  Target ontology: {strategy.default_target_ontology_type}")
            
            # Get steps
            stmt = (
                select(MappingStrategyStep)
                .where(MappingStrategyStep.strategy_id == strategy.id)
                .order_by(MappingStrategyStep.step_order)
            )
            result = await session.execute(stmt)
            steps = result.scalars().all()
            
            logger.info(f"\n  Steps ({len(steps)}):")
            for step in steps:
                logger.info(f"    {step.step_order}. {step.step_id}: {step.action_type}")
                logger.info(f"       {step.description}")
        else:
            logger.warning("Strategy UKBB_TO_HPA_PROTEIN_PIPELINE not found in database!")
            logger.warning("Please run: python scripts/populate_metamapper_db.py")


if __name__ == "__main__":
    logger.info("Starting YAML Strategy Test")
    
    # First check if the database is populated
    asyncio.run(check_database_state())
    
    # Then run the test
    logger.info("\n" + "="*50)
    asyncio.run(test_yaml_strategy())