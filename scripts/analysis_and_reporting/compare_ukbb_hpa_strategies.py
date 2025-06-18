#!/usr/bin/env python
"""
Compare UKBB to HPA mapping strategies.

This script runs both the original and efficient strategies on the same dataset
and provides a detailed comparison of their results and performance.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
import pandas as pd

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

# Strategies to compare
STRATEGIES = {
    "original": "UKBB_TO_HPA_PROTEIN_PIPELINE",
    "efficient": "UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT"
}

SOURCE_ENDPOINT = "UKBB_PROTEIN"
TARGET_ENDPOINT = "HPA_OSP_PROTEIN"


async def run_strategy(executor: MappingExecutor, strategy_name: str, identifiers: List[str]) -> Tuple[Dict[str, Any], float]:
    """Run a single strategy and return results with timing."""
    start_time = datetime.now()
    
    result = await executor.execute_yaml_strategy(
        strategy_name=strategy_name,
        source_endpoint_name=SOURCE_ENDPOINT,
        target_endpoint_name=TARGET_ENDPOINT,
        input_identifiers=identifiers,
        use_cache=True,
        progress_callback=lambda curr, total, status: logger.debug(f"{strategy_name}: {curr}/{total} - {status}")
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    return result, duration


async def compare_strategies():
    """Compare the two strategies on the full dataset."""
    logger.info("Starting UKBB to HPA strategy comparison")
    logger.info("=" * 80)
    
    executor = None
    
    try:
        # Initialize MappingExecutor
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        
        # Load input identifiers
        strategy = await executor.get_strategy(STRATEGIES["original"])
        source_ontology_type = strategy.default_source_ontology_type
        
        logger.info(f"Loading identifiers from {SOURCE_ENDPOINT}...")
        input_identifiers = await executor.load_endpoint_identifiers(
            endpoint_name=SOURCE_ENDPOINT,
            ontology_type=source_ontology_type
        )
        
        logger.info(f"Loaded {len(input_identifiers)} identifiers")
        
        # Run both strategies
        results = {}
        
        for name, strategy_name in STRATEGIES.items():
            logger.info(f"\nRunning {name} strategy: {strategy_name}")
            logger.info("-" * 60)
            
            try:
                result, duration = await run_strategy(executor, strategy_name, input_identifiers)
                results[name] = {
                    "result": result,
                    "duration": duration,
                    "success": True
                }
                logger.info(f"✓ Completed in {duration:.2f} seconds")
            except Exception as e:
                logger.error(f"✗ Failed: {e}")
                results[name] = {
                    "result": None,
                    "duration": None,
                    "success": False,
                    "error": str(e)
                }
        
        # Compare results
        logger.info("\n" + "=" * 80)
        logger.info("COMPARISON RESULTS")
        logger.info("=" * 80)
        
        if all(r["success"] for r in results.values()):
            original_result = results["original"]["result"]
            efficient_result = results["efficient"]["result"]
            
            # Extract mapping results
            original_mapped = {k: v for k, v in original_result["results"].items() if v.get("mapped_value")}
            efficient_mapped = {k: v for k, v in efficient_result["results"].items() if v.get("mapped_value")}
            
            # Performance comparison
            logger.info("\nPERFORMANCE:")
            logger.info(f"Original strategy:  {results['original']['duration']:.2f} seconds")
            logger.info(f"Efficient strategy: {results['efficient']['duration']:.2f} seconds")
            speedup = results['original']['duration'] / results['efficient']['duration']
            logger.info(f"Speedup: {speedup:.2f}x faster")
            
            # Coverage comparison
            logger.info("\nCOVERAGE:")
            logger.info(f"Original strategy:  {len(original_mapped)} mapped ({len(original_mapped)/len(input_identifiers)*100:.1f}%)")
            logger.info(f"Efficient strategy: {len(efficient_mapped)} mapped ({len(efficient_mapped)/len(input_identifiers)*100:.1f}%)")
            
            # Find differences
            only_original = set(original_mapped.keys()) - set(efficient_mapped.keys())
            only_efficient = set(efficient_mapped.keys()) - set(original_mapped.keys())
            both_mapped = set(original_mapped.keys()) & set(efficient_mapped.keys())
            
            logger.info("\nDIFFERENCES:")
            logger.info(f"Mapped by both strategies: {len(both_mapped)}")
            logger.info(f"Only by original: {len(only_original)}")
            logger.info(f"Only by efficient: {len(only_efficient)}")
            
            # Check if mappings agree
            disagreements = []
            for id in both_mapped:
                if original_mapped[id]["mapped_value"] != efficient_mapped[id]["mapped_value"]:
                    disagreements.append({
                        "id": id,
                        "original": original_mapped[id]["mapped_value"],
                        "efficient": efficient_mapped[id]["mapped_value"]
                    })
            
            if disagreements:
                logger.warning(f"\nFound {len(disagreements)} disagreements in mapped values!")
                for d in disagreements[:5]:  # Show first 5
                    logger.warning(f"  {d['id']}: {d['original']} vs {d['efficient']}")
            else:
                logger.info("\n✓ All common mappings agree!")
            
            # Step analysis
            logger.info("\nSTEP ANALYSIS:")
            logger.info("Original strategy steps:")
            for step in original_result["summary"]["step_results"]:
                logger.info(f"  - {step['step_id']}: {step.get('output_count', 'N/A')} output")
            
            logger.info("\nEfficient strategy steps:")
            for step in efficient_result["summary"]["step_results"]:
                logger.info(f"  - {step['step_id']}: {step.get('output_count', 'N/A')} output")
            
            # Save detailed comparison
            comparison_df = pd.DataFrame({
                "identifier": input_identifiers,
                "original_mapped": [original_mapped.get(id, {}).get("mapped_value") for id in input_identifiers],
                "efficient_mapped": [efficient_mapped.get(id, {}).get("mapped_value") for id in input_identifiers],
                "original_confidence": [original_mapped.get(id, {}).get("confidence", 0) for id in input_identifiers],
                "efficient_confidence": [efficient_mapped.get(id, {}).get("confidence", 0) for id in input_identifiers]
            })
            
            output_file = "/home/ubuntu/biomapper/data/results/strategy_comparison.csv"
            comparison_df.to_csv(output_file, index=False)
            logger.info(f"\nDetailed comparison saved to: {output_file}")
            
        else:
            logger.error("\nComparison failed - not all strategies completed successfully")
            for name, result in results.items():
                if not result["success"]:
                    logger.error(f"{name}: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
    finally:
        if executor:
            await executor.async_dispose()


if __name__ == "__main__":
    asyncio.run(compare_strategies())