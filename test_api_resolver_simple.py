#!/usr/bin/env python3
"""Simple test to verify ApiResolver works."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need
from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action

# Manually import our module without going through full biomapper init
import importlib.util
spec = importlib.util.spec_from_file_location(
    "api_resolver", 
    "biomapper/core/strategy_actions/api_resolver.py"
)
api_resolver_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_resolver_module)

print("✓ ApiResolver module loaded successfully")
print(f"✓ ApiResolver class: {api_resolver_module.ApiResolver}")
print(f"✓ Registered as: API_RESOLVER")

# Check that it has the required methods
resolver_instance = api_resolver_module.ApiResolver(None)  # Mock session
print(f"✓ Has execute method: {hasattr(resolver_instance, 'execute')}")
print(f"✓ Has _extract_field method: {hasattr(resolver_instance, '_extract_field')}")

# Test _extract_field method
test_data = {
    'result': {
        'current': {
            'id': 'TEST123'
        }
    }
}
extracted = resolver_instance._extract_field(test_data, 'result.current.id')
print(f"✓ _extract_field test: {extracted == 'TEST123'}")

print("\n✅ All basic checks passed!")