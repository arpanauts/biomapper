# Import Path Resolution Fix

Systematically resolve BiOMapper import path issues.

USAGE: `/fix-imports [specific_module]`

## Diagnostic Process

### 1. Identify Import Failures
```bash
python scripts/check_import_paths.py --verbose
```

### 2. Common Fixes

#### PYTHONPATH Issues
```bash
# Fix: Add src to PYTHONPATH
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Permanent fix: Add to .bashrc or .zshrc
echo 'export PYTHONPATH="${PWD}/src:${PYTHONPATH}"' >> ~/.bashrc
```

#### Module Structure Issues
```bash
# Check for missing __init__.py files
find src/ -type d -exec sh -c 'test -f "$1/__init__.py" || echo "Missing: $1/__init__.py"' _ {} \;

# Create missing __init__.py files
find src/ -type d -exec touch {}/__init__.py \;
```

#### Action Registry Issues
```python
# Fix: Ensure action uses decorator
from actions.registry import register_action

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction):
    # ...
```

### 3. Validate Fix
```bash
# Test specific import
python -c "from actions.registry import ACTION_REGISTRY; print(f'Actions: {len(ACTION_REGISTRY)}')"

# Test all imports
python scripts/check_import_paths.py
```

## Common Import Patterns

### Correct Patterns
```python
# From src/actions/
from actions.registry import register_action
from core.minimal_strategy_service import MinimalStrategyService
from client.client_v2 import BiomapperClient
```

### Incorrect Patterns
```python
# DON'T use these
from biomapper.actions...  # Wrong prefix
from src.actions...        # Don't include src
import actions.module      # Use from...import
```

**Success Criteria**: All core modules import without errors.