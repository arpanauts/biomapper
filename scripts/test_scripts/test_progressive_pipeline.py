#!/usr/bin/env python3
"""Test progressive pipeline execution with real data."""

from src.client.client_v2 import BiomapperClient
import json
from datetime import datetime


def test_progressive_stages():
    """Test pipeline stages progressively."""
    
    client = BiomapperClient(base_url="http://localhost:8001", timeout=120)
    
    print("="*70)
    print("PROGRESSIVE PIPELINE TEST WITH REAL DATA")
    print("="*70)
    print(f"Timestamp: {datetime.now()}")
    print("-"*70)
    
    # Test each stage combination
    stage_combinations = [
        [1],
        [1, 2],
        [1, 2, 3],
        [1, 2, 3, 4]
    ]
    
    results = {}
    
    for stages in stage_combinations:
        print(f"\nTesting Stages: {stages}")
        print("-"*40)
        
        try:
            result = client.run(
                "met_arv_to_ukbb_progressive_v4.0",
                parameters={
                    "stages_to_run": stages,
                    "debug_mode": False,
                    "verbose_logging": False,
                    "output_dir": f"/tmp/biomapper/progressive_test_{'-'.join(map(str, stages))}"
                }
            )
            
            if result.success:
                print(f"✅ Stages {stages} executed successfully!")
                
                # Analyze coverage
                if result.result_data and "datasets" in result.result_data:
                    datasets = result.result_data["datasets"]
                    coverage_info = analyze_coverage(datasets, stages)
                    results[str(stages)] = coverage_info
                    
                    print(f"Coverage: {coverage_info['cumulative_coverage']:.1f}%")
                    print(f"New matches in this stage: {coverage_info.get('incremental_matches', 0)}")
            else:
                print(f"❌ Stages {stages} failed: {result.error}")
                results[str(stages)] = {"error": result.error}
                
                # If it fails, don't try more stages
                if "interface" in str(result.error).lower() or "execute_typed" in str(result.error).lower():
                    print("\n⚠️ Interface issue detected. This is the known problem.")
                    print("The fixes we applied are working for individual actions")
                    print("but not in the full pipeline context.")
                break
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            results[str(stages)] = {"error": str(e)}
            break
    
    # Summary
    print("\n" + "="*70)
    print("PROGRESSIVE COVERAGE SUMMARY")
    print("="*70)
    
    cumulative_coverage = 0
    for stages_str, info in results.items():
        if "error" in info:
            print(f"Stages {stages_str}: ERROR - {info['error'][:50]}...")
        else:
            print(f"Stages {stages_str}:")
            print(f"  Total matches: {info.get('total_matches', 0)}")
            print(f"  Cumulative coverage: {info.get('cumulative_coverage', 0):.1f}%")
            if info.get('incremental_matches'):
                print(f"  Incremental matches: +{info['incremental_matches']}")
            cumulative_coverage = info.get('cumulative_coverage', 0)
    
    # Final assessment
    print("\n" + "="*70)
    print("FINAL ASSESSMENT")
    print("="*70)
    
    if cumulative_coverage > 0:
        print(f"Maximum coverage achieved: {cumulative_coverage:.1f}%")
        
        if cumulative_coverage < 30:
            print("⚠️ Coverage is significantly below claimed 77.9%")
            print("   Stage 5 LIPID MAPS could be valuable")
        elif cumulative_coverage < 50:
            print("📊 Coverage is moderate but below claims")
            print("   Stage 5 might provide meaningful improvement")
        else:
            print("✅ Coverage approaches reasonable levels")
            print("   Stage 5 would provide marginal benefit")
    else:
        print("❌ Pipeline execution failed - interface fixes needed")
        print("   Individual actions work but pipeline integration broken")
    
    return results


def analyze_coverage(datasets, stages):
    """Analyze coverage from dataset results."""
    info = {
        "stages_run": stages,
        "total_matches": 0,
        "cumulative_coverage": 0,
        "incremental_matches": 0
    }
    
    # Count reference
    ref_count = 250  # Known from Stage 1 results
    
    # Count matches per stage
    stage_matches = {}
    
    # Stage 1
    if 1 in stages:
        for key in ["stage_1_matched", "stage_1_matched_debug", "nightingale_matched"]:
            if key in datasets:
                data = datasets[key]
                count = len(data) if isinstance(data, list) else data.get("_row_count", 0)
                if count > 0:
                    stage_matches[1] = count
                    break
    
    # Stage 2
    if 2 in stages:
        for key in ["stage_2_matched", "fuzzy_matched"]:
            if key in datasets:
                data = datasets[key]
                count = len(data) if isinstance(data, list) else data.get("_row_count", 0)
                if count > 0:
                    stage_matches[2] = count
                    break
    
    # Stage 3
    if 3 in stages:
        for key in ["stage_3_matched", "rampdb_matched"]:
            if key in datasets:
                data = datasets[key]
                count = len(data) if isinstance(data, list) else data.get("_row_count", 0)
                if count > 0:
                    stage_matches[3] = count
                    break
    
    # Stage 4
    if 4 in stages:
        for key in ["stage_4_matched", "vector_matched"]:
            if key in datasets:
                data = datasets[key]
                count = len(data) if isinstance(data, list) else data.get("_row_count", 0)
                if count > 0:
                    stage_matches[4] = count
                    break
    
    # Calculate totals
    info["total_matches"] = sum(stage_matches.values())
    info["cumulative_coverage"] = (info["total_matches"] / ref_count) * 100 if ref_count > 0 else 0
    
    # Calculate incremental for last stage
    if len(stages) > 1 and stages[-1] in stage_matches:
        info["incremental_matches"] = stage_matches[stages[-1]]
    
    info["stage_breakdown"] = stage_matches
    
    return info


if __name__ == "__main__":
    results = test_progressive_stages()
    
    # Save results
    with open("/tmp/biomapper/progressive_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to /tmp/biomapper/progressive_test_results.json")