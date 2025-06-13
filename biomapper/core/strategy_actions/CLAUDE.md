# Strategy Actions - AI Assistant Instructions

## Overview

This directory contains the action type implementations for biomapper's mapping strategies. Each action type represents a specific operation that can be performed on identifiers during the mapping process. When working with action types, follow these guidelines carefully.

## Directory Purpose

Action types are the building blocks of mapping strategies. They:
- Execute specific operations on identifier lists
- Handle the complexity of bioinformatics data (composites, many-to-many)
- Provide detailed provenance tracking
- Can read/write to shared execution context

## Key Principles

### 1. **Modular Design**
- Each action type is a separate module
- All inherit from `BaseStrategyAction`
- Minimal modifications to MappingExecutor (just add to dispatch logic)
- Future goal: Dynamic loading to eliminate MappingExecutor changes

### 2. **Assume Complexity**
- Always handle composite identifiers (e.g., Q14213_Q8NEV9)
- Always support many-to-many mappings
- Never assume 1:1 relationships
- Handle empty inputs gracefully

### 3. **Consistent Interface**
All actions must implement:
```python
async def execute(
    self,
    current_identifiers: List[str],
    current_ontology_type: str,
    action_params: Dict[str, Any],
    source_endpoint: Endpoint,
    target_endpoint: Endpoint,
    context: Dict[str, Any]
) -> Dict[str, Any]
```

### 4. **Comprehensive Return Structure**
Actions must return:
```python
{
    'input_identifiers': List[str],      # What came in
    'output_identifiers': List[str],     # What goes out
    'output_ontology_type': str,         # May change from input
    'provenance': List[Dict],            # Detailed tracking
    'details': Dict[str, Any]            # Action-specific info
}
```

## When Creating New Actions

### Step 1: Check Existing Actions First
Before creating a new action, check if an existing one can be enhanced with parameters.

### Step 2: Follow Naming Conventions
- Module name: `lowercase_with_underscores.py`
- Class name: `PascalCaseAction`
- Action type constant: `UPPERCASE_WITH_UNDERSCORES`

### Step 3: Required Implementation Elements

1. **Comprehensive docstring**:
   ```python
   """
   Brief description of what the action does.
   
   This action:
   - Key capability 1
   - Key capability 2
   - Handles edge case X
   """
   ```

2. **Parameter validation**:
   ```python
   # Validate required parameters
   if not action_params.get('required_param'):
       raise ValueError("required_param is required")
   ```

3. **Early exit for empty input**:
   ```python
   if not current_identifiers:
       return self._empty_result()
   ```

4. **Logging at appropriate levels**:
   ```python
   logger.debug(f"Processing {len(identifiers)} identifiers")
   logger.info(f"Completed with {success_count} successes")
   logger.warning(f"Failed to process {failed_count} identifiers")
   ```

### Step 4: Register Your Action

1. In `__init__.py`, add import and update `__all__`:
   ```python
   from .your_new_action import YourNewAction
   
   __all__ = [
       # ... existing actions ...
       "YourNewAction",
   ]
   ```

2. In `mapping_executor.py` (around line 3470), add to dispatch logic:
   ```python
   elif action_type == "YOUR_NEW_ACTION":
       action = YourNewAction(session)
   ```

## When Modifying Existing Actions

### 1. **Maintain Backward Compatibility**
- Don't change required parameters
- Make new parameters optional with sensible defaults
- Don't change return structure

### 2. **Document Changes**
- Update docstrings
- Add comments explaining why changes were made
- Update tests to cover new functionality

### 3. **Test Thoroughly**
- Run existing tests to ensure nothing breaks
- Add new tests for new functionality
- Test with realistic data

## Common Patterns to Follow

### Composite Identifier Handling
```python
def _handle_composites(self, identifiers: List[str]) -> List[str]:
    """Standard composite handling."""
    expanded = []
    for id in identifiers:
        if '_' in id:  # Or configurable delimiter
            expanded.extend(id.split('_'))
        expanded.append(id)  # Always keep original
    return list(set(expanded))
```

### Many-to-Many Mapping
```python
from collections import defaultdict

mappings = defaultdict(list)
for source, target in matches:
    mappings[source].append(target)
```

### Context Usage
```python
# Read from context
previous_results = context.get('previous_matches', [])

# Write to context
if save_key := action_params.get('save_results_to'):
    context[save_key] = results
```

## Testing Requirements

### 1. **Unit Tests are Mandatory**
- Create test file in `/tests/unit/core/strategy_actions/`
- Test all parameter combinations
- Test error conditions
- Test edge cases (empty input, composites, M2M)

### 2. **Test File Structure**
```python
class TestYourAction:
    @pytest.fixture
    def action(self, mock_session):
        return YourAction(session=mock_session)
        
    async def test_basic_functionality(self, action):
        # Test happy path
        
    async def test_composite_handling(self, action):
        # Test with composite IDs
        
    async def test_error_conditions(self, action):
        # Test validation and errors
```

## Performance Considerations

1. **Load only necessary data** - Use column filtering
2. **Process in batches** for large datasets
3. **Cache expensive operations** in context
4. **Early exit** when possible

## Debugging Support

### Always Include Detailed Logging
```python
logger.debug(f"Action parameters: {action_params}")
logger.info(f"Processing {len(identifiers)} identifiers of type {ontology_type}")
logger.debug(f"First 5 identifiers: {identifiers[:5]}")
```

### Comprehensive Provenance
```python
provenance.append({
    'action': self.__class__.__name__,
    'timestamp': datetime.utcnow().isoformat(),
    'input': input_id,
    'output': output_ids,
    'method': specific_method_used,
    'confidence': confidence_score,
    'details': any_relevant_details
})
```

## Code Review Checklist

Before submitting a new action:

- [ ] Follows BaseStrategyAction interface exactly
- [ ] Handles composite identifiers
- [ ] Supports many-to-many mappings
- [ ] Validates all parameters
- [ ] Returns complete result structure
- [ ] Has comprehensive unit tests
- [ ] Includes detailed logging
- [ ] Provides detailed provenance
- [ ] Added to __init__.py imports and __all__
- [ ] Added to MappingExecutor dispatch logic
- [ ] Documented in ACTION_TYPES_REFERENCE.md

## Common Mistakes to Avoid

1. **Assuming 1:1 mappings** - Always use lists/sets
2. **Modifying input lists** - Work with copies
3. **Poor error messages** - Be specific
4. **Missing provenance** - Track everything
5. **Forgetting edge cases** - Empty input, None values
6. **Tight coupling** - Actions should be independent

## Getting Help

- Review existing actions for patterns
- Check test files for usage examples
- Consult `/roadmap/technical_notes/action_types/developing_new_action_types.md`
- Look at integration tests to see actions in use

Remember: Actions are the workhorses of biomapper. They must be robust, well-tested, and handle the messy reality of bioinformatics data gracefully.