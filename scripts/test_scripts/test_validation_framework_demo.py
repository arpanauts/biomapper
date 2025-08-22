#!/usr/bin/env python3
"""
Quick demonstration of the biological validation framework components.

This is a standalone demo that imports the validation components directly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Quick demo of validation framework components."""
    
    logger.info("=== Validation Framework Components Demo ===")
    
    # Import validation components
    from validation.gold_standard_curator import GoldStandardCurator, MetaboliteClass
    from validation.flagging_logic import ExpertReviewFlagger, FlaggingCategory
    from validation.pipeline_modes import PipelineModeFactory
    
    output_dir = Path("/tmp/validation_quick_demo")
    output_dir.mkdir(exist_ok=True)
    
    # 1. Test Gold Standard Curator
    logger.info("\n1. Testing Gold Standard Curator...")
    curator = GoldStandardCurator(output_dir=str(output_dir))
    
    # Create a small sample instead of full dataset
    clinical_entries = curator._create_clinical_markers()[:5]  # Just 5 for demo
    logger.info(f"✓ Created {len(clinical_entries)} clinical marker entries")
    
    # 2. Test Expert Review Flagger
    logger.info("\n2. Testing Expert Review Flagger...")
    
    # Create mock pipeline results
    mock_results = pd.DataFrame({
        "metabolite_id": ["DEMO_001", "DEMO_002", "DEMO_003", "DEMO_004"],
        "matched_name": ["High Confidence Match", "Medium Match", "Low Match", "Edge Case"],
        "confidence_score": [0.95, 0.80, 0.65, 0.77],
        "alternative_matches": ["", "", "", "alt1, alt2"]
    })
    
    flagger = ExpertReviewFlagger(
        auto_accept_threshold=0.85,
        auto_reject_threshold=0.75,
        max_flagging_rate=0.25
    )
    
    flagged_results = flagger.flag_results_for_review(mock_results)
    
    logger.info("✓ Flagging Results:")
    for idx, row in flagged_results.iterrows():
        logger.info(f"  - {row['metabolite_id']}: {row['flagging_category']} "
                   f"(conf={row['confidence_score']:.3f}, review={row['expert_review_flag']})")
    
    # 3. Test Pipeline Mode Factory
    logger.info("\n3. Testing Pipeline Mode Factory...")
    
    production_config = PipelineModeFactory.create_production_config()
    cost_config = PipelineModeFactory.create_cost_optimized_config()
    
    logger.info(f"✓ Production config: flagging={production_config.enable_expert_flagging}, "
               f"max_cost=${production_config.max_total_cost}")
    logger.info(f"✓ Cost-optimized config: LLM_enabled={cost_config.llm_semantic_match.enabled}, "
               f"max_cost=${cost_config.max_total_cost}")
    
    # 4. Export Example
    logger.info("\n4. Testing Export Functionality...")
    
    export_file = output_dir / "demo_export.csv"
    flagger.export_flagged_results_for_review(flagged_results, str(export_file))
    
    logger.info(f"✓ Exported results to: {export_file}")
    
    # Show what was created
    logger.info("\n=== Demo Summary ===")
    logger.info("Components tested successfully:")
    logger.info("✓ Gold Standard Curator - Creates stratified metabolite datasets")
    logger.info("✓ Expert Review Flagger - Flags results for expert review")
    logger.info("✓ Pipeline Mode Factory - Creates different pipeline configurations")
    logger.info("✓ Export Functionality - Exports results for external review")
    
    logger.info(f"\nFiles created in {output_dir}:")
    for file_path in output_dir.glob("*"):
        if file_path.is_file():
            logger.info(f"  - {file_path.name}")
    
    logger.info("\nValidation framework is ready for integration with progressive pipeline!")
    

if __name__ == "__main__":
    main()