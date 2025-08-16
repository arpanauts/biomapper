# Biomapper Action Types - MVP Implementation Plan

## Overview

This document outlines a pragmatic MVP approach for implementing generalized action types in Biomapper. The MVP focuses on the 80/20 rule: simple table operations that handle most biological mapping use cases, with YAML-driven configuration for flexibility.

## Core Philosophy

### Keep It Simple
- **Data Model**: Tables (DataFrames) as the primary data structure
- **Operations**: SQL-like operations (merge, filter, transform)
- **Configuration**: YAML defines all column names and operational parameters
- **No Streaming**: Metadata files are small enough for in-memory processing
- **No Complex Parsers**: Basic string operations and pandas for identifier handling

### Action Types as Compound Operations
Each action encapsulates a complete biological workflow step with multiple internal operations, not just thin pandas wrappers.

## MVP Data Model

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd

class TableData(BaseModel):
    """Simple table representation - core data structure"""
    rows: List[Dict[str, Any]]
    
    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)
    
    @classmethod 
    def from_dataframe(cls, df: pd.DataFrame) -> 'TableData':
        return cls(rows=df.to_dict('records'))

class ActionResult(BaseModel):
    """Standard output from any action"""
    data: TableData
    metadata: Dict[str, Any] = {}
    row_count: int
    columns: List[str]
    
class SimpleContext(dict):
    """Context stores named DataFrames between actions"""
    
    def get_dataframe(self, key: str) -> pd.DataFrame:
        return self[key].to_dataframe()
    
    def set_dataframe(self, key: str, df: pd.DataFrame):
        self[key] = TableData.from_dataframe(df)
```

## Essential MVP Actions (10 Actions)

### 1. LOAD_DATASET_IDENTIFIERS
**Purpose**: Load + parse + validate + normalize identifiers in one step

```python
class LoadDatasetIdentifiersParams(BaseModel):
    file_path: str
    column_mappings: List[ColumnMapping]
    required_columns: List[str] = []
    drop_columns: List[str] = []
    output_key: str

class ColumnMapping(BaseModel):
    column_name: str                    # Actual CSV column name
    identifier_type: str               # What type of ID this is
    is_primary: bool = False           # Is this the main identifier?
    is_composite: bool = False         # Multi-value field?
    composite_separator: str = ";"     # How to split multi-values
    validation_pattern: Optional[str]  # Regex for validation
```

**Operations**:
- Load CSV/TSV file
- Parse identifier columns (basic string cleaning)
- Handle multi-value fields (explode semicolon-separated values)
- Validate required columns exist
- Basic normalization (strip, uppercase)

### 2. MERGE_DATASETS
**Purpose**: Join two datasets with flexible matching

```python
class MergeDatasetsParams(BaseModel):
    left_dataset: str
    right_dataset: str
    join_conditions: List[JoinCondition]
    how: Literal['outer', 'inner', 'left', 'right'] = 'outer'
    output_key: str

class JoinCondition(BaseModel):
    left_column: str
    right_column: str
    match_type: Literal['exact', 'fuzzy'] = 'exact'
    similarity_threshold: float = 0.8  # For fuzzy matching
```

**Operations**:
- Perform pandas merge operations
- Handle multiple join conditions
- Basic fuzzy matching using string similarity
- Resolve column name conflicts

### 3. RESOLVE_CROSS_REFERENCES
**Purpose**: Look up external mappings via APIs

```python
class ResolveCrossReferencesParams(BaseModel):
    input_key: str
    source_column: str
    target_database: Literal['uniprot', 'ensembl', 'hmdb', 'chebi']
    result_column: str
    confidence_column: str = "mapping_confidence"
    batch_size: int = 100
    output_key: str
```

**Operations**:
- Batch API calls with rate limiting
- Parse API responses (basic JSON/XML parsing)
- Calculate simple confidence scores
- Handle one-to-many mappings (take highest confidence)

### 4. CALCULATE_SET_OVERLAP
**Purpose**: Comprehensive set analysis

```python
class CalculateSetOverlapParams(BaseModel):
    set_a_key: str
    set_b_key: str
    compare_columns: List[CompareColumn]
    overlap_method: Literal['any_match', 'all_match'] = 'any_match'
    output_key: str

class CompareColumn(BaseModel):
    a_column: str
    b_column: str
    weight: float = 1.0  # For weighted overlap
```

**Operations**:
- Extract identifier sets from specified columns
- Calculate intersection, union, Jaccard index
- Generate overlap matrix
- Basic statistical analysis
- Prepare data for visualization

### 5. TRANSFORM_COLUMNS
**Purpose**: Column-level transformations

```python
class TransformColumnsParams(BaseModel):
    input_key: str
    operations: List[ColumnOperation]
    output_key: str

class ColumnOperation(BaseModel):
    type: Literal['rename', 'strip_whitespace', 'extract_pattern', 'fill_missing', 'uppercase', 'lowercase']
    column: str
    new_name: Optional[str] = None      # For rename
    pattern: Optional[str] = None       # For extract_pattern
    new_column: Optional[str] = None    # For extract_pattern
    fill_value: Optional[str] = None    # For fill_missing
```

### 6. FILTER_ROWS
**Purpose**: Row-level filtering

```python
class FilterRowsParams(BaseModel):
    input_key: str
    conditions: List[FilterCondition]
    combine_method: Literal['and', 'or'] = 'and'
    output_key: str

class FilterCondition(BaseModel):
    column: str
    operator: Literal['eq', 'ne', 'contains', 'not_contains', 'regex', 'is_null', 'not_null']
    value: Optional[str] = None
    case_sensitive: bool = True
```

### 7. DEDUPLICATE_RECORDS
**Purpose**: Remove duplicate records

```python
class DeduplicateRecordsParams(BaseModel):
    input_key: str
    key_columns: List[str]
    keep: Literal['first', 'last', 'best'] = 'first'
    quality_column: Optional[str] = None  # For 'best' strategy
    output_key: str
```

### 8. VALIDATE_DATA_QUALITY
**Purpose**: Data quality checks

```python
class ValidateDataQualityParams(BaseModel):
    input_key: str
    validations: List[ValidationRule]
    fail_on_error: bool = False
    output_key: str

class ValidationRule(BaseModel):
    type: Literal['required_columns', 'pattern_match', 'value_range', 'no_duplicates']
    columns: List[str]
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
```

### 9. AGGREGATE_STATISTICS
**Purpose**: Calculate summary statistics

```python
class AggregateStatisticsParams(BaseModel):
    input_key: str
    group_by_columns: List[str] = []
    aggregations: List[AggregationRule]
    output_key: str

class AggregationRule(BaseModel):
    column: str
    functions: List[Literal['count', 'sum', 'mean', 'median', 'std', 'min', 'max']]
    result_prefix: str = ""
```

### 10. GENERATE_MAPPING_REPORT
**Purpose**: Create standardized output

```python
class GenerateMappingReportParams(BaseModel):
    primary_data: str
    include_statistics: bool = True
    output_format: Literal['csv', 'tsv', 'excel', 'json'] = 'csv'
    output_path: str
    summary_stats: bool = True
```

## Example MVP Strategy

```yaml
name: PROTEIN_MAPPING_MVP
description: Map proteins between UKBB and HPA datasets

steps:
  - name: load_ukbb_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "data/ukbb_proteins.csv"
        column_mappings:
          - column_name: "uniprot_id"
            identifier_type: "uniprot_accession"
            is_primary: true
            validation_pattern: "^[A-Z0-9]{6,10}$"
          - column_name: "gene_names"
            identifier_type: "gene_symbol"
            is_composite: true
            composite_separator: ";"
        required_columns: ["uniprot_id"]
        output_key: "ukbb_data"

  - name: load_hpa_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "data/hpa_proteins.csv"
        column_mappings:
          - column_name: "ensembl_id"
            identifier_type: "ensembl_gene"
            is_primary: true
        output_key: "hpa_data"

  - name: resolve_ukbb_to_ensembl
    action:
      type: RESOLVE_CROSS_REFERENCES
      params:
        input_key: "ukbb_data"
        source_column: "uniprot_id"
        target_database: "ensembl"
        result_column: "ensembl_id"
        confidence_column: "mapping_confidence"
        batch_size: 50
        output_key: "ukbb_with_ensembl"

  - name: merge_datasets
    action:
      type: MERGE_DATASETS
      params:
        left_dataset: "ukbb_with_ensembl"
        right_dataset: "hpa_data"
        join_conditions:
          - left_column: "ensembl_id"
            right_column: "ensembl_id"
            match_type: "exact"
        how: "outer"
        output_key: "merged_data"

  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        set_a_key: "ukbb_with_ensembl"
        set_b_key: "hpa_data"
        compare_columns:
          - a_column: "ensembl_id"
            b_column: "ensembl_id"
        output_key: "overlap_analysis"

  - name: validate_results
    action:
      type: VALIDATE_DATA_QUALITY
      params:
        input_key: "merged_data"
        validations:
          - type: "required_columns"
            columns: ["uniprot_id", "ensembl_id"]
        output_key: "validated_results"

  - name: generate_final_report
    action:
      type: GENERATE_MAPPING_REPORT
      params:
        primary_data: "validated_results"
        include_statistics: true
        output_format: "csv"
        output_path: "results/protein_mapping_results.csv"
```

## Implementation Timeline

### Week 1: Core Infrastructure
**Days 1-2**: Base action framework
- `TypedStrategyAction` base class
- `TableData` and `ActionResult` models
- `SimpleContext` for data passing
- Basic YAML strategy executor

**Days 3-5**: Essential actions
- `LOAD_DATASET_IDENTIFIERS`
- `MERGE_DATASETS` 
- `TRANSFORM_COLUMNS`

### Week 2: Mapping Actions
**Days 1-3**: External integration
- `RESOLVE_CROSS_REFERENCES` (UniProt, Ensembl APIs)
- `CALCULATE_SET_OVERLAP`
- `FILTER_ROWS`

**Days 4-5**: Quality and output
- `VALIDATE_DATA_QUALITY`
- `GENERATE_MAPPING_REPORT`
- `DEDUPLICATE_RECORDS`

### Week 3: Testing and Integration
**Days 1-3**: Testing
- Unit tests for each action
- Integration tests with real datasets
- YAML strategy validation

**Days 4-5**: Documentation and polish
- Usage examples
- Error handling improvements
- Performance optimization

## Success Criteria

1. **Functional**: Successfully map UKBB proteins to HPA proteins
2. **Configurable**: Change datasets by only modifying YAML config
3. **Testable**: Comprehensive test suite with >80% coverage
4. **Documented**: Clear examples and API documentation
5. **Performance**: Handle 10K+ protein datasets in <30 seconds

## Post-MVP Enhancements

After MVP is stable:
- Advanced fuzzy matching algorithms
- Streaming support for larger datasets
- Plugin architecture for custom parsers
- Graph-based cross-reference resolution
- Machine learning for mapping confidence
- Web UI for strategy creation

## Key Benefits of This Approach

1. **Pragmatic**: Focuses on common use cases, not edge cases
2. **Flexible**: YAML configuration drives all operations
3. **Testable**: Clear inputs/outputs for each action
4. **Extensible**: Easy to add new actions or enhance existing ones
5. **Maintainable**: Simple codebase focused on table operations
6. **Fast to Implement**: Can be built in 2-3 weeks
7. **Immediately Useful**: Solves real mapping problems from day one