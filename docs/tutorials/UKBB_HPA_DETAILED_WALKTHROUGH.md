# UKBB → HPA Protein Mapping: Detailed Implementation Guide

## Overview
This document walks through each step of the UKBB→HPA protein mapping in detail, showing exact data transformations at each stage.

## Initial Data

### UKBB Protein Data (`UKBB_Protein_Meta.tsv`)
```
Assay	UniProt	Panel
AARSD1	Q9BTE6	Oncology
ABHD14B	Q96IU4	Oncology
EBI3	Q14213_Q8NEV9	Inflammation
ACP1	P24666	Neurology
```

### HPA Data (`hpa_osps.csv`)
```
gene,uniprot,organ
CFH,P08603,liver
ALS2,Q96Q42,brain
IL27,Q14213_Q6UWB1,lymph_node
PTPRM,P28827,brain
```

## Step-by-Step Execution

### Step 1: LOAD_DATASET_IDENTIFIERS (UKBB)

**Action**: `LOAD_DATASET_IDENTIFIERS`
**Input**: File path and column mappings
**Process**:
1. Read TSV file
2. Identify composite IDs (containing '_')
3. Expand composite rows
4. Add tracking metadata

**Output to context['datasets']['ukbb_raw']**:
```
TableData(rows=[
    {
        'Assay': 'AARSD1',
        'UniProt': 'Q9BTE6',
        'Panel': 'Oncology',
        '_row_source': 'UKBB_Protein_Meta.tsv:2'
    },
    {
        'Assay': 'ABHD14B',
        'UniProt': 'Q96IU4',
        'Panel': 'Oncology',
        '_row_source': 'UKBB_Protein_Meta.tsv:3'
    },
    {
        'Assay': 'EBI3',
        'UniProt': 'Q14213',
        'Panel': 'Inflammation',
        '_composite_source': 'Q14213_Q8NEV9',
        '_composite_group': 'EBI3_Q14213_Q8NEV9',
        '_row_source': 'UKBB_Protein_Meta.tsv:4'
    },
    {
        'Assay': 'EBI3',
        'UniProt': 'Q8NEV9',
        'Panel': 'Inflammation',
        '_composite_source': 'Q14213_Q8NEV9',
        '_composite_group': 'EBI3_Q14213_Q8NEV9',
        '_row_source': 'UKBB_Protein_Meta.tsv:4'
    },
    {
        'Assay': 'ACP1',
        'UniProt': 'P24666',
        'Panel': 'Neurology',
        '_row_source': 'UKBB_Protein_Meta.tsv:5'
    }
])
```

**Metadata to context['metadata']['ukbb_raw']**:
```python
{
    'row_count': 5,  # After expansion
    'original_row_count': 4,
    'composite_expansions': 1,
    'columns': ['Assay', 'UniProt', 'Panel'],
    'primary_column': 'UniProt',
    'source_file': 'UKBB_Protein_Meta.tsv',
    'load_timestamp': '2024-01-15T10:00:00Z'
}
```

### Step 2: LOAD_DATASET_IDENTIFIERS (HPA)

**Similar process for HPA data**

**Output to context['datasets']['hpa_raw']**:
```
TableData(rows=[
    {
        'gene': 'CFH',
        'uniprot': 'P08603',
        'organ': 'liver',
        '_row_source': 'hpa_osps.csv:2'
    },
    {
        'gene': 'ALS2',
        'uniprot': 'Q96Q42',
        'organ': 'brain',
        '_row_source': 'hpa_osps.csv:3'
    },
    {
        'gene': 'IL27',
        'uniprot': 'Q14213',
        'organ': 'lymph_node',
        '_composite_source': 'Q14213_Q6UWB1',
        '_composite_group': 'IL27_Q14213_Q6UWB1',
        '_row_source': 'hpa_osps.csv:4'
    },
    {
        'gene': 'IL27',
        'uniprot': 'Q6UWB1',
        'organ': 'lymph_node',
        '_composite_source': 'Q14213_Q6UWB1',
        '_composite_group': 'IL27_Q14213_Q6UWB1',
        '_row_source': 'hpa_osps.csv:4'
    },
    {
        'gene': 'PTPRM',
        'uniprot': 'P28827',
        'organ': 'brain',
        '_row_source': 'hpa_osps.csv:5'
    }
])
```

### Step 3: RESOLVE_CROSS_REFERENCES (UKBB)

**Action**: `RESOLVE_CROSS_REFERENCES`
**Input**: UKBB data with UniProt IDs
**Process**:
1. Extract unique UniProt IDs: ['Q9BTE6', 'Q96IU4', 'Q14213', 'Q8NEV9', 'P24666']
2. Batch API calls to UniProt
3. Parse responses
4. Add resolved IDs and confidence scores

**API Simulation**:
```
Q9BTE6 → Q9BTE6 (no change, confidence: 1.0)
Q96IU4 → Q96IU4 (no change, confidence: 1.0)
Q14213 → Q14213 (no change, confidence: 1.0)
Q8NEV9 → P0CG08 (obsolete, replaced, confidence: 0.95)
P24666 → P24666 (no change, confidence: 1.0)
```

**Output to context['datasets']['ukbb_resolved']**:
```
TableData(rows=[
    {
        'Assay': 'AARSD1',
        'UniProt': 'Q9BTE6',
        'UniProt_Current': 'Q9BTE6',
        'UniProt_Confidence': 1.0,
        'Panel': 'Oncology',
        '_resolution_type': 'direct',
        '_row_source': 'UKBB_Protein_Meta.tsv:2'
    },
    {
        'Assay': 'EBI3',
        'UniProt': 'Q8NEV9',
        'UniProt_Current': 'P0CG08',
        'UniProt_Confidence': 0.95,
        'Panel': 'Inflammation',
        '_resolution_type': 'obsolete',
        '_resolution_note': 'Q8NEV9 obsoleted, replaced by P0CG08',
        '_composite_source': 'Q14213_Q8NEV9',
        '_composite_group': 'EBI3_Q14213_Q8NEV9',
        '_row_source': 'UKBB_Protein_Meta.tsv:4'
    },
    # ... other rows
])
```

### Step 4: RESOLVE_CROSS_REFERENCES (HPA)

**Similar process for HPA data**

### Step 5: MERGE_DATASETS

**Action**: `MERGE_DATASETS`
**Input**: Two resolved datasets
**Process**:
1. Perform outer join on UniProt_Current = uniprot_current
2. Handle column conflicts
3. Preserve all metadata

**Key Decision**: Q14213 appears in both datasets!
- UKBB: EBI3 assay → Q14213
- HPA: IL27 gene → Q14213

**Output to context['datasets']['merged_proteins']**:
```
TableData(rows=[
    # Matched row
    {
        'UniProt_Current': 'Q14213',  # Join column (kept once)
        'Assay': 'EBI3',
        'UniProt_ukbb': 'Q14213',
        'Panel': 'Inflammation',
        'gene': 'IL27',
        'uniprot_hpa': 'Q14213',
        'organ': 'lymph_node',
        '_in_both': True,
        '_merge_source': 'both'
    },
    # UKBB-only rows
    {
        'UniProt_Current': 'Q9BTE6',
        'Assay': 'AARSD1',
        'UniProt_ukbb': 'Q9BTE6',
        'Panel': 'Oncology',
        'gene': None,
        'uniprot_hpa': None,
        'organ': None,
        '_in_both': False,
        '_merge_source': 'ukbb_only'
    },
    # HPA-only rows
    {
        'UniProt_Current': 'P08603',
        'Assay': None,
        'UniProt_ukbb': None,
        'Panel': None,
        'gene': 'CFH',
        'uniprot_hpa': 'P08603',
        'organ': 'liver',
        '_in_both': False,
        '_merge_source': 'hpa_only'
    },
    # ... other rows
])
```

### Step 6: CALCULATE_SET_OVERLAP

**Action**: `CALCULATE_SET_OVERLAP`
**Input**: Two resolved datasets
**Process**:
1. Extract unique UniProt_Current from each dataset
2. Calculate intersection, unique sets
3. Compute statistics

**Output to context['datasets']['overlap_analysis']**:
```
TableData(rows=[
    {'UniProt_ID': 'Q14213', 'in_UKBB': True, 'in_HPA': True},
    {'UniProt_ID': 'Q9BTE6', 'in_UKBB': True, 'in_HPA': False},
    {'UniProt_ID': 'Q96IU4', 'in_UKBB': True, 'in_HPA': False},
    {'UniProt_ID': 'P0CG08', 'in_UKBB': True, 'in_HPA': False},
    {'UniProt_ID': 'P24666', 'in_UKBB': True, 'in_HPA': False},
    {'UniProt_ID': 'P08603', 'in_UKBB': False, 'in_HPA': True},
    {'UniProt_ID': 'Q96Q42', 'in_UKBB': False, 'in_HPA': True},
    {'UniProt_ID': 'Q6UWB1', 'in_UKBB': False, 'in_HPA': True},
    {'UniProt_ID': 'P28827', 'in_UKBB': False, 'in_HPA': True},
])
```

**Statistics to context['statistics']['overlap_analysis']**:
```python
{
    'set_a_count': 5,  # UKBB unique proteins
    'set_b_count': 5,  # HPA unique proteins
    'intersection_count': 1,  # Q14213
    'union_count': 9,
    'set_a_only': 4,
    'set_b_only': 4,
    'jaccard_index': 0.111,  # 1/9
    'dice_coefficient': 0.200,  # 2*1/(5+5)
    'overlap_percentage_a': 20.0,  # 1/5
    'overlap_percentage_b': 20.0   # 1/5
}
```

### Step 7: AGGREGATE_STATISTICS

**Action**: `AGGREGATE_STATISTICS`
**Input**: Merged dataset
**Process**: Group by Panel × organ combinations

**Output to context['datasets']['category_statistics']**:
```
TableData(rows=[
    {
        'Panel': 'Inflammation',
        'organ': 'lymph_node',
        'proteins_count': 1,
        'proteins_nunique': 1,
        'confidence_mean': 1.0,
        'confidence_min': 1.0
    },
    {
        'Panel': 'Oncology',
        'organ': None,
        'proteins_count': 2,
        'proteins_nunique': 2,
        'confidence_mean': 1.0,
        'confidence_min': 1.0
    },
    # ... other combinations
])
```

### Step 8: FILTER_ROWS (Optional high-confidence)

**Action**: `FILTER_ROWS`
**Input**: Merged dataset
**Process**: Keep only rows with confidence >= 0.95

**Result**: Removes the Q8NEV9→P0CG08 mapping (confidence 0.95)

### Step 9: GENERATE_MAPPING_REPORT

**Action**: `GENERATE_MAPPING_REPORT`
**Input**: All datasets and statistics
**Output**: Excel file with multiple sheets

**Excel Structure**:
```
ukbb_hpa_protein_mapping_20240115_100000.xlsx
├── All_Mappings (9 rows - full outer join)
├── Overlapping_Only (1 row - Q14213)
├── Statistics_By_Category (aggregated data)
├── Summary (overview with charts)
├── Unique_to_UKBB (4 proteins)
└── Unique_to_HPA (4 proteins)
```

## Key Insights from This Walkthrough

1. **Composite expansion is critical**: The Q14213 match only works because we expanded Q14213_Q8NEV9
2. **Historical resolution matters**: Q8NEV9 → P0CG08 change would be missed without it
3. **Metadata preservation**: We can analyze by Panel/organ because we kept all columns
4. **Low overlap is expected**: Only 1/9 proteins overlap in this example (realistic for different platforms)
5. **Tracking is essential**: _composite_source helps understand why EBI3 has two proteins

## Reusability for Other Mappings

This exact pattern works for all 9 protein mappings:
- Only change: file paths and column names in LOAD_DATASET_IDENTIFIERS
- Everything else remains the same
- Same 9-step process
- Same output format