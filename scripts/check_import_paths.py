#!/usr/bin/env python3
"""
Check import paths for BiOMapper modules.
Ensures PYTHONPATH is configured correctly and modules can be imported.
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple


def check_pythonpath() -> Tuple[bool, List[str]]:
    """Verify PYTHONPATH includes necessary directories."""
    issues = []
    src_path = Path.cwd() / 'src'
    
    # Check if src is in PYTHONPATH
    if str(src_path) not in sys.path:
        # Try to add it
        sys.path.insert(0, str(src_path))
        issues.append(f"⚠️ Added {src_path} to PYTHONPATH (was missing)")
    
    # Check environment variable
    pythonpath = os.environ.get('PYTHONPATH', '')
    if 'src' not in pythonpath:
        issues.append("⚠️ PYTHONPATH env variable doesn't include 'src' directory")
        issues.append("   Run: export PYTHONPATH=\"${PWD}/src:${PYTHONPATH}\"")
    
    return len(issues) == 0, issues


def check_biomapper_imports() -> Tuple[bool, List[str]]:
    """Verify core BiOMapper modules can be imported."""
    issues = []
    
    critical_imports = [
        ('actions.registry', 'ACTION_REGISTRY'),
        ('core.minimal_strategy_service', 'MinimalStrategyService'),
        ('core.context_adapter', 'ContextAdapter'),
        ('client.client_v2', 'BiomapperClient')
    ]
    
    for module_name, object_name in critical_imports:
        try:
            module = __import__(module_name, fromlist=[object_name])
            obj = getattr(module, object_name, None)
            
            if obj is None:
                issues.append(f"❌ Cannot find {object_name} in {module_name}")
            else:
                print(f"✅ Successfully imported {module_name}.{object_name}")
                
        except ImportError as e:
            issues.append(f"❌ Cannot import {module_name}: {e}")
        except Exception as e:
            issues.append(f"❌ Error loading {module_name}: {e}")
    
    return len(issues) == 0, issues


def check_action_registry() -> Tuple[bool, List[str]]:
    """Verify action registry is populated."""
    issues = []
    
    try:
        from actions.registry import ACTION_REGISTRY
        
        action_count = len(ACTION_REGISTRY)
        
        if action_count == 0:
            issues.append("❌ Action registry is empty - no actions loaded")
            issues.append("   Check that action files use @register_action decorator")
        else:
            print(f"✅ Action registry loaded with {action_count} actions")
            
            # Check for critical actions
            critical_actions = [
                'LOAD_DATASET_IDENTIFIERS',
                'MERGE_DATASETS',
                'EXPORT_DATASET'
            ]
            
            for action in critical_actions:
                if action not in ACTION_REGISTRY:
                    issues.append(f"⚠️ Critical action missing: {action}")
                    
    except ImportError as e:
        issues.append(f"❌ Cannot import action registry: {e}")
    
    return len(issues) == 0, issues


def check_module_structure() -> Tuple[bool, List[str]]:
    """Verify expected module structure exists."""
    issues = []
    
    expected_dirs = [
        'src/actions',
        'src/api',
        'src/client',
        'src/core',
        'src/configs/strategies',
        'tests/unit',
        'tests/integration'
    ]
    
    for dir_path in expected_dirs:
        path = Path(dir_path)
        if not path.exists():
            issues.append(f"❌ Missing directory: {dir_path}")
        else:
            # Check for __init__.py
            init_file = path / '__init__.py'
            if not init_file.exists() and 'configs' not in str(path):
                issues.append(f"⚠️ Missing __init__.py in {dir_path}")
    
    return len(issues) == 0, issues


def main():
    """CLI interface for import path checking."""
    print("🔍 Checking BiOMapper import paths...")
    print("=" * 50)
    
    all_valid = True
    
    # Check PYTHONPATH
    valid, issues = check_pythonpath()
    if not valid:
        all_valid = False
        print("PYTHONPATH Issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ PYTHONPATH configured correctly")
    
    # Check module structure
    valid, issues = check_module_structure()
    if not valid:
        all_valid = False
        print("\nModule Structure Issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ Module structure intact")
    
    # Check imports
    valid, issues = check_biomapper_imports()
    if not valid:
        all_valid = False
        print("\nImport Issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ Core modules import successfully")
    
    # Check action registry
    valid, issues = check_action_registry()
    if not valid:
        all_valid = False
        print("\nAction Registry Issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ Action registry populated")
    
    print("=" * 50)
    
    if all_valid:
        print("✅ All import paths validated successfully")
        sys.exit(0)
    else:
        print("❌ Import path issues detected - fix before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()