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

### ExecuteMappingPathAction Refactor

The `ExecuteMappingPathAction` has been refactored to use the typed system:

```python
from typing import Type, List
from pydantic import BaseModel, Field, field_validator

class ExecuteMappingPathParams(BaseModel):
    """Parameters for ExecuteMappingPathAction."""
    
    path_name: str = Field(
        ...,
        description="Name of the mapping path to execute",
        min_length=1
    )
    batch_size: int = Field(
        default=250,
        description="Batch size for processing identifiers",
        gt=0,
        le=1000
    )
    min_confidence: float = Field(
        default=0.0,
        description="Minimum confidence score to accept a mapping",
        ge=0.0,
        le=1.0
    )
    
    @field_validator('path_name')
    @classmethod
    def validate_path_name(cls, v: str) -> str:
        """Ensure path name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("path_name cannot be empty or whitespace")
        return v.strip()


class ExecuteMappingPathResult(StandardActionResult):
    """Result of executing a mapping path."""
    
    path_source_type: str = Field(description="Source type of the mapping path")
    path_target_type: str = Field(description="Target type of the mapping path")
    total_input: int = Field(description="Total number of input identifiers")
    total_mapped: int = Field(description="Total number of successfully mapped identifiers")
    total_unmapped: int = Field(description="Total number of unmapped identifiers")


class ExecuteMappingPathTypedAction(TypedStrategyAction[ExecuteMappingPathParams, ExecuteMappingPathResult]):
    """Typed implementation of ExecuteMappingPathAction."""
    
    def get_params_model(self) -> Type[ExecuteMappingPathParams]:
        return ExecuteMappingPathParams
    
    def get_result_model(self) -> Type[ExecuteMappingPathResult]:
        return ExecuteMappingPathResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ExecuteMappingPathParams,
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: StrategyExecutionContext
    ) -> ExecuteMappingPathResult:
        # Implementation with full type safety
        # ...
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
# Old approach
@register_action("EXECUTE_MAPPING_PATH")
class ExecuteMappingPathAction(StrategyAction):
    async def execute(self, ...):
        # Dictionary-based implementation
        pass

# New approach
@register_action("EXECUTE_MAPPING_PATH")
class ExecuteMappingPathTypedAction(TypedStrategyAction[...]):
    async def execute_typed(self, ...):
        # Typed implementation
        pass
```

## Usage Examples

### Typed Usage (Recommended)

```python
# Create typed parameters with validation
params = ExecuteMappingPathParams(
    path_name="uniprot_to_ensembl",
    batch_size=100,
    min_confidence=0.8
)

# Execute with type safety
result = await action.execute_typed(
    current_identifiers=["P12345", "Q67890"],
    current_ontology_type="PROTEIN_UNIPROT",
    params=params,
    source_endpoint=source_endpoint,
    target_endpoint=target_endpoint,
    context=context
)

# Access typed result fields
print(f"Mapped {result.total_mapped} of {result.total_input} identifiers")
print(f"Path: {result.path_source_type} -> {result.path_target_type}")
```

### Legacy Usage (Backward Compatible)

```python
# Legacy dictionary-based parameters
action_params = {
    'path_name': 'uniprot_to_ensembl',
    'batch_size': 100,
    'min_confidence': 0.8
}

# Execute with legacy interface
result = await action.execute(
    current_identifiers=["P12345", "Q67890"],
    current_ontology_type="PROTEIN_UNIPROT",
    action_params=action_params,
    source_endpoint=source_endpoint,
    target_endpoint=target_endpoint,
    context=context
)

# Access dictionary result
print(f"Output IDs: {result['output_identifiers']}")
print(f"Details: {result['details']}")
```

## YAML Strategy Compatibility

Existing YAML strategies work unchanged:

```yaml
steps:
  - name: "execute_mapping_path"
    action: "EXECUTE_MAPPING_PATH"
    description: "Map UniProt to Ensembl"
    params:
      path_name: "uniprot_to_ensembl"
      batch_size: 250
      min_confidence: 0.75
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
    params = ExecuteMappingPathParams(
        path_name="",  # Invalid: empty string
        batch_size=0   # Invalid: must be > 0
    )
except ValidationError as e:
    print("Validation errors:", e.errors())
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

### Migration Timeline

- **Phase 1**: Core actions (ExecuteMappingPath, FilterByTargetPresence)
- **Phase 2**: Utility actions (GenerateReport, ExportResults)
- **Phase 3**: Advanced actions (BidirectionalMatch, OverlapAnalyzer)
- **Phase 4**: Deprecate legacy base class

## Conclusion

The typed strategy action system provides a modern, type-safe approach to implementing strategy actions while maintaining full backward compatibility. It improves developer experience, reduces errors, and provides better tooling support, all while ensuring existing YAML strategies continue to work unchanged.

The self-registering action pattern combined with Pydantic validation creates a robust, extensible system that's both powerful for developers and accessible for researchers creating YAML workflows.

---

## Verification Sources
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

* `biomapper/core/strategy_actions/typed_base.py` (TypedStrategyAction implementation)
* `biomapper/core/strategy_actions/registry.py` (Action registration system)
* `biomapper/core/strategy_actions/entities/` (Entity-specific typed actions)
* `tests/unit/core/strategy_actions/` (Action unit tests)
* `CLAUDE.md` (Migration patterns and guidelines)
* `README.md` (Type safety migration status)