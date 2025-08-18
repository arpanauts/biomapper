# Typed Strategy Actions

This document describes the typed strategy action system in BioMapper, which provides type-safe, validated, and IDE-friendly strategy actions while maintaining backward compatibility with existing YAML strategies.

## Overview

The typed strategy action system introduces a new base class `TypedStrategyAction` that extends the existing `BaseStrategyAction` with:

- **Type Safety**: Pydantic models for parameters and results
- **Validation**: Automatic validation of parameter types and ranges
- **IDE Support**: Full autocomplete and type hints
- **Backward Compatibility**: Existing YAML strategies continue to work unchanged
- **Documentation**: Self-documenting code with clear parameter models

## Architecture

### Base Classes

- **`BaseStrategyAction`**: Original abstract base class
- **`TypedStrategyAction[TParams, TResult]`**: Generic typed base class
- **`StandardActionResult`**: Standard result model for common cases

### Key Components

1. **Parameter Models**: Pydantic models defining action parameters
2. **Result Models**: Pydantic models defining action results
3. **Compatibility Layer**: Automatic conversion between typed and dictionary formats
4. **Validation**: Built-in parameter validation with clear error messages

## Implementation Example

### Example: Creating a Typed Action

Here's how to create a typed action following the established patterns:

```python
from typing import Type, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from biomapper.actions.typed_base import TypedStrategyAction
from biomapper.actions.registry import register_action

class ProteinNormalizeParams(BaseModel):
    """Parameters for protein normalization action."""
    
    input_key: str = Field(
        ...,
        description="Key to retrieve input dataset from context",
        min_length=1
    )
    output_key: str = Field(
        ...,
        description="Key to store normalized dataset in context",
        min_length=1
    )
    remove_isoforms: bool = Field(
        default=True,
        description="Remove isoform suffixes (-1, -2, etc.)"
    )
    validate_format: bool = Field(
        default=True,
        description="Validate UniProt accession format"
    )
    
    @field_validator('input_key', 'output_key')
    @classmethod
    def validate_keys(cls, v: str) -> str:
        """Ensure keys are not empty or just whitespace."""
        if not v.strip():
            raise ValueError("Key cannot be empty or whitespace")
        return v.strip()


@register_action("PROTEIN_NORMALIZE_ACCESSIONS")
class ProteinNormalizeAction(TypedStrategyAction[ProteinNormalizeParams, ActionResult]):
    """Normalize and validate UniProt accessions."""
    
    def get_params_model(self) -> Type[ProteinNormalizeParams]:
        return ProteinNormalizeParams
    
    async def execute_typed(
        self,
        params: ProteinNormalizeParams,
        context: Dict[str, Any]
    ) -> ActionResult:
        # Access input data from context
        input_data = context["datasets"].get(params.input_key, [])
        if not input_data:
            return ActionResult(
                success=False,
                message=f"No data found for key: {params.input_key}"
            )
        
        # Normalize accessions
        normalized = []
        for item in input_data:
            accession = item.get("identifier", "")
            if params.remove_isoforms:
                accession = accession.split("-")[0]
            if params.validate_format:
                # UniProt format: [OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}
                if self._is_valid_uniprot(accession):
                    normalized.append({**item, "identifier": accession})
            else:
                normalized.append({**item, "identifier": accession})
        
        # Store results in context
        context["datasets"][params.output_key] = normalized
        
        # Track statistics
        context.setdefault("statistics", {}).update({
            f"{params.output_key}_count": len(normalized),
            f"{params.output_key}_removed": len(input_data) - len(normalized)
        })
        
        return ActionResult(
            success=True,
            message=f"Normalized {len(normalized)} of {len(input_data)} accessions",
            data={
                "normalized_count": len(normalized),
                "removed_count": len(input_data) - len(normalized)
            }
        )
    
    def _is_valid_uniprot(self, accession: str) -> bool:
        """Validate UniProt accession format."""
        import re
        pattern = r'^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$'
        return bool(re.match(pattern, accession))
```

## Benefits

### For Developers

1. **IDE Autocomplete**: Full parameter name completion
2. **Type Checking**: Compile-time type validation
3. **Documentation**: Self-documenting parameter models
4. **Refactoring**: Safe refactoring with IDE support
5. **Debugging**: Clear error messages for invalid parameters

### For Users

1. **Validation**: Parameter validation with clear error messages
2. **Documentation**: Built-in parameter documentation
3. **Reliability**: Fewer runtime errors due to typos
4. **Compatibility**: Existing YAML strategies work unchanged

## Migration Strategy

### Incremental Migration

Actions can be migrated one at a time:

1. **Phase 1**: Create typed version alongside legacy version
2. **Phase 2**: Update registration to use typed version
3. **Phase 3**: Remove legacy version after testing

### Example Migration

```python
# Old approach (legacy)
@register_action("MY_ACTION")
class MyAction(BaseStrategyAction):
    async def execute(self, params: Dict, context: Dict) -> Dict:
        # Dictionary-based implementation
        input_key = params.get("input_key")
        # Manual validation needed
        return {"success": True, "message": "Done"}

# New approach (typed)
@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyParams, ActionResult]):
    async def execute_typed(self, params: MyParams, context: Dict[str, Any]) -> ActionResult:
        # Typed implementation with automatic validation
        input_data = context["datasets"][params.input_key]  # Type-safe access
        return ActionResult(success=True, message="Done")
```

## Usage Examples

### Typed Usage (Recommended)

```python
# Create typed parameters with validation
params = ProteinNormalizeParams(
    input_key="raw_proteins",
    output_key="normalized_proteins",
    remove_isoforms=True,
    validate_format=True
)

# Execute with type safety
result = await action.execute_typed(
    params=params,
    context=context  # Shared execution context
)

# Access typed result fields
print(f"Success: {result.success}")
print(f"Message: {result.message}")
print(f"Normalized: {result.data['normalized_count']} proteins")
```

### Legacy Usage (Backward Compatible)

```python
# Legacy dictionary-based parameters (still works)
action_params = {
    'input_key': 'raw_proteins',
    'output_key': 'normalized_proteins',
    'remove_isoforms': True,
    'validate_format': True
}

# Execute with legacy interface (backward compatible)
result = await action.execute(
    params=action_params,
    context=context
)

# Access dictionary result
print(f"Success: {result['success']}")
print(f"Message: {result['message']}")
print(f"Data: {result['data']}")
```

## YAML Strategy Compatibility

Existing YAML strategies work unchanged:

```yaml
steps:
  - name: "normalize_proteins"
    action:
      type: "PROTEIN_NORMALIZE_ACCESSIONS"
    params:
      input_key: "raw_proteins"
      output_key: "normalized_proteins"
      remove_isoforms: true
      validate_format: true
```

The typed action will:
1. Parse YAML parameters into a dictionary
2. Convert dictionary to typed Pydantic model
3. Validate parameters
4. Execute typed implementation
5. Convert typed result back to dictionary

## Error Handling

### Parameter Validation Errors

```python
# Invalid parameters
try:
    params = ProteinNormalizeParams(
        input_key="",  # Invalid: empty string
        output_key="normalized",
        validate_format="yes"  # Invalid: must be bool
    )
except ValidationError as e:
    print("Validation errors:", e.errors())
    # Output: Shows field-specific validation errors with clear messages
```

### Runtime Errors

```python
# In typed mode - exceptions propagate
try:
    result = await action.execute_typed(...)
except ValueError as e:
    print("Execution error:", e)

# In legacy mode - errors returned in result
result = await action.execute(...)
if 'error' in result['details']:
    print("Execution error:", result['details']['error'])
```

## Best Practices

### Parameter Model Design

1. **Use descriptive field names**: `path_name` not `path`
2. **Add validation**: Use Pydantic validators for complex logic
3. **Provide defaults**: Set reasonable defaults for optional parameters
4. **Document fields**: Use `Field(description=...)` for documentation
5. **Validate ranges**: Use `gt`, `ge`, `lt`, `le` for numeric validation

### Result Model Design

1. **Extend StandardActionResult**: For consistency with existing system
2. **Add specific fields**: Include action-specific result data
3. **Use clear names**: Field names should be self-explanatory
4. **Validate results**: Add validators for complex result validation

### Testing

1. **Test both interfaces**: Test both typed and legacy execution
2. **Test validation**: Verify parameter validation works
3. **Test error handling**: Ensure errors are handled correctly
4. **Test compatibility**: Verify YAML strategies work unchanged

## Future Enhancements

### Planned Features

1. **Configuration Schema**: Generate JSON schema for YAML validation
2. **OpenAPI Integration**: Auto-generate API documentation
3. **Performance Optimization**: Optimize conversion between formats
4. **Advanced Validation**: More sophisticated parameter validation
5. **IDE Extensions**: Enhanced IDE support for YAML strategies

### Migration Status (as of 2025-08-14)

- **Completed**: ~35 of 37 actions migrated to TypedStrategyAction
- **In Progress**: Final 2-3 infrastructure actions (CHUNK_PROCESSOR remains flexible)
- **Next Phase**: Schema generation for YAML validation
- **Future**: Deprecate legacy BaseStrategyAction after full migration

## Conclusion

The typed strategy action system provides a modern, type-safe approach to implementing strategy actions while maintaining full backward compatibility. It improves developer experience, reduces errors, and provides better tooling support, all while ensuring existing YAML strategies continue to work unchanged.

The self-registering action pattern combined with Pydantic validation creates a robust, extensible system that's both powerful for developers and accessible for researchers creating YAML workflows.

---

---

## Verification Sources
*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- `/biomapper/src/biomapper/actions/typed_base.py` (TypedStrategyAction with dual context support and execute() compatibility wrapper)
- `/biomapper/src/biomapper/actions/registry.py` (Global ACTION_REGISTRY with @register_action decorator)
- `/biomapper/src/biomapper/actions/base.py` (BaseStrategyAction abstract base class)
- `/biomapper/src/biomapper/actions/entities/proteins/` (Typed protein actions with Pydantic parameter models)
- `/biomapper/tests/unit/core/strategy_actions/` (TDD unit tests with both typed and legacy interfaces)
- `/biomapper/CLAUDE.md` (Type safety migration status: ~35 of 37 actions completed)
- `/biomapper/README.md` (TypedStrategyAction adoption and backward compatibility guarantees)