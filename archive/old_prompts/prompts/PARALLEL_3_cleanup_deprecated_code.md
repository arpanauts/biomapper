# PARALLEL 3: Cleanup and Remove Deprecated Code

**Prerequisites: Can run in parallel with action implementations after PRIORITY_1 is complete**

## Problem Statement

The biomapper project has accumulated technical debt over time, including:
- Deprecated API v1 endpoints (old YAML strategies have been removed)
- Unused imports and dead code paths
- Duplicate functionality across modules
- Old test data and obsolete configuration files
- Inconsistent naming conventions
- Orphaned notebooks and scripts

## Objective

Systematically identify and safely remove deprecated code, consolidate duplicate functionality, and improve codebase maintainability.

## Analysis Phase

### 1. Inventory Current State

```bash
# Get baseline metrics
echo "=== Codebase Statistics ==="
find /home/ubuntu/biomapper -name "*.py" -type f | wc -l
find /home/ubuntu/biomapper -name "*.yaml" -type f | wc -l
find /home/ubuntu/biomapper -name "*.ipynb" -type f | wc -l

# Check for unused imports
echo "=== Checking for unused imports ==="
cd /home/ubuntu/biomapper
poetry run autoflake --check-diff -r biomapper/ biomapper-api/ biomapper_client/ | head -50

# Find potentially dead code
echo "=== Finding potentially dead code ==="
poetry run vulture biomapper/ --min-confidence 80 | head -50

# Check for duplicate code
echo "=== Checking for code duplication ==="
poetry run pylint --disable=all --enable=duplicate-code biomapper/ | head -50
```

### 2. API v1 Deprecation Analysis

Since old YAML strategies have been removed, investigate if API v1 is still needed:

```python
# Create analysis script
cat > /tmp/analyze_api_versions.py << 'EOF'
import os
import re
from pathlib import Path

def analyze_api_usage():
    """Analyze API version usage in codebase."""
    
    biomapper_root = Path("/home/ubuntu/biomapper")
    
    v1_references = []
    v2_references = []
    
    # Search for API version references
    for py_file in biomapper_root.rglob("*.py"):
        if "test" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            content = py_file.read_text()
            
            # Look for v1 API references
            if re.search(r'/api/v1/|api_v1|APIv1', content, re.IGNORECASE):
                v1_references.append(str(py_file))
            
            # Look for v2 API references
            if re.search(r'/api/v2/|api_v2|APIv2', content, re.IGNORECASE):
                v2_references.append(str(py_file))
                
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    print(f"\n=== API Version Analysis ===")
    print(f"Files referencing v1: {len(v1_references)}")
    for f in v1_references[:10]:
        print(f"  - {f}")
    
    print(f"\nFiles referencing v2: {len(v2_references)}")
    for f in v2_references[:10]:
        print(f"  - {f}")
    
    # Check router structure
    api_dir = biomapper_root / "biomapper-api" / "app" / "api"
    if api_dir.exists():
        print(f"\n=== API Router Structure ===")
        for router_file in api_dir.rglob("*.py"):
            print(f"  - {router_file.relative_to(biomapper_root)}")
    
    return v1_references, v2_references

if __name__ == "__main__":
    v1_refs, v2_refs = analyze_api_usage()
    
    # Recommendation
    print("\n=== Recommendation ===")
    if not v1_refs:
        print("✓ No v1 references found - safe to remove v1 entirely")
    elif len(v1_refs) < 5:
        print("⚠ Few v1 references remain - consider migration to v2")
    else:
        print("✗ Significant v1 usage - needs careful migration plan")
EOF

python /tmp/analyze_api_versions.py
```

## Cleanup Tasks

### Task 1: Remove API v1 (If Analysis Supports)

```python
# Create v1 removal script
cat > /tmp/remove_api_v1.py << 'EOF'
import os
import shutil
from pathlib import Path

def remove_api_v1():
    """Remove API v1 endpoints and related code."""
    
    biomapper_root = Path("/home/ubuntu/biomapper")
    removed_items = []
    
    # 1. Remove v1 router files
    v1_router = biomapper_root / "biomapper-api" / "app" / "api" / "v1"
    if v1_router.exists():
        print(f"Removing v1 router directory: {v1_router}")
        # shutil.rmtree(v1_router)  # Uncomment to actually remove
        removed_items.append(str(v1_router))
    
    # 2. Update main API router to remove v1 imports
    main_router = biomapper_root / "biomapper-api" / "app" / "api" / "__init__.py"
    if main_router.exists():
        content = main_router.read_text()
        # Remove v1 imports and includes
        new_content = re.sub(r'.*api\.v1.*\n', '', content)
        if content != new_content:
            print(f"Updating {main_router} to remove v1 references")
            # main_router.write_text(new_content)  # Uncomment to actually update
            removed_items.append(f"v1 references from {main_router}")
    
    # 3. Remove v1-specific models
    v1_models = biomapper_root / "biomapper-api" / "app" / "models" / "v1"
    if v1_models.exists():
        print(f"Removing v1 models: {v1_models}")
        # shutil.rmtree(v1_models)  # Uncomment to actually remove
        removed_items.append(str(v1_models))
    
    # 4. Update tests to remove v1 tests
    v1_tests = biomapper_root / "tests" / "api" / "v1"
    if v1_tests.exists():
        print(f"Removing v1 tests: {v1_tests}")
        # shutil.rmtree(v1_tests)  # Uncomment to actually remove
        removed_items.append(str(v1_tests))
    
    return removed_items

if __name__ == "__main__":
    items = remove_api_v1()
    print(f"\n=== Summary ===")
    print(f"Would remove {len(items)} items")
    print("\nTo actually perform removal, uncomment the action lines in the script")
EOF
```

### Task 2: Remove Unused Imports

```bash
# Auto-remove unused imports
cd /home/ubuntu/biomapper

# Dry run first
poetry run autoflake --check-diff -r --remove-all-unused-imports \
    biomapper/ biomapper-api/ biomapper_client/ > /tmp/unused_imports.diff

# Review the diff
echo "=== Unused Imports to Remove ==="
wc -l /tmp/unused_imports.diff

# If looks good, actually remove
poetry run autoflake --in-place -r --remove-all-unused-imports \
    biomapper/ biomapper-api/ biomapper_client/
```

### Task 3: Identify and Remove Dead Code

```python
# Create dead code analysis script
cat > /tmp/find_dead_code.py << 'EOF'
import ast
import os
from pathlib import Path
from collections import defaultdict

def find_unused_functions():
    """Find potentially unused functions."""
    
    biomapper_root = Path("/home/ubuntu/biomapper")
    
    # Collect all function definitions and calls
    definitions = defaultdict(list)
    calls = set()
    
    for py_file in biomapper_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
            
            # Find function definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    definitions[node.name].append(str(py_file))
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
                        
        except Exception as e:
            pass
    
    # Find unused functions
    unused = []
    for func_name, files in definitions.items():
        if func_name not in calls and not func_name.startswith('_'):
            # Skip test functions and special methods
            if not any(x in func_name for x in ['test_', '__', 'setUp', 'tearDown']):
                unused.append((func_name, files))
    
    print("=== Potentially Unused Functions ===")
    for func_name, files in sorted(unused)[:20]:
        print(f"{func_name}:")
        for f in files[:3]:
            print(f"  - {Path(f).relative_to(biomapper_root)}")
    
    return unused

if __name__ == "__main__":
    unused = find_unused_functions()
    print(f"\nFound {len(unused)} potentially unused functions")
EOF

python /tmp/find_dead_code.py
```

### Task 4: Consolidate Duplicate Code

```python
# Identify duplicate code patterns
cat > /tmp/find_duplicates.py << 'EOF'
import ast
import hashlib
from pathlib import Path
from collections import defaultdict

def find_duplicate_code():
    """Find duplicate code blocks."""
    
    biomapper_root = Path("/home/ubuntu/biomapper")
    code_hashes = defaultdict(list)
    
    for py_file in biomapper_root.rglob("*.py"):
        if "__pycache__" in str(py_file) or "test" in str(py_file):
            continue
            
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
            
            # Hash each function
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function body as string
                    func_str = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                    func_hash = hashlib.md5(func_str.encode()).hexdigest()
                    code_hashes[func_hash].append({
                        'file': str(py_file),
                        'function': node.name,
                        'lines': node.lineno
                    })
                    
        except Exception:
            pass
    
    # Find duplicates
    duplicates = {k: v for k, v in code_hashes.items() if len(v) > 1}
    
    print("=== Duplicate Code Blocks ===")
    for hash_val, locations in list(duplicates.items())[:10]:
        print(f"\nDuplicate found in {len(locations)} locations:")
        for loc in locations:
            print(f"  - {Path(loc['file']).relative_to(biomapper_root)}:{loc['lines']} ({loc['function']})")
    
    return duplicates

if __name__ == "__main__":
    duplicates = find_duplicate_code()
    print(f"\nFound {len(duplicates)} duplicate code blocks")
EOF

python /tmp/find_duplicates.py
```

### Task 5: Clean Up Old Files

```bash
# Find old/unused data files
echo "=== Old Test Data Files ==="
find /home/ubuntu/biomapper -name "*.csv" -o -name "*.tsv" -o -name "*.json" | \
    xargs ls -lt | tail -20

# Find empty directories
echo "=== Empty Directories ==="
find /home/ubuntu/biomapper -type d -empty

# Find backup files
echo "=== Backup Files ==="
find /home/ubuntu/biomapper -name "*.bak" -o -name "*~" -o -name "*.orig"

# Find large files that might be unnecessary
echo "=== Large Files (>10MB) ==="
find /home/ubuntu/biomapper -type f -size +10M -exec ls -lh {} \;
```

### Task 6: Standardize Naming Conventions

```python
# Check for naming convention violations
cat > /tmp/check_naming.py << 'EOF'
import re
from pathlib import Path

def check_naming_conventions():
    """Check for naming convention violations."""
    
    biomapper_root = Path("/home/ubuntu/biomapper")
    issues = []
    
    # Check Python files
    for py_file in biomapper_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        # Check file naming (should be snake_case)
        filename = py_file.stem
        if not re.match(r'^[a-z_][a-z0-9_]*$', filename) and filename != '__init__':
            issues.append(f"File naming: {py_file} (not snake_case)")
        
        try:
            content = py_file.read_text()
            
            # Check for camelCase variables (basic check)
            camel_vars = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', content)
            if camel_vars:
                issues.append(f"CamelCase variables in {py_file}: {camel_vars[:3]}")
                
        except Exception:
            pass
    
    # Check for inconsistent directory structure
    strategy_dirs = list(biomapper_root.glob("*/strategies"))
    if len(strategy_dirs) > 1:
        issues.append(f"Multiple strategy directories: {strategy_dirs}")
    
    print("=== Naming Convention Issues ===")
    for issue in issues[:30]:
        print(f"  - {issue}")
    
    return issues

if __name__ == "__main__":
    issues = check_naming_conventions()
    print(f"\nFound {len(issues)} naming convention issues")
EOF

python /tmp/check_naming.py
```

## Documentation of Changes

Create a comprehensive change log:

```markdown
# Biomapper Cleanup Report

## Date: [Current Date]

## Removed Components

### API v1 Removal
- Removed `/biomapper-api/app/api/v1/` directory
- Removed v1 router imports from main API
- Removed v1-specific models and schemas
- Updated all client code to use v2 endpoints
- **Justification**: Old YAML strategies removed, v1 no longer needed

### Unused Imports
- Removed [X] unused imports across [Y] files
- Most common: pandas, numpy, logging not used
- **Impact**: Reduced import time, cleaner code

### Dead Code
- Removed [X] unused functions
- Removed [Y] unreachable code blocks
- Removed [Z] commented-out code sections
- **Files affected**: [List main files]

### Duplicate Code
- Consolidated [X] duplicate functions into utilities
- Created shared modules for common patterns
- **New utility modules**: 
  - `biomapper/core/utils/common.py`
  - `biomapper/core/utils/validation.py`

### Old Files
- Removed [X] backup files (.bak, ~, .orig)
- Removed [Y] old test data files
- Removed [Z] empty directories
- **Space saved**: [X] MB

## Refactoring Performed

### Naming Standardization
- Renamed [X] files to follow snake_case convention
- Updated [Y] variable names from camelCase to snake_case
- Standardized action naming to UPPERCASE_WITH_UNDERSCORES

### Directory Structure
- Consolidated multiple strategy directories into single location
- Moved shared utilities to common location
- Organized tests to mirror source structure

## Migration Guide

### For API Users
```python
# Old (v1)
response = requests.post("http://localhost:8000/api/v1/strategies/execute")

# New (v2)
response = requests.post("http://localhost:8000/api/v2/strategies/execute")
```

### For Developers
- Import utilities from `biomapper.core.utils` instead of scattered locations
- Use standardized naming conventions (see CONTRIBUTING.md)
- Run pre-commit hooks to catch issues early

## Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Total Files | X | Y | -Z% |
| Lines of Code | X | Y | -Z% |
| Unused Imports | X | 0 | -100% |
| Duplicate Functions | X | Y | -Z% |
| Test Coverage | X% | Y% | +Z% |

## Risks and Rollback

### Identified Risks
1. Some internal tools may still reference v1 endpoints
2. Notebooks may import removed functions
3. Documentation may reference old structure

### Rollback Plan
1. All changes committed separately with clear messages
2. Can revert specific commits if issues found
3. Backup of removed files in `/tmp/biomapper_cleanup_backup/`

## Next Steps
1. Update all documentation to reflect changes
2. Run full test suite to ensure no regressions
3. Update CI/CD pipelines if needed
4. Notify team of breaking changes
```

## Success Criteria

1. ✅ API v1 completely removed (if analysis supports)
2. ✅ Zero unused imports remaining
3. ✅ Identified dead code documented and removed where safe
4. ✅ Duplicate code consolidated into shared utilities
5. ✅ Naming conventions standardized
6. ✅ All tests still pass after cleanup
7. ✅ Documentation updated to reflect changes
8. ✅ Codebase size reduced by at least 20%

## Safety Measures

1. **Create backup before starting**
   ```bash
   tar -czf /tmp/biomapper_backup_$(date +%Y%m%d).tar.gz /home/ubuntu/biomapper
   ```

2. **Use version control**
   - Create feature branch for cleanup
   - Make atomic commits for each type of change
   - Easy rollback if needed

3. **Test after each major change**
   ```bash
   poetry run pytest
   poetry run mypy biomapper biomapper-api biomapper_client
   ```

4. **Gradual approach**
   - Start with obvious removals (unused imports)
   - Move to safe removals (empty files, backups)
   - Careful with potentially used code
   - Get review before removing uncertain items

## Time Estimate

- Analysis phase: 1 hour
- API v1 removal: 1 hour
- Unused imports cleanup: 30 minutes
- Dead code identification and removal: 1.5 hours
- Duplicate code consolidation: 1.5 hours
- File cleanup and naming: 1 hour
- Documentation and testing: 1 hour
- **Total: 7.5 hours**

## Notes

- Prioritize safety over aggressive cleanup
- Keep detailed log of all changes
- Consider creating deprecation warnings before removal
- Some "dead code" may be used by external tools
- Focus on measurable improvements (file count, line count, test coverage)