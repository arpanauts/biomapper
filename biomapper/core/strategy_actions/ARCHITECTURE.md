# Strategy Actions Architecture

## Overview

This document describes the architectural patterns and design decisions for biomapper's strategy action system, particularly the distinction between business logic and infrastructure components.

## Architectural Principles

### Business Logic vs Infrastructure Actions

The biomapper action system is divided into two distinct categories based on their architectural role:

#### Business Logic Actions (TypedStrategyAction)
- **Purpose:** Process biological data (proteins, metabolites, chemistry)
- **Pattern:** TypedStrategyAction with Pydantic models
- **Type Safety:** Full compile-time and runtime validation
- **Examples:** 
  - `LOAD_DATASET_IDENTIFIERS`
  - `METABOLITE_CTS_BRIDGE`
  - `PROTEIN_NORMALIZE_ACCESSIONS`
  - `CHEMISTRY_EXTRACT_LOINC`

#### Infrastructure Actions (BaseAction/Dict-based)
- **Purpose:** Performance wrappers, meta-actions, system utilities
- **Pattern:** Flexible Dict[str, Any] for maximum compatibility
- **Type Safety:** Internal validation where appropriate, but flexible interfaces
- **Examples:** 
  - `CHUNK_PROCESSOR` - Wraps other actions for memory-efficient processing

This architectural decision maintains clean separation of concerns while maximizing type safety where it matters most - the biological data processing pipeline.

## Type Safety Migration Status

### ✅ Completed Migrations (30+ Actions)
All core business logic actions have been successfully migrated to TypedStrategyAction:

**Data Operations:**
- `load_dataset_identifiers.py`
- `merge_datasets.py`
- `filter_dataset.py`
- `custom_transform_expression.py`

**Metabolite Actions:**
- All matching strategies (cts_bridge, nightingale_nmr_match, semantic_match, vector_enhanced_match)
- All identification actions (extract_identifiers, normalize_hmdb)
- All enrichment actions (api_enrichment)

**Protein Actions:**
- `extract_uniprot_from_xrefs.py` ✅
- `normalize_accessions.py` ✅
- `multi_bridge.py` ✅

**Chemistry Actions:**
- `extract_loinc.py` ✅

**IO Actions:**
- `export_dataset_v2.py`
- `sync_to_google_drive_v2.py`

### 🏗️ Infrastructure Exceptions
These actions remain as flexible infrastructure components by design:

**CHUNK_PROCESSOR** (`utils/data_processing/chunk_processor.py`)
- **Rationale:** Meta-action that wraps ANY other action for chunked processing
- **Requirements:** Must accept arbitrary action types and parameters
- **Pattern:** Uses Dict[str, Any] to maintain compatibility with all action types
- **Benefits:** Provides universal performance optimization without type constraints

## Design Patterns

### TypedStrategyAction Pattern

```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel, Field

class MyActionParams(BaseModel):
    """Strongly typed parameters with validation."""
    input_key: str = Field(..., description="Input dataset key")
    output_key: str = Field(..., description="Output dataset key")
    # Additional parameters with validation

class ActionResult(BaseModel):
    """Standard result model for consistency."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

@register_action("MY_ACTION_NAME")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    """Business logic action with full type safety."""
    
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self, params: MyActionParams, context: Dict[str, Any]
    ) -> ActionResult:
        # Type-safe implementation
        pass
```

### Infrastructure Pattern

```python
@register_action("INFRASTRUCTURE_ACTION")
class InfrastructureAction:
    """Flexible infrastructure action for meta-operations."""
    
    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Flexible implementation that can wrap or orchestrate other actions
        target_action = params.get("target_action")
        # Dynamic action invocation
        pass
```

## Benefits Realized

### Developer Experience
- **IDE Support:** Perfect autocomplete and inline documentation
- **Error Detection:** Type errors caught at development time, not runtime
- **Self-Documenting:** Parameter contracts are explicit in the code

### Runtime Reliability
- **Parameter Validation:** Pydantic catches errors before execution
- **Clear Error Messages:** Validation errors provide specific field issues
- **Backward Compatibility:** `extra="allow"` permits additional fields

### System Maintainability
- **Clear Contracts:** Action interfaces are explicit and enforceable
- **Consistent Patterns:** All business logic follows the same structure
- **Separation of Concerns:** Infrastructure and business logic clearly separated

## Migration Guidelines

### When to Use TypedStrategyAction
✅ Processing biological data (proteins, metabolites, chemistry)
✅ Data transformation and enrichment
✅ External API integrations
✅ File I/O operations
✅ Report generation

### When to Keep Flexible Patterns
✅ Meta-actions that wrap other actions
✅ Performance optimization utilities
✅ Dynamic action orchestration
✅ System-level utilities

## Future Directions

### Phase 1: Complete Business Logic Migration ✅
- All biological data processing actions use TypedStrategyAction
- Consistent error handling and validation
- Full type coverage for data operations

### Phase 2: Enhanced Testing
- Property-based testing for typed actions
- Performance benchmarks for infrastructure actions
- Integration test coverage for all patterns

### Phase 3: Advanced Patterns
- Generic action composition
- Type-safe action pipelines
- Runtime action validation framework

## Conclusion

The dual-pattern architecture (TypedStrategyAction for business logic, flexible patterns for infrastructure) provides the optimal balance of:

1. **Type Safety** where it matters most - biological data processing
2. **Flexibility** where needed - performance optimization and meta-operations
3. **Maintainability** through clear architectural boundaries
4. **Scalability** by allowing both patterns to evolve independently

This architecture ensures biomapper remains robust for scientific computing while flexible enough for research workflows.