#!/usr/bin/env python3
"""
Demonstration of the Biological Validation Framework

Shows how to use the validation framework components together:
1. Gold standard dataset creation
2. Confidence threshold optimization  
3. Expert review flagging
4. Production workflow integration
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate the complete validation framework workflow."""
    
    logger.info("=== Biomapper Validation Framework Demo ===")
    
    # Set up output directory
    output_dir = Path("/tmp/validation_demo")
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Create Gold Standard Dataset
    logger.info("\n1. Creating Gold Standard Dataset...")
    
    from src.validation import GoldStandardCurator
    
    curator = GoldStandardCurator(output_dir=str(output_dir))
    gold_standard_dataset = curator.create_gold_standard_dataset()
    
    # Save gold standard dataset
    dataset_file = curator.save_dataset(gold_standard_dataset)
    logger.info(f"✓ Created gold standard with {gold_standard_dataset.total_entries} metabolites")
    logger.info(f"✓ Class distribution: {gold_standard_dataset.class_distribution}")
    logger.info(f"✓ Saved to: {dataset_file}")
    
    # Step 2: Create Mock Pipeline Results
    logger.info("\n2. Creating Mock Pipeline Results...")
    
    # Generate realistic pipeline results for demonstration
    np.random.seed(42)  # For reproducible demo
    
    mock_results = []
    for i in range(100):
        # Simulate different confidence levels and stages
        stage = np.random.choice(["nightingale", "fuzzy", "rampdb", "semantic"], 
                                 p=[0.3, 0.4, 0.2, 0.1])
        
        # Different stages have different confidence distributions
        if stage == "nightingale":
            confidence = np.random.beta(8, 2)  # High confidence
        elif stage == "fuzzy":
            confidence = np.random.beta(5, 3)  # Medium-high confidence
        elif stage == "rampdb":
            confidence = np.random.beta(4, 4)  # Medium confidence
        else:  # semantic
            confidence = np.random.beta(3, 5)  # Lower confidence
        
        mock_results.append({
            "metabolite_id": f"DEMO_{i+1:03d}",
            "matched_name": f"Demo Metabolite {i+1}",
            "confidence_score": round(confidence, 3),
            "matched_stage": stage,
            "molecular_formula": f"C{6+i%10}H{12+i%20}O{6+i%5}",
            "alternative_matches": "alt1, alt2" if i % 5 == 0 else ""
        })
    
    pipeline_results = pd.DataFrame(mock_results)
    logger.info(f"✓ Created {len(pipeline_results)} mock pipeline results")
    logger.info(f"✓ Confidence range: {pipeline_results['confidence_score'].min():.3f} - {pipeline_results['confidence_score'].max():.3f}")
    
    # Step 3: Apply Expert Review Flagging
    logger.info("\n3. Applying Expert Review Flagging...")
    
    from src.validation import ExpertReviewFlagger
    
    flagger = ExpertReviewFlagger(
        auto_accept_threshold=0.85,
        auto_reject_threshold=0.75,
        max_flagging_rate=0.15  # 15% maximum review workload
    )
    
    flagged_results = flagger.flag_results_for_review(pipeline_results)
    
    # Analyze flagging results
    flagging_summary = {
        "total_processed": len(flagged_results),
        "auto_accepted": len(flagged_results[flagged_results["flagging_category"] == "auto_accept"]),
        "auto_rejected": len(flagged_results[flagged_results["flagging_category"] == "auto_reject"]),
        "needs_review": len(flagged_results[flagged_results["expert_review_flag"] == True])
    }
    
    logger.info("✓ Flagging Summary:")
    for key, value in flagging_summary.items():
        logger.info(f"  - {key}: {value}")
    
    # Step 4: Create Expert Review Batches
    logger.info("\n4. Creating Expert Review Batches...")
    
    review_batches = flagger.create_expert_review_batch(flagged_results, batch_size=10)
    
    if review_batches:
        total_review_time = sum(batch.estimated_total_time for batch in review_batches)
        logger.info(f"✓ Created {len(review_batches)} review batches")
        logger.info(f"✓ Total estimated review time: {total_review_time} minutes")
    else:
        logger.info("✓ No items require expert review (all auto-processed)")
    
    # Step 5: Export for External Review
    logger.info("\n5. Exporting Results for External Review...")
    
    export_file = output_dir / "expert_review_export.csv"
    flagger.export_flagged_results_for_review(flagged_results, str(export_file))
    
    logger.info(f"✓ Exported flagged results to: {export_file}")
    logger.info(f"✓ Instructions file created: {export_file.with_suffix('.csv').with_name(export_file.stem + '_instructions.md')}")
    
    # Step 6: Confidence Threshold Optimization (if sklearn available)
    logger.info("\n6. Confidence Threshold Optimization...")
    
    try:
        from src.validation import ConfidenceThresholdOptimizer
        
        optimizer = ConfidenceThresholdOptimizer(output_dir=str(output_dir))
        
        # Create validation dataset from pipeline results
        # For demo, we'll simulate ground truth
        validation_data = pipeline_results.copy()
        
        # Simulate ground truth: higher confidence = more likely to be correct
        validation_data["is_correct_match"] = (
            validation_data["confidence_score"] + np.random.normal(0, 0.1, len(validation_data)) > 0.7
        ).astype(int)
        
        # Optimize thresholds
        optimization_results = optimizer.optimize_thresholds_for_dataset(
            validation_data, 
            confidence_column="confidence_score",
            truth_column="is_correct_match"
        )
        
        logger.info("✓ Threshold Optimization Results:")
        for group, result in optimization_results.items():
            logger.info(f"  - {group}: optimal threshold = {result.optimal_threshold:.3f}")
            logger.info(f"    precision = {result.precision:.3f}, recall = {result.recall:.3f}")
        
        # Generate production recommendations
        recommendations = optimizer.recommend_production_thresholds(optimization_results)
        logger.info("✓ Production threshold recommendations generated")
        
    except ImportError:
        logger.warning("⚠ scikit-learn not available - skipping threshold optimization")
    
    # Step 7: Pipeline Mode Configuration
    logger.info("\n7. Pipeline Mode Configuration...")
    
    from src.validation import PipelineModeFactory
    
    # Create different pipeline configurations
    configs = {
        "production": PipelineModeFactory.create_production_config(),
        "validation": PipelineModeFactory.create_validation_config(dataset_file),
        "cost_optimized": PipelineModeFactory.create_cost_optimized_config()
    }
    
    logger.info("✓ Created pipeline configurations:")
    for config_name, config in configs.items():
        logger.info(f"  - {config_name}: expert_flagging={config.enable_expert_flagging}, max_cost=${config.max_total_cost}")
    
    # Summary
    logger.info("\n=== Demo Complete ===")
    logger.info(f"✓ All validation framework components demonstrated")
    logger.info(f"✓ Results saved in: {output_dir}")
    logger.info("")
    logger.info("Files created:")
    for file_path in output_dir.glob("*"):
        if file_path.is_file():
            logger.info(f"  - {file_path.name}")
    
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Review the exported CSV file for expert review workflow")
    logger.info("2. Integrate validation framework with progressive pipeline")
    logger.info("3. Run end-to-end validation with real data")
    logger.info("4. Deploy production thresholds and monitoring")


if __name__ == "__main__":
    main()