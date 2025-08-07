# Prompt: Update MinimalStrategyService to Support Both Dict and Pydantic Patterns

## Context
The MinimalStrategyService currently passes a simple dictionary as execution context to actions, but many actions expect a strict Pydantic StrategyExecutionContext model. This causes validation errors and prevents strategy execution.

## Current State

### What Works
- MinimalStrategyService loads YAML strategies successfully
- Simple actions like LOAD_DATASET_IDENTIFIERS work (accept dicts)
- Data loading processes 100s-1000s of rows successfully

### What Fails
- Complex actions like NIGHTINGALE_NMR_MATCH fail with Pydantic validation errors
- Required fields missing: `provenance.source`, `provenance.timestamp`
- Strict type checking prevents execution

## Requirements

### 1. Dual Context Support
Update MinimalStrategyService to maintain BOTH:
- A plain dictionary (for backward compatibility)
- A StrategyExecutionContext Pydantic model (for type-safe actions)

### 2. Smart Action Execution
The service should:
1. Check if an action expects Pydantic model (via type hints or try/except)
2. Pass the appropriate context type
3. Synchronize changes between dict and Pydantic model after each action

### 3. Backward Compatibility
- Existing dict-based actions must continue working unchanged
- No breaking changes to current working strategies
- LOAD_DATASET_IDENTIFIERS and MERGE_DATASETS must remain functional

### 4. Forward Compatibility
- New actions can choose either pattern
- Pydantic-based actions get type safety and validation
- Dict-based actions get flexibility

## Implementation Details

### Files to Modify
1. `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py`
   - Add StrategyExecutionContext initialization
   - Implement dual context management
   - Add smart action execution logic

2. `/home/ubuntu/biomapper/biomapper/core/strategy_execution_context.py` (if exists)
   - Make fields optional with defaults
   - Add method to sync with dict

### Proposed Implementation Pattern

```python
class MinimalStrategyService:
    async def execute_strategy(self, strategy_name: str, context: Dict = None):
        # Initialize both contexts
        dict_context = context or {}
        
        # Initialize Pydantic context with sensible defaults
        try:
            pydantic_context = StrategyExecutionContext(
                provenance=[],
                datasets={},
                statistics={},
                output_files=[],
                current_identifiers=[]
            )
        except:
            # If StrategyExecutionContext doesn't exist, just use dict
            pydantic_context = None
        
        # For each action in strategy
        for step in strategy['steps']:
            action_class = self.action_registry[action_type]
            
            # Try Pydantic first, fallback to dict
            try:
                if pydantic_context and hasattr(action_class, '__annotations__'):
                    # Check if action expects Pydantic model
                    result = await action_class.execute(params, pydantic_context)
                    # Sync back to dict
                    dict_context.update(pydantic_context.model_dump())
                else:
                    raise TypeError("Use dict")
            except (TypeError, AttributeError, ValidationError):
                # Fallback to dict-based execution
                result = await action_class.execute(params, dict_context)
                # Try to update Pydantic from dict
                if pydantic_context:
                    try:
                        pydantic_context = StrategyExecutionContext(**dict_context)
                    except:
                        pass  # Keep contexts separate if sync fails
            
            # Update the dict context with results
            dict_context = result or dict_context
        
        return dict_context
```

## Testing Requirements

### Must Pass Tests
1. SIMPLE_DATA_LOADER_DEMO strategy executes successfully
2. LOAD_DATASET_IDENTIFIERS action works with dict context
3. New Pydantic-based action works with proper context
4. THREE_WAY_METABOLOMICS_COMPLETE loads data (even if later steps fail)

### Error Handling
- Clear error messages indicating which context type failed
- Graceful fallback from Pydantic to dict
- No silent failures

## Success Criteria
1. ✅ Existing working strategies continue to work
2. ✅ New actions can use either dict or Pydantic patterns
3. ✅ Clear separation between flexible and type-safe actions
4. ✅ No breaking changes to current API
5. ✅ Better error messages for context mismatches

## Additional Considerations
- Add logging to show which context type each action uses
- Document the pattern for action developers
- Consider adding action base classes for each pattern
- Update action registry to store context type preference

## Example Usage After Fix

```python
# Dict-based action (flexible)
@register_action("SIMPLE_TRANSFORM")
class SimpleTransform:
    async def execute(self, params: Dict, context: Dict) -> Dict:
        context['datasets']['transformed'] = transform_data(...)
        return context

# Pydantic-based action (type-safe)
@register_action("VALIDATED_ANALYSIS")
class ValidatedAnalysis:
    async def execute(self, params: Dict, context: StrategyExecutionContext) -> StrategyExecutionContext:
        context.provenance.append(ProvenanceRecord(
            source="validated_analysis",
            timestamp=datetime.now()
        ))
        return context
```

## Notes
- This is a critical architectural fix needed before developing more actions
- Should be implemented and tested before creating new strategies
- Consider this a prerequisite for scaling the action library