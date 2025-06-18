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

### 3. **Consistent Interface and Parameter Handling**
All actions inherit from `BaseStrategyAction`. The `MappingExecutor` instantiates actions, passing YAML-defined parameters to `__init__`. These parameters are stored in `self.params` and are available during the `execute` phase.

**Initialization (`__init__`)**:
The `__init__` method receives the static configuration parameters for the action instance as defined in the YAML strategy.
```python
def __init__(self, params: Dict[str, Any], executor: 'MappingExecutor'):
    super().__init__(params, executor)
    # `self.params` now holds the YAML configuration for this action instance.
    # `self.executor` provides access to executor functionalities (e.g., logging, db sessions).
    # Perform any one-time setup or parameter validation based on `self.params`.
    # Example:
    # self.output_key = self.params.get('output_key', 'default_output')
    # if not self.params.get('required_yaml_param'):
    #     raise ValueError(f"Action {self.__class__.__name__}: Missing 'required_yaml_param' in configuration.")
```

**Execution (`execute`)**:
The `execute` method performs the core logic of the action. It receives the current execution `context` (a dictionary, potentially wrapped in an `ExecutionContext` object in the future), modifies it, and returns the updated `context`.
```python
async def execute(
    self,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    # Extract necessary data from context, e.g.:
    # current_identifiers = context.get('current_identifiers', [])
    # current_ontology_type = context.get('current_ontology_type')
    # source_endpoint_name = context.get('source_endpoint_name')
    # target_endpoint_name = context.get('target_endpoint_name')
    # logger = self.executor.logger

    # Access YAML parameters via self.params:
    # my_yaml_param = self.params.get('my_yaml_param_key')
    # logger.debug(f"Action {self.__class__.__name__} executing with param: {my_yaml_param}")

    # --- Action's core logic begins ---
    # 1. Operate on current_identifiers.
    # 2. Generate output_identifiers and their output_ontology_type.
    # 3. Create detailed provenance entries for the operations performed.
    # 4. Store results and any intermediate data back into the context.
    # --- Action's core logic ends ---

    # Example updates to context:
    # context['current_identifiers'] = new_identifier_list
    # context['current_ontology_type'] = new_ontology_type
    # context.setdefault('provenance', []).extend(action_specific_provenance_entries)
    # context['my_action_output_key'] = some_result_data
    
    return context
```

### 4. **Modifying and Returning the Execution Context**
Actions operate by modifying the `context` dictionary they receive and returning this modified dictionary. The `MappingExecutor` then passes this updated context to the next action in the strategy.

Key items typically managed in the `context`:
- **`current_identifiers` (List[str])**: The primary list of identifiers the current action should process. The action updates this to reflect its output.
- **`current_ontology_type` (str)**: The ontology type of the `current_identifiers`. Updated if the action changes the identifier type.
- **`provenance` (List[Dict])**: A list where each action appends its detailed provenance records. (See "Comprehensive Provenance" section for structure).
- **`source_endpoint_name` (str)**, **`target_endpoint_name` (str)**: Names of the overall source and target endpoints. Usually read-only by actions.
- **`source_endpoint` (Endpoint)**, **`target_endpoint` (Endpoint)**: Loaded `Endpoint` objects. Usually read-only.
- **Custom Keys**: Actions can read data placed in the context by previous actions (e.g., `context.get('intermediate_results_from_action_X')`) and can write their own specific outputs to new keys (e.g., `context['my_action_specific_output'] = data`). These keys must be coordinated with other actions in the strategy that might consume them.

**Important:** Actions should generally avoid removing standard keys from the context unless it's explicitly part of their function (e.g., a cleanup action). They primarily add to or update existing keys like `current_identifiers` and `provenance`.

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

2. **Ensure Action is Discoverable:**
   The `MappingExecutor` typically discovers actions specified via `action_class_path` in the YAML strategy by dynamically importing them. For this to work:
   - Ensure your new action class (e.g., `YourNewAction`) is in its own module (e.g., `your_new_action.py`) within the `biomapper.core.strategy_actions` package.
   - Add your action class to the `__all__` list in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/__init__.py`:
     ```python
     from .your_new_action import YourNewAction
     
     __all__ = [
         # ... existing actions ...
         "YourNewAction",
     ]
     ```
   - For most new actions defined with `action_class_path` in YAML, direct modification of `MappingExecutor.py`'s dispatch logic is **no longer required**. The dynamic import mechanism handles instantiation. Manual additions to `MappingExecutor` might only be needed for very core, built-in action types not intended to be specified by class path.

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


### Handling Path Parameters with Variable Expansion
Action parameters defined in YAML (accessible via `self.params`) might include file paths that contain variables needing expansion, such as `${OUTPUT_DIR}` or `${DATA_DIR}`. Actions are responsible for resolving these paths.

**Example:**
```python
# In __init__ or execute method:
# output_file_template = self.params.get('output_file') # e.g., "${OUTPUT_DIR}/my_results.csv"

# Method 1: Using executor's utility (Preferred if available)
# resolved_output_path = self.executor.resolve_path_parameter(output_file_template)

# Method 2: Using os.path.expandvars (if variables are set as environment variables)
# import os
# resolved_output_path = os.path.expandvars(output_file_template)
# Ensure the relevant environment variables (e.g., OUTPUT_DIR) are set when the pipeline runs.

# Method 3: Using context variables (if OUTPUT_DIR is passed in context)
# output_dir = context.get('OUTPUT_DIR_PATH') # Assuming it's placed in context
# if output_dir and output_file_template:
#    resolved_output_path = output_file_template.replace('${OUTPUT_DIR}', output_dir)
# else:
#    # Handle error or default path

# Always ensure paths are absolute and validated before use.
# resolved_output_path = os.path.abspath(resolved_output_path)
# os.makedirs(os.path.dirname(resolved_output_path), exist_ok=True)
```
Consult with the `MappingExecutor`'s capabilities or project conventions for the standard way to resolve these path variables. The `executor` object itself might provide helper methods.

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