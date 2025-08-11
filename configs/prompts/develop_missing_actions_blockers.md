# Develop Missing Actions Blocking Strategies

## Overview

This prompt guides the implementation of critical missing actions identified during Week 4 Integration Testing. These actions are blocking 40% of biomapper strategies and are essential for achieving 70-80% strategy success rate.

## Critical Missing Actions Identified

### 1. CUSTOM_TRANSFORM Action
**Priority**: CRITICAL - Blocks multiple strategies
**Usage**: Found in 6+ strategies for data transformation operations
**Estimated Development Time**: 1-2 days

### 2. CALCULATE_MAPPING_QUALITY Action  
**Priority**: CRITICAL - Blocks quality assessment workflows
**Usage**: Found in 4+ strategies for mapping validation
**Estimated Development Time**: 1 day

### 3. Additional Infrastructure Actions
**Priority**: HIGH - Support for external dependencies
**Usage**: Vector operations, file handling improvements
**Estimated Development Time**: 1 day

## Prerequisites

Before implementing these actions:
- ✅ Integration testing completed with issue identification
- ✅ Strategy failure analysis available in `INTEGRATION_TEST_REPORT.md`
- ✅ Test infrastructure in place for validation

## Action 1: CUSTOM_TRANSFORM Implementation

### Purpose
Provides flexible data transformation capabilities for strategies that need custom data processing beyond standard actions.

### Location
`biomapper/core/strategy_actions/utils/data_processing/custom_transform.py`

### Parameter Model
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Union, Literal, Optional
import pandas as pd

class TransformOperation(BaseModel):
    """Single transformation operation specification."""
    type: Literal[
        "column_rename", "column_add", "column_drop", "column_transform",
        "filter_rows", "merge_columns", "split_column", "aggregate",
        "pivot", "unpivot", "sort", "deduplicate", "fill_na"
    ]
    params: Dict[str, Any]
    condition: Optional[str] = None  # Optional condition for conditional transforms

class CustomTransformParams(BaseModel):
    """Parameters for CUSTOM_TRANSFORM action."""
    
    input_key: str = Field(..., description="Key of input dataset to transform")
    output_key: str = Field(..., description="Key for transformed dataset")
    
    transformations: List[TransformOperation] = Field(
        ..., 
        description="List of transformation operations to apply in sequence"
    )
    
    validate_schema: bool = Field(
        default=True,
        description="Whether to validate output schema matches expectations"
    )
    
    expected_columns: Optional[List[str]] = Field(
        default=None,
        description="Expected columns in output (for validation)"
    )
    
    preserve_index: bool = Field(
        default=True,
        description="Whether to preserve original DataFrame index"
    )
    
    error_handling: Literal["strict", "warn", "ignore"] = Field(
        default="strict",
        description="How to handle transformation errors"
    )

class CustomTransformResult(ActionResult):
    """Result of CUSTOM_TRANSFORM action."""
    
    rows_processed: int
    columns_before: int
    columns_after: int
    transformations_applied: int
    transformations_failed: int
    warnings: List[str]
    schema_validation_passed: bool
    
    class Config:
        extra = "forbid"
```

### Implementation
```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import (
    DatasetNotFoundError, TransformationError, SchemaValidationError
)
import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

@register_action("CUSTOM_TRANSFORM")
class CustomTransformAction(TypedStrategyAction[CustomTransformParams, CustomTransformResult]):
    """
    Flexible data transformation action supporting multiple transformation types.
    
    Handles complex data transformations that don't fit standard action patterns.
    Supports chaining multiple transformations with error handling and validation.
    """
    
    def get_params_model(self) -> type[CustomTransformParams]:
        return CustomTransformParams
    
    async def execute_typed(
        self, 
        params: CustomTransformParams, 
        context: Dict[str, Any]
    ) -> CustomTransformResult:
        """Execute custom transformations on dataset."""
        
        # Validate input dataset exists
        if params.input_key not in context.get('datasets', {}):
            available_keys = list(context.get('datasets', {}).keys())
            raise DatasetNotFoundError(
                f"Dataset '{params.input_key}' not found. Available: {available_keys}"
            )
        
        df = context['datasets'][params.input_key].copy()
        original_rows = len(df)
        original_cols = len(df.columns)
        
        transformations_applied = 0
        transformations_failed = 0
        warnings = []
        
        # Apply transformations in sequence
        for i, transform_op in enumerate(params.transformations):
            try:
                # Check conditional execution
                if transform_op.condition and not self._evaluate_condition(df, transform_op.condition):
                    continue
                
                df = await self._apply_transformation(df, transform_op)
                transformations_applied += 1
                
                self.logger.debug(f"Applied transformation {i+1}: {transform_op.type}")
                
            except Exception as e:
                transformations_failed += 1
                error_msg = f"Transformation {i+1} ({transform_op.type}) failed: {str(e)}"
                
                if params.error_handling == "strict":
                    raise TransformationError(error_msg)
                elif params.error_handling == "warn":
                    warnings.append(error_msg)
                    self.logger.warning(error_msg)
                # "ignore" continues without logging
        
        # Schema validation
        schema_validation_passed = True
        if params.validate_schema and params.expected_columns:
            missing_cols = set(params.expected_columns) - set(df.columns)
            if missing_cols:
                schema_validation_passed = False
                error_msg = f"Missing expected columns: {missing_cols}"
                
                if params.error_handling == "strict":
                    raise SchemaValidationError(error_msg)
                else:
                    warnings.append(error_msg)
        
        # Store result
        context.setdefault('datasets', {})[params.output_key] = df
        
        # Update statistics
        context.setdefault('statistics', {}).update({
            f'{params.output_key}_rows_processed': len(df),
            f'{params.output_key}_transformations_applied': transformations_applied
        })
        
        return CustomTransformResult(
            success=True,
            rows_processed=len(df),
            columns_before=original_cols,
            columns_after=len(df.columns),
            transformations_applied=transformations_applied,
            transformations_failed=transformations_failed,
            warnings=warnings,
            schema_validation_passed=schema_validation_passed
        )
    
    async def _apply_transformation(
        self, 
        df: pd.DataFrame, 
        transform_op: TransformOperation
    ) -> pd.DataFrame:
        """Apply single transformation operation."""
        
        transform_type = transform_op.type
        params = transform_op.params
        
        if transform_type == "column_rename":
            return df.rename(columns=params.get('mapping', {}))
        
        elif transform_type == "column_add":
            for col_name, col_value in params.get('columns', {}).items():
                if callable(col_value):
                    df[col_name] = col_value(df)
                else:
                    df[col_name] = col_value
            return df
        
        elif transform_type == "column_drop":
            cols_to_drop = params.get('columns', [])
            return df.drop(columns=cols_to_drop, errors='ignore')
        
        elif transform_type == "column_transform":
            col_name = params['column']
            transform_func = params['function']
            
            if isinstance(transform_func, str):
                # Handle string-based transformations
                if transform_func == "lower":
                    df[col_name] = df[col_name].str.lower()
                elif transform_func == "upper":
                    df[col_name] = df[col_name].str.upper()
                elif transform_func == "strip":
                    df[col_name] = df[col_name].str.strip()
                elif transform_func.startswith("replace:"):
                    # Format: "replace:old_value:new_value"
                    _, old_val, new_val = transform_func.split(":", 2)
                    df[col_name] = df[col_name].str.replace(old_val, new_val)
            elif callable(transform_func):
                df[col_name] = df[col_name].apply(transform_func)
            
            return df
        
        elif transform_type == "filter_rows":
            query = params.get('query')
            if query:
                return df.query(query)
            else:
                # Handle column-based filtering
                for col, condition in params.get('conditions', {}).items():
                    if col in df.columns:
                        if isinstance(condition, dict):
                            op = condition.get('operator', '==')
                            value = condition.get('value')
                            
                            if op == '==':
                                df = df[df[col] == value]
                            elif op == '!=':
                                df = df[df[col] != value]
                            elif op == '>':
                                df = df[df[col] > value]
                            elif op == '<':
                                df = df[df[col] < value]
                            elif op == '>=':
                                df = df[df[col] >= value]
                            elif op == '<=':
                                df = df[col] <= value]
                            elif op == 'in':
                                df = df[df[col].isin(value)]
                            elif op == 'not_in':
                                df = df[~df[col].isin(value)]
                return df
        
        elif transform_type == "merge_columns":
            new_col = params['new_column']
            source_cols = params['source_columns']
            separator = params.get('separator', '_')
            
            df[new_col] = df[source_cols].astype(str).agg(separator.join, axis=1)
            return df
        
        elif transform_type == "split_column":
            source_col = params['source_column']
            separator = params.get('separator', '_')
            new_cols = params['new_columns']
            
            split_data = df[source_col].str.split(separator, expand=True)
            for i, new_col in enumerate(new_cols):
                if i < split_data.shape[1]:
                    df[new_col] = split_data[i]
            return df
        
        elif transform_type == "deduplicate":
            subset = params.get('subset')
            keep = params.get('keep', 'first')
            return df.drop_duplicates(subset=subset, keep=keep)
        
        elif transform_type == "fill_na":
            method = params.get('method', 'value')
            if method == 'value':
                fill_value = params.get('value', '')
                return df.fillna(fill_value)
            elif method == 'forward':
                return df.fillna(method='ffill')
            elif method == 'backward':
                return df.fillna(method='bfill')
        
        elif transform_type == "sort":
            by_columns = params.get('by', [])
            ascending = params.get('ascending', True)
            return df.sort_values(by=by_columns, ascending=ascending)
        
        else:
            raise TransformationError(f"Unsupported transformation type: {transform_type}")
    
    def _evaluate_condition(self, df: pd.DataFrame, condition: str) -> bool:
        """Evaluate conditional expression for transformation."""
        try:
            # Simple condition evaluation - can be extended
            return eval(condition, {"df": df, "len": len, "any": any, "all": all})
        except:
            return True  # Default to applying transformation if condition fails
```

### Test Requirements

```python
# tests/unit/core/strategy_actions/utils/data_processing/test_custom_transform.py

import pytest
import pandas as pd
from unittest.mock import AsyncMock

from biomapper.core.strategy_actions.utils.data_processing.custom_transform import (
    CustomTransformAction, CustomTransformParams, TransformOperation
)
from biomapper.core.exceptions import DatasetNotFoundError, TransformationError

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
    
    @pytest.mark.asyncio
    async def test_schema_validation(self, action, sample_data):
        """Test schema validation functionality."""
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
            expected_columns=['id', 'name', 'score', 'category']  # Includes dropped column
        )
        
        with pytest.raises(SchemaValidationError):
            await action.execute_typed(params, context)
    
    @pytest.mark.asyncio
    async def test_error_handling_warn(self, action, sample_data):
        """Test warning error handling mode."""
        context = {'datasets': {'input': sample_data}}
        
        params = CustomTransformParams(
            input_key='input',
            output_key='output',
            transformations=[
                TransformOperation(
                    type='column_drop',
                    params={'columns': ['nonexistent_column']}  # Will cause error
                )
            ],
            error_handling='warn'
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.transformations_failed == 0  # drop with errors='ignore'
        assert len(result.warnings) >= 0
    
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

# Additional test cases for other transformation types...
```

## Action 2: CALCULATE_MAPPING_QUALITY Implementation

### Purpose
Calculates quality metrics for biological identifier mappings, essential for strategy validation and optimization.

### Location
`biomapper/core/strategy_actions/utils/data_processing/calculate_mapping_quality.py`

### Parameter Model
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
import pandas as pd

class QualityMetric(BaseModel):
    """Single quality metric specification."""
    name: str = Field(..., description="Name of the quality metric")
    weight: float = Field(default=1.0, description="Weight of this metric in overall score")
    higher_is_better: bool = Field(default=True, description="Whether higher values indicate better quality")

class CalculateMappingQualityParams(BaseModel):
    """Parameters for CALCULATE_MAPPING_QUALITY action."""
    
    source_key: str = Field(..., description="Key of source dataset")
    mapped_key: str = Field(..., description="Key of mapped dataset")
    output_key: str = Field(..., description="Key for quality metrics output")
    
    source_id_column: str = Field(..., description="Column containing source identifiers")
    mapped_id_column: str = Field(..., description="Column containing mapped identifiers")
    confidence_column: Optional[str] = Field(default=None, description="Column containing mapping confidence scores")
    
    metrics_to_calculate: List[Literal[
        "match_rate", "coverage", "precision", "recall", "f1_score",
        "confidence_distribution", "duplicate_rate", "ambiguity_rate",
        "identifier_quality", "semantic_similarity"
    ]] = Field(
        default=["match_rate", "coverage", "precision"],
        description="Quality metrics to calculate"
    )
    
    confidence_threshold: float = Field(
        default=0.8,
        description="Minimum confidence threshold for high-quality matches"
    )
    
    reference_dataset_key: Optional[str] = Field(
        default=None,
        description="Key of reference dataset for precision/recall calculation"
    )
    
    include_detailed_report: bool = Field(
        default=True,
        description="Whether to include detailed per-identifier analysis"
    )

class MappingQualityResult(ActionResult):
    """Result of CALCULATE_MAPPING_QUALITY action."""
    
    total_source_identifiers: int
    total_mapped_identifiers: int
    successful_mappings: int
    failed_mappings: int
    
    overall_quality_score: float
    individual_metrics: Dict[str, float]
    quality_distribution: Dict[str, int]
    
    high_confidence_mappings: int
    low_confidence_mappings: int
    ambiguous_mappings: int
    
    detailed_report: Optional[Dict[str, Any]]
    recommendations: List[str]
    
    class Config:
        extra = "forbid"
```

### Implementation
```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import DatasetNotFoundError, MappingQualityError
import pandas as pd
import numpy as np
from typing import Dict, Any, Set, List
import logging
from collections import Counter

@register_action("CALCULATE_MAPPING_QUALITY")
class CalculateMappingQualityAction(TypedStrategyAction[CalculateMappingQualityParams, MappingQualityResult]):
    """
    Calculate comprehensive quality metrics for biological identifier mappings.
    
    Provides detailed analysis of mapping success rates, confidence distributions,
    and quality scores to help validate and optimize mapping strategies.
    """
    
    def get_params_model(self) -> type[CalculateMappingQualityParams]:
        return CalculateMappingQualityParams
    
    async def execute_typed(
        self, 
        params: CalculateMappingQualityParams, 
        context: Dict[str, Any]
    ) -> MappingQualityResult:
        """Calculate mapping quality metrics."""
        
        # Validate required datasets
        datasets = context.get('datasets', {})
        if params.source_key not in datasets:
            raise DatasetNotFoundError(f"Source dataset '{params.source_key}' not found")
        if params.mapped_key not in datasets:
            raise DatasetNotFoundError(f"Mapped dataset '{params.mapped_key}' not found")
        
        source_df = datasets[params.source_key]
        mapped_df = datasets[params.mapped_key]
        
        # Validate required columns
        if params.source_id_column not in source_df.columns:
            raise MappingQualityError(f"Source ID column '{params.source_id_column}' not found")
        if params.mapped_id_column not in mapped_df.columns:
            raise MappingQualityError(f"Mapped ID column '{params.mapped_id_column}' not found")
        
        # Calculate basic counts
        total_source = len(source_df)
        total_mapped = len(mapped_df)
        
        # Identify successful mappings (non-null mapped identifiers)
        successful_mask = mapped_df[params.mapped_id_column].notna() & \
                         (mapped_df[params.mapped_id_column] != '') & \
                         (mapped_df[params.mapped_id_column] != 'unknown')
        
        successful_mappings = successful_mask.sum()
        failed_mappings = total_mapped - successful_mappings
        
        # Calculate individual metrics
        individual_metrics = {}
        
        if "match_rate" in params.metrics_to_calculate:
            individual_metrics["match_rate"] = successful_mappings / total_source if total_source > 0 else 0
        
        if "coverage" in params.metrics_to_calculate:
            individual_metrics["coverage"] = successful_mappings / total_mapped if total_mapped > 0 else 0
        
        # Calculate confidence-based metrics
        high_confidence_mappings = 0
        low_confidence_mappings = 0
        confidence_scores = []
        
        if params.confidence_column and params.confidence_column in mapped_df.columns:
            confidence_scores = mapped_df[params.confidence_column].dropna()
            high_confidence_mappings = (confidence_scores >= params.confidence_threshold).sum()
            low_confidence_mappings = (confidence_scores < params.confidence_threshold).sum()
            
            if "confidence_distribution" in params.metrics_to_calculate:
                individual_metrics["avg_confidence"] = confidence_scores.mean()
                individual_metrics["min_confidence"] = confidence_scores.min()
                individual_metrics["max_confidence"] = confidence_scores.max()
        
        # Calculate duplicate and ambiguity rates
        ambiguous_mappings = 0
        if "duplicate_rate" in params.metrics_to_calculate:
            mapped_ids = mapped_df[mapped_df[params.mapped_id_column].notna()][params.mapped_id_column]
            duplicate_count = len(mapped_ids) - len(mapped_ids.unique())
            individual_metrics["duplicate_rate"] = duplicate_count / len(mapped_ids) if len(mapped_ids) > 0 else 0
        
        if "ambiguity_rate" in params.metrics_to_calculate:
            # Count how many source IDs map to multiple targets
            mapping_counts = mapped_df.groupby(params.source_id_column)[params.mapped_id_column].nunique()
            ambiguous_mappings = (mapping_counts > 1).sum()
            individual_metrics["ambiguity_rate"] = ambiguous_mappings / total_source if total_source > 0 else 0
        
        # Precision and recall (if reference dataset provided)
        if params.reference_dataset_key and params.reference_dataset_key in datasets:
            reference_df = datasets[params.reference_dataset_key]
            
            if "precision" in params.metrics_to_calculate or "recall" in params.metrics_to_calculate:
                precision, recall, f1 = self._calculate_precision_recall(
                    mapped_df, reference_df, params
                )
                
                if "precision" in params.metrics_to_calculate:
                    individual_metrics["precision"] = precision
                if "recall" in params.metrics_to_calculate:
                    individual_metrics["recall"] = recall
                if "f1_score" in params.metrics_to_calculate:
                    individual_metrics["f1_score"] = f1
        
        # Calculate identifier quality metrics
        if "identifier_quality" in params.metrics_to_calculate:
            id_quality = self._assess_identifier_quality(mapped_df, params.mapped_id_column)
            individual_metrics.update(id_quality)
        
        # Calculate overall quality score (weighted average)
        overall_quality_score = self._calculate_overall_quality(individual_metrics)
        
        # Quality distribution
        quality_distribution = {
            "high_quality": high_confidence_mappings,
            "medium_quality": successful_mappings - high_confidence_mappings - low_confidence_mappings,
            "low_quality": low_confidence_mappings,
            "failed": failed_mappings
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            individual_metrics, total_source, successful_mappings, params
        )
        
        # Detailed report (if requested)
        detailed_report = None
        if params.include_detailed_report:
            detailed_report = self._generate_detailed_report(
                source_df, mapped_df, params, individual_metrics
            )
        
        # Store quality metrics in context
        context.setdefault('statistics', {}).update({
            f'{params.output_key}_overall_quality': overall_quality_score,
            f'{params.output_key}_match_rate': individual_metrics.get("match_rate", 0),
            f'{params.output_key}_successful_mappings': successful_mappings
        })
        
        # Store detailed metrics dataset
        quality_df = pd.DataFrame([{
            'metric': k,
            'value': v,
            'category': 'mapping_quality'
        } for k, v in individual_metrics.items()])
        
        context.setdefault('datasets', {})[params.output_key] = quality_df
        
        return MappingQualityResult(
            success=True,
            total_source_identifiers=total_source,
            total_mapped_identifiers=total_mapped,
            successful_mappings=successful_mappings,
            failed_mappings=failed_mappings,
            overall_quality_score=overall_quality_score,
            individual_metrics=individual_metrics,
            quality_distribution=quality_distribution,
            high_confidence_mappings=high_confidence_mappings,
            low_confidence_mappings=low_confidence_mappings,
            ambiguous_mappings=ambiguous_mappings,
            detailed_report=detailed_report,
            recommendations=recommendations
        )
    
    def _calculate_precision_recall(
        self, 
        mapped_df: pd.DataFrame, 
        reference_df: pd.DataFrame,
        params: CalculateMappingQualityParams
    ) -> tuple[float, float, float]:
        """Calculate precision, recall, and F1 score against reference."""
        
        # Extract mapped pairs
        mapped_pairs = set()
        for _, row in mapped_df.iterrows():
            source_id = row[params.source_id_column]
            mapped_id = row[params.mapped_id_column]
            if pd.notna(mapped_id) and mapped_id != '':
                mapped_pairs.add((source_id, mapped_id))
        
        # Extract reference pairs (assuming same column structure)
        reference_pairs = set()
        for _, row in reference_df.iterrows():
            source_id = row[params.source_id_column] 
            ref_id = row[params.mapped_id_column]
            if pd.notna(ref_id) and ref_id != '':
                reference_pairs.add((source_id, ref_id))
        
        # Calculate metrics
        true_positives = len(mapped_pairs & reference_pairs)
        precision = true_positives / len(mapped_pairs) if mapped_pairs else 0
        recall = true_positives / len(reference_pairs) if reference_pairs else 0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return precision, recall, f1_score
    
    def _assess_identifier_quality(self, df: pd.DataFrame, id_column: str) -> Dict[str, float]:
        """Assess quality of identifiers themselves."""
        
        ids = df[id_column].dropna()
        if len(ids) == 0:
            return {"id_format_consistency": 0, "id_completeness": 0}
        
        # Check format consistency (example for UniProt-like IDs)
        format_scores = []
        for id_val in ids:
            id_str = str(id_val)
            score = 0
            
            # Length consistency
            if len(id_str) >= 6:
                score += 0.3
            
            # Alphanumeric pattern
            if id_str.isalnum():
                score += 0.3
            
            # No spaces or special characters
            if not any(c in id_str for c in [' ', '\t', '\n', '|', ';']):
                score += 0.4
            
            format_scores.append(score)
        
        return {
            "id_format_consistency": np.mean(format_scores),
            "id_completeness": len(ids) / len(df)
        }
    
    def _calculate_overall_quality(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted overall quality score."""
        
        # Default weights for common metrics
        weights = {
            "match_rate": 0.3,
            "coverage": 0.2, 
            "precision": 0.2,
            "avg_confidence": 0.15,
            "id_format_consistency": 0.1,
            "f1_score": 0.05
        }
        
        total_score = 0
        total_weight = 0
        
        for metric, value in metrics.items():
            if metric in weights:
                total_score += value * weights[metric]
                total_weight += weights[metric]
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _generate_recommendations(
        self, 
        metrics: Dict[str, float], 
        total_source: int,
        successful_mappings: int,
        params: CalculateMappingQualityParams
    ) -> List[str]:
        """Generate actionable recommendations based on quality metrics."""
        
        recommendations = []
        
        match_rate = metrics.get("match_rate", 0)
        if match_rate < 0.7:
            recommendations.append(
                f"Low match rate ({match_rate:.1%}). Consider using additional identifier types or fuzzy matching."
            )
        
        if "duplicate_rate" in metrics and metrics["duplicate_rate"] > 0.1:
            recommendations.append(
                f"High duplicate rate ({metrics['duplicate_rate']:.1%}). Review mapping logic for one-to-many relationships."
            )
        
        if "ambiguity_rate" in metrics and metrics["ambiguity_rate"] > 0.05:
            recommendations.append(
                f"High ambiguity rate ({metrics['ambiguity_rate']:.1%}). Consider adding disambiguation criteria."
            )
        
        if "avg_confidence" in metrics and metrics["avg_confidence"] < params.confidence_threshold:
            recommendations.append(
                f"Low average confidence ({metrics['avg_confidence']:.2f}). Review confidence scoring algorithm."
            )
        
        if successful_mappings < total_source * 0.8:
            recommendations.append(
                "Consider preprocessing source identifiers (normalization, cleaning) to improve match rates."
            )
        
        return recommendations
    
    def _generate_detailed_report(
        self,
        source_df: pd.DataFrame,
        mapped_df: pd.DataFrame, 
        params: CalculateMappingQualityParams,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate detailed per-identifier analysis."""
        
        # Per-identifier success analysis
        identifier_analysis = []
        
        for _, row in mapped_df.iterrows():
            source_id = row[params.source_id_column]
            mapped_id = row[params.mapped_id_column]
            confidence = row.get(params.confidence_column, None) if params.confidence_column else None
            
            analysis = {
                "source_id": source_id,
                "mapped_id": mapped_id,
                "success": pd.notna(mapped_id) and mapped_id != '',
                "confidence": confidence
            }
            
            identifier_analysis.append(analysis)
        
        return {
            "identifier_analysis": identifier_analysis[:100],  # Limit for performance
            "summary_stats": metrics,
            "data_quality": {
                "source_completeness": (source_df[params.source_id_column].notna()).sum() / len(source_df),
                "mapped_completeness": (mapped_df[params.mapped_id_column].notna()).sum() / len(mapped_df)
            }
        }
```

### Test Requirements

```python
# tests/unit/core/strategy_actions/utils/data_processing/test_calculate_mapping_quality.py

import pytest
import pandas as pd
from unittest.mock import AsyncMock

from biomapper.core.strategy_actions.utils.data_processing.calculate_mapping_quality import (
    CalculateMappingQualityAction, CalculateMappingQualityParams
)

class TestCalculateMappingQualityAction:
    """Test suite for CalculateMappingQualityAction."""
    
    @pytest.fixture
    def source_data(self):
        """Source dataset for testing."""
        return pd.DataFrame({
            'protein_id': ['P12345', 'P67890', 'P11111', 'P22222'],
            'name': ['Protein A', 'Protein B', 'Protein C', 'Protein D']
        })
    
    @pytest.fixture
    def mapped_data(self):
        """Mapped dataset for testing."""
        return pd.DataFrame({
            'protein_id': ['P12345', 'P67890', 'P11111', 'P22222'],
            'uniprot_id': ['P12345', 'P67890', None, 'P22222'],
            'confidence': [0.95, 0.87, None, 0.72]
        })
    
    @pytest.fixture
    def action(self):
        """CalculateMappingQualityAction instance."""
        return CalculateMappingQualityAction()
    
    @pytest.mark.asyncio
    async def test_basic_quality_calculation(self, action, source_data, mapped_data):
        """Test basic quality metrics calculation."""
        context = {
            'datasets': {
                'source': source_data,
                'mapped': mapped_data
            }
        }
        
        params = CalculateMappingQualityParams(
            source_key='source',
            mapped_key='mapped',
            output_key='quality',
            source_id_column='protein_id',
            mapped_id_column='uniprot_id',
            confidence_column='confidence',
            metrics_to_calculate=['match_rate', 'coverage', 'confidence_distribution']
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.total_source_identifiers == 4
        assert result.successful_mappings == 3  # P11111 has None
        assert result.failed_mappings == 1
        
        # Check individual metrics
        assert 'match_rate' in result.individual_metrics
        assert result.individual_metrics['match_rate'] == 0.75  # 3/4
        assert 'avg_confidence' in result.individual_metrics
        
        # Check quality distribution
        assert result.quality_distribution['high_quality'] == 2  # confidence >= 0.8
        assert result.quality_distribution['low_quality'] == 1   # confidence < 0.8
    
    @pytest.mark.asyncio
    async def test_precision_recall_with_reference(self, action, source_data, mapped_data):
        """Test precision and recall calculation with reference dataset."""
        reference_data = pd.DataFrame({
            'protein_id': ['P12345', 'P67890', 'P11111', 'P22222'],
            'uniprot_id': ['P12345', 'P67890', 'P33333', 'P22222']  # Different P11111 mapping
        })
        
        context = {
            'datasets': {
                'source': source_data,
                'mapped': mapped_data,
                'reference': reference_data
            }
        }
        
        params = CalculateMappingQualityParams(
            source_key='source',
            mapped_key='mapped',
            output_key='quality',
            source_id_column='protein_id',
            mapped_id_column='uniprot_id',
            reference_dataset_key='reference',
            metrics_to_calculate=['precision', 'recall', 'f1_score']
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert 'precision' in result.individual_metrics
        assert 'recall' in result.individual_metrics
        assert 'f1_score' in result.individual_metrics
        
        # Should have good precision/recall for matching entries
        assert result.individual_metrics['precision'] > 0.8
    
    @pytest.mark.asyncio 
    async def test_recommendations_generation(self, action, source_data):
        """Test that appropriate recommendations are generated."""
        # Create low-quality mapped data
        poor_mapped_data = pd.DataFrame({
            'protein_id': ['P12345', 'P67890', 'P11111', 'P22222'],
            'uniprot_id': [None, None, 'P11111', None],  # Only 1/4 successful
            'confidence': [None, None, 0.6, None]        # Low confidence
        })
        
        context = {
            'datasets': {
                'source': source_data,
                'mapped': poor_mapped_data
            }
        }
        
        params = CalculateMappingQualityParams(
            source_key='source',
            mapped_key='mapped', 
            output_key='quality',
            source_id_column='protein_id',
            mapped_id_column='uniprot_id',
            confidence_column='confidence',
            metrics_to_calculate=['match_rate', 'confidence_distribution']
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert len(result.recommendations) > 0
        
        # Should recommend improvements for low match rate
        rec_text = ' '.join(result.recommendations)
        assert 'Low match rate' in rec_text or 'match rate' in rec_text.lower()
```

Would you like me to continue with the third prompt file for investigating infrastructure dependencies and parameter resolution issues?