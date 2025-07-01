# Biomapper Action Development Prompt

## Context

You are working with Biomapper's action system. Actions are the building blocks of mapping strategies - self-contained operations that process biological identifiers in a pipeline.

**Key Architecture Facts:**
- Actions inherit from `BaseStrategyAction` or implement its interface
- Actions are registered using the `@register_action("ACTION_TYPE")` decorator
- Actions receive parameters from YAML strategies and execute transformations
- Actions communicate via a shared context dictionary passed between steps

## Action Interface

**CORRECT Interface (as implemented):**
```python
async def execute(
    self,
    current_identifiers: List[str],
    current_ontology_type: str,
    action_params: Dict[str, Any],
    source_endpoint: Endpoint,
    target_endpoint: Endpoint,
    context: Dict[str, Any]
) -> Dict[str, Any]:
```

**Required Return Structure:**
```python
{
    'input_identifiers': List[str],      # Original input
    'output_identifiers': List[str],     # Processed output
    'output_ontology_type': str,         # Ontology type after processing
    'provenance': List[Dict],            # Tracking information
    'details': Dict[str, Any]            # Action-specific metadata
}
```

## Common Action Patterns

### 1. Context-Based Data Flow
Actions read from and write to the context dictionary:
```python
# Read from context
input_data = context.get(action_params.get('input_context_key'), [])

# Write to context
context[action_params.get('output_context_key')] = processed_data
```

### 2. Parameter Validation
```python
required_param = action_params.get('required_param')
if not required_param:
    raise ValueError("required_param is required for ACTION_NAME")
```

### 3. Endpoint Data Access
```python
# Actions that need to load endpoint data use CSVAdapter
from biomapper.mapping.adapters.csv_adapter import CSVAdapter
adapter = CSVAdapter(endpoint=endpoint)
df = await adapter.load_data(columns_to_load=['column_name'])
```

## Task Requirements

**Current Task**: [Describe the specific action development task]

**Action Type**: [New action or modification to existing]

**Action Name**: [ACTION_TYPE to register]

**Purpose**: [What this action accomplishes]

**Parameters from YAML**:
- `param1`: [Description and type]
- `param2`: [Description and type]

**Input Requirements**:
- What identifiers/data does it expect?
- What context keys does it read?

**Output Requirements**:
- What does it produce?
- What context keys does it write?

## Implementation Constraints

1. **MUST** use the exact execute() signature shown above
2. **MUST** return all required fields in the result dictionary
3. **MUST** handle empty inputs gracefully
4. **MUST** add meaningful provenance records
5. **MUST** validate all required parameters
6. **SHOULD** log operations at appropriate levels
7. **SHOULD** handle composite identifiers if applicable

## Available Infrastructure

**Existing Actions for Reference**:
- `LOCAL_ID_CONVERTER`: Maps IDs using local files
- `LOAD_ENDPOINT_IDENTIFIERS`: Loads all IDs from an endpoint
- `DATASET_OVERLAP_ANALYZER`: Analyzes overlap between datasets
- `COMPOSITE_ID_SPLITTER`: Splits composite identifiers

**Common Utilities**:
- `CSVAdapter`: For reading endpoint data files
- Database session available via `self.session`
- Logging via `logger = logging.getLogger(__name__)`

## Testing Requirements

Create unit tests that cover:
1. Successful execution with valid inputs
2. Empty input handling
3. Missing parameter validation
4. Edge cases specific to the action
5. Context updates and provenance

## Files to Create/Modify

1. **Action Implementation**: 
   `/home/ubuntu/biomapper/biomapper/core/strategy_actions/[action_name].py`

2. **Registration** (if new):
   Import in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/__init__.py`

3. **Unit Tests**:
   `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_[action_name].py`

4. **Example Usage**:
   Update or create YAML strategy showing the action in use

## Success Criteria

- [ ] Action executes without errors
- [ ] Returns all required fields
- [ ] Handles edge cases gracefully
- [ ] Tests pass with good coverage
- [ ] Can be used in YAML strategies
- [ ] Logs provide useful debugging info

Remember: Focus on making the action robust, well-tested, and easy to use in strategies.