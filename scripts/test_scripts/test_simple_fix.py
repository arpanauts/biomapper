#!/usr/bin/env python3
"""
Simple test to verify the progressive pipeline works with minimal fixes.

🔄 This applies targeted fixes to enable context flow.
"""

import sys
sys.path.insert(0, 'src')

# Apply minimal fixes to the specific actions that need them
def apply_minimal_fixes():
    """Apply minimal targeted fixes to enable pipeline execution."""
    
    print("🔄 Applying minimal circuitous fixes...")
    
    # Fix Stage 2: METABOLITE_FUZZY_STRING_MATCH
    try:
        from actions.entities.metabolites.matching.fuzzy_string_match import MetaboliteFuzzyStringMatch
        
        # Wrap the execute_typed method to handle context properly
        original_execute_typed = MetaboliteFuzzyStringMatch.execute_typed
        
        async def fixed_execute_typed(self, params, context):
            # Ensure context works with .get() method
            if not hasattr(context, 'get'):
                # Wrap in dict-like interface
                class ContextWrapper:
                    def __init__(self, ctx):
                        self._ctx = ctx
                    
                    def get(self, key, default=None):
                        if hasattr(self._ctx, key):
                            return getattr(self._ctx, key)
                        elif hasattr(self._ctx, 'get'):
                            return self._ctx.get(key, default)
                        return default
                    
                    def __setitem__(self, key, value):
                        if hasattr(self._ctx, '__setitem__'):
                            self._ctx[key] = value
                        else:
                            setattr(self._ctx, key, value)
                    
                    def __getitem__(self, key):
                        if hasattr(self._ctx, '__getitem__'):
                            return self._ctx[key]
                        return getattr(self._ctx, key)
                
                context = ContextWrapper(context)
            
            return await original_execute_typed(self, params, context)
        
        MetaboliteFuzzyStringMatch.execute_typed = fixed_execute_typed
        print("   ✅ Fixed Stage 2 (Fuzzy String Match)")
    except Exception as e:
        print(f"   ⚠️ Could not fix Stage 2: {e}")
    
    # Fix Stage 3: METABOLITE_RAMPDB_BRIDGE
    try:
        from actions.entities.metabolites.matching.rampdb_bridge import MetaboliteRampdbBridge
        
        original_execute_typed = MetaboliteRampdbBridge.execute_typed
        
        async def fixed_execute_typed(self, params, context):
            # Same wrapper approach
            if not hasattr(context, 'get'):
                class ContextWrapper:
                    def __init__(self, ctx):
                        self._ctx = ctx
                    
                    def get(self, key, default=None):
                        if hasattr(self._ctx, key):
                            return getattr(self._ctx, key)
                        elif hasattr(self._ctx, 'get'):
                            return self._ctx.get(key, default)
                        return default
                    
                    def __setitem__(self, key, value):
                        if hasattr(self._ctx, '__setitem__'):
                            self._ctx[key] = value
                        else:
                            setattr(self._ctx, key, value)
                
                context = ContextWrapper(context)
            
            return await original_execute_typed(self, params, context)
        
        MetaboliteRampdbBridge.execute_typed = fixed_execute_typed
        print("   ✅ Fixed Stage 3 (RampDB Bridge)")
    except Exception as e:
        print(f"   ⚠️ Could not fix Stage 3: {e}")
    
    print("🔄 Minimal fixes applied\n")


def test_pipeline_with_fixes():
    """Test the pipeline after applying fixes."""
    
    from client.client_v2 import BiomapperClient
    
    print("=" * 70)
    print("🔄 TESTING PIPELINE WITH MINIMAL CIRCUITOUS FIXES")
    print("=" * 70)
    
    client = BiomapperClient(base_url="http://localhost:8001", timeout=120)
    
    # Test progressively
    tests = [
        ("Stage 1 Only", [1]),
        ("Stages 1-2", [1, 2]),
        ("Stages 1-3", [1, 2, 3])
    ]
    
    for test_name, stages in tests:
        print(f"\n🔄 Testing {test_name}")
        print("-" * 40)
        
        try:
            result = client.run(
                "met_arv_to_ukbb_progressive_v4.0",
                parameters={
                    "stages_to_run": stages,
                    "debug_mode": True,
                    "output_dir": f"/tmp/biomapper/simple_fix_stage_{max(stages)}"
                }
            )
            
            if result.success:
                print(f"   ✅ SUCCESS! {test_name} executed")
                
                # Check for datasets
                if result.result_data and "datasets" in result.result_data:
                    datasets = result.result_data["datasets"]
                    
                    # Count coverage for each stage
                    for stage_num in stages:
                        for key_variant in [f"stage_{stage_num}_matched", f"stage_{stage_num}_matched_debug"]:
                            if key_variant in datasets:
                                data = datasets[key_variant]
                                if isinstance(data, dict) and "_row_count" in data:
                                    count = data["_row_count"]
                                    print(f"      Stage {stage_num}: {count} metabolites matched")
                                    break
            else:
                print(f"   ❌ Failed: {result.error}")
                
                # Check error type
                if "has no attribute 'get'" in str(result.error):
                    print("      (Context interface issue)")
                elif "current_identifiers" in str(result.error):
                    print("      (Signature mismatch issue)")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n" + "=" * 70)
    print("🔄 TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    # Apply fixes first
    apply_minimal_fixes()
    
    # Then test
    test_pipeline_with_fixes()