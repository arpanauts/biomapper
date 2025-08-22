#!/usr/bin/env python3
"""
BiOMapper TDD Enforcer - Simple Test-Driven Development enforcement.
No external dependencies - pure Python implementation.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import json
from datetime import datetime


class TDDEnforcer:
    """Simple TDD enforcement for BiOMapper development."""
    
    def __init__(self):
        self.mode = os.getenv('BIOMAPPER_HOOKS_MODE', 'warn')
        self.cache_file = Path('.claude/hooks/.tdd_cache.json')
        self.cache = self._load_cache()
        
    def _load_cache(self) -> dict:
        """Load cache for performance optimization."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to disk."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def _get_test_path(self, implementation_path: Path) -> Path:
        """Map implementation file to test file."""
        # Convert src/actions/foo.py → tests/unit/core/strategy_actions/test_foo.py
        if 'src/actions' in str(implementation_path):
            test_path = str(implementation_path).replace('src/actions', 'tests/unit/core/strategy_actions')
            test_path = test_path.replace('.py', '.py')  # Keep .py extension
            # Add test_ prefix to filename
            parts = test_path.split('/')
            filename = parts[-1].replace('.py', '')
            parts[-1] = f'test_{filename}.py'
            return Path('/'.join(parts))
        
        # Generic mapping: src/foo/bar.py → tests/unit/foo/test_bar.py
        test_path = str(implementation_path).replace('src/', 'tests/unit/')
        parts = test_path.split('/')
        filename = parts[-1].replace('.py', '')
        parts[-1] = f'test_{filename}.py'
        return Path('/'.join(parts))
    
    def check_test_exists(self, file_path: str) -> Tuple[bool, str]:
        """Check if test exists for implementation file."""
        impl_path = Path(file_path)
        
        # Skip test files themselves
        if 'tests/' in str(impl_path) or 'test_' in impl_path.name:
            return True, "Test file - no TDD check needed"
        
        # Skip non-Python files
        if not file_path.endswith('.py'):
            return True, "Non-Python file - no TDD check needed"
        
        # Check cache first (5-minute TTL)
        cache_key = str(impl_path)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached['timestamp']) < 300:
                return cached['exists'], cached['message']
        
        # Check for test file
        test_path = self._get_test_path(impl_path)
        exists = test_path.exists()
        
        # Generate message
        if exists:
            message = f"✅ TDD: Test found at {test_path}"
        else:
            message = f"❌ TDD: Test required at {test_path}"
            
            if self.mode == 'enforce_all':
                message += "\n   Run: poetry run create-test " + str(impl_path)
                message += "\n   Or create manually and write failing tests first"
            elif self.mode == 'warn':
                message += "\n   ⚠️ Warning: Proceeding without test (not recommended)"
        
        # Update cache
        self.cache[cache_key] = {
            'exists': exists,
            'message': message,
            'timestamp': datetime.now().timestamp()
        }
        self._save_cache()
        
        return exists, message
    
    def enforce(self, file_path: str) -> bool:
        """Enforce TDD based on current mode."""
        exists, message = self.check_test_exists(file_path)
        
        print(message)
        
        if not exists:
            if self.mode == 'enforce_all':
                print("\n🚫 TDD ENFORCEMENT: Cannot proceed without test")
                print("   Create test first, then implement")
                return False
            elif self.mode == 'enforce_new':
                # Check if file is new (created in last 7 days)
                impl_path = Path(file_path)
                if impl_path.exists():
                    created = impl_path.stat().st_ctime
                    if (datetime.now().timestamp() - created) < (7 * 24 * 3600):
                        print("\n🚫 TDD ENFORCEMENT: New files require tests")
                        return False
        
        return True


def main():
    """CLI interface for TDD enforcement."""
    if len(sys.argv) < 2:
        print("Usage: tdd_enforcer.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    enforcer = TDDEnforcer()
    
    if not enforcer.enforce(file_path):
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()