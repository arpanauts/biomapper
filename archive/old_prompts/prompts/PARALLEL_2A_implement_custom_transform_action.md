# PARALLEL 2A: Implement CUSTOM_TRANSFORM Action

**Prerequisites: PRIORITY_1_fix_variable_substitution.md must be completed first**

## Problem Statement

The existing protein strategies (ARIVALE_TO_KG2C_PROTEINS and UKBB_TO_KG2C_PROTEINS) fail because the CUSTOM_TRANSFORM action is not implemented. This is blocking protein data harmonization capabilities.

## Objective

Implement a flexible CUSTOM_TRANSFORM action that allows strategies to apply custom data transformations using Python expressions or callable functions.

## Context and Requirements

### Expected Usage Pattern
Based on existing strategies, CUSTOM_TRANSFORM should:
1. Apply arbitrary transformations to dataset columns
2. Support Python expressions for simple transformations
3. Support lambda functions for complex logic
4. Handle missing/null values gracefully
5. Preserve data types where appropriate

### Example Usage in Strategies
```yaml
- name: transform_protein_ids
  action:
    type: CUSTOM_TRANSFORM
    params:
      input_key: protein_data
      output_key: transformed_proteins
      transformations:
        - column: uniprot_id
          expression: "value.upper().strip()"
        - column: concentration
          expression: "float(value) if value else 0.0"
        - column: gene_symbol
          expression: "value.split('|')[0] if '|' in value else value"
```

## Implementation Requirements

### 1. Create Action File
Create `/home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/custom_transform.py`:

```python
"""
Custom transformation action for flexible data manipulation.

This action allows strategies to apply arbitrary transformations to dataset columns
using Python expressions or callable functions.
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
import ast
import logging

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.models import ActionResult

logger = logging.getLogger(__name__)

class TransformationSpec(BaseModel):
    """Specification for a single column transformation."""
    column: str = Field(..., description="Column name to transform")
    expression: str = Field(..., description="Python expression to apply (value available as 'value')")
    new_column: Optional[str] = Field(None, description="Optional new column name for result")
    on_error: str = Field("keep_original", description="Action on error: keep_original, null, raise")

class CustomTransformParams(BaseModel):
    """Parameters for custom transformation action."""
    input_key: str = Field(..., description="Key for input dataset in context")
    output_key: str = Field(..., description="Key for output dataset in context")
    transformations: List[TransformationSpec] = Field(..., description="List of transformations to apply")
    drop_original: bool = Field(False, description="Whether to drop original columns after transformation")
    parallel: bool = Field(True, description="Whether to apply transformations in parallel")

@register_action("CUSTOM_TRANSFORM")
class CustomTransformAction(TypedStrategyAction[CustomTransformParams, ActionResult]):
    """
    Apply custom transformations to dataset columns.
    
    Supports:
    - Python expressions with 'value' as the current cell value
    - Safe evaluation using ast.literal_eval for simple expressions
    - Complex transformations using eval with restricted namespace
    - Error handling with configurable behavior
    """
    
    def get_params_model(self) -> type[CustomTransformParams]:
        return CustomTransformParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self,
        params: CustomTransformParams,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Execute custom transformations on dataset."""
        try:
            # Get input dataset
            if params.input_key not in context:
                raise ValueError(f"Input key '{params.input_key}' not found in context")
            
            input_data = context[params.input_key]
            
            # Convert to DataFrame if needed
            if isinstance(input_data, dict) and 'data' in input_data:
                df = pd.DataFrame(input_data['data'])
            elif isinstance(input_data, pd.DataFrame):
                df = input_data.copy()
            elif isinstance(input_data, list):
                df = pd.DataFrame(input_data)
            else:
                raise ValueError(f"Unsupported input type: {type(input_data)}")
            
            logger.info(f"Applying {len(params.transformations)} transformations to {len(df)} rows")
            
            # Apply each transformation
            for transform in params.transformations:
                df = await self._apply_transformation(df, transform)
            
            # Store result in context
            context[params.output_key] = {
                'data': df.to_dict('records'),
                'row_count': len(df),
                'columns': list(df.columns),
                'transformations_applied': len(params.transformations)
            }
            
            return ActionResult(
                success=True,
                message=f"Applied {len(params.transformations)} transformations successfully",
                data={
                    'rows_processed': len(df),
                    'transformations_applied': len(params.transformations),
                    'output_columns': list(df.columns)
                }
            )
            
        except Exception as e:
            logger.error(f"Custom transformation failed: {e}")
            return ActionResult(
                success=False,
                error=str(e),
                data={'input_key': params.input_key}
            )
    
    async def _apply_transformation(
        self,
        df: pd.DataFrame,
        transform: TransformationSpec
    ) -> pd.DataFrame:
        """Apply a single transformation to a DataFrame column."""
        
        if transform.column not in df.columns:
            logger.warning(f"Column '{transform.column}' not found in DataFrame")
            return df
        
        target_column = transform.new_column or transform.column
        
        try:
            # Create safe namespace for evaluation
            safe_namespace = {
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'len': len,
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'upper': str.upper,
                'lower': str.lower,
                'strip': str.strip,
                'split': str.split,
                'replace': str.replace,
                'np': np,
                'pd': pd
            }
            
            # Apply transformation
            def transform_value(value):
                if pd.isna(value):
                    return np.nan
                try:
                    # Add value to namespace
                    local_namespace = {'value': value}
                    local_namespace.update(safe_namespace)
                    
                    # Evaluate expression
                    result = eval(transform.expression, {"__builtins__": {}}, local_namespace)
                    return result
                except Exception as e:
                    if transform.on_error == "raise":
                        raise
                    elif transform.on_error == "null":
                        return np.nan
                    else:  # keep_original
                        return value
            
            # Apply to column
            df[target_column] = df[transform.column].apply(transform_value)
            
            # Drop original if requested and it's a new column
            if transform.drop_original and transform.new_column and transform.column != transform.new_column:
                df = df.drop(columns=[transform.column])
            
            logger.debug(f"Transformed column '{transform.column}' -> '{target_column}'")
            
        except Exception as e:
            logger.error(f"Failed to transform column '{transform.column}': {e}")
            if transform.on_error == "raise":
                raise
        
        return df
```

### 2. Write Comprehensive Unit Tests

Create `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/utils/data_processing/test_custom_transform.py`:

```python
import pytest
import pandas as pd
import numpy as np
from biomapper.core.strategy_actions.utils.data_processing.custom_transform import (
    CustomTransformAction,
    CustomTransformParams,
    TransformationSpec
)

class TestCustomTransformAction:
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context with test data."""
        return {
            'test_proteins': {
                'data': [
                    {'uniprot_id': 'p12345', 'gene_symbol': 'BRCA1|BRCA2', 'concentration': '1.5'},
                    {'uniprot_id': 'Q67890', 'gene_symbol': 'TP53', 'concentration': '2.3'},
                    {'uniprot_id': 'a11111', 'gene_symbol': 'EGFR|', 'concentration': None},
                ]
            }
        }
    
    @pytest.mark.asyncio
    async def test_simple_string_transformation(self, sample_context):
        """Test uppercase transformation on string column."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='uniprot_id',
                    expression='value.upper()'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success
        assert 'transformed_proteins' in sample_context
        
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['uniprot_id'] == 'P12345'
        assert output_data[1]['uniprot_id'] == 'Q67890'
        assert output_data[2]['uniprot_id'] == 'A11111'
    
    @pytest.mark.asyncio
    async def test_complex_string_splitting(self, sample_context):
        """Test splitting gene symbols on pipe character."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='gene_symbol',
                    expression="value.split('|')[0] if '|' in value else value",
                    new_column='primary_gene'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['primary_gene'] == 'BRCA1'
        assert output_data[1]['primary_gene'] == 'TP53'
        assert output_data[2]['primary_gene'] == 'EGFR'
    
    @pytest.mark.asyncio
    async def test_numeric_transformation_with_nulls(self, sample_context):
        """Test converting string to float with null handling."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='concentration',
                    expression='float(value) if value else 0.0',
                    on_error='null'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['concentration'] == 1.5
        assert output_data[1]['concentration'] == 2.3
        assert output_data[2]['concentration'] == 0.0 or pd.isna(output_data[2]['concentration'])
    
    @pytest.mark.asyncio
    async def test_multiple_transformations(self, sample_context):
        """Test applying multiple transformations in sequence."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='uniprot_id',
                    expression='value.upper()'
                ),
                TransformationSpec(
                    column='gene_symbol',
                    expression="value.split('|')[0] if '|' in value else value"
                ),
                TransformationSpec(
                    column='concentration',
                    expression='float(value) * 1000 if value else 0.0',
                    new_column='concentration_ng'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success
        assert result.data['transformations_applied'] == 3
        
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['uniprot_id'] == 'P12345'
        assert output_data[0]['gene_symbol'] == 'BRCA1'
        assert output_data[0]['concentration_ng'] == 1500.0
    
    @pytest.mark.asyncio
    async def test_error_handling_modes(self, sample_context):
        """Test different error handling modes."""
        action = CustomTransformAction()
        
        # Test with invalid expression and keep_original mode
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='uniprot_id',
                    expression='invalid_function(value)',
                    on_error='keep_original'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        assert result.success
        
        # Original values should be preserved
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['uniprot_id'] == 'p12345'
    
    @pytest.mark.asyncio
    async def test_missing_column_handling(self, sample_context):
        """Test behavior when transforming non-existent column."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='nonexistent_column',
                    expression='value.upper()'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        # Should succeed but skip the missing column
        assert result.success
        assert 'transformed_proteins' in sample_context
    
    @pytest.mark.asyncio
    async def test_expression_with_conditionals(self, sample_context):
        """Test complex expressions with conditionals."""
        action = CustomTransformAction()
        params = CustomTransformParams(
            input_key='test_proteins',
            output_key='transformed_proteins',
            transformations=[
                TransformationSpec(
                    column='uniprot_id',
                    expression='"HUMAN_" + value.upper() if value.startswith("p") else value.upper()',
                    new_column='species_prefixed_id'
                )
            ]
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success
        output_data = sample_context['transformed_proteins']['data']
        assert output_data[0]['species_prefixed_id'] == 'HUMAN_P12345'
        assert output_data[1]['species_prefixed_id'] == 'Q67890'  # Doesn't start with 'p'
```

### 3. Run Tests First (TDD)

```bash
cd /home/ubuntu/biomapper

# Run tests - they should fail initially
poetry run pytest tests/unit/core/strategy_actions/utils/data_processing/test_custom_transform.py -xvs

# After implementation, all should pass
poetry run pytest tests/unit/core/strategy_actions/utils/data_processing/test_custom_transform.py -xvs
```

### 4. Integration Test

Create `/tmp/test_custom_transform_integration.py`:

```python
import asyncio
from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def test_with_real_strategy():
    """Test CUSTOM_TRANSFORM with a real protein strategy."""
    service = MinimalStrategyService()
    
    # This should work after implementing CUSTOM_TRANSFORM
    try:
        result = await service.execute_strategy("ARIVALE_TO_KG2C_PROTEINS", {})
        print("SUCCESS: ARIVALE_TO_KG2C_PROTEINS strategy executed with CUSTOM_TRANSFORM")
        return True
    except Exception as e:
        if "CUSTOM_TRANSFORM" in str(e):
            print(f"FAILED: CUSTOM_TRANSFORM still not working: {e}")
            return False
        else:
            print(f"Different error: {e}")
            return None

if __name__ == "__main__":
    success = asyncio.run(test_with_real_strategy())
    exit(0 if success else 1)
```

## Success Criteria

1. ✅ All unit tests pass
2. ✅ CUSTOM_TRANSFORM action is registered in ACTION_REGISTRY
3. ✅ At least one protein strategy (ARIVALE_TO_KG2C_PROTEINS) executes successfully
4. ✅ Handles edge cases (nulls, missing columns, errors) gracefully
5. ✅ Performance is acceptable for datasets up to 100k rows

## Documentation Requirements

1. **Add to action documentation**
   - Document supported expressions and functions
   - Provide examples of common transformations
   - Explain error handling modes

2. **Update CLAUDE.md**
   - Add CUSTOM_TRANSFORM to list of available actions
   - Include usage examples

3. **Create examples in docstring**
   - Show various transformation patterns
   - Demonstrate error handling

## Deliverables

1. Implementation file: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/custom_transform.py`
2. Test file: `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/utils/data_processing/test_custom_transform.py`
3. Integration test results showing protein strategy working
4. Brief report including:
   - Any design decisions made
   - Performance considerations
   - Limitations of the implementation
   - Suggestions for future enhancements

## Time Estimate

- Implementation: 45 minutes
- Writing tests: 30 minutes
- Integration testing: 15 minutes
- Documentation: 15 minutes
- **Total: 1.75 hours**

## Notes

- This unblocks the existing protein strategies immediately
- Focus on flexibility and safety (restricted eval namespace)
- Consider performance for large datasets
- Make it reusable for other entity types (not just proteins)