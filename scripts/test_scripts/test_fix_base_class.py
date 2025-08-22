#!/usr/bin/env python3
"""Test a fix for the TypedStrategyAction base class."""

import sys
import inspect
sys.path.insert(0, 'src')

# Check the signature of execute_typed for each action
from actions.registry import ACTION_REGISTRY

metabolite_actions = [
    "METABOLITE_NIGHTINGALE_BRIDGE",
    "METABOLITE_FUZZY_STRING_MATCH", 
    "METABOLITE_RAMPDB_BRIDGE",
    "HMDB_VECTOR_MATCH"
]

print("Analyzing execute_typed signatures...")
print("-" * 40)

signatures = {}
for action_name in metabolite_actions:
    if action_name in ACTION_REGISTRY:
        action_class = ACTION_REGISTRY[action_name]
        action = action_class()
        
        if hasattr(action, 'execute_typed'):
            sig = inspect.signature(action.execute_typed)
            params = list(sig.parameters.keys())
            signatures[action_name] = params
            print(f"{action_name}:")
            print(f"  Parameters: {params}")
            
            # Determine signature type
            if len(params) == 2:
                print(f"  Type: SIMPLIFIED (params, context)")
            elif len(params) == 6:
                print(f"  Type: FULL (all parameters)")
            else:
                print(f"  Type: UNKNOWN")

print("\n" + "=" * 40)
print("Recommendation:")
print("-" * 40)

# Count signature types
simplified = sum(1 for params in signatures.values() if len(params) == 2)
full = sum(1 for params in signatures.values() if len(params) == 6)

print(f"Actions with SIMPLIFIED signature: {simplified}")
print(f"Actions with FULL signature: {full}")

if simplified > 0 and full > 0:
    print("\n⚠️ MIXED SIGNATURES DETECTED!")
    print("The TypedStrategyAction.execute() method needs to handle both:")
    print("1. Old: execute_typed(current_identifiers, ontology, params, source, target, context)")
    print("2. New: execute_typed(params, context)")
    print("\nSolution: Update TypedStrategyAction.execute() to detect signature type")
    print("and call execute_typed() with appropriate parameters.")
else:
    print("\n✅ All actions use the same signature type")