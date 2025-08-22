#!/usr/bin/env python3
"""
Universal hook wrapper for BiOMapper validation scripts.
Adapts validation scripts to work with Claude Code's hook system.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


def run_tdd_check(file_path: str) -> int:
    """Run TDD enforcement check."""
    cmd = [sys.executable, '.claude/hooks/tdd_enforcer.py', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(result.stdout)
        if os.getenv('BIOMAPPER_HOOKS_MODE') == 'enforce_all':
            return 1  # Block
    return 0


def run_params_check(file_path: str) -> int:
    """Run parameter validation check."""
    cmd = [sys.executable, 'scripts/check_yaml_params.py', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(result.stdout)
        if os.getenv('BIOMAPPER_HOOKS_MODE') in ['enforce_all', 'enforce_new']:
            return 1  # Block
    return 0


def run_imports_check(file_path: str = None) -> int:
    """Run import verification check."""
    cmd = [sys.executable, 'scripts/check_import_paths.py']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("⚠️ Import issues detected:")
        print(result.stdout)
        # Don't block, just warn
    return 0


def run_victory_check() -> int:
    """Run victory blocker check."""
    mode = os.getenv('BIOMAPPER_HOOKS_MODE', 'warn')
    
    if mode == 'disabled':
        return 0
        
    cmd = [sys.executable, 'scripts/prevent_partial_victory.py']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(result.stdout)
        if mode in ['enforce_all', 'enforce_new']:
            print("\n🚫 Cannot declare success without validation")
            print("   Run: /diagnose")
            return 1  # Block
    return 0


def main():
    """Main hook wrapper entry point."""
    if len(sys.argv) < 2:
        print("Usage: hook_wrapper.py <check_type> [file_path]")
        sys.exit(1)
    
    check_type = sys.argv[1]
    file_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Route to appropriate checker
    if check_type == 'tdd':
        sys.exit(run_tdd_check(file_path))
    elif check_type == 'params':
        sys.exit(run_params_check(file_path))
    elif check_type == 'imports':
        sys.exit(run_imports_check(file_path))
    elif check_type == 'victory':
        sys.exit(run_victory_check())
    else:
        print(f"Unknown check type: {check_type}")
        sys.exit(1)


if __name__ == "__main__":
    main()