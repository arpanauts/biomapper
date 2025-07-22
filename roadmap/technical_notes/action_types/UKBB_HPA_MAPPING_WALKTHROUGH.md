# UKBB→HPA Protein Mapping: Detailed Walkthrough

## Scenario Overview
Map proteins from UK Biobank (UKBB) proteomics data to Human Protein Atlas (HPA) organ-specific proteins.

## Starting Data

### UKBB_Protein_Meta.tsv
```
Assay       UniProt         Panel
AARSD1      Q9BTE6          Oncology
ABHD14B     Q96IU4          Oncology
ACP1        P24666          Neurology
```

### hpa_osps.csv  
```
gene    uniprot     organ
CFH     P08603      liver
ALS2    Q96Q42      brain
PTPRM   P28827      brain
```

## Step-by-Step Data Flow

### Step 1: LOAD_DATASET_IDENTIFIERS (UKBB)

**Purpose**: Load UKBB protein data with proper parsing

**Params**:
```yaml
file_path: "/data/ukbb/UKBB_Protein_Meta.tsv"
column_mappings:
  - column_name: "UniProt"
    identifier_type: "uniprot_accession"
    is_primary: true
    is_composite: true  # Some entries like "Q14213_Q8NEV9"
    composite_separator: "_"
  - column_name: "Assay"
    identifier_type: "protein_name"
  - column_name: "Panel"
    identifier_type: "research_panel"
output_key: "ukbb_raw"
```

**Context After Execution**:
```python
context['datasets']['ukbb_raw'] = TableData(rows=[
    {'UniProt': 'Q9BTE6', 'Assay': 'AARSD1', 'Panel': 'Oncology'},
    {'UniProt': 'Q96IU4', 'Assay': 'ABHD14B', 'Panel': 'Oncology'},
    {'UniProt': 'P24666', 'Assay': 'ACP1', 'Panel': 'Neurology'},
    # ... composite entries expanded:
    {'UniProt': 'Q14213', 'Assay': 'EBI3', 'Panel': 'Inflammation'},
    {'UniProt': 'Q8NEV9', 'Assay': 'EBI3', 'Panel': 'Inflammation'},
])

context['metadata']['ukbb_raw'] = {
    'row_count': 2941,  # After expanding composites
    'original_row_count': 2923,
    'composite_ids_expanded': 18,
    'columns': ['UniProt', 'Assay', 'Panel'],
    'primary_column': 'UniProt'
}
```

### Step 2: LOAD_DATASET_IDENTIFIERS (HPA)

**Purpose**: Load HPA organ-specific proteins

**Params**:
```yaml
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
```

**Context After**:
```python
context['datasets']['hpa_raw'] = TableData(rows=[
    {'uniprot': 'P08603', 'gene': 'CFH', 'organ': 'liver'},
    {'uniprot': 'Q96Q42', 'gene': 'ALS2', 'organ': 'brain'},
    # ...
])

context['metadata']['hpa_raw'] = {
    'row_count': 1557,
    'columns': ['uniprot', 'gene', 'organ'],
    'organs': ['liver', 'brain', 'kidney', ...],  # Unique organs
    'primary_column': 'uniprot'
}
```

### Step 3: RESOLVE_CROSS_REFERENCES (Historical UniProt)

**Purpose**: Update obsolete UniProt IDs to current versions

**Params**:
```yaml
input_key: "ukbb_raw"
source_column: "UniProt"
target_database: "uniprot"
api_type: "historical"  # Special mode for historical resolution
result_column: "UniProt_Current"
confidence_column: "resolution_confidence"
output_key: "ukbb_resolved"
```

**API Calls (Internal)**:
```
Q9BTE6 → Q9BTE6 (no change, confidence: 1.0)
P35555 → P35555-2 (isoform update, confidence: 0.95)
Q8NEV9 → P0CG08 (merged entry, confidence: 0.90)
```

**Context After**:
```python
context['datasets']['ukbb_resolved'] = TableData(rows=[
    {
        'UniProt': 'Q9BTE6',
        'UniProt_Current': 'Q9BTE6',
        'resolution_confidence': 1.0,
        'Assay': 'AARSD1',
        'Panel': 'Oncology'
    },
    {
        'UniProt': 'Q8NEV9',
        'UniProt_Current': 'P0CG08',  # Historical ID resolved
        'resolution_confidence': 0.90,
        'Assay': 'EBI3',
        'Panel': 'Inflammation'
    },
    # ...
])

context['metadata']['ukbb_resolved'] = {
    'resolution_stats': {
        'total': 2941,
        'unchanged': 2850,
        'updated': 85,
        'failed': 6,
        'average_confidence': 0.98
    }
}
```

### Step 4: RESOLVE_CROSS_REFERENCES (HPA Historical)

**Similar process for HPA data**

### Step 5: MERGE_DATASETS

**Purpose**: Join UKBB and HPA on resolved UniProt IDs

**Params**:
```yaml
left_dataset: "ukbb_resolved"
right_dataset: "hpa_resolved"
join_conditions:
  - left_column: "UniProt_Current"
    right_column: "uniprot_current"
    match_type: "exact"
how: "inner"  # Only proteins in both datasets
output_key: "ukbb_hpa_merged"
```

**Context After**:
```python
context['datasets']['ukbb_hpa_merged'] = TableData(rows=[
    {
        # From UKBB
        'UniProt': 'P24666',
        'UniProt_Current': 'P24666',
        'Assay': 'ACP1',
        'Panel': 'Neurology',
        # From HPA
        'uniprot': 'P24666',
        'uniprot_current': 'P24666',
        'gene': 'ACP1',
        'organ': 'brain'
    },
    # ... ~485 matching proteins
])

context['metadata']['ukbb_hpa_merged'] = {
    'merge_stats': {
        'left_rows': 2941,
        'right_rows': 1557,
        'matched_rows': 485,
        'match_rate_left': 0.165,
        'match_rate_right': 0.311
    }
}
```

### Step 6: CALCULATE_SET_OVERLAP

**Purpose**: Detailed overlap analysis

**Params**:
```yaml
set_a_key: "ukbb_resolved"
set_b_key: "hpa_resolved"
compare_columns:
  - a_column: "UniProt_Current"
    b_column: "uniprot_current"
output_key: "overlap_analysis"
```

**Context After**:
```python
context['datasets']['overlap_analysis'] = TableData(rows=[
    {'identifier': 'P24666', 'in_ukbb': True, 'in_hpa': True},
    {'identifier': 'Q9BTE6', 'in_ukbb': True, 'in_hpa': False},
    {'identifier': 'P08603', 'in_ukbb': False, 'in_hpa': True},
])

context['statistics']['overlap_analysis'] = {
    'ukbb_only': 2456,
    'hpa_only': 1072,
    'both': 485,
    'jaccard_index': 0.137,
    'dice_coefficient': 0.241
}
```

### Step 7: AGGREGATE_STATISTICS

**Purpose**: Compute organ-specific and panel-specific statistics

**Params**:
```yaml
input_key: "ukbb_hpa_merged"
group_by_columns: ["organ", "Panel"]
aggregations:
  - column: "UniProt_Current"
    functions: ["count", "nunique"]
    result_prefix: "proteins_"
output_key: "mapping_statistics"
```

**Context After**:
```python
context['datasets']['mapping_statistics'] = TableData(rows=[
    {'organ': 'brain', 'Panel': 'Neurology', 'proteins_count': 45, 'proteins_nunique': 43},
    {'organ': 'brain', 'Panel': 'Inflammation', 'proteins_count': 12, 'proteins_nunique': 12},
    {'organ': 'liver', 'Panel': 'Cardiometabolic', 'proteins_count': 67, 'proteins_nunique': 65},
])

context['statistics']['mapping_summary'] = {
    'total_mappings': 485,
    'organs_covered': 15,
    'panels_represented': 8,
    'most_common_organ': 'liver',
    'most_common_panel': 'Cardiometabolic'
}
```

### Step 8: FILTER_ROWS (Optional - High Confidence Only)

**Purpose**: Keep only high-confidence mappings

**Params**:
```yaml
input_key: "ukbb_hpa_merged"
conditions:
  - column: "resolution_confidence"
    operator: "ge"
    value: 0.95
output_key: "high_confidence_mappings"
```

### Step 9: VALIDATE_DATA_QUALITY

**Purpose**: Ensure mapping quality

**Params**:
```yaml
input_key: "high_confidence_mappings"
validations:
  - type: "no_duplicates"
    columns: ["UniProt_Current", "organ"]
  - type: "pattern_match"
    columns: ["UniProt_Current"]
    pattern: "^[OPQ][0-9][A-Z0-9]{3}[0-9](?:-[0-9]+)?$"
output_key: "validated_mappings"
```

### Step 10: GENERATE_MAPPING_REPORT

**Purpose**: Create output files

**Params**:
```yaml
primary_data: "validated_mappings"
include_statistics: true
statistics_keys: ["overlap_analysis", "mapping_summary"]
output_format: "excel"
output_path: "results/ukbb_hpa_protein_mapping.xlsx"
sheets:
  - name: "Mappings"
    data_key: "validated_mappings"
  - name: "Statistics"
    data_key: "mapping_statistics"
  - name: "Summary"
    statistics: true
```

## Key Design Decisions

### 1. Composite ID Handling
- LOAD_DATASET_IDENTIFIERS handles composite IDs during loading
- Expands "Q14213_Q8NEV9" into two separate rows
- Maintains relationship via shared Assay name

### 2. Historical ID Resolution
- RESOLVE_CROSS_REFERENCES has special "historical" mode
- Calls UniProt API to resolve obsolete IDs
- Tracks confidence scores for traceability

### 3. Multi-Step Overlap Analysis
- First merge for direct matches
- Then calculate comprehensive overlap statistics
- Allows for different analysis approaches

### 4. Flexible Output Generation
- Can generate multiple output formats
- Includes both data and statistics
- Supports multi-sheet Excel files

## Missing Actions Identified

1. **EXPAND_TO_GENE_FAMILIES**: Convert proteins to gene families for broader matching
2. **RECIPROCAL_BEST_HIT**: Bidirectional mapping validation
3. **ANNOTATE_WITH_METADATA**: Add functional annotations from external sources
4. **PATHWAY_ENRICHMENT**: Analyze pathway representation in mapped sets

## Context Conventions

1. **Naming**: `{source}_{processing_stage}` (e.g., `ukbb_raw`, `ukbb_resolved`)
2. **Metadata**: Always store in `context['metadata'][dataset_key]`
3. **Statistics**: Global stats in `context['statistics'][analysis_key]`
4. **Validation**: Reports in `context['validation_reports'][dataset_key]`
5. **Column Preservation**: Keep all original columns through transformations