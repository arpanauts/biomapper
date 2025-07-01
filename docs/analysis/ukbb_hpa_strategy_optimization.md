# UKBB-HPA Strategy Optimization Analysis

## Current Issue

The existing UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS strategy performs an unnecessary conversion:
- Converts UKBB Assay IDs → UniProt IDs
- But the UKBB data already has a UniProt column that could be used directly

## Key Findings

### 1. UKBB Configuration
- The UKBB_PROTEIN endpoint is configured with UniProt as the **primary identifier**
- File: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
- Columns: Assay, UniProt, Panel
- Current strategy uses Assay column unnecessarily

### 2. HPA Configuration  
- The HPA_OSP_PROTEIN endpoint has **gene as primary identifier**, not UniProt
- File: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`
- Columns: gene (primary), uniprot
- This creates a challenge for loading UniProt IDs directly

### 3. Strategy Issues
- Original strategy references "HPA_PROTEIN_DATA" endpoint which doesn't exist in config
- May be using outdated endpoint names or missing configuration

## Optimization Approaches

### Approach 1: Work with Existing Actions
Created `ukbb_hpa_analysis_strategy_optimized_v2.yaml`:
- Uses LOAD_ENDPOINT_IDENTIFIERS for UKBB (works perfectly)
- Uses LOCAL_ID_CONVERTER as a workaround to load HPA UniProt IDs
- Reduces steps from 4 to 3

### Approach 2: Create New Action Type
A new action `LOAD_COLUMN_VALUES` could be beneficial:
```yaml
- name: LOAD_HPA_UNIPROT_VALUES
  action:
    type: LOAD_COLUMN_VALUES
    params:
      endpoint_name: "HPA_OSP_PROTEIN"
      column_name: "uniprot"  # Load any column, not just primary
      output_context_key: "hpa_uniprot_ids"
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

Benefits:
- More flexible than LOAD_ENDPOINT_IDENTIFIERS
- Cleaner than using LOCAL_ID_CONVERTER workarounds
- Useful for many scenarios where non-primary columns are needed

## Recommendations

1. **Immediate**: Use the optimized strategy with existing actions
2. **Short-term**: Investigate why "HPA_PROTEIN_DATA" is referenced - missing config?
3. **Medium-term**: Consider implementing LOAD_COLUMN_VALUES action for cleaner data loading
4. **Long-term**: Review all strategies for similar optimization opportunities

## Performance Impact

The optimization eliminates:
- One file read operation (UKBB file)
- One mapping operation (Assay → UniProt)
- Memory usage for intermediate identifier storage

This should improve performance, especially with large datasets.