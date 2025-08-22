#!/usr/bin/env python3
"""
Test the metabolomics pipeline directly with circuitous framework fixes.

🔄 This validates that the UniversalContext wrapper resolves context flow issues.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, 'src')

from core.minimal_strategy_service import MinimalStrategyService
from core.universal_context import UniversalContext
from core.circuitous_orchestration import apply_circuitous_orchestration


async def test_with_circuitous_fixes():
    """Test pipeline with circuitous orchestration applied."""
    
    print("\n" + "=" * 70)
    print("🔄 CIRCUITOUS FRAMEWORK PIPELINE TEST")
    print("=" * 70)
    
    # Create service
    strategies_dir = Path("src/configs/strategies")
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Apply circuitous orchestration
    apply_circuitous_orchestration(service)
    print("\n✅ Circuitous orchestration applied to service")
    
    # Test Stage 1 with circuitous context
    print("\n🔄 Testing Stage 1 with UniversalContext")
    print("-" * 40)
    
    # Create context with UniversalContext
    context = UniversalContext({
        "parameters": {
            "stages_to_run": [1],
            "debug_mode": True,
            "output_dir": "/tmp/biomapper/circuitous_stage1"
        }
    })
    
    try:
        result = await service.execute_strategy(
            strategy_name="test_stage1_only",  # Use simpler test strategy
            context=context
        )
        
        if result.get("success", False):
            print("   ✅ Stage 1 execution successful with circuitous fixes!")
            
            # Check datasets
            datasets = result.get("datasets", {})
            if datasets:
                print(f"   📊 Datasets created: {list(datasets.keys())[:5]}...")
                
                # Check for matched data
                if "stage_1_matched" in datasets or "nightingale_matched" in datasets:
                    matched_key = "nightingale_matched" if "nightingale_matched" in datasets else "stage_1_matched"
                    data = datasets[matched_key]
                    
                    if isinstance(data, dict) and "_row_count" in data:
                        count = data["_row_count"]
                        print(f"   📊 Stage 1 matched: {count} metabolites")
                        print(f"   📊 Coverage: {count/250*100:.1f}% (of 250 test metabolites)")
                    elif isinstance(data, list):
                        count = len(data)
                        print(f"   📊 Stage 1 matched: {count} metabolites")
            
            print("\n🔄 SUCCESS: Circuitous framework enables pipeline execution!")
            return True
        else:
            error = result.get("error", "Unknown error")
            print(f"   ❌ Execution failed: {error}")
            
            # Check if it's still the context issue
            if "has no attribute 'get'" in str(error):
                print("\n⚠️ Context issue still present - need to update action")
            elif "current_identifiers" in str(error):
                print("\n⚠️ Signature issue still present - need TypedStrategyAction fix")
            else:
                print("\n⚠️ New error type - investigate further")
            
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        
        # Analyze exception type
        import traceback
        tb = traceback.format_exc()
        
        if "has no attribute 'get'" in tb:
            print("\n⚠️ Actions still using dict methods on object context")
            print("   Need to ensure UniversalContext is used throughout")
        elif "current_identifiers" in tb:
            print("\n⚠️ TypedStrategyAction signature mismatch persists")
            print("   The base class fix may not be applied in runtime")
        
        return False


def main():
    """Run the circuitous pipeline test."""
    
    print("\n" + "🔄" * 35)
    print("\n🔄 CIRCUITOUS FRAMEWORK VALIDATION")
    print("\n   Testing if UniversalContext resolves pipeline issues...")
    print("\n" + "🔄" * 35)
    
    success = asyncio.run(test_with_circuitous_fixes())
    
    print("\n" + "=" * 70)
    print("🔄 FINAL ASSESSMENT")
    print("=" * 70)
    
    if success:
        print("\n✅ CIRCUITOUS FRAMEWORK SUCCESS!")
        print("   The UniversalContext wrapper successfully enables")
        print("   context flow through the pipeline without modifying")
        print("   individual action implementations.")
        print("\n🔄 Ready to proceed with full pipeline testing!")
    else:
        print("\n⚠️ ADDITIONAL FIXES NEEDED")
        print("   The circuitous framework provides the foundation but")
        print("   additional integration work is required to fully resolve")
        print("   the context flow issues in the runtime environment.")
    
    print("\n" + "🔄" * 35)


if __name__ == "__main__":
    main()