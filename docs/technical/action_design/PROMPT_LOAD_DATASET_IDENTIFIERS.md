# Development Prompt: LOAD_DATASET_IDENTIFIERS Action

## Overview
Please implement the LOAD_DATASET_IDENTIFIERS action for the Biomapper project following Test-Driven Development (TDD) practices.

**Reference the general guidelines in**: `/home/ubuntu/biomapper/MVP_DEVELOPER_REFERENCE.md`

## Action Purpose
Load biological dataset files (CSV/TSV) with intelligent handling of identifier columns, including optional prefix stripping and row filtering. This is the entry point for all mapping workflows.

## Specifications

### Parameters (Pydantic Model)
```python
class LoadDatasetIdentifiersParams(BaseModel):
    # File access
    file_path: str = Field(..., description="Path to CSV/TSV file")
    file_type: Optional[Literal["csv", "tsv", "auto"]] = Field("auto", description="File format")
    
    # Column identification  
    identifier_column: str = Field(..., description="Column containing primary identifiers")
    
    # Data cleaning (optional)
    strip_prefix: Optional[str] = Field(None, description="Prefix to remove (e.g., 'UniProtKB:')")
    
    # Filtering (optional)
    filter_column: Optional[str] = Field(None, description="Column to filter on")
    filter_values: Optional[List[str]] = Field(None, description="Values to match (can be regex)")
    filter_mode: Literal["include", "exclude"] = Field("include", description="Include or exclude matches")
    
    # Output
    output_key: str = Field(..., description="Key for storing in context['datasets']")
    
    # Options
    drop_empty_ids: bool = Field(True, description="Remove rows where identifier column is empty")
```

### Processing Logic
1. **Read file** based on file_type (auto-detect from extension if "auto")
2. **Validate** that identifier_column exists
3. **Apply filter** if filter_column and filter_values specified
   - Use regex matching
   - Include or exclude based on filter_mode
4. **Strip prefix** if specified
   - Preserve original in `{identifier_column}_original`
   - Clean data goes in the main identifier_column
5. **Drop empty identifiers** if drop_empty_ids is True
6. **Add metadata columns**:
   - `_source_file`: Full path to source file
   - `_row_number`: Original row number (1-based)
7. **Store in context**

### Critical Design Decision
**When stripping prefixes, ALWAYS preserve the original**:
```python
# If strip_prefix is specified:
df[f"{identifier_column}_original"] = df[identifier_column].copy()
df[identifier_column] = df[identifier_column].str.replace(strip_prefix, '', regex=False)
```

This ensures downstream actions can use the expected column name with clean data.

## Test Cases to Implement

### 1. Parameter Validation Tests
- Valid parameters accept
- Missing required parameters fail
- Invalid file_type rejected

### 2. Basic Loading Tests
```python
def test_load_simple_csv():
    """Test loading a basic CSV file."""
    # Use test data: /procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/isb_osp/hpa_osps.csv
    # Verify all rows loaded, columns preserved

def test_load_tsv_file():
    """Test loading a TSV file."""
    # Use test data: /procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/ukbb/UKBB_Protein_Meta.tsv
```

### 3. Prefix Stripping Tests
```python
def test_strip_prefix():
    """Test prefix removal with original preservation."""
    # Create mock data with "UniProtKB:P12345"
    # Verify creates "id" = "P12345" and "id_original" = "UniProtKB:P12345"

def test_strip_prefix_not_present():
    """Test stripping when prefix not in all values."""
    # Some with prefix, some without
```

### 4. Filtering Tests
```python
def test_filter_include_mode():
    """Test filtering rows to include matches."""
    # Filter KG2C to only UniProtKB entries
    
def test_filter_exclude_mode():
    """Test filtering rows to exclude matches."""
    
def test_filter_regex_pattern():
    """Test regex pattern matching."""
    # Use pattern like "^UniProtKB:" to match start of string
```

### 5. Empty ID Handling
```python
def test_drop_empty_ids():
    """Test removal of rows with empty identifier column."""
    
def test_keep_empty_ids():
    """Test keeping rows when drop_empty_ids=False."""
```

### 6. Edge Cases
```python
def test_missing_identifier_column():
    """Test error when specified column doesn't exist."""
    # Should raise ValueError with helpful message
    
def test_empty_file():
    """Test handling of empty CSV file."""
    
def test_file_not_found():
    """Test handling of missing file."""
```

### 7. Real Data Integration Tests
```python
def test_load_ukbb_real_data():
    """Test with actual UKBB data structure."""
    # Column: "UniProt" (capitalized)
    # File: TSV format
    
def test_load_kg2c_with_filtering():
    """Test KG2C loading with prefix strip and filter."""
    # Strip "UniProtKB:" prefix
    # Filter to only UniProtKB entries
    # Verify ~8-9 rows in test data
```

## Context Output Format

### Datasets Storage
```python
context['datasets'][output_key] = TableData(
    rows=[
        {
            'all': 'original columns',
            'identifier_column': 'cleaned value',
            'identifier_column_original': 'original value (if stripped)',
            '_source_file': '/full/path/to/file.csv',
            '_row_number': 1
        },
        # ... more rows
    ]
)
```

### Metadata Storage
```python
context['metadata'][output_key] = {
    'source_file': str,
    'row_count': int,
    'identifier_column': str,
    'columns': List[str],
    'filtered': bool,
    'prefix_stripped': bool,
    'filter_stats': {  # Only if filtered
        'original_count': int,
        'filtered_count': int,
        'filter_column': str,
        'filter_mode': str
    }
}
```

## Example Usage in YAML

### Simple Load
```yaml
params:
  file_path: "/data/ukbb/proteins.tsv"
  identifier_column: "UniProt"
  output_key: "ukbb_raw"
```

### Complex Load with Filtering
```yaml
params:
  file_path: "/data/kg2c/proteins.csv"
  identifier_column: "id"
  strip_prefix: "UniProtKB:"
  filter_column: "id"
  filter_values: ["^UniProtKB:"]
  filter_mode: "include"
  output_key: "kg2c_proteins"
```

## Implementation Notes

1. **File Type Detection**: If file_type="auto", use file extension
2. **Regex Handling**: filter_values are regex patterns - compile with re.compile()
3. **Memory Efficiency**: For large files, consider chunked reading (post-MVP)
4. **Error Messages**: Include sample data in errors (e.g., "Column 'uniprot' not found. Available: ['id', 'name']")
5. **Pandas String Methods**: Use .str accessor for string operations
6. **Copy explicitly**: When preserving original, use .copy() to avoid warnings

## Success Criteria

1. All tests pass with >80% coverage
2. Handles all test data files correctly
3. Clear error messages with context
4. Efficient pandas operations (vectorized, not loops)
5. Preserves all original columns
6. Metadata accurately reflects operations performed

## Questions to Consider

1. Should we validate the identifier column contains unique values? (No - duplicates are valid)
2. Should we handle compressed files? (No - post-MVP feature)
3. Should we auto-detect delimiter for CSV? (No - use pandas defaults)

Start with the failing tests, then implement the minimal code to make them pass!