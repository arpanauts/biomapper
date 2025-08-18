# Pydantic Model Migration Guide

## Overview

This guide helps migrate Pydantic models in the biomapper project to use flexible base models that allow extra fields for backward compatibility.

## Problem Statement

Strict Pydantic models (default behavior with `extra='forbid'`) cause validation failures when:
- YAML strategies contain extra parameters not defined in the model
- New fields are added to models breaking existing strategies
- Debug/trace flags are passed but not explicitly defined
- Parameter names evolve over time

## Solution: Flexible Base Models

We've created a hierarchy of base models in `biomapper.core.standards.base_models` that provide flexibility while maintaining type safety.

## When to Use Each Base Model

### FlexibleBaseModel (Default for Most Cases)
Use for:
- Action parameters that may evolve
- Strategy configurations
- Any user-facing models
- Models that interface with YAML configurations
- Development and prototyping

**Example:**
```python
from biomapper.core.standards import FlexibleBaseModel

class MyConfigModel(FlexibleBaseModel):
    required_field: str
    optional_field: int = 10
    # Automatically accepts extra fields!
```

### ActionParamsBase (For All Strategy Actions)
Use for:
- All strategy action parameter models
- Actions that need debug/trace capabilities
- Actions with retry logic

**Example:**
```python
from biomapper.core.standards import ActionParamsBase

class MyActionParams(ActionParamsBase):
    input_key: str
    threshold: float = 0.8
    # Inherits debug, trace, timeout, retry fields
```

### DatasetOperationParams (For Dataset Operations)
Use for:
- Actions that read from and write to datasets
- Transformation operations
- Merge and filter operations

**Example:**
```python
from biomapper.core.standards import DatasetOperationParams

class TransformParams(DatasetOperationParams):
    transformation_type: str
    # Inherits input_key, output_key, plus all ActionParamsBase fields
```

### FileOperationParams (For File I/O)
Use for:
- Actions that read from or write to files
- Export operations
- Data loading operations

**Example:**
```python
from biomapper.core.standards import FileOperationParams

class LoadDataParams(FileOperationParams):
    delimiter: str = "\t"
    encoding: str = "utf-8"
    # Inherits file_path, create_dirs, plus all ActionParamsBase fields
```

### APIOperationParams (For External APIs)
Use for:
- Actions that call external APIs
- Enrichment operations
- Data fetching from remote sources

**Example:**
```python
from biomapper.core.standards import APIOperationParams

class EnrichmentParams(APIOperationParams):
    endpoint: str
    query_field: str
    # Inherits api_url, api_key, rate limits, plus all ActionParamsBase fields
```

### StrictBaseModel (Use Sparingly)
Use for:
- Internal data structures that must not change
- API responses with fixed schemas
- Security-critical validations
- Data exchange formats with external systems

**Example:**
```python
from biomapper.core.standards import StrictBaseModel

class SecurityToken(StrictBaseModel):
    token: str
    expires_at: datetime
    # Rejects any extra fields - use only when necessary!
```

## Migration Examples

### Before (Too Strict):
```python
from pydantic import BaseModel

class MergeParams(BaseModel):
    source_dataset_key: str
    target_dataset_key: str
    merge_strategy: str = "inner"
    # Problem: Rejects debug, trace, or any future fields!
```

### After (Flexible):
```python
from biomapper.core.standards import DatasetOperationParams

class MergeParams(DatasetOperationParams):
    source_dataset_key: str  # Additional to inherited input_key
    merge_strategy: str = "inner"
    # Accepts extra fields, includes debug/trace/timeout automatically
```

## Step-by-Step Migration Process

### 1. Identify the Model Type
Determine which base model is most appropriate:
- General parameters → `FlexibleBaseModel`
- Action parameters → `ActionParamsBase`
- Dataset operations → `DatasetOperationParams`
- File operations → `FileOperationParams`
- API operations → `APIOperationParams`

### 2. Update the Import
```python
# Before
from pydantic import BaseModel

# After
from biomapper.core.standards import ActionParamsBase  # or appropriate base
```

### 3. Change the Base Class
```python
# Before
class MyParams(BaseModel):

# After
class MyParams(ActionParamsBase):
```

### 4. Remove Redundant Fields
Remove fields that are now inherited:
```python
# Before
class MyParams(BaseModel):
    debug: bool = False  # Remove - inherited
    input_key: str
    output_key: str      # Remove if using DatasetOperationParams

# After
class MyParams(DatasetOperationParams):
    # Only keep unique fields
```

### 5. Handle Extra Fields if Needed
```python
class MyParams(ActionParamsBase):
    my_field: str
    
    def process(self, context):
        # Log any extra fields for debugging
        self.log_extra_fields()
        
        # Access extra fields if needed
        extra = self.get_extra_fields()
        if 'legacy_param' in extra:
            # Handle legacy parameter
            self.my_field = extra['legacy_param']
```

## Handling Legacy Parameters

### Using Field Aliases
```python
from pydantic import Field

class MyParams(ActionParamsBase):
    # Accept both 'output_key' and legacy 'dataset_key'
    output_key: str = Field(..., alias='dataset_key')
```

### Custom Migration Logic
```python
class MyParams(ActionParamsBase):
    current_name: str
    
    def migrate_legacy_params(self):
        """Handle old parameter names"""
        extra = self.get_extra_fields()
        
        # Map old names to new
        if 'old_name' in extra:
            self.current_name = extra['old_name']
            
        return self.model_dump()
```

## Testing Your Migration

### 1. Test with Extra Fields
```python
def test_accepts_extra_fields():
    params = MyParams(
        required_field="value",
        extra_field="should not fail",  # Extra field
        debug=True  # Common field
    )
    assert params.required_field == "value"
    assert params.debug is True
    assert params.get_extra_fields()['extra_field'] == "should not fail"
```

### 2. Test Backward Compatibility
```python
def test_legacy_parameters():
    # Old strategy YAML might have old parameter names
    params = MyParams(
        dataset_key="old_name",  # Legacy name
        new_field="value"
    )
    migrated = params.migrate_legacy_params()
    assert migrated['output_key'] == "old_name"
```

### 3. Test with Real YAML Strategies
```python
def test_yaml_strategy_compatibility():
    # Load actual strategy YAML
    with open("strategy.yaml") as f:
        config = yaml.safe_load(f)
    
    # Should not raise validation errors
    params = MyParams(**config['steps'][0]['params'])
    assert params.validate_params()
```

## Common Pitfalls and Solutions

### Pitfall 1: Forgetting to Import from standards
```python
# Wrong - uses strict Pydantic BaseModel
from pydantic import BaseModel
class MyParams(BaseModel): ...

# Right - uses flexible base
from biomapper.core.standards import ActionParamsBase
class MyParams(ActionParamsBase): ...
```

### Pitfall 2: Overriding model_config
```python
# Wrong - loses flexibility
class MyParams(ActionParamsBase):
    model_config = ConfigDict(extra='forbid')  # Don't do this!

# Right - extend config if needed
class MyParams(ActionParamsBase):
    # Inherit flexible config, add specifics if needed
    pass
```

### Pitfall 3: Not Handling Evolution
```python
# Wrong - brittle code
if hasattr(params, 'new_field'):
    value = params.new_field

# Right - graceful handling
value = getattr(params, 'new_field', default_value)
# or
extra = params.get_extra_fields()
value = extra.get('new_field', default_value)
```

## Validation Best Practices

### 1. Use Pydantic Validators
```python
from pydantic import field_validator

class MyParams(ActionParamsBase):
    file_path: str
    
    @field_validator('file_path')
    def validate_path(cls, v):
        if not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v
```

### 2. Override validate_params for Complex Logic
```python
class MyParams(ActionParamsBase):
    threshold: float
    
    def validate_params(self) -> bool:
        if not 0 <= self.threshold <= 1:
            logger.error(f"Invalid threshold: {self.threshold}")
            return False
        return super().validate_params()
```

### 3. Document Expected Fields
```python
class MyParams(ActionParamsBase):
    """Parameters for data transformation.
    
    Fields:
        input_key: Dataset key to transform
        transform_expr: Python expression for transformation
        
    Extra fields accepted:
        legacy_expr: Old parameter name for transform_expr
        verbose: Enable verbose logging (deprecated, use debug)
    """
    input_key: str = Field(..., description="Dataset to transform")
    transform_expr: str = Field(..., description="Transformation expression")
```

## Gradual Migration Strategy

### Phase 1: Create Base Models ✅
- Created flexible base models
- Established inheritance hierarchy
- Added utility methods

### Phase 2: Audit Existing Models
- Run audit script to find all models
- Categorize by urgency
- Identify breaking changes

### Phase 3: Migrate Critical Models
- Start with models causing failures
- Update one action at a time
- Test each migration

### Phase 4: Update Documentation
- Update action documentation
- Add migration notes
- Update example strategies

### Phase 5: Monitor and Iterate
- Log warnings for extra fields
- Collect usage patterns
- Refine base models as needed

## Success Metrics

✅ All models accept extra fields without failing
✅ 100% backward compatibility with existing YAML strategies
✅ No validation errors from extra parameters
✅ Debug/trace flags work on all actions
✅ Clear migration path for new developers
✅ Reduced maintenance burden for model evolution

## Getting Help

- Check existing migrated models in `biomapper/core/strategy_actions/`
- Run the audit script: `python scripts/audit_pydantic_models.py`
- Review test examples in `tests/test_model_flexibility.py`
- Ask team members who have completed migrations

## Related Documentation

- [Base Models API](../biomapper/core/standards/base_models.py)
- [Compatibility Layer](../biomapper/core/standards/compatibility.py)
- [Testing Guide](../tests/test_model_flexibility.py)
- [Action Development Guide](../CLAUDE.md#creating-new-strategy-actions)