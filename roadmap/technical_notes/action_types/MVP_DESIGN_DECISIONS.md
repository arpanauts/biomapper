# MVP Action Types - Critical Design Decisions

## 1. Composite ID Handling

### The Problem
Some identifiers contain multiple values: `"Q14213_Q8NEV9"` represents one assay measuring two proteins.

### Decision: Handle During Load
**Rationale**: Maintains relationship between composite parts and source data

**Implementation in LOAD_DATASET_IDENTIFIERS**:
```python
# Input CSV row:
Assay,UniProt,Panel
EBI3,Q14213_Q8NEV9,Inflammation

# Output TableData rows:
[
    {
        'Assay': 'EBI3',
        'UniProt': 'Q14213',
        'Panel': 'Inflammation',
        '_composite_source': 'Q14213_Q8NEV9',
        '_composite_group': 'EBI3_Q14213_Q8NEV9'  # Unique group ID
    },
    {
        'Assay': 'EBI3', 
        'UniProt': 'Q8NEV9',
        'Panel': 'Inflammation',
        '_composite_source': 'Q14213_Q8NEV9',
        '_composite_group': 'EBI3_Q14213_Q8NEV9'  # Same group ID
    }
]
```

**Conventions**:
- Prefix metadata columns with `_` to distinguish from data columns
- `_composite_source`: Original composite value
- `_composite_group`: Unique ID to track related rows
- All original columns preserved for both expanded rows

## 2. Context Data Structure

### Standard Context Layout
```python
context = {
    # Primary data storage
    'datasets': {
        'dataset_name': TableData(rows=[...])
    },
    
    # Dataset metadata
    'metadata': {
        'dataset_name': {
            'row_count': int,
            'columns': List[str],
            'primary_column': str,
            'creation_timestamp': str,
            'source_file': str
        }
    },
    
    # Analysis results
    'statistics': {
        'analysis_name': {
            # Analysis-specific stats
        }
    },
    
    # Validation reports
    'validation_reports': {
        'dataset_name': {
            'passed': bool,
            'checks': List[Dict],
            'warnings': List[str]
        }
    },
    
    # API cache (for RESOLVE_CROSS_REFERENCES)
    'api_cache': {
        'cache_key': {
            'result': Any,
            'timestamp': str,
            'ttl': int
        }
    }
}
```

## 3. Column Naming Conventions

### Base Rules
1. **Preserve original column names** when loading data
2. **Add new columns** with descriptive names, not replacing originals
3. **Use suffixes** for clarity: `_current`, `_resolved`, `_confidence`
4. **Prefix metadata** with underscore: `_composite_source`, `_merge_key`

### Merge Conflict Resolution
When MERGE_DATASETS encounters duplicate columns:
```python
# Left dataset has: gene, uniprot, tissue
# Right dataset has: gene, uniprot, organ

# Result columns:
gene_left, gene_right, uniprot_left, uniprot_right, tissue, organ

# Special handling for join columns (they're equal by definition):
# If joining on 'uniprot', keep single 'uniprot' column
```

## 4. API Integration Pattern

### For RESOLVE_CROSS_REFERENCES

**Supported API Types**:
```yaml
# Configuration per API type
api_configs:
  uniprot_historical:
    base_url: "https://rest.uniprot.org"
    endpoint: "/uniprotkb/search"
    batch_param: "query"
    batch_format: "accession:({ids})"
    response_parser: "uniprot_historical_parser"
    rate_limit: 10  # requests per second
    
  ensembl_mapping:
    base_url: "https://rest.ensembl.org"
    endpoint: "/xrefs/id/{id}"
    batch_capable: false  # One ID at a time
    response_parser: "ensembl_parser"
    rate_limit: 15
```

**Action Parameters**:
```yaml
params:
  input_key: "dataset_name"
  source_column: "UniProt"
  target_database: "uniprot"  # Selects api_config
  api_type: "historical"       # Selects specific endpoint behavior
  result_column: "UniProt_Current"
  confidence_column: "resolution_confidence"
  include_failed: true         # Keep rows that couldn't be resolved
  cache_results: true          # Use context['api_cache']
  output_key: "dataset_resolved"
```

## 5. Error Handling Patterns

### Principles
1. **Never lose data** - Failed operations keep original rows
2. **Track failures** - Add error columns when needed
3. **Graceful degradation** - Continue processing valid data
4. **Clear error messages** - Include row numbers and values

### Standard Error Columns
```python
# For API failures in RESOLVE_CROSS_REFERENCES
{
    'UniProt': 'Q99999',
    'UniProt_Current': None,  # Or original value
    'resolution_confidence': 0.0,
    '_error': 'API timeout after 3 retries',
    '_error_timestamp': '2024-01-15T10:30:00Z'
}

# For validation failures in VALIDATE_DATA_QUALITY  
{
    'UniProt': 'INVALID',
    '_validation_errors': ['Failed pattern match: ^[OPQ][0-9]...'],
    '_validation_status': 'failed'
}
```

## 6. TableData Operations

### Core Methods Every Action Needs
```python
class TableData(BaseModel):
    rows: List[Dict[str, Any]]
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas for operations"""
        
    def get_column(self, column: str) -> List[Any]:
        """Extract single column values"""
        
    def add_column(self, column: str, values: List[Any]):
        """Add new column to all rows"""
        
    def filter_rows(self, condition: Callable) -> 'TableData':
        """Filter rows based on condition"""
        
    def get_unique_values(self, column: str) -> Set[Any]:
        """Get unique values from column"""
```

## 7. Progress and Logging

### Standard Logging Pattern
```python
# Each action logs:
logger.info(f"Starting {action_name} with {len(input_data)} rows")
logger.debug(f"Parameters: {params}")

# During processing:
logger.info(f"Processed {current}/{total} rows")

# Completion:
logger.info(f"Completed {action_name}: {output_rows} rows output")
logger.debug(f"Statistics: {stats}")
```

## 8. Testing Patterns

### Each Action Needs Tests For:
1. **Happy path** - Normal operation
2. **Empty input** - Empty TableData
3. **Missing columns** - Required columns not present
4. **Invalid data** - Malformed values
5. **API failures** - For external calls
6. **Large datasets** - Performance with 10k+ rows

### Standard Test Structure
```python
def test_action_happy_path():
    # Arrange
    input_data = TableData(rows=[
        {'id': 'P12345', 'name': 'Protein A'},
        {'id': 'Q67890', 'name': 'Protein B'}
    ])
    context = {'datasets': {'input': input_data}}
    params = ActionParams(input_key='input', output_key='output')
    
    # Act
    result = action.execute_typed(params, context, None, None)
    
    # Assert
    assert context['datasets']['output'].row_count == 2
    assert 'new_column' in context['datasets']['output'].columns
```

## 9. Performance Considerations

### Guidelines
1. **Batch API calls** - Default 100 items per request
2. **Use generators** for large file reading
3. **Chunk processing** for memory efficiency
4. **Progress indicators** for long operations
5. **Implement caching** for expensive operations

### Memory Limits
```python
# For LOAD_DATASET_IDENTIFIERS
if file_size > 1_000_000_000:  # 1GB
    logger.warning("Large file detected, using chunked reading")
    # Process in chunks of 10,000 rows
```

## 10. Common Pitfalls to Avoid

1. **Don't mutate input data** - Always create new TableData
2. **Don't assume column exists** - Always check first
3. **Don't silently drop data** - Log and track removals
4. **Don't hardcode separators** - Make configurable
5. **Don't ignore empty values** - Handle None/empty strings

## Summary for Parallel Developers

When implementing your action:
1. Read from `context['datasets'][input_key]`
2. Create new TableData, don't modify input
3. Write to `context['datasets'][output_key]`
4. Update `context['metadata'][output_key]`
5. Handle errors gracefully with error columns
6. Use `_` prefix for metadata columns
7. Log progress for long operations
8. Write comprehensive tests
9. Document all parameters in Pydantic model
10. Follow the patterns in this document