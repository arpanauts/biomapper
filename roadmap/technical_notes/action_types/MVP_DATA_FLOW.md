# MVP Action Types - Data Flow Architecture

## Overview

This document defines how data flows between the 10 MVP action types in Biomapper. It establishes conventions for context keys, data structures, and the migration from identifier-based to table-based operations.

## Core Data Flow Principles

### 1. Context as Shared State
Each action reads from and writes to a shared `context` dictionary that persists throughout strategy execution. Actions use specific context keys to exchange data.

### 2. Table-Based Operations
MVP actions work with tabular data (DataFrames) rather than simple identifier lists, enabling richer data processing while maintaining backward compatibility.

### 3. Standard Context Keys
```python
# Core keys maintained by the system
context = {
    'initial_identifiers': List[str],      # Original input (legacy)
    'current_identifiers': List[str],      # Current working set (legacy)
    'current_ontology_type': str,          # Current data type (legacy)
    'step_results': List[Dict],            # Accumulated results
    'all_provenance': List[Dict],          # Provenance chain
    
    # MVP table-based keys
    'datasets': Dict[str, TableData],      # Named datasets
    'metadata': Dict[str, Dict],           # Dataset metadata
    'statistics': Dict[str, Dict],         # Computed statistics
}
```

## MVP Action Data Flow

### 1. LOAD_DATASET_IDENTIFIERS
**Purpose**: Entry point - loads external data into the pipeline

**Input**:
- File path (from params)
- No context dependencies for initial load

**Output**:
- Stores loaded data in `context['datasets'][output_key]`
- Updates `context['metadata'][output_key]` with column info
- Optionally updates legacy `current_identifiers` if `is_primary=True`

**Example**:
```python
# After execution
context['datasets']['ukbb_data'] = TableData(rows=[...])
context['metadata']['ukbb_data'] = {
    'columns': ['uniprot_id', 'gene_names'],
    'row_count': 150,
    'primary_column': 'uniprot_id'
}
```

### 2. MERGE_DATASETS
**Purpose**: Joins two datasets from context

**Input**:
- Reads from `context['datasets'][left_dataset]`
- Reads from `context['datasets'][right_dataset]`

**Output**:
- Stores merged result in `context['datasets'][output_key]`
- Updates `context['metadata'][output_key]` with merge statistics

**Example**:
```python
# Input datasets
left = context['datasets']['ukbb_with_ensembl']
right = context['datasets']['hpa_data']

# After execution
context['datasets']['merged_data'] = merged_df
context['metadata']['merged_data'] = {
    'merge_type': 'outer',
    'left_rows': 150,
    'right_rows': 200,
    'result_rows': 220,
    'matched_rows': 130
}
```

### 3. RESOLVE_CROSS_REFERENCES
**Purpose**: Enriches dataset with external mappings

**Input**:
- Reads from `context['datasets'][input_key]`
- Uses specified source column for API lookups

**Output**:
- Stores enriched data in `context['datasets'][output_key]`
- Adds new columns for results and confidence
- Updates metadata with resolution statistics

**Example**:
```python
# Before: ukbb_data has columns [uniprot_id, gene_names]
# After: ukbb_with_ensembl has columns [uniprot_id, gene_names, ensembl_id, mapping_confidence]

context['metadata']['ukbb_with_ensembl'] = {
    'resolved_count': 145,
    'failed_count': 5,
    'confidence_threshold': 0.8
}
```

### 4. CALCULATE_SET_OVERLAP
**Purpose**: Analyzes overlap between datasets

**Input**:
- Reads from `context['datasets'][set_a_key]`
- Reads from `context['datasets'][set_b_key]`

**Output**:
- Stores overlap analysis in `context['datasets'][output_key]`
- Updates `context['statistics'][output_key]` with metrics

**Example**:
```python
# Output dataset contains intersection data
context['datasets']['overlap_analysis'] = TableData(
    rows=[
        {'identifier': 'P12345', 'in_set_a': True, 'in_set_b': True},
        {'identifier': 'Q98765', 'in_set_a': True, 'in_set_b': False},
    ]
)

context['statistics']['overlap_analysis'] = {
    'set_a_count': 150,
    'set_b_count': 200,
    'intersection_count': 130,
    'union_count': 220,
    'jaccard_index': 0.59
}
```

### 5. TRANSFORM_COLUMNS
**Purpose**: Modifies column data in-place

**Input**:
- Reads from `context['datasets'][input_key]`

**Output**:
- Stores transformed data in `context['datasets'][output_key]`
- Can be same key for in-place transformation

**Example**:
```python
# Rename and clean columns
operations = [
    {'type': 'rename', 'column': 'uniprot_id', 'new_name': 'uniprot_accession'},
    {'type': 'uppercase', 'column': 'gene_names'}
]
```

### 6. FILTER_ROWS
**Purpose**: Reduces dataset based on conditions

**Input**:
- Reads from `context['datasets'][input_key]`

**Output**:
- Stores filtered data in `context['datasets'][output_key]`
- Updates metadata with filter statistics

**Example**:
```python
context['metadata']['filtered_data'] = {
    'original_rows': 220,
    'filtered_rows': 180,
    'removed_rows': 40,
    'filter_conditions': ['confidence >= 0.8', 'gene_names not null']
}
```

### 7. DEDUPLICATE_RECORDS
**Purpose**: Removes duplicate entries

**Input**:
- Reads from `context['datasets'][input_key]`

**Output**:
- Stores deduplicated data in `context['datasets'][output_key]`
- Updates metadata with deduplication stats

**Example**:
```python
context['metadata']['unique_proteins'] = {
    'original_rows': 180,
    'unique_rows': 165,
    'duplicates_removed': 15,
    'dedup_columns': ['uniprot_accession']
}
```

### 8. VALIDATE_DATA_QUALITY
**Purpose**: Checks data integrity and quality

**Input**:
- Reads from `context['datasets'][input_key]`

**Output**:
- Stores validated data in `context['datasets'][output_key]`
- Adds validation report to context

**Example**:
```python
context['validation_reports'][output_key] = {
    'passed': True,
    'checks': [
        {'type': 'required_columns', 'status': 'passed'},
        {'type': 'pattern_match', 'column': 'uniprot_id', 'status': 'passed', 'invalid_count': 0}
    ],
    'warnings': ['5 rows have missing gene_names']
}
```

### 9. AGGREGATE_STATISTICS  
**Purpose**: Computes summary statistics

**Input**:
- Reads from `context['datasets'][input_key]`

**Output**:
- Stores aggregated data in `context['datasets'][output_key]`
- Updates statistics in context

**Example**:
```python
context['statistics']['summary_stats'] = {
    'total_proteins': 165,
    'proteins_per_organ': {'liver': 45, 'brain': 32, 'kidney': 28},
    'avg_confidence': 0.92,
    'coverage_by_dataset': {'ukbb': 0.87, 'hpa': 0.93}
}
```

### 10. GENERATE_MAPPING_REPORT
**Purpose**: Creates final output files

**Input**:
- Reads from `context['datasets'][primary_data]`
- Optionally reads from `context['statistics']` and `context['validation_reports']`

**Output**:
- Writes files to disk
- Stores output metadata in context

**Example**:
```python
context['output_files'] = {
    'data_file': 'results/protein_mapping_results.csv',
    'summary_file': 'results/protein_mapping_summary.json',
    'rows_written': 165,
    'timestamp': '2024-01-15T10:30:00Z'
}
```

## Backward Compatibility

### Supporting Legacy Actions
MVP actions maintain compatibility by:
1. Reading `current_identifiers` when no dataset is specified
2. Updating `current_identifiers` when `is_primary=True`
3. Converting between identifier lists and TableData

### Migration Path
```python
# Legacy action expects List[str]
if 'datasets' not in context:
    # Fall back to legacy behavior
    identifiers = context.get('current_identifiers', [])
    df = pd.DataFrame({'identifier': identifiers})
else:
    # Use table-based data
    df = context['datasets'][input_key].to_dataframe()
```

## Best Practices

### 1. Context Key Naming
- Use descriptive keys: `ukbb_proteins` not `data1`
- Include data type in key: `ukbb_uniprot_ids`, `hpa_gene_names`
- Use consistent suffixes: `_raw`, `_cleaned`, `_mapped`

### 2. Metadata Tracking
Always update metadata when:
- Loading data (columns, row count)
- Transforming data (operations applied)
- Filtering data (conditions, rows affected)
- Merging data (join statistics)

### 3. Error Handling
- Check if required context keys exist
- Validate data structure before processing
- Store error information in context for debugging

### 4. Memory Management
- Use `output_key` same as `input_key` for in-place operations
- Clean up intermediate datasets when no longer needed
- Consider streaming for very large datasets (post-MVP)

## Example Complete Flow

```yaml
# 1. Load UKBB data → creates context['datasets']['ukbb_data']
# 2. Load HPA data → creates context['datasets']['hpa_data']  
# 3. Resolve UKBB to Ensembl → creates context['datasets']['ukbb_with_ensembl']
# 4. Merge datasets → creates context['datasets']['merged_data']
# 5. Calculate overlap → creates context['datasets']['overlap_analysis']
# 6. Validate quality → creates context['datasets']['validated_results']
# 7. Generate report → writes files, updates context['output_files']
```

Each step builds on previous results by reading from and writing to the shared context, creating a clear data pipeline.