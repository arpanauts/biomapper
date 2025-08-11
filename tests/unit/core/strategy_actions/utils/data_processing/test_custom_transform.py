"""Tests for CustomTransformAction."""

import pytest
import pandas as pd
from unittest.mock import AsyncMock

from biomapper.core.strategy_actions.utils.data_processing.custom_transform import (
    CustomTransformAction, CustomTransformParams, TransformOperation
)
from biomapper.core.exceptions import DatasetNotFoundError, TransformationError, SchemaValidationError


class TestCustomTransformAction:
    """Test suite for CustomTransformAction."""
    
    @pytest.fixture
    def sample_data(self):
        """Sample DataFrame for testing."""
        return pd.DataFrame({
            'id': ['P12345', 'P67890', 'P11111'],
            'name': ['Protein A', 'Protein B', 'Protein C'], 
            'score': [0.95, 0.87, 0.92],
            'category': ['enzyme', 'receptor', 'enzyme']
        })
    
    @pytest.fixture  
    def action(self):
        """CustomTransformAction instance."""
        return CustomTransformAction()
    
    @pytest.mark.asyncio
    async def test_column_rename_transform(self, action, sample_data):
        """Test column renaming transformation."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_rename',
                    params={'mapping': {'id': 'protein_id', 'name': 'protein_name'}}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_applied == 1
        assert result.transformations_failed == 0
        
        output_df = context['datasets']['output']
        assert 'protein_id' in output_df.columns
        assert 'protein_name' in output_df.columns
        assert 'id' not in output_df.columns
    
    @pytest.mark.asyncio  
    async def test_column_add_transform(self, action, sample_data):
        """Test adding new columns."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output', 
            transformations=[
                TransformOperation(
                    type='column_add',
                    params={
                        'columns': {
                            'source': 'biomapper',
                            'high_score': lambda df: df['score'] > 0.9
                        }
                    }
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert 'source' in output_df.columns
        assert 'high_score' in output_df.columns
        assert output_df['source'].iloc[0] == 'biomapper'
        assert output_df['high_score'].sum() == 2  # 2 proteins with score > 0.9
    
    @pytest.mark.asyncio
    async def test_filter_rows_transform(self, action, sample_data):
        """Test row filtering transformation.""" 
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='filter_rows', 
                    params={
                        'conditions': {
                            'category': {'operator': '==', 'value': 'enzyme'}
                        }
                    }
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert len(output_df) == 2  # Only enzyme proteins
        assert all(output_df['category'] == 'enzyme')
    
    @pytest.mark.asyncio
    async def test_column_drop_transform(self, action, sample_data):
        """Test column dropping transformation."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_drop',
                    params={'columns': ['category']}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert 'category' not in output_df.columns
        assert 'id' in output_df.columns  # Others should remain
    
    @pytest.mark.asyncio
    async def test_column_transform_string_operations(self, action, sample_data):
        """Test string transformation operations."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_transform',
                    params={'column': 'name', 'function': 'upper'}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert output_df['name'].iloc[0] == 'PROTEIN A'
    
    @pytest.mark.asyncio
    async def test_column_transform_replace(self, action, sample_data):
        """Test string replacement transformation."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_transform',
                    params={'column': 'name', 'function': 'replace:Protein:Gene'}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert output_df['name'].iloc[0] == 'Gene A'
    
    @pytest.mark.asyncio
    async def test_merge_columns_transform(self, action, sample_data):
        """Test column merging transformation."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='merge_columns',
                    params={
                        'new_column': 'full_name',
                        'source_columns': ['id', 'name'],
                        'separator': ' - '
                    }
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert 'full_name' in output_df.columns
        assert output_df['full_name'].iloc[0] == 'P12345 - Protein A'
    
    @pytest.mark.asyncio
    async def test_split_column_transform(self, action):
        """Test column splitting transformation."""
        test_data = pd.DataFrame({
            'combined': ['A_B_C', 'D_E_F', 'G_H_I']
        })
        context = {'datasets': {'input': test_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='split_column',
                    params={
                        'source_column': 'combined',
                        'separator': '_',
                        'new_columns': ['col1', 'col2', 'col3']
                    }
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert 'col1' in output_df.columns
        assert 'col2' in output_df.columns
        assert 'col3' in output_df.columns
        assert output_df['col1'].iloc[0] == 'A'
        assert output_df['col2'].iloc[0] == 'B'
        assert output_df['col3'].iloc[0] == 'C'
    
    @pytest.mark.asyncio
    async def test_deduplicate_transform(self, action):
        """Test deduplication transformation."""
        test_data = pd.DataFrame({
            'id': ['A', 'B', 'A', 'C'],
            'value': [1, 2, 1, 3]
        })
        context = {'datasets': {'input': test_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='deduplicate',
                    params={'subset': ['id'], 'keep': 'first'}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert len(output_df) == 3  # One duplicate removed
        assert list(output_df['id']) == ['A', 'B', 'C']
    
    @pytest.mark.asyncio
    async def test_fill_na_transform(self, action):
        """Test fill NA transformation."""
        test_data = pd.DataFrame({
            'id': ['A', 'B', None, 'D'],
            'value': [1, None, 3, 4]
        })
        context = {'datasets': {'input': test_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='fill_na',
                    params={'method': 'value', 'value': 'MISSING'}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert output_df['id'].iloc[2] == 'MISSING'
        assert output_df['value'].iloc[1] == 'MISSING'
    
    @pytest.mark.asyncio
    async def test_sort_transform(self, action, sample_data):
        """Test sorting transformation."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='sort',
                    params={'by': ['score'], 'ascending': False}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        output_df = context['datasets']['output']
        assert output_df['score'].iloc[0] == 0.95  # Highest score first
        assert output_df['score'].iloc[-1] == 0.87  # Lowest score last
    
    @pytest.mark.asyncio
    async def test_multiple_transformations(self, action, sample_data):
        """Test chaining multiple transformations."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_add',
                    params={'columns': {'processed': True}}
                ),
                TransformOperation(
                    type='filter_rows',
                    params={'conditions': {'score': {'operator': '>', 'value': 0.9}}}
                ),
                TransformOperation(
                    type='column_rename', 
                    params={'mapping': {'name': 'protein_name'}}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_applied == 3
        
        output_df = context['datasets']['output']
        assert len(output_df) == 2  # Filtered to high scores
        assert 'processed' in output_df.columns
        assert 'protein_name' in output_df.columns
        assert 'name' not in output_df.columns
    
    @pytest.mark.asyncio
    async def test_schema_validation_strict(self, action, sample_data):
        """Test schema validation functionality in strict mode."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_drop',
                    params={'columns': ['category']}
                )
            ],
            validate_schema=True,
            expected_columns=['id', 'name', 'score', 'category'],  # Includes dropped column
            error_handling='strict'
        )
        
        with pytest.raises(SchemaValidationError):
            await action.execute_typed(params, context)
    
    @pytest.mark.asyncio
    async def test_schema_validation_warn(self, action, sample_data):
        """Test schema validation with warning mode."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_drop',
                    params={'columns': ['category']}
                )
            ],
            validate_schema=True,
            expected_columns=['id', 'name', 'score', 'category'],  # Includes dropped column
            error_handling='warn'
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert not result.schema_validation_passed
        assert len(result.warnings) > 0
        assert 'Missing expected columns' in result.warnings[0]
    
    @pytest.mark.asyncio
    async def test_error_handling_warn(self, action, sample_data):
        """Test warning error handling mode with transformation error."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_transform',
                    params={'column': 'nonexistent_column', 'function': 'upper'}  # Will cause error
                )
            ],
            error_handling='warn'
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_failed == 1
        assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_ignore(self, action, sample_data):
        """Test ignore error handling mode."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_transform',
                    params={'column': 'nonexistent_column', 'function': 'upper'}  # Will cause error
                )
            ],
            error_handling='ignore'
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_failed == 1
        assert len(result.warnings) == 0  # No warnings in ignore mode
    
    @pytest.mark.asyncio
    async def test_dataset_not_found(self, action):
        """Test error when input dataset doesn't exist."""
        context = {'datasets': {}}
        
        params = CustomTransformParams(
            input_key='nonexistent',
            output_key='output',
            transformations=[]
        )
        
        with pytest.raises(DatasetNotFoundError):
            await action.execute_typed(params, context)
    
    @pytest.mark.asyncio
    async def test_unsupported_transformation_type(self, action, sample_data):
        """Test error for unsupported transformation type."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='unsupported_operation',  # type: ignore
                    params={}
                )
            ],
            error_handling='strict'
        )
        
        with pytest.raises(TransformationError):
            await action.execute_typed(params, context)
    
    @pytest.mark.asyncio
    async def test_conditional_transformation(self, action, sample_data):
        """Test conditional transformation execution."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_add',
                    params={'columns': {'conditional_col': 'added'}},
                    condition='len(df) > 5'  # Should not execute (df has 3 rows)
                ),
                TransformOperation(
                    type='column_add',
                    params={'columns': {'normal_col': 'always_added'}}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_applied == 1  # Only second transformation applied
        output_df = context['datasets']['output']
        assert 'conditional_col' not in output_df.columns
        assert 'normal_col' in output_df.columns
    
    @pytest.mark.asyncio
    async def test_context_statistics_update(self, action, sample_data):
        """Test that context statistics are properly updated."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_add',
                    params={'columns': {'new_col': 'test'}}
                )
            ]
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert 'statistics' in context
        assert 'output_rows_processed' in context['statistics']
        assert 'output_transformations_applied' in context['statistics']
        assert context['statistics']['output_rows_processed'] == 3
        assert context['statistics']['output_transformations_applied'] == 1