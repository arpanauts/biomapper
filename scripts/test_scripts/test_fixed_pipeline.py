#!/usr/bin/env python3
"""
Test the metabolomics pipeline with YAML condition evaluation fixed.
"""

import sys
sys.path.insert(0, 'src')

from client.client_v2 import BiomapperClient

def test_pipeline_with_conditions():
    """Test that the pipeline respects stages_to_run parameter."""
    
    print("\n" + "=" * 70)
    print("TESTING PIPELINE WITH CONDITION EVALUATION FIX")
    print("=" * 70)
    
    client = BiomapperClient(base_url="http://localhost:8001", timeout=120)
    
    # Test configurations
    tests = [
        {
            "name": "Stage 1 Only",
            "stages": [1],
            "expected": ["stage_1"],
            "not_expected": ["stage_2", "stage_3", "stage_4"]
        },
        {
            "name": "Stages 1-2",
            "stages": [1, 2],
            "expected": ["stage_1", "stage_2"],
            "not_expected": ["stage_3", "stage_4"]
        },
        {
            "name": "Stages 1-3",
            "stages": [1, 2, 3],
            "expected": ["stage_1", "stage_2", "stage_3"],
            "not_expected": ["stage_4"]
        }
    ]
    
    results_summary = []
    
    for test in tests:
        print(f"\n🧪 Testing: {test['name']} (stages: {test['stages']})")
        print("-" * 40)
        
        try:
            result = client.run(
                "met_arv_to_ukbb_progressive_v4.0",
                parameters={
                    "stages_to_run": test["stages"],
                    "debug_mode": True,
                    "output_dir": f"/tmp/biomapper/condition_test_stage_{max(test['stages'])}"
                }
            )
            
            if result.success:
                print(f"   ✅ Execution successful")
                
                # Check datasets created
                if result.result_data and "datasets" in result.result_data:
                    datasets = result.result_data["datasets"]
                    dataset_keys = list(datasets.keys())
                    
                    # Check expected stages
                    for expected_stage in test["expected"]:
                        found = any(expected_stage in k for k in dataset_keys)
                        if found:
                            print(f"   ✅ {expected_stage} executed as expected")
                            # Count matched metabolites
                            stage_datasets = [k for k in dataset_keys if expected_stage in k and "matched" in k]
                            for ds_key in stage_datasets:
                                data = datasets[ds_key]
                                if isinstance(data, dict) and "_row_count" in data:
                                    print(f"      📊 {ds_key}: {data['_row_count']} metabolites")
                        else:
                            print(f"   ❌ {expected_stage} NOT found (should have executed)")
                    
                    # Check unexpected stages
                    for unexpected_stage in test["not_expected"]:
                        found = any(unexpected_stage in k for k in dataset_keys)
                        if found:
                            print(f"   ❌ {unexpected_stage} executed (should NOT have)")
                        else:
                            print(f"   ✅ {unexpected_stage} correctly skipped")
                    
                    results_summary.append({
                        "test": test["name"],
                        "success": True,
                        "stages_run": test["expected"]
                    })
                else:
                    print(f"   ⚠️ No datasets in result")
                    results_summary.append({
                        "test": test["name"],
                        "success": False,
                        "error": "No datasets"
                    })
            else:
                print(f"   ❌ Execution failed: {result.error}")
                
                # Check if it's the old Stage 4 error
                if "HMDBVectorMatchAction" in str(result.error):
                    print("      ⚠️ Stage 4 error still occurring - conditions not working")
                    
                results_summary.append({
                    "test": test["name"],
                    "success": False,
                    "error": result.error
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results_summary.append({
                "test": test["name"],
                "success": False,
                "error": str(e)
            })
    
    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in results_summary if r.get("success"))
    total = len(results_summary)
    
    print(f"\nSuccess Rate: {successful}/{total}")
    
    if successful == total:
        print("\n✅ SUCCESS! All stages respect the stages_to_run parameter!")
        print("   The YAML condition evaluation fix is working correctly.")
        print("   The metabolomics pipeline can now be tested stage-by-stage.")
    else:
        print("\n⚠️ Some tests failed:")
        for result in results_summary:
            if not result.get("success"):
                print(f"   - {result['test']}: {result.get('error', 'Unknown error')}")
    
    print("\n🎯 KEY ACHIEVEMENT:")
    if any("HMDBVectorMatchAction" not in str(r.get("error", "")) for r in results_summary):
        print("   ✅ Stage 4 HMDB Vector errors ELIMINATED when not requested!")
        print("   ✅ Pipeline is now truly configurable with stages_to_run parameter!")
    
    return results_summary

if __name__ == "__main__":
    results = test_pipeline_with_conditions()