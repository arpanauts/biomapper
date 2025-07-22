# Biomapper MVP Action Development Reference

This document contains standard guidelines for developing MVP action types for the Biomapper project.

## Project Context

Biomapper is a biological data harmonization toolkit that helps researchers map identifiers between different biological databases (proteins, metabolites, clinical labs). The key differentiator is intelligent handling of historical/obsolete identifiers through API resolution.

## Development Environment

### File Locations
- **Action modules**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- **Base classes**: `typed_base.py` in same directory
- **Tests**: `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/`
- **Test data**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/`

### Python Environment
- Use Poetry: `poetry shell` to activate
- Python 3.11+
- Key dependencies: pandas, pydantic, pytest, httpx (for API calls)

## Test-Driven Development (TDD) Requirements

### Follow the TDD Cycle
1. **RED**: Write failing tests first
2. **GREEN**: Write minimal code to pass tests  
3. **REFACTOR**: Improve code while keeping tests green

### Test Structure
```python
# tests/unit/core/strategy_actions/test_action_name.py

def test_action_params_validation():
    """Test that parameters are validated correctly."""
    # Valid params
    params = ActionNameParams(required_field="value")
    assert params.required_field == "value"
    
    # Invalid params
    with pytest.raises(ValidationError):
        ActionNameParams()  # Missing required field

def test_action_happy_path():
    """Test normal operation with valid data."""
    # Arrange
    input_data = TableData(rows=[...])
    context = {'datasets': {'input': input_data}}
    params = ActionNameParams(...)
    
    # Act
    result = await action.execute_typed(params, context, None, None)
    
    # Assert
    assert context['datasets']['output'].row_count == expected
    assert 'new_column' in context['datasets']['output'].columns

def test_action_empty_input():
    """Test handling of empty input data."""
    # Empty data should return empty result, not error
    
def test_action_missing_column():
    """Test error handling for missing columns."""
    # Should raise clear error message

def test_action_with_real_test_data():
    """Test with actual biological data files."""
    # Use files from test_data directory
```

### Minimum Test Coverage
- Parameter validation
- Happy path with valid data  
- Empty input handling
- Missing column handling
- Edge cases specific to the action
- At least one test with real test data files

## Code Structure

### Action Implementation Pattern
```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.models import ActionResult, TableData
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ActionNameParams(BaseModel):
    """Parameters for ACTION_NAME."""
    
    # Define all parameters with types and descriptions
    required_param: str = Field(..., description="Clear description")
    optional_param: int = Field(10, description="Default value with description")
    
    # Add validators as needed
    @validator('required_param')
    def validate_required(cls, v):
        if not v:
            raise ValueError("Cannot be empty")
        return v

@register_action("ACTION_NAME")
class ActionNameAction(TypedStrategyAction[ActionNameParams, ActionResult]):
    """Clear description of what this action does."""
    
    def get_params_model(self) -> type[ActionNameParams]:
        return ActionNameParams
    
    async def execute_typed(
        self,
        params: ActionNameParams,
        context: Dict[str, Any],
        source_endpoint: Optional[Any],
        target_endpoint: Optional[Any]
    ) -> ActionResult:
        """Execute the action."""
        
        # 1. Validate context structure
        if 'datasets' not in context:
            context['datasets'] = {}
        if 'metadata' not in context:
            context['metadata'] = {}
        
        # 2. Get input data
        if params.input_key not in context['datasets']:
            raise ValueError(f"Input dataset '{params.input_key}' not found")
        
        input_data = context['datasets'][params.input_key]
        df = input_data.to_dataframe()
        
        logger.info(f"Starting ACTION_NAME with {len(df)} rows")
        
        # 3. Validate required columns exist
        # 4. Process data
        # 5. Store results in context
        # 6. Update metadata
        # 7. Return ActionResult
```

## Design Principles

### 1. Data Immutability
- **Never modify original columns** - create new ones
- Use suffix convention: `{column}_original` for preserved data
- Original data should always be recoverable

### 2. Context Management
- Read from `context['datasets'][input_key]`
- Write to `context['datasets'][output_key]`
- Update `context['metadata'][output_key]` with statistics
- Don't assume context structure - check and create if needed

### 3. Error Handling
- **Fail fast with clear messages** - include what was expected vs found
- **Never silently drop data** - log all filtering/removal
- **Handle missing values gracefully** - don't crash on NaN/None
- Include column names and sample values in error messages

### 4. Logging
- INFO level: Major operations (start, complete, row counts)
- DEBUG level: Detailed operations, parameters
- WARNING level: Unexpected but handled situations
- ERROR level: Failures that stop execution

### 5. TableData Convention
```python
# Creating from pandas
table_data = TableData.from_dataframe(df)

# Converting to pandas  
df = table_data.to_dataframe()

# Accessing properties
row_count = len(table_data.rows)
columns = table_data.columns  # If implemented
```

## Common Patterns

### Column Validation
```python
missing_columns = [col for col in required_cols if col not in df.columns]
if missing_columns:
    available = list(df.columns)
    raise ValueError(
        f"Required columns not found: {missing_columns}. "
        f"Available columns: {available}"
    )
```

### Progress Logging
```python
total = len(df)
for i, chunk in enumerate(chunks):
    if i % 10 == 0:
        logger.info(f"Processing {i*chunk_size}/{total} rows")
```

### Metadata Structure
```python
context['metadata'][params.output_key] = {
    'row_count': len(result_df),
    'columns': list(result_df.columns),
    'source_dataset': params.input_key,
    'processing_stats': {
        'filtered': rows_filtered,
        'modified': rows_modified,
        # Action-specific stats
    },
    'timestamp': datetime.now().isoformat()
}
```

## Testing with Real Data

### Available Test Data
- **UKBB**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/ukbb/`
- **HPA**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/isb_osp/hpa_osps.csv`
- **KG2C**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/kg2c_ontologies/`
- **SPOKE**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/spoke_ontologies/`

Each file contains ~10 rows of real data with correct column structure.

## Performance Guidelines

- Process DataFrames in chunks for large files (>100K rows)
- Use vectorized pandas operations, avoid row-by-row iteration
- For API calls: batch requests, implement rate limiting, add retry logic
- Cache expensive operations when appropriate

## Documentation

Each action must include:
1. Clear module docstring explaining purpose
2. Comprehensive parameter descriptions in Pydantic model
3. Example usage in docstring or tests
4. Any special considerations or limitations

## Checklist Before Submission

- [ ] All tests pass (`pytest tests/unit/core/strategy_actions/test_my_action.py`)
- [ ] Test coverage >80% for the action module
- [ ] Type hints on all functions
- [ ] Logging at appropriate levels
- [ ] Error messages are helpful (include context)
- [ ] Real test data example included
- [ ] No hardcoded paths or values
- [ ] Follows naming conventions
- [ ] Docstrings complete

## Questions?

If you need clarification during development:
1. Check existing actions in the same directory for patterns
2. Refer to `typed_base.py` for the base class interface
3. Look at test examples in the tests directory