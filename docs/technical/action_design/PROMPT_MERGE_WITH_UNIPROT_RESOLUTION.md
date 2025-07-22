# Development Prompt: MERGE_WITH_UNIPROT_RESOLUTION Action

## Overview
Please implement the MERGE_WITH_UNIPROT_RESOLUTION action for the Biomapper project following Test-Driven Development (TDD) practices.

**Reference the general guidelines in**: `/home/ubuntu/biomapper/MVP_DEVELOPER_REFERENCE.md`

## Action Purpose
Intelligently merge two protein datasets by:
1. First attempting direct matching (including composite ID logic)
2. Using UniProt API only for unresolved identifiers
3. Preserving ALL rows (matched and unmatched)
4. Tracking detailed match metadata for reporting

This action replaces the need for separate MERGE and RESOLVE actions.

## Specifications

### Parameters (Pydantic Model)
```python
class MergeWithUniprotResolutionParams(BaseModel):
    # Input datasets
    source_dataset_key: str = Field(..., description="First dataset from context")
    target_dataset_key: str = Field(..., description="Second dataset from context")
    
    # Column specifications
    source_id_column: str = Field(..., description="ID column in source dataset")
    target_id_column: str = Field(..., description="ID column in target dataset")
    
    # Composite handling
    composite_separator: str = Field("_", description="Separator for composite IDs")
    
    # API configuration
    use_api: bool = Field(True, description="Whether to use API for unresolved")
    api_batch_size: int = Field(100, description="IDs per API call")
    api_cache_results: bool = Field(True, description="Cache API responses")
    
    # Output
    output_key: str = Field(..., description="Key for merged dataset")
    
    # Options
    confidence_threshold: float = Field(0.0, description="Minimum confidence to keep")
```

### Processing Logic (3 Phases)

#### Phase 1: Direct Matching with Composite Logic
```python
def find_matches(source_id, target_id, separator):
    """Find all matches between IDs, including composite logic.
    Returns list of (match_value, match_type) tuples."""
    matches = []
    
    # Exact match
    if source_id == target_id:
        matches.append((source_id, 'direct'))
        return matches
    
    # Source composite, target single
    if separator in source_id:
        parts = source_id.split(separator)
        if target_id in parts:
            matches.append((target_id, 'composite'))
    
    # Target composite, source single  
    elif separator in target_id:
        parts = target_id.split(separator)
        if source_id in parts:
            matches.append((source_id, 'composite'))
    
    # Both composite - find all overlapping parts
    elif separator in source_id and separator in target_id:
        parts1 = set(source_id.split(separator))
        parts2 = set(target_id.split(separator))
        for common in parts1 & parts2:
            matches.append((common, 'composite'))
    
    return matches

# For each source_id × target_id combination:
matches = find_matches(source_id, target_id, composite_separator)
for match_value, match_type in matches:
    # Create match record with metadata
```

#### Phase 2: API Resolution for Unmatched
```python
# 1. Identify unresolved IDs
matched_source_ids = {m['source_id'] for m in direct_matches}
matched_target_ids = {m['target_id'] for m in direct_matches}

unresolved_source = source_ids - matched_source_ids
unresolved_target = target_ids - matched_target_ids

# 2. Call UniProt API in batches (reuse existing client logic)
# 3. Try matching with resolved IDs
# 4. Add matches with match_type='historical'
```

#### Phase 3: Create Full Merged Dataset
```python
# 1. Build comprehensive match records
# 2. Outer merge to preserve ALL rows
# 3. Add match metadata columns
# 4. Handle column naming conflicts with suffixes
```

### Critical Design Decisions

#### 1. Composite ID Handling Creates Multiple Rows
```python
# If UKBB has "Q14213_Q8NEV9" and HPA has both "Q14213" and "Q8NEV9"
# Create TWO output rows:
# Row 1: Q14213_Q8NEV9 → Q14213 (match_type='composite', match_value='Q14213')
# Row 2: Q14213_Q8NEV9 → Q8NEV9 (match_type='composite', match_value='Q8NEV9')
```

#### 2. Match Metadata Columns (Critical!)
Every row in the output must have:
- `match_value`: The actual ID that created the match
- `match_type`: 'direct', 'composite', 'historical', or None
- `match_confidence`: Confidence score (1.0 for direct/composite, varies for API)
- `match_status`: 'matched', 'source_only', or 'target_only'
- `api_resolved`: Boolean indicating if API was used

#### 3. Column Naming with Suffixes
```python
# Handle conflicts with _source and _target suffixes
# ID columns preserved without suffix
# All other columns get suffixes if conflicts exist
```

## Test Cases to Implement

### 1. Parameter Validation Tests
```python
def test_params_validation():
    """Test parameter validation."""
    # Valid parameters
    params = MergeWithUniprotResolutionParams(
        source_dataset_key="ukbb", 
        target_dataset_key="hpa",
        source_id_column="UniProt",
        target_id_column="uniprot",
        output_key="merged"
    )
    
    # Missing required parameters
    with pytest.raises(ValidationError):
        MergeWithUniprotResolutionParams()
```

### 2. Direct Matching Tests
```python
def test_direct_exact_match():
    """Test exact ID matching."""
    # P12345 in both datasets → direct match
    
def test_composite_to_single_match():
    """Test composite ID matching single ID."""
    # Q14213_Q8NEV9 in source, Q14213 in target → composite match

def test_composite_to_composite_match():
    """Test composite ID matching composite ID."""
    # Q14213_Q8NEV9 in source, Q14213_P12345 in target → composite match on Q14213
```

### 3. API Resolution Tests
```python
def test_api_resolution():
    """Test API resolution for unmatched IDs."""
    # Mock API to return historical resolution
    # Verify only unmatched IDs are sent to API
    
def test_api_disabled():
    """Test with use_api=False."""
    # Should only do direct matching
```

### 4. Output Structure Tests
```python
def test_match_metadata_columns():
    """Test that all match metadata columns are present."""
    # Verify match_value, match_type, match_confidence, match_status, api_resolved
    
def test_all_rows_preserved():
    """Test that no rows are lost."""
    # Total output rows should account for all source + target + composite expansions
    
def test_column_suffixes():
    """Test column conflict resolution."""
    # Conflicting columns should have _source and _target suffixes
```

### 5. Real Data Integration Tests
```python
def test_ukbb_hpa_merge():
    """Test with actual UKBB and HPA test data."""
    # Use: /procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/ukbb/UKBB_Protein_Meta.tsv
    # Use: /procedure/data/local_data/MAPPING_ONTOLOGIES/test_data/isb_osp/hpa_osps.csv
    
def test_composite_expansion_real_data():
    """Test composite handling with real data."""
    # Look for composite IDs in test data
```

### 6. Edge Cases
```python
def test_empty_datasets():
    """Test with empty input datasets."""
    
def test_missing_id_columns():
    """Test error when ID columns don't exist."""
    
def test_all_null_ids():
    """Test with all null ID values."""
```

## Expected Output Structure

### Match Metadata Columns
```python
# Required columns in output:
'match_value': str | None      # The actual ID that matched
'match_type': str | None       # 'direct', 'composite', 'historical', None
'match_confidence': float      # 1.0 for direct/composite, varies for API
'match_status': str           # 'matched', 'source_only', 'target_only'
'api_resolved': bool          # True if API was used for this match
```

### Data Columns
```python
# All original columns preserved with suffixes for conflicts
# ID columns kept without suffix
# Example: 'UniProt', 'Assay_source', 'Panel_source', 'gene_target', 'organ_target'
```

## Context Output

### Datasets Storage
```python
context['datasets'][output_key] = TableData(
    rows=[
        {
            'UniProt': 'Q14213',  # ID columns no suffix
            'match_value': 'Q14213',
            'match_type': 'composite',
            'match_confidence': 1.0,
            'match_status': 'matched',
            'api_resolved': False,
            'Assay_source': 'EBI3',
            'Panel_source': 'Inflammation',
            'gene_target': 'IL27',
            'organ_target': 'lymph_node'
        },
        # ... more rows
    ]
)
```

### Metadata Storage
```python
context['metadata'][output_key] = {
    'total_source_rows': int,
    'total_target_rows': int,
    'total_output_rows': int,
    'matches_by_type': {
        'direct': int,
        'composite': int,
        'historical': int,
    },
    'unmatched_source': int,
    'unmatched_target': int,
    'api_calls_made': int,
    'unique_source_ids': int,
    'unique_target_ids': int,
    'processing_time': float
}
```

## Implementation Notes

### 1. API Integration
- Reuse existing UniProt client logic from `/home/ubuntu/biomapper/biomapper/core/strategy_actions/uniprot_historical_resolver.py`
- Adapt to work with TableData instead of identifier lists
- Implement proper error handling and retries

### 2. Performance Considerations
- Use vectorized pandas operations where possible
- Implement progress logging for large datasets
- Cache API results in context if enabled

### 3. Memory Management
- Process in chunks for very large datasets
- Clean up intermediate DataFrames
- Use generators for large file processing

### 4. Error Handling
- Validate datasets exist in context
- Check ID columns exist in datasets
- Handle API failures gracefully
- Provide detailed error messages with context

## Example Usage in YAML

```yaml
- name: merge_ukbb_hpa
  action:
    type: MERGE_WITH_UNIPROT_RESOLUTION
    params:
      source_dataset_key: "ukbb_raw"
      target_dataset_key: "hpa_raw"
      source_id_column: "UniProt"
      target_id_column: "uniprot"
      composite_separator: "_"
      use_api: true
      api_batch_size: 100
      output_key: "ukbb_hpa_merged"
      confidence_threshold: 0.8
```

## Success Criteria

1. **All tests pass** with >80% coverage
2. **Handles composite IDs correctly** - creates multiple rows as needed
3. **Preserves all data** - no rows lost
4. **Efficient API usage** - only calls API for unresolved IDs
5. **Rich metadata** - detailed match tracking for reporting
6. **Memory efficient** - works with large datasets
7. **Clear error messages** - helpful debugging information

## Questions to Consider

1. Should we validate that composite separator doesn't appear in single IDs?
2. How to handle very large datasets (>100K rows)?
3. Should we support custom API endpoints beyond UniProt?
4. How to handle circular composite references?

Start with the failing tests, then implement the three-phase processing logic!