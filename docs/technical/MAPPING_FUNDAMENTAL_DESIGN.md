# Fundamental Design: Mapping as Outer Merge

## Core Insight
Biological mapping is fundamentally an outer merge operation where:
1. We join on identifier columns (after cleaning/resolving)
2. We preserve ALL columns from both datasets
3. We handle naming conflicts with source prefixes
4. We track which rows came from which source

## Why We Need 7 Actions Instead of Just MERGE

While the core operation is a merge, the 7 actions handle the necessary pre/post-processing:

### 1. LOAD_DATASET_IDENTIFIERS
**Why not just pd.read_csv?**
- **Composite ID expansion**: "Q14213_Q8NEV9" → two rows
- **Column name mapping**: Handle inconsistent naming (UniProt vs uniprot)
- **ID prefix stripping**: "UniProtKB:P12345" → "P12345"
- **Type filtering**: Only UniProtKB entries from mixed KG2C
- **Metadata tracking**: Source file, line numbers, expansion tracking

**Core question**: Should composite expansion be a separate action?

### 2. RESOLVE_CROSS_REFERENCES
**Why needed?**
- **Historical changes**: Q8NEV9 → P0CG08 (would miss matches without this)
- **Obsolete handling**: Some IDs no longer exist
- **Confidence scoring**: Not all resolutions are equal
- **API batching**: Efficiency and rate limiting

**Core question**: Is this biomapper's key differentiator?

### 3. MERGE_DATASETS
**The fundamental operation**
```python
# What it really does:
merged = pd.merge(
    ukbb_df, 
    hpa_df,
    left_on='UniProt_Current',
    right_on='uniprot_current',
    how='outer',
    suffixes=('_ukbb', '_hpa')
)
```

**Key decisions**:
- Always outer join (preserve all data)
- Smart suffix handling (source-based, not generic _x, _y)
- Join column handling (keep one copy)
- Add tracking columns (_in_both, _merge_source)

### 4. CALCULATE_SET_OVERLAP
**Why separate from merge?**
- Provides set-theoretic view (Venn diagram data)
- Calculates statistics not available from merge alone
- Can compare without full merge (memory efficient)
- Useful for quick feasibility checks

**Core question**: Could this be part of MERGE_DATASETS?

### 5. AGGREGATE_STATISTICS
**Post-merge analysis**
- Group by metadata categories (Panel × organ)
- Count/summarize mappings
- Enable biological insights

**Not strictly needed for mapping, but essential for understanding**

### 6. FILTER_ROWS
**Quality control**
- Remove low-confidence mappings
- Focus on specific subsets
- Handle thresholds

**Core question**: Generic utility action or mapping-specific?

### 7. GENERATE_MAPPING_REPORT
**Output and visualization**
- Multi-sheet Excel with different views
- Include statistics and plots
- Make results accessible to biologists

## Simplified View: 3 Core Operations

Perhaps we really only need:

### 1. PREPARE_FOR_MAPPING
Combines LOAD + RESOLVE operations:
- Load data with column mapping
- Expand composites
- Clean IDs (strip prefixes)
- Resolve historical IDs
- Output: Clean, resolved TableData

### 2. MAP_DATASETS
The core operation:
- Outer merge on specified columns
- Smart column naming (source prefixes)
- Calculate overlap statistics
- Output: Merged data + statistics

### 3. REPORT_MAPPING
Output generation:
- Filter and aggregate as needed
- Generate multi-sheet reports
- Create visualizations

## Design Questions

1. **Granularity**: Many small actions vs fewer comprehensive ones?
   - Pro small: Composable, testable, clear purpose
   - Pro large: Fewer steps, less context passing

2. **Column Naming Strategy**:
   ```python
   # Option A: Source-based prefixes
   UniProt_ukbb, UniProt_hpa, Panel_ukbb, organ_hpa
   
   # Option B: Keep original, track source separately
   UniProt, Panel, organ, _source_dataset
   
   # Option C: Nested structure
   ukbb.UniProt, ukbb.Panel, hpa.uniprot, hpa.organ
   ```

3. **Composite Handling**:
   - In LOAD (current design) - maintains relationship to source
   - Separate EXPAND action - more flexible
   - In MERGE - too late, lose context

4. **Statistics Integration**:
   - Calculate during merge (efficient)
   - Separate action (current) - more flexible
   - Both options available?

## Proposed Refinement

Keep 7 actions but clarify their roles:

1. **LOAD_DATASET_IDENTIFIERS**: Data ingestion with smart parsing
2. **RESOLVE_CROSS_REFERENCES**: External ID resolution (biomapper's value-add)
3. **MERGE_DATASETS**: The core mapping operation
4. **CALCULATE_SET_OVERLAP**: Optional set analysis
5. **AGGREGATE_STATISTICS**: Optional aggregation
6. **FILTER_ROWS**: Optional filtering
7. **GENERATE_MAPPING_REPORT**: Output generation

Actions 1-3 are essential for mapping
Actions 4-7 are utilities that enhance the analysis

## The Fundamental Mapping Pattern

```python
# Pseudocode for any biological mapping
def map_biological_datasets(source_file, target_file, id_columns):
    # 1. Load and prepare
    source = load_with_expansion(source_file, id_columns['source'])
    target = load_with_expansion(target_file, id_columns['target'])
    
    # 2. Resolve historical IDs (the key differentiator)
    source_resolved = resolve_historical(source)
    target_resolved = resolve_historical(target)
    
    # 3. Merge (the fundamental operation)
    mapped = outer_merge(
        source_resolved, 
        target_resolved,
        on=id_columns,
        track_source=True
    )
    
    # 4. Analyze and report (optional but valuable)
    stats = calculate_statistics(mapped)
    report = generate_report(mapped, stats)
    
    return mapped, report
```

This is what all 9 protein mappings do!