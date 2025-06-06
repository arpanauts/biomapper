"""
Script to test the new execute_strategy method for YAML-defined strategies.

This script demonstrates:
1. Testing the new execute_strategy method with the UKBB_TO_HPA_PROTEIN_PIPELINE strategy
2. Verifying the MappingResultBundle return format
3. Testing error handling for non-existent and inactive strategies
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


async def test_execute_strategy():
    """Test the new execute_strategy method."""
    
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
        
        # Execute the strategy using the new method
        result_bundle = await executor.execute_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            initial_identifiers=test_identifiers,
            source_ontology_type="HGNC_SYMBOL",
            target_ontology_type="HPA_SYMBOL",
            entity_type="protein"
        )
        
        # Display results from MappingResultBundle
        logger.info("\n=== Execute Strategy Results ===")
        
        result_dict = result_bundle.to_dict()
        
        logger.info(f"Strategy: {result_dict['strategy_name']}")
        logger.info(f"Execution Status: {result_dict['execution_status']}")
        logger.info(f"Initial identifiers count: {result_dict['initial_identifiers_count']}")
        logger.info(f"Final identifiers count: {result_dict['final_identifiers_count']}")
        logger.info(f"Source ontology type: {result_dict['source_ontology_type']}")
        logger.info(f"Target ontology type: {result_dict['target_ontology_type']}")
        logger.info(f"Current ontology type: {result_dict['current_ontology_type']}")
        logger.info(f"Total steps: {result_dict['total_steps']}")
        logger.info(f"Completed steps: {result_dict['completed_steps']}")
        logger.info(f"Failed steps: {result_dict['failed_steps']}")
        
        if result_dict['duration_seconds']:
            logger.info(f"Duration: {result_dict['duration_seconds']:.2f} seconds")
        
        # Display step results
        logger.info("\n=== Step Results ===")
        for step in result_dict['step_results']:
            logger.info(f"\nStep: {step['step_id']}")
            logger.info(f"  Description: {step['description']}")
            logger.info(f"  Action: {step['action_type']}")
            logger.info(f"  Status: {step['status']}")
            logger.info(f"  Input count: {step['input_count']}")
            logger.info(f"  Output count: {step['output_count']}")
            if step['details']:
                logger.info(f"  Details: {step['details']}")
            if step['error']:
                logger.error(f"  Error: {step['error']}")
        
        # Display provenance
        logger.info("\n=== Provenance Summary ===")
        for prov in result_dict['provenance'][:3]:  # Show first 3 provenance entries
            logger.info(f"\nStep: {prov['step_id']}")
            logger.info(f"  Action: {prov['action_type']}")
            logger.info(f"  Input ontology: {prov['input_ontology_type']}")
            logger.info(f"  Output ontology: {prov['output_ontology_type']}")
            logger.info(f"  Sample input IDs: {prov['input_identifiers']}")
            logger.info(f"  Sample output IDs: {prov['output_identifiers']}")
        
        # Display final identifiers sample
        logger.info("\n=== Final Identifiers Sample ===")
        logger.info(f"First 10 final identifiers: {result_dict['final_identifiers'][:10]}")
        
        # Test error handling - non-existent strategy
        logger.info("\n=== Testing error handling - non-existent strategy ===")
        try:
            await executor.execute_strategy(
                strategy_name="NON_EXISTENT_STRATEGY",
                initial_identifiers=["TEST"],
                source_ontology_type="HGNC_SYMBOL",
                target_ontology_type="HPA_SYMBOL"
            )
        except Exception as e:
            logger.info(f"Expected StrategyNotFoundError caught: {type(e).__name__}: {e}")
        
        # Test error handling - empty identifiers
        logger.info("\n=== Testing with empty identifiers ===")
        result_bundle_empty = await executor.execute_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            initial_identifiers=[],
            source_ontology_type="HGNC_SYMBOL",
            target_ontology_type="HPA_SYMBOL"
        )
        logger.info(f"Result with empty identifiers - Status: {result_bundle_empty.execution_status}")
        logger.info(f"Final count: {len(result_bundle_empty.current_identifiers)}")
        
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
            logger.info(f"  Is active: {strategy.is_active}")
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
                logger.info(f"       Description: {step.description}")
                logger.info(f"       Parameters: {step.action_parameters}")
        else:
            logger.warning("Strategy UKBB_TO_HPA_PROTEIN_PIPELINE not found in database!")
            logger.warning("Please run: python scripts/populate_metamapper_db.py")


if __name__ == "__main__":
    logger.info("Starting Execute Strategy Test")
    
    # First check if the database is populated
    asyncio.run(check_database_state())
    
    # Then run the test
    logger.info("\n" + "="*50)
    asyncio.run(test_execute_strategy())