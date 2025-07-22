# MVP Action Specifications for Protein Mapping

Based on the UKBB→HPA walkthrough, here are the exact specifications for each action.

## 1. LOAD_DATASET_IDENTIFIERS

### Purpose
Load tabular data from files, handling composite identifiers and column mapping.

### Input Parameters
```python
class LoadDatasetIdentifiersParams(BaseModel):
    file_path: str = Field(..., description="Path to CSV/TSV file")
    
    column_mappings: List[ColumnMapping] = Field(
        ..., 
        description="How to interpret each column"
    )
    
    drop_empty_primary: bool = Field(
        True,
        description="Remove rows where primary identifier is empty"
    )
    
    output_key: str = Field(..., description="Context key for output")

class ColumnMapping(BaseModel):
    column_name: str = Field(..., description="Actual column name in file")
    identifier_type: str = Field(..., description="Semantic type")
    is_primary: bool = Field(False, description="Is this the main ID?")
    is_composite: bool = Field(False, description="Contains multiple IDs?")
    composite_separator: str = Field("_", description="Separator character")
```

### Processing Logic
1. **Read file** (CSV or TSV based on extension)
2. **Validate columns** exist
3. **For each composite column**:
   - Find rows with separator
   - Split into multiple values
   - Create new row for each value
   - Add tracking metadata:
     - `_composite_source`: Original value
     - `_composite_group`: Unique group ID
4. **Add row source**: `_row_source` = "filename:line_number"
5. **Drop empty primary** if configured

### Output
- **To context['datasets'][output_key]**: TableData with expanded rows
- **To context['metadata'][output_key]**:
  ```python
  {
      'row_count': int,
      'original_row_count': int,
      'composite_expansions': int,
      'columns': List[str],
      'primary_column': str,
      'source_file': str,
      'load_timestamp': str
  }
  ```

### Error Handling
- FileNotFoundError → Clear message with path
- Missing columns → List missing and available columns
- Invalid composite separator in data → Warning, treat as non-composite

---

## 2. RESOLVE_CROSS_REFERENCES

### Purpose
Resolve identifiers via external APIs (initially UniProt historical resolution).

### Input Parameters
```python
class ResolveCrossReferencesParams(BaseModel):
    input_key: str = Field(..., description="Dataset to resolve")
    source_column: str = Field(..., description="Column with IDs to resolve")
    
    target_database: str = Field(
        "uniprot",
        description="Which database to query"
    )
    
    api_type: str = Field(
        "historical",
        description="Type of resolution"
    )
    
    result_column: str = Field(..., description="Column for resolved IDs")
    confidence_column: str = Field(..., description="Column for confidence scores")
    
    batch_size: int = Field(100, description="IDs per API call")
    cache_results: bool = Field(True, description="Cache API responses")
    include_failed: bool = Field(True, description="Keep unresolved rows")
    
    output_key: str = Field(..., description="Context key for output")
```

### Processing Logic
1. **Extract unique IDs** from source_column
2. **Check cache** in context['api_cache'] if enabled
3. **Batch API calls**:
   ```python
   for batch in chunks(unique_ids, batch_size):
       response = call_api(batch)
       parse_and_store(response)
   ```
4. **Parse responses** based on api_type:
   - For UniProt historical:
     - Direct match → confidence 1.0
     - Secondary accession → confidence 0.95
     - Obsolete → confidence 0.90
     - Not found → confidence 0.0, keep original
5. **Add columns** to original data:
   - `result_column`: Resolved ID
   - `confidence_column`: Confidence score
   - `_resolution_type`: Type of resolution
   - `_resolution_note`: Any warnings
6. **Update cache** if enabled

### Output
- **To context['datasets'][output_key]**: Original data + resolution columns
- **To context['metadata'][output_key]**: Add resolution stats
  ```python
  {
      ...existing metadata...,
      'resolution_stats': {
          'total_ids': int,
          'unchanged': int,
          'resolved': int,
          'failed': int,
          'average_confidence': float,
          'api_calls_made': int,
          'cache_hits': int
      }
  }
  ```

### Error Handling
- API timeout → Retry with exponential backoff
- API error → Log, mark as failed with confidence 0
- Invalid response format → Log, treat as not found

---

## 3. MERGE_DATASETS

### Purpose
Join two datasets on specified columns with sophisticated conflict resolution.

### Input Parameters
```python
class MergeDatasetsParams(BaseModel):
    left_dataset: str = Field(..., description="First dataset key")
    right_dataset: str = Field(..., description="Second dataset key")
    
    join_conditions: List[JoinCondition] = Field(
        ...,
        description="How to match rows"
    )
    
    how: Literal['inner', 'outer', 'left', 'right'] = Field(
        'outer',
        description="Join type"
    )
    
    suffixes: Dict[str, str] = Field(
        default={'left': '_left', 'right': '_right'},
        description="Suffixes for conflicting columns"
    )
    
    output_key: str = Field(..., description="Context key for output")

class JoinCondition(BaseModel):
    left_column: str
    right_column: str
    match_type: Literal['exact', 'fuzzy'] = 'exact'
    similarity_threshold: float = 0.8  # For fuzzy
```

### Processing Logic
1. **Get datasets** from context
2. **Identify conflicts**:
   - Join columns (keep one copy)
   - Other columns with same name (apply suffixes)
3. **Perform merge**:
   ```python
   merged = pd.merge(
       left_df, right_df,
       left_on=[jc.left_column for jc in join_conditions],
       right_on=[jc.right_column for jc in join_conditions],
       how=how,
       suffixes=(suffixes['left'], suffixes['right'])
   )
   ```
4. **Add tracking columns**:
   - `_in_both`: Boolean
   - `_merge_source`: 'both', 'left_only', 'right_only'
5. **Handle join columns**:
   - Keep as single column (they're equal in matches)
   - For outer joins with nulls, coalesce left/right values

### Output
- **To context['datasets'][output_key]**: Merged TableData
- **To context['metadata'][output_key]**:
  ```python
  {
      'row_count': int,
      'columns': List[str],
      'merge_stats': {
          'left_rows': int,
          'right_rows': int,
          'matched_rows': int,
          'left_only_rows': int,
          'right_only_rows': int,
          'join_columns': List[str]
      }
  }
  ```

---

## 4. CALCULATE_SET_OVERLAP

### Purpose
Analyze overlap between two sets of identifiers with detailed statistics.

### Input Parameters
```python
class CalculateSetOverlapParams(BaseModel):
    set_a_key: str = Field(..., description="First dataset")
    set_b_key: str = Field(..., description="Second dataset")
    
    compare_columns: List[CompareColumn] = Field(
        ...,
        description="Which columns to compare"
    )
    
    set_a_name: str = Field("Set A", description="Display name")
    set_b_name: str = Field("Set B", description="Display name")
    
    output_key: str = Field(..., description="Context key for output")

class CompareColumn(BaseModel):
    a_column: str
    b_column: str
    weight: float = 1.0  # For weighted overlap
```

### Processing Logic
1. **Extract unique values** from each dataset
2. **Calculate sets**:
   ```python
   set_a = set(df_a[column_a].dropna().unique())
   set_b = set(df_b[column_b].dropna().unique())
   intersection = set_a & set_b
   union = set_a | set_b
   ```
3. **Create overlap table**:
   ```python
   all_ids = sorted(union)
   rows = []
   for id in all_ids:
       rows.append({
           'identifier': id,
           f'in_{set_a_name}': id in set_a,
           f'in_{set_b_name}': id in set_b
       })
   ```
4. **Calculate statistics**:
   - Counts (set_a, set_b, intersection, union)
   - Jaccard index: |A∩B| / |A∪B|
   - Dice coefficient: 2|A∩B| / (|A| + |B|)
   - Overlap percentages

### Output
- **To context['datasets'][output_key]**: Overlap table
- **To context['statistics'][output_key]**:
  ```python
  {
      'set_a_count': int,
      'set_b_count': int,
      'intersection_count': int,
      'union_count': int,
      'set_a_only': int,
      'set_b_only': int,
      'jaccard_index': float,
      'dice_coefficient': float,
      'overlap_percentage_a': float,
      'overlap_percentage_b': float,
      'set_a_name': str,
      'set_b_name': str
  }
  ```

---

## 5. AGGREGATE_STATISTICS

### Purpose
Calculate grouped statistics with multiple aggregation functions.

### Input Parameters
```python
class AggregateStatisticsParams(BaseModel):
    input_key: str = Field(..., description="Dataset to aggregate")
    
    group_by_columns: List[str] = Field(
        [],
        description="Columns to group by"
    )
    
    aggregations: List[AggregationRule] = Field(
        ...,
        description="What to calculate"
    )
    
    include_totals: bool = Field(
        True,
        description="Add grand total row"
    )
    
    output_key: str = Field(..., description="Context key for output")

class AggregationRule(BaseModel):
    column: str
    functions: List[Literal['count', 'nunique', 'sum', 'mean', 'min', 'max', 'std']]
    result_prefix: str = ""
```

### Processing Logic
1. **Group data**:
   ```python
   if group_by_columns:
       grouped = df.groupby(group_by_columns, dropna=False)
   else:
       grouped = df  # No grouping
   ```
2. **Apply aggregations**:
   ```python
   agg_dict = {}
   for rule in aggregations:
       for func in rule.functions:
           col_name = f"{rule.result_prefix}{func}"
           agg_dict[col_name] = (rule.column, func)
   
   result = grouped.agg(**agg_dict)
   ```
3. **Add totals row** if requested
4. **Handle null groups** (e.g., Panel=None)

### Output
- **To context['datasets'][output_key]**: Aggregated data
- **To context['metadata'][output_key]**: Aggregation metadata

---

## 6. GENERATE_MAPPING_REPORT

### Purpose
Create comprehensive Excel reports with multiple sheets and visualizations.

### Input Parameters
```python
class GenerateMappingReportParams(BaseModel):
    primary_data: str = Field(..., description="Main dataset key")
    
    additional_datasets: List[DatasetSheet] = Field(
        [],
        description="Other datasets to include"
    )
    
    statistics_keys: List[str] = Field(
        [],
        description="Statistics to include"
    )
    
    output_format: Literal['excel', 'csv', 'tsv'] = 'excel'
    output_path: str = Field(..., description="Output file path")
    
    summary_sheet: SummaryConfig = Field(
        default_factory=SummaryConfig,
        description="Summary sheet configuration"
    )
    
    metadata_to_include: List[str] = Field(
        default_factory=list,
        description="What metadata to add"
    )

class DatasetSheet(BaseModel):
    key: str
    sheet_name: str
    filter: Optional[str] = None  # e.g., "_in_both == True"

class SummaryConfig(BaseModel):
    enabled: bool = True
    include_plots: bool = True
    plot_types: List[PlotConfig] = []
```

### Processing Logic
1. **Create Excel writer**
2. **Write primary data** to first sheet
3. **Add additional sheets**:
   - Apply filters if specified
   - Format columns appropriately
4. **Create summary sheet**:
   - Total counts from metadata
   - Statistics from context
   - Plots if requested (as images or data for charts)
5. **Add metadata sheet**:
   - Processing timestamp
   - File paths
   - Parameters used
   - Row counts
6. **Format Excel**:
   - Auto-adjust column widths
   - Add filters to data rows
   - Format numbers appropriately
   - Color-code confidence scores

### Output
- **File written** to output_path
- **To context['output_files']**:
  ```python
  {
      'main_report': str,  # Path to file
      'timestamp': str,
      'sheets_created': List[str],
      'total_rows_written': int
  }
  ```

---

## Common Patterns Across All Actions

1. **Always preserve metadata columns** (starting with _)
2. **Never mutate input data** - always create new datasets
3. **Track provenance** in metadata
4. **Handle missing values gracefully**
5. **Provide detailed error messages**
6. **Log progress for long operations**
7. **Support dry-run mode** (validate without executing)