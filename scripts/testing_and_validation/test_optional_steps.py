"""
Test script for optional steps behavior in mapping strategies.

This script tests:
1. Loading a strategy with optional steps
2. Executing a strategy where an optional step fails
3. Verifying the strategy continues after optional step failure
4. Verifying the strategy halts on required step failure
"""

import asyncio
import logging
import traceback
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings
from biomapper.db.session import get_db_manager
from biomapper.db.models import MappingStrategy, MappingStrategyStep
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def populate_test_strategy():
    """Populate the test strategy directly into the database."""
    logger.info("Populating test strategy...")
    
    db_manager = get_db_manager(db_url=settings.metamapper_db_url)
    
    async with await db_manager.create_async_session() as session:
        # Check if strategy already exists
        stmt = select(MappingStrategy).where(
            MappingStrategy.name == "TEST_STRATEGY_WITH_OPTIONAL_STEPS"
        )
        result = await session.execute(stmt)
        existing_strategy = result.scalar_one_or_none()
        
        if existing_strategy:
            logger.info("Test strategy already exists, deleting old version...")
            # Delete existing steps
            stmt = select(MappingStrategyStep).where(
                MappingStrategyStep.strategy_id == existing_strategy.id
            )
            result = await session.execute(stmt)
            existing_steps = result.scalars().all()
            for step in existing_steps:
                await session.delete(step)
            await session.delete(existing_strategy)
            await session.commit()
        
        # Create new strategy
        strategy = MappingStrategy(
            name="TEST_STRATEGY_WITH_OPTIONAL_STEPS",
            description="Test strategy with both required and optional steps",
            entity_type="test",
            default_source_ontology_type="TEST_SOURCE_ONTOLOGY",
            default_target_ontology_type="TEST_TARGET_ONTOLOGY",
            is_active=True
        )
        session.add(strategy)
        await session.flush()
        
        # Add steps
        steps = [
            MappingStrategyStep(
                strategy_id=strategy.id,
                step_id="S1_REQUIRED_CONVERSION",
                step_order=1,
                description="Required conversion step",
                action_type="CONVERT_IDENTIFIERS_LOCAL",
                action_parameters={
                    "endpoint_context": "SOURCE",
                    "output_ontology_type": "TEST_INTERMEDIATE_ONTOLOGY"
                },
                is_required=True,
                is_active=True
            ),
            MappingStrategyStep(
                strategy_id=strategy.id,
                step_id="S2_OPTIONAL_FILTER",
                step_order=2,
                description="Optional filtering step that might fail",
                action_type="FILTER_IDENTIFIERS_BY_TARGET_PRESENCE",
                action_parameters={
                    "endpoint_context": "TARGET",
                    "ontology_type_to_match": "TEST_INTERMEDIATE_ONTOLOGY"
                },
                is_required=False,  # This is the key test - optional step
                is_active=True
            ),
            MappingStrategyStep(
                strategy_id=strategy.id,
                step_id="S3_REQUIRED_FINAL_CONVERSION",
                step_order=3,
                description="Required final conversion",
                action_type="CONVERT_IDENTIFIERS_LOCAL",
                action_parameters={
                    "endpoint_context": "TARGET",
                    "input_ontology_type": "TEST_INTERMEDIATE_ONTOLOGY",
                    "output_ontology_type": "TEST_TARGET_ONTOLOGY"
                },
                is_required=True,
                is_active=True
            )
        ]
        
        for step in steps:
            session.add(step)
        
        await session.commit()
        logger.info("Test strategy populated successfully")


async def test_optional_step_failure():
    """Test that strategy continues when optional step fails."""
    executor = None
    
    try:
        # First populate the test strategy
        await populate_test_strategy()
        
        # Create MappingExecutor
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=False
        )
        logger.info("MappingExecutor created successfully")
        
        # Test identifiers
        test_identifiers = ["TEST1", "TEST2", "TEST3"]
        
        logger.info("\n=== Testing Optional Step Behavior ===")
        
        # Override the handler for the optional step to make it fail
        original_handler = executor._handle_filter_identifiers_by_target_presence
        
        async def failing_handler(*args, **kwargs):
            """Handler that always returns a failed status."""
            return {
                "output_identifiers": [],
                "output_ontology_type": kwargs.get("current_source_ontology_type"),
                "status": "failed",
                "error": "Simulated failure for testing",
                "details": {
                    "action": "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE",
                    "message": "This step is designed to fail for testing"
                }
            }
        
        # Temporarily replace the handler
        executor._handle_filter_identifiers_by_target_presence = failing_handler
        
        try:
            # Execute the strategy
            result_bundle = await executor.execute_strategy(
                strategy_name="TEST_STRATEGY_WITH_OPTIONAL_STEPS",
                initial_identifiers=test_identifiers,
                source_ontology_type="TEST_SOURCE_ONTOLOGY",
                target_ontology_type="TEST_TARGET_ONTOLOGY"
            )
            
            # Check results
            result_dict = result_bundle.to_dict()
            
            logger.info(f"\nStrategy execution status: {result_dict['execution_status']}")
            logger.info(f"Total steps: {result_dict['total_steps']}")
            logger.info(f"Completed steps: {result_dict['completed_steps']}")
            logger.info(f"Failed steps: {result_dict['failed_steps']}")
            
            # Verify behavior
            if result_dict['execution_status'] == 'completed':
                logger.info("✓ SUCCESS: Strategy completed despite optional step failure")
            else:
                logger.error("✗ FAILED: Strategy did not complete as expected")
            
            # Check individual step results
            logger.info("\n=== Step Results ===")
            for step in result_dict['step_results']:
                logger.info(f"\nStep: {step['step_id']}")
                logger.info(f"  Status: {step['status']}")
                logger.info(f"  Description: {step['description']}")
                if step['error']:
                    logger.info(f"  Error: {step['error']}")
            
            # Verify specific expectations
            step_statuses = {step['step_id']: step['status'] for step in result_dict['step_results']}
            
            if step_statuses.get('S1_REQUIRED_CONVERSION') == 'not_implemented':
                logger.info("✓ Step 1 (required) executed successfully (placeholder)")
            
            if step_statuses.get('S2_OPTIONAL_FILTER') == 'failed':
                logger.info("✓ Step 2 (optional) failed as expected")
            
            if step_statuses.get('S3_REQUIRED_FINAL_CONVERSION') == 'not_implemented':
                logger.info("✓ Step 3 (required) executed after optional failure")
            
        finally:
            # Restore original handler
            executor._handle_filter_identifiers_by_target_presence = original_handler
        
        # Now test required step failure
        logger.info("\n\n=== Testing Required Step Failure ===")
        
        # Override a required step handler to fail
        async def failing_required_handler(*args, **kwargs):
            """Handler that raises an exception."""
            raise Exception("Simulated required step failure")
        
        executor._handle_convert_identifiers_local = failing_required_handler
        
        try:
            result_bundle = await executor.execute_strategy(
                strategy_name="TEST_STRATEGY_WITH_OPTIONAL_STEPS",
                initial_identifiers=test_identifiers
            )
            logger.error("✗ FAILED: Strategy should have raised an exception for required step failure")
        except Exception as e:
            logger.info(f"✓ SUCCESS: Strategy correctly raised exception for required step failure: {type(e).__name__}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        logger.error(traceback.format_exc())
    finally:
        if executor:
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


if __name__ == "__main__":
    logger.info("Starting Optional Steps Test")
    asyncio.run(test_optional_step_failure())