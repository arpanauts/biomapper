#!/usr/bin/env python3
"""Test the v3.0 strategy fix for the kg2c_normalized issue"""

import asyncio
import logging
import sys
from pathlib import Path

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent))

from biomapper.core.minimal_strategy_service import MinimalStrategyService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Test the fixed v3.0 strategy"""
    
    # Load the strategy
    strategy_path = Path("/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml")
    
    service = MinimalStrategyService(strategies_dir="/home/ubuntu/biomapper/configs/strategies")
    
    # Load strategy configuration
    strategy_config = service.load_strategy_config(str(strategy_path))
    logger.info(f"Loaded strategy: {strategy_config['name']}")
    
    # Execute only the first few steps to test the fix
    test_steps = [
        "load_arivale_proteins",
        "load_kg2c_entities", 
        "initialize_progressive_stats",
        "extract_uniprot_from_kg2c",
        "normalize_arivale_accessions",
        "normalize_kg2c_accessions",
        "direct_uniprot_match"
    ]
    
    context = {}
    
    for step_name in test_steps:
        # Find the step in the strategy
        step = next((s for s in strategy_config['steps'] if s['name'] == step_name), None)
        if not step:
            logger.error(f"Step '{step_name}' not found in strategy")
            break
            
        logger.info(f"Executing step: {step_name}")
        
        try:
            # Execute the step
            action_type = step['action']['type']
            params = step['action'].get('params', {})
            
            # Substitute parameters
            params = service._substitute_variables(params, strategy_config.get('parameters', {}), {})
            
            # Get the action
            from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
            if action_type not in ACTION_REGISTRY:
                logger.error(f"Action '{action_type}' not found in registry")
                break
                
            action = ACTION_REGISTRY[action_type]()
            
            # Execute
            result = await action.execute(params, context)
            
            if not result.get('success', False):
                logger.error(f"Step '{step_name}' failed: {result.get('error', 'Unknown error')}")
                break
            else:
                logger.info(f"Step '{step_name}' succeeded")
                
            # Check datasets after critical steps
            if step_name in ['extract_uniprot_from_kg2c', 'normalize_kg2c_accessions']:
                datasets = context.get('datasets', {})
                logger.info(f"Available datasets after {step_name}: {list(datasets.keys())}")
                
                if step_name == 'extract_uniprot_from_kg2c' and 'kg2c_with_uniprot' in datasets:
                    import pandas as pd
                    df = pd.DataFrame(datasets['kg2c_with_uniprot'])
                    logger.info(f"  kg2c_with_uniprot columns: {df.columns.tolist()}")
                    logger.info(f"  Has 'extracted_uniprot' column: {'extracted_uniprot' in df.columns}")
                    
                if step_name == 'normalize_kg2c_accessions' and 'kg2c_normalized' in datasets:
                    logger.info(f"  ✅ kg2c_normalized dataset created successfully!")
                elif step_name == 'normalize_kg2c_accessions' and 'kg2c_normalized' not in datasets:
                    logger.error(f"  ❌ kg2c_normalized dataset NOT created!")
                    
        except Exception as e:
            logger.error(f"Error in step '{step_name}': {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Final check
    datasets = context.get('datasets', {})
    if 'kg2c_normalized' in datasets:
        logger.info("✅ SUCCESS: kg2c_normalized dataset exists!")
        logger.info(f"Total datasets: {list(datasets.keys())}")
    else:
        logger.error("❌ FAILURE: kg2c_normalized dataset missing!")
        logger.error(f"Available datasets: {list(datasets.keys())}")
        
if __name__ == "__main__":
    asyncio.run(main())