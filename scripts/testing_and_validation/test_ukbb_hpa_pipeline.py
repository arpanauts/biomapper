#!/usr/bin/env python3
"""
Script to test the UKBB to HPA protein mapping pipeline.

This script tests the UKBB_TO_HPA_PROTEIN_PIPELINE strategy defined in protein_config.yaml
with the specific sample UKBB Protein Assay IDs provided in the task instructions.
"""

import asyncio
import logging
import traceback
import os
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


async def test_ukbb_hpa_pipeline():
    """Test the UKBB to HPA protein mapping pipeline."""
    
    executor = None
    
    try:
        # Set the DATA_DIR environment variable if not already set
        if not os.environ.get('DATA_DIR'):
            os.environ['DATA_DIR'] = '/home/ubuntu/biomapper/data'
            logger.info(f"Set DATA_DIR to: {os.environ['DATA_DIR']}")
        
        # Create MappingExecutor using the async factory method
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        logger.info("MappingExecutor created successfully")
        
        # Sample UKBB Protein Assay IDs that are actually in our test file
        sample_identifiers = [
            "CFH_TEST",
            "ALS2_TEST", 
            "PLIN1_TEST",
            "FABP4_TEST", 
            "UNKNOWN_TEST"
        ]
        
        logger.info(f"Input UKBB Assay IDs: {sample_identifiers}")
        logger.info(f"Testing with {len(sample_identifiers)} UKBB protein assay identifiers")
        
        # Execute the YAML strategy using the correct method name
        try:
            result = await executor.execute_yaml_strategy(
                strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
                source_endpoint_name="UKBB_PROTEIN",
                target_endpoint_name="HPA_OSP_PROTEIN", 
                input_identifiers=sample_identifiers,
                use_cache=False,
                progress_callback=lambda curr, total, status: logger.info(f"Progress: {curr}/{total} - {status}")
            )
        except AttributeError:
            # Try alternative method name if execute_yaml_strategy doesn't exist
            logger.info("Trying execute_strategy_by_name method...")
            result = await executor.execute_strategy_by_name(
                strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
                input_identifiers=sample_identifiers,
                use_cache=False
            )
        
        # Display results
        logger.info("\n" + "="*60)
        logger.info("UKBB TO HPA PROTEIN PIPELINE EXECUTION RESULTS")
        logger.info("="*60)
        
        # Show input identifiers
        logger.info(f"Input UKBB Assay IDs: {sample_identifiers}")
        
        # Display summary
        if isinstance(result, dict) and "summary" in result:
            summary = result.get("summary", {})
            logger.info(f"\nStrategy: {summary.get('strategy_name', 'N/A')}")
            logger.info(f"Total input: {summary.get('total_input', len(sample_identifiers))}")
            logger.info(f"Total mapped: {summary.get('total_mapped', 'N/A')}")
            logger.info(f"Total unmapped: {summary.get('total_unmapped', 'N/A')}")
            logger.info(f"Steps executed: {summary.get('steps_executed', 'N/A')}")
            
            # Display step results
            logger.info("\n=== Step-by-Step Results ===")
            for step in summary.get("step_results", []):
                logger.info(f"\nStep: {step.get('step_id')}")
                logger.info(f"  Description: {step.get('description', 'N/A')}")
                logger.info(f"  Action: {step.get('action_type')}")
                logger.info(f"  Success: {step.get('success')}")
                logger.info(f"  Input count: {step.get('input_count')}")
                logger.info(f"  Output count: {step.get('output_count')}")
                if step.get('details'):
                    logger.info(f"  Details: {step.get('details')}")
                if step.get('error'):
                    logger.error(f"  Error: {step.get('error')}")
        
        # Display individual mapping results  
        logger.info("\n=== Final Mapping Results ===")
        
        if isinstance(result, dict) and "results" in result:
            results = result.get("results", {})
            final_mapped_identifiers = []
            
            for source_id, mapping in results.items():
                mapped_value = mapping.get('mapped_value', 'None') 
                confidence = mapping.get('confidence', 0.0)
                error = mapping.get('error', '')
                
                if mapped_value and mapped_value != 'None':
                    logger.info(f"✓ {source_id} -> {mapped_value} (confidence: {confidence:.2f})")
                    final_mapped_identifiers.append(mapped_value)
                else:
                    logger.warning(f"✗ {source_id} -> No mapping found. {error}")
            
            logger.info(f"\nFinal list of mapped HPA Gene Symbols: {final_mapped_identifiers}")
            
            # Check for the expected mapping from our test data
            if "Gene:ALS2" in final_mapped_identifiers:
                logger.info("✓ VERIFICATION PASSED: Expected mapping 'ALS2_TEST' -> 'Gene:ALS2' found!")
            else:
                logger.warning("⚠ VERIFICATION: Expected mapping 'ALS2_TEST' -> 'Gene:ALS2' not found")
                
        elif isinstance(result, list):
            # Handle case where result is a list
            logger.info(f"Final mapped identifiers: {result}")
            final_mapped_identifiers = result
            
            if "Gene:ALS2" in result:
                logger.info("✓ VERIFICATION PASSED: Expected mapping 'ALS2_TEST' -> 'Gene:ALS2' found!")
            else:
                logger.warning("⚠ VERIFICATION: Expected mapping 'ALS2_TEST' -> 'Gene:ALS2' not found")
        else:
            logger.warning(f"Unexpected result format: {type(result)}")
            logger.info(f"Result content: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during pipeline execution: {e}")
        logger.error(traceback.format_exc())
        return None
    finally:
        if executor:
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


async def check_strategy_in_database():
    """Check if the UKBB_TO_HPA_PROTEIN_PIPELINE strategy is loaded in the database."""
    from biomapper.db.session import get_db_manager
    from biomapper.config import settings
    from biomapper.db.models import MappingStrategy, MappingStrategyStep
    from sqlalchemy import select
    
    try:
        db_manager = get_db_manager(db_url=settings.metamapper_db_url)
        
        async with await db_manager.create_async_session() as session:
            # Check if strategy exists
            stmt = select(MappingStrategy).where(
                MappingStrategy.name == "UKBB_TO_HPA_PROTEIN_PIPELINE"
            )
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            
            if strategy:
                logger.info(f"✓ Strategy found in database: {strategy.name}")
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
                
                logger.info(f"  Steps ({len(steps)}):")
                for step in steps:
                    logger.info(f"    {step.step_order}. {step.step_id}: {step.action_type}")
                return True
            else:
                logger.warning("✗ Strategy UKBB_TO_HPA_PROTEIN_PIPELINE not found in database!")
                logger.warning("Please run: python scripts/populate_metamapper_db.py")
                return False
                
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("UKBB TO HPA PROTEIN PIPELINE TEST")
    logger.info("="*60)
    
    # First check if the strategy is in the database
    logger.info("Checking if strategy is loaded in database...")
    strategy_exists = asyncio.run(check_strategy_in_database())
    
    if strategy_exists:
        logger.info("\n" + "="*50)
        logger.info("Running pipeline test...")
        asyncio.run(test_ukbb_hpa_pipeline())
    else:
        logger.error("Cannot proceed - strategy not found in database.")
        logger.info("Please populate the database first with: python scripts/populate_metamapper_db.py")