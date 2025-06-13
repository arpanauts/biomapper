#!/usr/bin/env python
"""
Test script for the new bidirectional UKBB to HPA protein mapping strategy.

This script tests the optimized bidirectional mapping approach that:
1. Directly matches UniProt IDs between datasets
2. Resolves unmatched IDs via UniProt API (forward)
3. Resolves remaining unmatched via reverse resolution
4. Converts final matches to HPA gene names

Usage:
    python scripts/main_pipelines/test_bidirectional_ukbb_hpa_mapping.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bidirectional_mapping():
    """Test the bidirectional UKBB to HPA mapping strategy."""
    
    logger.info("=" * 60)
    logger.info("Testing Bidirectional UKBB to HPA Protein Mapping")
    logger.info("=" * 60)
    
    # Test parameters
    STRATEGY_NAME = "UKBB_TO_HPA_BIDIRECTIONAL_OPTIMIZED"
    SOURCE_ENDPOINT = "UKBB_PROTEIN"
    TARGET_ENDPOINT = "HPA_OSP_PROTEIN"
    
    # Small test set of identifiers
    test_identifiers = [
        "P04217",  # A1BG - should match directly
        "P01023",  # A2M - should match directly
        "Q9BTE6",  # AARSD1 - from UKBB data
        "P00519",  # ABL1 - should match
        "Q14213_Q8NEV9",  # Example composite ID
        "P99999",  # Fake ID to test unmatched handling
        "OLD_ID_123",  # Fake old ID to test resolution
    ]
    
    try:
        # Initialize MappingExecutor
        logger.info("Initializing MappingExecutor...")
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        
        logger.info(f"Testing strategy: {STRATEGY_NAME}")
        logger.info(f"Test identifiers: {test_identifiers}")
        
        # Execute the bidirectional strategy
        result = await executor.execute_yaml_strategy(
            strategy_name=STRATEGY_NAME,
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=test_identifiers,
            use_cache=False,  # Disable cache for testing
            progress_callback=lambda curr, total, status: logger.info(
                f"Progress: {curr}/{total} - {status}"
            )
        )
        
        # Analyze results
        logger.info("\n" + "=" * 60)
        logger.info("RESULTS ANALYSIS")
        logger.info("=" * 60)
        
        # Check context for tracking
        context = result.get('context', {})
        logger.info(f"Context keys available: {list(context.keys())}")
        direct_matches = context.get('direct_matches', [])
        unmatched_ukbb = context.get('unmatched_ukbb', [])
        unmatched_hpa = context.get('unmatched_hpa', [])
        all_matches = context.get('all_matches', [])
        final_unmatched = context.get('final_unmatched', {})
        
        logger.info(f"Direct matches found: {len(direct_matches)}")
        logger.info(f"Unmatched UKBB after direct: {len(unmatched_ukbb)}")
        logger.info(f"Unmatched HPA after direct: {len(unmatched_hpa)}")
        logger.info(f"Total matches after resolution: {len(all_matches)}")
        logger.info(f"Final unmatched: {final_unmatched}")
        
        # Detailed step results
        summary = result.get('summary', {})
        step_results = summary.get('step_results', [])
        
        logger.info("\nStep-by-step results:")
        for step in step_results:
            logger.info(f"\n{step['step_id']}: {step.get('description', 'N/A')}")
            logger.info(f"  Success: {step.get('success', False)}")
            logger.info(f"  Input count: {step.get('input_count', 0)}")
            logger.info(f"  Output count: {step.get('output_count', 0)}")
            if step.get('error'):
                logger.error(f"  Error: {step['error']}")
        
        # Final mapping results
        final_identifiers = result.get('final_identifiers', [])
        logger.info(f"\nFinal mapped identifiers: {len(final_identifiers)}")
        for i, identifier in enumerate(final_identifiers[:10]):  # Show first 10
            logger.info(f"  {i+1}. {identifier}")
        
        # Compare with original strategy
        logger.info("\n" + "=" * 60)
        logger.info("STRATEGY COMPARISON")
        logger.info("=" * 60)
        logger.info("Original strategy: 4 steps (Convert → Resolve → Filter → Convert)")
        logger.info("Bidirectional strategy: 4 steps (Match → Resolve Forward → Resolve Reverse → Convert)")
        logger.info("\nExpected benefits:")
        logger.info("- Faster initial matching (no conversion needed)")
        logger.info("- Better coverage (bidirectional resolution)")
        logger.info("- Clearer tracking (context-based)")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise
    finally:
        if 'executor' in locals():
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


async def test_direct_gene_matching():
    """Test the direct gene name matching strategy."""
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Direct Gene Name Matching")
    logger.info("=" * 60)
    
    # This would test UKBB_TO_HPA_DIRECT_GENE_MATCH strategy
    # Similar structure but using gene names directly
    logger.info("Direct gene matching test not implemented yet")
    # TODO: Implement when BIDIRECTIONAL_MATCH supports case-insensitive matching


if __name__ == "__main__":
    try:
        # Run the bidirectional test
        asyncio.run(test_bidirectional_mapping())
        
        # Optionally test direct gene matching
        # asyncio.run(test_direct_gene_matching())
        
        logger.info("\nAll tests completed successfully!")
    except Exception as e:
        logger.error(f"Tests failed: {e}")
        sys.exit(1)