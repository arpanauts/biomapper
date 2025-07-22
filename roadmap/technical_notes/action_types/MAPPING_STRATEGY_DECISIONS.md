# Biomapper Mapping Strategy - Key Decisions

## Current State Analysis

### Existing System (List-Based)
- **Data Flow**: `List[str]` → Action → `List[str]`
- **Metadata**: Lost between actions, only preserved in return values
- **Example**: UKBB protein "AARSD1" with UniProt "Q9BTE6" in panel "Oncology"
  - After loading: Only "Q9BTE6" is passed forward
  - Lost: Assay name "AARSD1", Panel "Oncology"

### Proposed MVP System (Table-Based)
- **Data Flow**: `TableData` → Action → `TableData`
- **Metadata**: Preserved and enriched through pipeline
- **Example**: Same UKBB protein
  - After loading: Full row `{Assay: "AARSD1", UniProt: "Q9BTE6", Panel: "Oncology"}`
  - After resolution: `{Assay: "AARSD1", UniProt: "Q9BTE6", UniProt_Current: "Q9BTE6", Panel: "Oncology", confidence: 1.0}`

## Critical Decision Points

### 1. **Adapter Pattern vs New Actions**

**Option A: Adapter Pattern**
```python
# Wrap existing actions with table-aware adapters
class TableAwareUniProtResolver:
    def execute(self, table_data: TableData) -> TableData:
        # Extract identifier column
        ids = table_data.get_column('UniProt')
        
        # Call existing UNIPROT_HISTORICAL_RESOLVER
        resolved_ids = existing_resolver.execute(ids)
        
        # Merge results back into table
        table_data.add_column('UniProt_Current', resolved_ids)
        return table_data
```

**Option B: New MVP Actions**
- Create parallel table-based actions
- Maintain both systems during transition
- Eventually deprecate list-based actions

**Recommendation**: Option A for existing specialized actions (UniProt resolver), Option B for generic operations (merge, filter, transform)

### 2. **Composite ID Handling**

**Current Issue**: Composite IDs like "Q14213_Q8NEV9" represent one assay with two proteins

**Option A: Expand During Load**
```python
# Input row: {Assay: "EBI3", UniProt: "Q14213_Q8NEV9", Panel: "Inflammation"}
# Output rows:
# {Assay: "EBI3", UniProt: "Q14213", Panel: "Inflammation", composite_source: "Q14213_Q8NEV9"}
# {Assay: "EBI3", UniProt: "Q8NEV9", Panel: "Inflammation", composite_source: "Q14213_Q8NEV9"}
```

**Option B: Separate Expansion Action**
- Keeps loading simple
- Explicit step for composite handling
- More visible in strategy

**Recommendation**: Option A - Handle during load to maintain assay relationships

### 3. **Context Structure**

**Current**: Flat dictionary with identifier lists
```python
context = {
    'ukbb_ids': ['Q9BTE6', 'Q96IU4', ...],
    'hpa_ids': ['P08603', 'Q96Q42', ...]
}
```

**Proposed MVP**: Structured with datasets namespace
```python
context = {
    'datasets': {
        'ukbb_raw': TableData(...),
        'ukbb_resolved': TableData(...),
        'hpa_raw': TableData(...)
    },
    'metadata': {
        'ukbb_raw': {'row_count': 2941, 'columns': [...]}
    },
    'statistics': {
        'overlap_analysis': {'jaccard': 0.137, ...}
    }
}
```

**Migration Path**: Support both patterns
```python
# In action execution
if 'datasets' in context:
    # New table-based flow
    data = context['datasets'][input_key]
else:
    # Legacy list-based flow
    data = context.get(input_key, [])
```

### 4. **API Integration Pattern**

**For RESOLVE_CROSS_REFERENCES**:

**Option A: Generic with API Types**
```yaml
params:
  target_database: "uniprot"
  api_type: "historical"  # or "mapping", "annotation"
```

**Option B: Specific Actions**
- RESOLVE_UNIPROT_HISTORICAL
- RESOLVE_ENSEMBL_MAPPING
- RESOLVE_CHEBI_STRUCTURE

**Recommendation**: Option A - One flexible action with configuration

### 5. **Missing Critical Actions**

Based on the UKBB→HPA walkthrough, we need:

1. **LOAD_DATASET_IDENTIFIERS** ✓ (in MVP plan)
2. **MERGE_DATASETS** ✓ (in MVP plan)
3. **RESOLVE_CROSS_REFERENCES** ✓ (replaces specific resolvers)
4. **CALCULATE_SET_OVERLAP** ✓ (in MVP plan)
5. **FILTER_ROWS** ✓ (in MVP plan)
6. **AGGREGATE_STATISTICS** ✓ (in MVP plan)
7. **GENERATE_MAPPING_REPORT** ✓ (in MVP plan)

**Additional Needs**:
- **ANNOTATE_WITH_CONFIDENCE**: Add quality scores to mappings
- **EXPORT_FOR_DOWNSTREAM**: Format for specific tools (Cytoscape, R, etc.)

## Implementation Strategy

### Phase 1: Hybrid Approach
1. Implement table-based LOAD_DATASET_IDENTIFIERS
2. Create adapters for existing specialized actions (UNIPROT_HISTORICAL_RESOLVER)
3. Implement new table-based generic actions (MERGE, FILTER, AGGREGATE)

### Phase 2: Full Migration
1. Replace list-based actions with table-based versions
2. Update all strategies to use new patterns
3. Deprecate but maintain legacy actions

### Phase 3: Advanced Features
1. Streaming support for large datasets
2. Parallel processing for API calls
3. Caching layer for expensive operations

## Example Hybrid Strategy

```yaml
name: UKBB_HPA_HYBRID_STRATEGY
steps:
  # New table-based loader
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "..."
        output_key: "ukbb_table"
  
  # Adapter for existing resolver
  - name: resolve_historical
    action:
      type: TABLE_UNIPROT_RESOLVER  # Adapter wrapping existing action
      params:
        input_key: "ukbb_table"
        id_column: "UniProt"
        output_key: "ukbb_resolved"
  
  # New table-based merge
  - name: merge_data
    action:
      type: MERGE_DATASETS
      params:
        left_dataset: "ukbb_resolved"
        right_dataset: "hpa_resolved"
        output_key: "merged"
```

## Recommendations for Parallel Development

1. **Start with Core Table Actions**: LOAD, MERGE, FILTER, AGGREGATE
2. **Create Adapter Pattern**: For UniProt resolver and other specialized actions
3. **Define Clear Interfaces**: TableData in/out for all new actions
4. **Maintain Backward Compatibility**: Support both list and table flows
5. **Document Context Conventions**: Clear namespace structure

This hybrid approach allows us to leverage existing specialized actions while building toward a richer, table-based future.