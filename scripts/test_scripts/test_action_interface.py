#!/usr/bin/env python3
"""Test action interface compatibility issue."""

import sys
sys.path.insert(0, 'src')

from actions.registry import ACTION_REGISTRY

# Check the interface of each metabolite action
metabolite_actions = [
    "METABOLITE_NIGHTINGALE_BRIDGE",
    "METABOLITE_FUZZY_STRING_MATCH", 
    "METABOLITE_RAMPDB_BRIDGE",
    "HMDB_VECTOR_MATCH"
]

print("Checking action interfaces...")
print("-" * 40)

for action_name in metabolite_actions:
    if action_name in ACTION_REGISTRY:
        action_class = ACTION_REGISTRY[action_name]
        action = action_class()
        
        # Check execute method signature
        import inspect
        execute_sig = inspect.signature(action.execute)
        print(f"\n{action_name}:")
        print(f"  execute params: {list(execute_sig.parameters.keys())}")
        
        # Check if it has execute_typed
        if hasattr(action, 'execute_typed'):
            typed_sig = inspect.signature(action.execute_typed)
            print(f"  execute_typed params: {list(typed_sig.parameters.keys())}")
            
            # Check if it's a TypedStrategyAction
            if hasattr(action, 'get_params_model'):
                params_model = action.get_params_model()
                print(f"  params model: {params_model.__name__}")
    else:
        print(f"\n{action_name}: NOT REGISTERED")

print("\n" + "=" * 40)
print("Testing execute method compatibility...")

# Test calling execute with the expected signature
test_context = {"datasets": {}}
test_params = {"input_key": "test", "output_key": "test_out"}

for action_name in metabolite_actions[:1]:  # Just test first one
    if action_name in ACTION_REGISTRY:
        action_class = ACTION_REGISTRY[action_name]
        action = action_class()
        
        print(f"\nTesting {action_name}.execute()...")
        try:
            # Try the signature MinimalStrategyService uses
            result = action.execute(
                current_identifiers=[],
                current_ontology_type="metabolite",
                action_params=test_params,
                source_endpoint=None,
                target_endpoint=None,
                context=test_context
            )
            print(f"  ✅ Execute succeeded (sync)")
        except TypeError as e:
            print(f"  ❌ Execute failed: {e}")
            
            # Show what it's trying to call
            import inspect
            source = inspect.getsource(action.execute)
            # Find the execute_typed call
            if 'execute_typed' in source:
                print("  Calls execute_typed internally")
                
                # Try to find what parameters it passes
                import re
                typed_call = re.search(r'execute_typed\((.*?)\)', source, re.DOTALL)
                if typed_call:
                    print(f"  execute_typed call: {typed_call.group(1)[:100]}...")