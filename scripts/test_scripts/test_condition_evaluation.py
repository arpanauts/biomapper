#!/usr/bin/env python3
"""
Test that YAML condition evaluation works correctly in MinimalStrategyService.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, 'src')

from core.minimal_strategy_service import MinimalStrategyService

async def test_condition_evaluation():
    """Test that conditions are properly evaluated."""
    
    print("\n" + "=" * 70)
    print("TESTING YAML CONDITION EVALUATION FIX")
    print("=" * 70)
    
    # Create service
    strategies_dir = Path("src/configs/strategies")
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Test the _evaluate_condition method directly
    print("\n1. Testing _evaluate_condition method:")
    print("-" * 40)
    
    test_cases = [
        ("1 in [1, 2, 3]", {"stages_to_run": [1, 2, 3]}, True, "Stage 1 should run"),
        ("4 in [1, 2, 3]", {"stages_to_run": [1, 2, 3]}, False, "Stage 4 should NOT run"),
        ("2 in parameters.stages_to_run", {"stages_to_run": [1, 2]}, True, "Stage 2 with params"),
        ("3 in parameters.stages_to_run", {"stages_to_run": [1, 2]}, False, "Stage 3 not in params"),
    ]
    
    for condition, params, expected, description in test_cases:
        result = service._evaluate_condition(condition, params)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {description}: {condition} -> {result}")
    
    print("\n2. Testing strategy execution with conditions:")
    print("-" * 40)
    
    # Test executing strategy with stages_to_run = [1]
    print("\n   Testing with stages_to_run = [1]:")
    
    context = {
        "parameters": {
            "stages_to_run": [1],
            "debug_mode": True,
            "output_dir": "/tmp/biomapper/condition_test"
        }
    }
    
    try:
        result = await service.execute_strategy(
            strategy_name="met_arv_to_ukbb_progressive_v4.0",
            context=context
        )
        
        # Check if it succeeded without Stage 4 errors
        if "error" in result:
            if "HMDBVectorMatchAction" in str(result["error"]):
                print("   ❌ Stage 4 still executing (condition not working)")
            else:
                print(f"   ⚠️ Different error: {result['error']}")
        else:
            print("   ✅ Execution completed without Stage 4 errors!")
            
            # Check which datasets were created
            datasets = result.get("datasets", {})
            stage_keys = [k for k in datasets.keys() if "stage_" in k]
            print(f"   📊 Stage datasets created: {stage_keys}")
            
            # Verify only Stage 1 ran
            if any("stage_2" in k or "stage_3" in k or "stage_4" in k for k in stage_keys):
                print("   ⚠️ Warning: Higher stages ran when only Stage 1 requested")
            else:
                print("   ✅ Only Stage 1 executed as requested!")
                
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print("\n3. Testing progressive stage execution:")
    print("-" * 40)
    
    # Test with stages 1-2
    print("\n   Testing with stages_to_run = [1, 2]:")
    
    context["parameters"]["stages_to_run"] = [1, 2]
    
    try:
        result = await service.execute_strategy(
            strategy_name="met_arv_to_ukbb_progressive_v4.0",
            context=context
        )
        
        if "error" not in result:
            datasets = result.get("datasets", {})
            stage_keys = [k for k in datasets.keys() if "stage_" in k]
            
            has_stage1 = any("stage_1" in k for k in stage_keys)
            has_stage2 = any("stage_2" in k for k in stage_keys)
            has_stage3 = any("stage_3" in k for k in stage_keys)
            has_stage4 = any("stage_4" in k for k in stage_keys)
            
            print(f"      Stage 1: {'✅' if has_stage1 else '❌'}")
            print(f"      Stage 2: {'✅' if has_stage2 else '❌'}")
            print(f"      Stage 3: {'❌' if not has_stage3 else '⚠️ (should not run)'}")
            print(f"      Stage 4: {'❌' if not has_stage4 else '⚠️ (should not run)'}")
        else:
            print(f"   ❌ Error: {result['error']}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 70)
    print("CONDITION EVALUATION TEST COMPLETE")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    asyncio.run(test_condition_evaluation())