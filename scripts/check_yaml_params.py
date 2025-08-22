#!/usr/bin/env python3
"""
Check YAML parameter substitution for BiOMapper strategies.
Validates that all ${parameters.x} patterns will resolve correctly at runtime.
"""

import sys
import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple


def find_parameter_references(content: str) -> List[str]:
    """Find all ${parameters.x} and ${x} patterns in YAML content."""
    patterns = []
    
    # Find ${parameters.key} patterns
    param_pattern = r'\$\{parameters\.([^}]+)\}'
    patterns.extend(re.findall(param_pattern, content))
    
    # Find ${KEY} environment variable patterns
    env_pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
    env_vars = re.findall(env_pattern, content)
    
    # Filter out parameters. prefix from env vars
    env_vars = [v for v in env_vars if not v.startswith('parameters.')]
    
    return patterns, env_vars


def validate_parameter_substitution(yaml_file: Path) -> Tuple[bool, List[str]]:
    """Validate that all parameters in a YAML file will resolve."""
    issues = []
    
    try:
        with open(yaml_file, 'r') as f:
            content = f.read()
            yaml_data = yaml.safe_load(content)
    except Exception as e:
        return False, [f"Failed to load YAML: {e}"]
    
    # Extract defined parameters
    defined_params = {}
    if yaml_data and 'parameters' in yaml_data:
        defined_params = yaml_data['parameters'] or {}
    
    # Find all parameter references
    param_refs, env_refs = find_parameter_references(content)
    
    # Check parameter references
    for param in param_refs:
        if param not in defined_params:
            issues.append(f"❌ Parameter '${{{param}}}' not defined in parameters section")
        elif defined_params[param] is None:
            issues.append(f"⚠️ Parameter '${{{param}}}' is defined but has None value")
    
    # Check environment variable references
    import os
    for env_var in env_refs:
        if env_var not in os.environ:
            # Check if it has a default value
            default_pattern = rf'\$\{{{env_var}:-([^}}]+)\}}'
            if not re.search(default_pattern, content):
                issues.append(f"⚠️ Environment variable '${{{env_var}}}' not set and no default provided")
    
    # Check for hardcoded paths (anti-pattern)
    hardcoded_patterns = [
        r'/home/[^/]+/',  # User home directories
        r'/Users/[^/]+/',  # macOS user directories
        r'C:\\Users\\',    # Windows paths
        r'/tmp/biomapper/' # Hardcoded temp paths without variables
    ]
    
    for pattern in hardcoded_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"⚠️ Hardcoded path detected: {matches[0]} - use parameters instead")
    
    return len(issues) == 0, issues


def check_all_strategies(strategy_dir: Path = None) -> Tuple[bool, Dict[str, List[str]]]:
    """Check all strategy YAML files in a directory."""
    if strategy_dir is None:
        strategy_dir = Path('src/configs/strategies')
    
    if not strategy_dir.exists():
        return False, {"error": [f"Strategy directory not found: {strategy_dir}"]}
    
    all_issues = {}
    all_valid = True
    
    for yaml_file in strategy_dir.rglob('*.yaml'):
        # Skip backup files
        if '.backup' in str(yaml_file):
            continue
            
        valid, issues = validate_parameter_substitution(yaml_file)
        if not valid:
            all_valid = False
            all_issues[str(yaml_file)] = issues
    
    return all_valid, all_issues


def main():
    """CLI interface for parameter validation."""
    if len(sys.argv) > 1:
        # Check specific file
        yaml_file = Path(sys.argv[1])
        if not yaml_file.exists():
            print(f"❌ File not found: {yaml_file}")
            sys.exit(1)
        
        valid, issues = validate_parameter_substitution(yaml_file)
        
        if valid:
            print(f"✅ All parameters in {yaml_file.name} will resolve correctly")
        else:
            print(f"❌ Parameter issues in {yaml_file.name}:")
            for issue in issues:
                print(f"   {issue}")
            sys.exit(1)
    else:
        # Check all strategies
        print("🔍 Checking all BiOMapper strategy YAML files...")
        valid, all_issues = check_all_strategies()
        
        if valid:
            print("✅ All strategy parameters validated successfully")
        else:
            print("❌ Parameter substitution issues found:")
            for file, issues in all_issues.items():
                print(f"\n{file}:")
                for issue in issues:
                    print(f"   {issue}")
            
            print(f"\n📊 Summary: {len(all_issues)} files with issues")
            sys.exit(1)


if __name__ == "__main__":
    main()