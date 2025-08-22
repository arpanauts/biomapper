#!/usr/bin/env python3
"""
Test the fixed progressive pipeline directly using MinimalStrategyService.
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, '/home/ubuntu/biomapper')
os.chdir('/home/ubuntu/biomapper')

from src.core.minimal_strategy_service import MinimalStrategyService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Execute the fixed progressive mapping pipeline directly."""
    
    # Strategy file path
    strategy_file = Path("/home/ubuntu/biomapper/src/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive_fixed.yaml")
    
    # Output directory
    output_dir = Path("/tmp/biomapper/protein_mapping_v3.0_progressive_fixed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set environment variable for output directory
    os.environ["OUTPUT_DIR"] = str(output_dir)
    
    logger.info(f"Executing FIXED progressive mapping pipeline")
    logger.info(f"Strategy file: {strategy_file}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        # Create service and execute
        strategies_dir = "/home/ubuntu/biomapper/src/configs/strategies"
        service = MinimalStrategyService(strategies_dir=strategies_dir)
        
        # Load and execute strategy
        logger.info("Loading strategy...")
        # The strategy name should be prot_arv_to_kg2c_uniprot_v3.0_progressive_fixed
        context = await service.execute_strategy("prot_arv_to_kg2c_uniprot_v3.0_progressive_fixed")
        
        logger.info("Pipeline execution completed!")
        
        # Check for output files
        output_file = output_dir / "progressive_mappings_fixed.tsv"
        if output_file.exists():
            # Load and analyze results
            df = pd.read_csv(output_file, sep='\t')
            
            # Calculate statistics
            total = len(df)
            unique_proteins = df['uniprot'].nunique() if 'uniprot' in df.columns else 0
            
            if 'mapping_stage' in df.columns:
                stage_1 = len(df[df['mapping_stage'] == 1])
                stage_2 = len(df[df['mapping_stage'] == 2])  
                stage_3 = len(df[df['mapping_stage'] == 3])
                unmapped = len(df[df['mapping_stage'] == 99])
            else:
                stage_1 = stage_2 = stage_3 = unmapped = 0
            
            logger.info("\n=== FIXED PROGRESSIVE MAPPING RESULTS ===")
            logger.info(f"Total records: {total}")
            logger.info(f"Unique proteins: {unique_proteins}")
            logger.info(f"Stage 1 (Direct): {stage_1} matches")
            logger.info(f"Stage 2 (Composite): {stage_2} matches")
            logger.info(f"Stage 3 (Historical): {stage_3} matches")
            logger.info(f"Unmapped: {unmapped}")
            
            if unique_proteins > 0:
                logger.info(f"Coverage: {100 * (1 - unmapped/unique_proteins):.2f}%")
            
            # Check for proteins with multiple match types (should be ZERO)
            if 'uniprot' in df.columns and 'match_type' in df.columns:
                duplicates = df.groupby('uniprot')['match_type'].nunique()
                multi_match = duplicates[duplicates > 1]
                
                if len(multi_match) > 0:
                    logger.warning(f"WARNING: {len(multi_match)} proteins have multiple match types!")
                    logger.warning(f"Examples: {multi_match.head().index.tolist()}")
                else:
                    logger.info("✅ SUCCESS: No proteins with duplicate match types!")
        else:
            logger.error(f"Output file not found: {output_file}")
            
    except Exception as e:
        logger.error(f"Error executing pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())