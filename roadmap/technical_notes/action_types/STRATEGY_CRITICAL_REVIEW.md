# Critical Review: UKBB-HPA Analysis Strategy

## Current Strategy Analysis

### What's Being Used (Existing Actions)
1. **LOAD_ENDPOINT_IDENTIFIERS** - Loading from predefined database endpoints
2. **UNIPROT_HISTORICAL_RESOLVER** - Specific action for UniProt history API
3. **LOCAL_ID_CONVERTER** - File-based ID mapping
4. **DATASET_OVERLAP_ANALYZER** - Set overlap analysis

### Critical Issues Identified

## 1. **Mixing Legacy and MVP Approaches**

**Problem**: The strategy uses legacy actions that work with identifier lists, not our new table-based MVP actions.

**Current Flow**:
```
LOAD_ENDPOINT_IDENTIFIERS → List[str] → UNIPROT_HISTORICAL_RESOLVER → List[str]
```

**MVP Flow Should Be**:
```
LOAD_DATASET_IDENTIFIERS → TableData → RESOLVE_CROSS_REFERENCES → TableData
```

## 2. **Lost Context and Metadata**

**Issue**: When loading just UniProt IDs, we lose important context:
- UKBB: Loses Assay names and Panel information
- HPA: Loses gene names and organ information

**Why It Matters**: 
- Can't generate organ-specific statistics
- Can't map back to original assay names
- Lose ability to filter by research panel

## 3. **Composite ID Handling**

**Current**: `expand_composites: true` in UNIPROT_HISTORICAL_RESOLVER
**Problem**: This is too late in the pipeline!

**Example Issue**:
```
Original: "Q14213_Q8NEV9" (composite)
After historical resolution: What if Q14213 maps to P12345 but Q8NEV9 is obsolete?
Lost connection between the two IDs that came from same assay
```

**Better Approach**: Handle during initial load to maintain relationships

## 4. **Workaround for HPA Data Loading**

**Current Hack**: Using LOCAL_ID_CONVERTER to load HPA data because "HPA's primary is gene"
```yaml
source_column: "gene"    # Use gene as source (HPA's primary)
target_column: "uniprot" # Extract UniProt values
```

**Problems**:
- Misusing an ID conversion action for data loading
- Only extracts UniProt column, loses all other data
- Can't handle empty UniProt values (though noted as complete)

## 5. **Limited Overlap Analysis**

**Current**: DATASET_OVERLAP_ANALYZER on identifier lists
**Missing**:
- Can't analyze overlap by organ
- Can't analyze overlap by research panel
- Can't track which specific proteins map between datasets
- Just counts, no detailed mapping table

## 6. **Incomplete Reporting**

**Current**: Optional gene name conversion at the end
**Missing**:
- No final report generation
- No CSV/Excel output
- No quality validation
- No confidence scores from historical resolution

## Proposed MVP Strategy Revision

```yaml
name: UKBB_HPA_PROTEIN_MAPPING_MVP
description: |
  Complete protein mapping between UKBB and HPA using MVP table-based actions.
  Preserves all metadata for rich analysis and reporting.

steps:
  # Load complete UKBB data with all columns
  - name: load_ukbb_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/ukbb/UKBB_Protein_Meta.tsv"
        column_mappings:
          - column_name: "UniProt"
            identifier_type: "uniprot_accession"
            is_primary: true
            is_composite: true
            composite_separator: "_"
          - column_name: "Assay"
            identifier_type: "protein_name"
          - column_name: "Panel"
            identifier_type: "research_panel"
        output_key: "ukbb_raw"

  # Load complete HPA data
  - name: load_hpa_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/hpa/hpa_osps.csv"
        column_mappings:
          - column_name: "uniprot"
            identifier_type: "uniprot_accession"
            is_primary: true
          - column_name: "gene"
            identifier_type: "gene_symbol"
          - column_name: "organ"
            identifier_type: "organ_name"
        output_key: "hpa_raw"

  # Resolve historical IDs for UKBB
  - name: resolve_ukbb_historical
    action:
      type: RESOLVE_CROSS_REFERENCES
      params:
        input_key: "ukbb_raw"
        source_column: "UniProt"
        target_database: "uniprot"
        api_type: "historical"
        result_column: "UniProt_Current"
        confidence_column: "resolution_confidence"
        output_key: "ukbb_resolved"

  # Resolve historical IDs for HPA
  - name: resolve_hpa_historical
    action:
      type: RESOLVE_CROSS_REFERENCES
      params:
        input_key: "hpa_raw"
        source_column: "uniprot"
        target_database: "uniprot"
        api_type: "historical"
        result_column: "uniprot_current"
        confidence_column: "resolution_confidence"
        output_key: "hpa_resolved"

  # Merge datasets on resolved IDs
  - name: merge_proteins
    action:
      type: MERGE_DATASETS
      params:
        left_dataset: "ukbb_resolved"
        right_dataset: "hpa_resolved"
        join_conditions:
          - left_column: "UniProt_Current"
            right_column: "uniprot_current"
        how: "outer"  # Keep all proteins for comprehensive analysis
        output_key: "merged_proteins"

  # Calculate detailed overlap statistics
  - name: analyze_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        set_a_key: "ukbb_resolved"
        set_b_key: "hpa_resolved"
        compare_columns:
          - a_column: "UniProt_Current"
            b_column: "uniprot_current"
        output_key: "overlap_analysis"

  # Aggregate by organ and panel
  - name: calculate_statistics
    action:
      type: AGGREGATE_STATISTICS
      params:
        input_key: "merged_proteins"
        group_by_columns: ["organ", "Panel"]
        aggregations:
          - column: "UniProt_Current"
            functions: ["count", "nunique"]
        output_key: "organ_panel_stats"

  # Validate data quality
  - name: validate_mappings
    action:
      type: VALIDATE_DATA_QUALITY
      params:
        input_key: "merged_proteins"
        validations:
          - type: "pattern_match"
            columns: ["UniProt_Current"]
            pattern: "^[OPQ][0-9][A-Z0-9]{3}[0-9](?:-[0-9]+)?$"
          - type: "required_columns"
            columns: ["UniProt_Current", "Assay"]
        output_key: "validated_mappings"

  # Generate comprehensive report
  - name: generate_report
    action:
      type: GENERATE_MAPPING_REPORT
      params:
        primary_data: "validated_mappings"
        include_statistics: true
        statistics_keys: ["overlap_analysis", "organ_panel_stats"]
        output_format: "excel"
        output_path: "results/ukbb_hpa_protein_mapping.xlsx"
        sheets:
          - name: "All_Mappings"
            data_key: "validated_mappings"
          - name: "Overlap_Only"
            data_key: "validated_mappings"
            filter: "in_both == True"
          - name: "Statistics"
            data_key: "organ_panel_stats"
          - name: "Summary"
            statistics: true
```

## Key Improvements

1. **Preserves All Data**: Complete tables flow through pipeline
2. **Handles Composites Early**: During initial load, maintaining relationships
3. **Comprehensive Analysis**: Organ-specific and panel-specific statistics
4. **Rich Output**: Multi-sheet Excel with different views
5. **Data Quality**: Validation ensures correctness
6. **Flexibility**: Can filter/transform at any step

## Design Decisions Needed

1. **Composite ID Expansion**: Should this be a flag in LOAD_DATASET_IDENTIFIERS or separate action?
2. **API Integration**: Should RESOLVE_CROSS_REFERENCES be generic or have specific subclasses?
3. **Missing Values**: How to handle rows with empty UniProt values?
4. **Performance**: Batch size optimization for API calls
5. **Caching**: Should API results be cached across runs?