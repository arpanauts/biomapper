# Strategy Validation

This module provides comprehensive validation for YAML strategy configurations.

## Usage

### Basic Validation

```python
from biomapper.core.validators import StrategyValidator

# Create a validator
validator = StrategyValidator(strict=True)

# Validate a strategy object
valid, errors = validator.validate_strategy(strategy)
if not valid:
    for error in errors:
        print(f"Validation error: {error}")
```

### Loading and Validating YAML Files

```python
from biomapper.core.validators import load_and_validate_strategy
from pathlib import Path

# Load and validate in one step
try:
    strategy = load_and_validate_strategy(Path("my_strategy.yaml"))
    print(f"Loaded strategy: {strategy.name}")
except ConfigurationError as e:
    print(f"Invalid strategy: {e}")
```

### Validating YAML Strings

```python
from biomapper.core.validators import StrategyValidator

yaml_content = """
name: MY_STRATEGY
steps:
  - name: LOAD_DATA
    action:
      type: LOAD_ENDPOINT_IDENTIFIERS
      params:
        endpoint_context: SOURCE
        input_ids_context_key: source_ids
"""

valid, errors = StrategyValidator.validate_yaml_string(yaml_content)
```

## Validation Rules

1. **Strategy Structure**
   - Must have a name
   - Must have at least one step
   - Each step must have a name and action

2. **Action Validation**
   - Action type must be registered in ACTION_REGISTRY
   - Required parameters must be present
   - Unknown parameters fail in strict mode, pass in lenient mode

3. **Parameter Schemas**
   - Each action type can define required and optional parameters
   - Parameters are validated against these schemas
   - Actions without schemas skip parameter validation

## Integration with Existing Code

To integrate validation into the strategy loading process:

```python
# In strategy_handler.py or similar
from biomapper.core.validators import StrategyValidator

async def load_strategy_from_yaml(yaml_path: Path) -> Strategy:
    """Load and validate a strategy from YAML."""
    # Validate first
    validator = StrategyValidator(strict=True)
    valid, errors = validator.validate_yaml_file(yaml_path)
    
    if not valid:
        logger.error(f"Invalid strategy in {yaml_path}:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ConfigurationError(f"Invalid strategy: {'; '.join(errors)}")
    
    # Load if valid
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return Strategy(**data)
```

## Adding New Action Schemas

To add parameter validation for a new action:

1. Add the schema to `StrategyValidator.ACTION_SCHEMAS`:

```python
ACTION_SCHEMAS = {
    # ... existing schemas ...
    "MY_NEW_ACTION": {
        "required": ["param1", "param2"],
        "optional": ["param3", "param4"]
    }
}
```

2. The validator will automatically use this schema when validating strategies that use `MY_NEW_ACTION`.

## Strict vs Lenient Mode

- **Strict mode** (`strict=True`): Unknown parameters cause validation errors
- **Lenient mode** (`strict=False`): Unknown parameters are allowed (useful for forward compatibility)