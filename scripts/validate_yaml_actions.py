#!/usr/bin/env python3
"""
Validate that all action types in a YAML strategy file are registered in the biomapper system.
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, Set

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

# Import all actions to populate the registry
from biomapper.core.strategy_actions import *


def extract_action_types(config: Dict) -> Set[str]:
    """Extract all action types from a strategy configuration."""
    action_types = set()

    if "steps" in config:
        for step in config["steps"]:
            if "action" in step and "type" in step["action"]:
                action_types.add(step["action"]["type"])

    return action_types


def validate_yaml_actions(yaml_path: str) -> None:
    """Validate all action types in the YAML file are registered."""
    print(f"\n🔍 Validating action types in: {yaml_path}\n")

    # Load YAML
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    # Get registered actions
    registered_actions = set(ACTION_REGISTRY.keys())

    print(f"📋 Registered actions ({len(registered_actions)}):")
    for action in sorted(registered_actions):
        print(f"  ✓ {action}")

    # Extract action types from YAML
    yaml_actions = extract_action_types(config)

    print(f"\n📄 Actions used in YAML ({len(yaml_actions)}):")

    # Check each action
    all_valid = True
    for action in sorted(yaml_actions):
        if action in registered_actions:
            print(f"  ✅ {action}")
        else:
            print(f"  ❌ {action} (NOT REGISTERED)")
            all_valid = False

    # Summary
    print("\n" + "=" * 50)
    if all_valid:
        print("✅ All action types are valid and registered!")
    else:
        print("❌ Some action types are not registered.")
        print("   Please fix the unregistered actions or implement them.")
    print("=" * 50 + "\n")

    return all_valid


if __name__ == "__main__":
    yaml_file = "configs/strategies/metabolomics_progressive_enhancement.yaml"
    if len(sys.argv) > 1:
        yaml_file = sys.argv[1]

    validate_yaml_actions(yaml_file)
