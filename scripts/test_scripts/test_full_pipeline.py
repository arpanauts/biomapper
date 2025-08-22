#!/usr/bin/env python3
"""Test full metabolomics pipeline Stages 1-4 to get real coverage metrics."""

from src.client.client_v2 import BiomapperClient
import json
from datetime import datetime

def test_full_pipeline():
    """Test all 4 stages to get actual coverage metrics."""
    
    # Use port 8001 where our API is running
    client = BiomapperClient(base_url="http://localhost:8001", timeout=120)
    
    print("="*70)
    print("METABOLOMICS PIPELINE - FULL COVERAGE TEST (STAGES 1-4)")
    print("="*70)
    print(f"Timestamp: {datetime.now()}")
    print("Testing all stages with interface fixes applied")
    print("-"*70)
    
    # Run all 4 stages
    result = client.run(
        "met_arv_to_ukbb_progressive_v4.0",
        parameters={
            "stages_to_run": [1, 2, 3, 4],  # All stages
            "debug_mode": True,
            "verbose_logging": True,
            "output_dir": f"/tmp/biomapper/full_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    )
    
    print(f"\nExecution status: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
    
    if result.success:
        print("\nPipeline executed all stages successfully!")
        
        # Analyze coverage at each stage
        if result.result_data and "datasets" in result.result_data:
            datasets = result.result_data["datasets"]
            
            print("\n" + "="*70)
            print("REAL COVERAGE METRICS - ALL STAGES")
            print("="*70)
            
            # Track counts
            metrics = {
                "original": 0,
                "reference": 0,
                "stage1": 0,
                "stage2": 0,
                "stage3": 0,
                "stage4": 0
            }
            
            # Original data
            if "arivale_raw" in datasets:
                metrics["original"] = _get_count(datasets["arivale_raw"])
            elif "arivale_debug" in datasets:
                metrics["original"] = _get_count(datasets["arivale_debug"])
            
            if "reference_raw" in datasets:
                metrics["reference"] = _get_count(datasets["reference_raw"])
            
            print(f"\nInput Data:")
            print(f"  Arivale metabolites: {metrics['original']}")
            print(f"  UKBB reference: {metrics['reference']}")
            
            # Stage results
            print("\n" + "-"*70)
            print("STAGE-BY-STAGE RESULTS:")
            
            # Stage 1
            for key in ["stage_1_matched", "stage_1_matched_debug", "nightingale_matched"]:
                if key in datasets:
                    metrics["stage1"] = _get_count(datasets[key])
                    break
            
            if metrics["stage1"] > 0 and metrics["reference"] > 0:
                pct = (metrics["stage1"] / metrics["reference"]) * 100
                print(f"\nStage 1 (Nightingale Bridge): {metrics['stage1']}/{metrics['reference']} = {pct:.1f}%")
            
            # Stage 2
            for key in ["stage_2_matched", "fuzzy_matched"]:
                if key in datasets:
                    metrics["stage2"] = _get_count(datasets[key])
                    break
            
            if metrics["stage2"] > 0 and metrics["reference"] > 0:
                pct = (metrics["stage2"] / metrics["reference"]) * 100
                print(f"Stage 2 (Fuzzy String Match): {metrics['stage2']}/{metrics['reference']} = {pct:.1f}%")
            
            # Stage 3
            for key in ["stage_3_matched", "rampdb_matched"]:
                if key in datasets:
                    metrics["stage3"] = _get_count(datasets[key])
                    break
            
            if metrics["stage3"] > 0 and metrics["reference"] > 0:
                pct = (metrics["stage3"] / metrics["reference"]) * 100
                print(f"Stage 3 (RampDB Bridge): {metrics['stage3']}/{metrics['reference']} = {pct:.1f}%")
            
            # Stage 4
            for key in ["stage_4_matched", "vector_matched"]:
                if key in datasets:
                    metrics["stage4"] = _get_count(datasets[key])
                    break
            
            if metrics["stage4"] > 0 and metrics["reference"] > 0:
                pct = (metrics["stage4"] / metrics["reference"]) * 100
                print(f"Stage 4 (HMDB Vector Match): {metrics['stage4']}/{metrics['reference']} = {pct:.1f}%")
            
            # Calculate cumulative coverage
            print("\n" + "-"*70)
            print("CUMULATIVE COVERAGE:")
            
            total_matched = metrics["stage1"] + metrics["stage2"] + metrics["stage3"] + metrics["stage4"]
            if metrics["reference"] > 0:
                total_pct = (total_matched / metrics["reference"]) * 100
                print(f"Total matched: {total_matched}/{metrics['reference']} = {total_pct:.1f}%")
                
                # Breakdown
                print(f"\nBreakdown:")
                print(f"  Stage 1: {metrics['stage1']} metabolites")
                print(f"  Stage 2: +{metrics['stage2']} metabolites")
                print(f"  Stage 3: +{metrics['stage3']} metabolites")
                print(f"  Stage 4: +{metrics['stage4']} metabolites")
                print(f"  Total:   {total_matched} metabolites")
            
            # Compare to claimed coverage
            print("\n" + "="*70)
            print("CLAIMED vs ACTUAL COVERAGE:")
            print("-"*70)
            print("Stage    Claimed    Actual")
            print("-"*30)
            
            if metrics["reference"] > 0:
                stage1_actual = (metrics["stage1"] / metrics["reference"]) * 100
                cumulative2 = ((metrics["stage1"] + metrics["stage2"]) / metrics["reference"]) * 100
                cumulative3 = ((metrics["stage1"] + metrics["stage2"] + metrics["stage3"]) / metrics["reference"]) * 100
                cumulative4 = total_pct
                
                print(f"Stage 1:  57.9%     {stage1_actual:.1f}%")
                print(f"Stage 2:  69.9%     {cumulative2:.1f}% (cumulative)")
                print(f"Stage 3:  74.9%     {cumulative3:.1f}% (cumulative)")
                print(f"Stage 4:  77.9%     {cumulative4:.1f}% (cumulative)")
            
            # Additional analysis
            print("\n" + "="*70)
            print("ANALYSIS:")
            print("-"*70)
            
            if total_pct < 30:
                print("⚠️ Actual coverage is significantly lower than claimed!")
                print(f"   Claimed: 77.9% → Actual: {total_pct:.1f}%")
                print(f"   Discrepancy: ~{77.9/total_pct:.1f}x overestimation")
            elif total_pct < 50:
                print("⚠️ Coverage is lower than claimed but shows multi-stage benefit")
            else:
                print("✅ Coverage approaches claimed values with all stages")
            
            # Check all datasets created
            print(f"\nAll datasets created: {list(datasets.keys())}")
            
            # Statistics if available
            if "statistics" in result.result_data:
                stats = result.result_data["statistics"]
                if stats:
                    print(f"\nStatistics available: {list(stats.keys())}")
                    
                    # Show progressive stats if available
                    for stage_num in range(1, 5):
                        stage_key = f"progressive_stage{stage_num}"
                        if stage_key in stats:
                            stage_stats = stats[stage_key]
                            print(f"\nStage {stage_num} stats:")
                            print(f"  Processing time: {stage_stats.get('processing_time_seconds', 0):.2f}s")
                            print(f"  API calls: {stage_stats.get('api_calls', 0)}")
                            print(f"  Cost: ${stage_stats.get('cost_dollars', 0):.2f}")
    else:
        print(f"\n❌ Pipeline failed: {result.error}")
        print("\nThis means one or more stages still has issues.")
        
    return result


def _get_count(data):
    """Get count from dataset regardless of format."""
    if isinstance(data, list):
        return len(data)
    elif isinstance(data, dict):
        if "_row_count" in data:
            return data["_row_count"]
        else:
            return len(data)
    return 0


if __name__ == "__main__":
    result = test_full_pipeline()
    exit(0 if result.success else 1)