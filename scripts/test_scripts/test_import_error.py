#!/usr/bin/env python3
"""Test if the error occurs during import."""

import sys
import traceback
sys.path.insert(0, 'src')

print("Testing imports...")
print("-" * 40)

try:
    print("1. Importing registry...")
    from actions.registry import ACTION_REGISTRY
    print(f"   Registry has {len(ACTION_REGISTRY)} actions")
    
    print("\n2. Checking for HMDBVectorMatchAction...")
    if "HMDB_VECTOR_MATCH" in ACTION_REGISTRY:
        print("   HMDB_VECTOR_MATCH is registered")
        action_class = ACTION_REGISTRY["HMDB_VECTOR_MATCH"]
        print(f"   Class: {action_class.__name__}")
        
        # Try to instantiate it
        print("\n3. Instantiating HMDBVectorMatchAction...")
        action = action_class()
        print("   Instantiated successfully")
        
        # Check its execute_typed signature
        import inspect
        sig = inspect.signature(action.execute_typed)
        print(f"   execute_typed params: {list(sig.parameters.keys())}")
        
    print("\n4. Testing a simple execute call...")
    # This is what MinimalStrategyService does
    action = ACTION_REGISTRY["HMDB_VECTOR_MATCH"]()
    
    # Simulate the call
    print("   Simulating MinimalStrategyService call pattern...")
    import asyncio
    
    async def test_call():
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="metabolite",
            action_params={"input_key": "test", "output_key": "out"},
            source_endpoint=None,
            target_endpoint=None,
            context={"datasets": {}}
        )
        return result
        
    try:
        result = asyncio.run(test_call())
        print("   ✅ Execute succeeded")
    except Exception as e:
        print(f"   ❌ Execute failed: {e}")
        # Get the actual error
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_tb:
            # Find the frame where execute_typed is called
            while exc_tb:
                frame = exc_tb.tb_frame
                if 'execute_typed' in frame.f_code.co_name:
                    print(f"   Error in {frame.f_code.co_filename}:{exc_tb.tb_lineno}")
                    break
                exc_tb = exc_tb.tb_next
        
except Exception as e:
    print(f"\nError: {e}")
    traceback.print_exc()