#!/usr/bin/env python3
"""
Validate the metabolomics progressive enhancement YAML configuration.
Checks YAML syntax, JSON schema validation, and parameter interpolation.
"""

import yaml
import json
import sys
from pathlib import Path
from jsonschema import validate, ValidationError
from typing import Dict, Any, List

def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """Load and parse YAML configuration."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error in {file_path}:")
        print(f"   {e}")
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None

def validate_against_schema(config: Dict[str, Any], schema_path: Path) -> bool:
    """Validate configuration against JSON schema."""
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        validate(config, schema)
        print(f"✅ Configuration validates against schema")
        return True
    except ValidationError as e:
        print(f"❌ Schema validation error:")
        print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
        print(f"   Error: {e.message}")
        return False
    except FileNotFoundError:
        print(f"❌ Schema file not found: {schema_path}")
        return False

def check_parameter_references(config: Dict[str, Any]) -> List[str]:
    """Check for unresolved parameter references in the configuration."""
    issues = []
    
    def check_value(value: Any, path: str = "") -> None:
        if isinstance(value, str) and "${" in value and "}" in value:
            # Extract parameter reference
            start = value.find("${")
            end = value.find("}", start)
            if start != -1 and end != -1:
                param_ref = value[start+2:end]
                # Check if parameter exists
                param_parts = param_ref.split(".")
                if param_parts[0] == "parameters":
                    current = config.get("parameters", {})
                    for part in param_parts[1:]:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            issues.append(f"Unresolved parameter reference at {path}: {param_ref}")
                            break
        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                check_value(v, f"{path}[{i}]")
    
    check_value(config)
    return issues

def check_action_dependencies(config: Dict[str, Any]) -> List[str]:
    """Check that action dependencies are properly ordered."""
    issues = []
    available_keys = set()
    
    for i, step in enumerate(config.get("steps", [])):
        step_name = step.get("name", f"step_{i}")
        action = step.get("action", {})
        params = action.get("params", {})
        
        # Add output key to available keys FIRST
        output_key = params.get("output_key")
        if output_key:
            available_keys.add(output_key)
        
        # Check for dataset key dependencies (skip output_key param)
        for param_name, param_value in params.items():
            if param_name == "output_key":
                continue
            if isinstance(param_value, str) and (param_value.endswith("_data") or param_value.endswith("_matches") or param_value == "nightingale_reference"):
                if param_value not in available_keys and not param_value.startswith("unmatched."):
                    issues.append(f"Step '{step_name}' references undefined dataset key: {param_value}")
            elif param_name == "dataset_keys" and isinstance(param_value, list):
                for key in param_value:
                    if key not in available_keys:
                        issues.append(f"Step '{step_name}' references undefined dataset key: {key}")
        
        # Handle unmatched keys
        unmatched_source = params.get("unmatched_source_key")
        unmatched_target = params.get("unmatched_target_key")
        if unmatched_source:
            available_keys.add(unmatched_source)
        if unmatched_target:
            available_keys.add(unmatched_target)
    
    return issues

def main():
    """Main validation function."""
    print("🔍 Validating Metabolomics Progressive Enhancement Configuration\n")
    
    # Define paths
    config_dir = Path(__file__).parent.parent / "configs"
    strategy_file = config_dir / "strategies" / "metabolomics_progressive_enhancement.yaml"
    schema_file = config_dir / "schemas" / "metabolomics_strategy_schema.json"
    
    # Load configuration
    print(f"Loading configuration from: {strategy_file}")
    config = load_yaml_config(strategy_file)
    if not config:
        return 1
    
    print(f"✅ YAML syntax is valid\n")
    
    # Validate against schema
    print(f"Validating against schema: {schema_file}")
    if not validate_against_schema(config, schema_file):
        return 1
    print()
    
    # Check parameter references
    print("Checking parameter references...")
    param_issues = check_parameter_references(config)
    if param_issues:
        print("❌ Found parameter reference issues:")
        for issue in param_issues:
            print(f"   - {issue}")
        return 1
    else:
        print("✅ All parameter references are valid\n")
    
    # Check action dependencies
    print("Checking action dependencies...")
    dep_issues = check_action_dependencies(config)
    if dep_issues:
        print("❌ Found dependency issues:")
        for issue in dep_issues:
            print(f"   - {issue}")
        return 1
    else:
        print("✅ All action dependencies are properly ordered\n")
    
    # Summary statistics
    print("📊 Configuration Summary:")
    print(f"   - Total steps: {len(config.get('steps', []))}")
    print(f"   - Parameters defined: {len(config.get('parameters', {}))}")
    print(f"   - Expected outcomes: {config.get('metadata', {}).get('expected_outcomes', {})}")
    print(f"   - Error handling: {'enabled' if config.get('error_handling', {}).get('log_errors') else 'disabled'}")
    print(f"   - Logging level: {config.get('logging', {}).get('level', 'Not specified')}")
    
    # Check for required action types
    action_types = [step['action']['type'] for step in config.get('steps', [])]
    required_actions = [
        'LOAD_DATASET_IDENTIFIERS',
        'NIGHTINGALE_NMR_MATCH',
        'BUILD_NIGHTINGALE_REFERENCE',
        'BASELINE_FUZZY_MATCH',
        'CTS_ENRICHED_MATCH',
        'VECTOR_ENHANCED_MATCH'
    ]
    
    print("\n📋 Required Action Types:")
    for action in required_actions:
        if action in action_types:
            print(f"   ✅ {action}")
        else:
            print(f"   ❌ {action} (missing)")
    
    # Check client configurations
    print("\n🔧 Checking client configurations...")
    cts_config = config_dir / "clients" / "cts_config.yaml"
    qdrant_config = config_dir / "clients" / "qdrant_config.yaml"
    
    if cts_config.exists():
        cts_data = load_yaml_config(cts_config)
        if cts_data:
            print(f"   ✅ CTS configuration loaded: {cts_data.get('name', 'Unknown')}")
    else:
        print(f"   ❌ CTS configuration not found: {cts_config}")
    
    if qdrant_config.exists():
        qdrant_data = load_yaml_config(qdrant_config)
        if qdrant_data:
            print(f"   ✅ Qdrant configuration loaded: {qdrant_data.get('name', 'Unknown')}")
    else:
        print(f"   ❌ Qdrant configuration not found: {qdrant_config}")
    
    print("\n✨ Configuration validation complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())