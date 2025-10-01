# Israeli10K Nightingale to Kraken Proto-Strategy

## Overview
This proto-strategy maps Israeli10K Nightingale NMR metabolomics biomarkers to Kraken Knowledge Graph (version 1.0.0) chemical nodes using direct ChEBI ID matching.

## Implementation Type
**Proto-Strategy**: Standalone Python scripts following the COMPLETE_MAPPING_GUIDE pattern
- No biomapper framework dependencies
- Direct pandas operations for ID matching
- Simple bash orchestration

## Usage

### Quick Start
```bash
# Run the complete pipeline
./run_all.sh
```

### Step-by-Step Execution
```bash
# Step 1: Load and prepare Nightingale data
python3 01_load_nightingale_data.py

# Step 2: Prepare Kraken reference data
python3 02_prepare_kraken_reference.py

# Step 3: Direct ChEBI ID mapping
python3 03_map_to_kraken.py

# Step 4: Generate final report
python3 04_generate_report.py
```

## Data Sources

### Input
- **Nightingale Metadata**: `/home/ubuntu/biomapper/data/processed/Nightingale_complete_metadata.tsv`
- **Kraken Chemicals**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv`

### Output
- **Main Mapping**: `results/israeli10k_nightingale_to_kraken_mapping.tsv`
- **Coverage Report**: `results/mapping_coverage_report.json`
- **Summary Statistics**: `results/mapping_summary_statistics.tsv`

## Results Summary

### Current Performance
- **Total Biomarkers**: 17 metabolites with ChEBI IDs
- **Successfully Mapped**: 17 (100% coverage)
- **Mapping Method**: Direct ChEBI ID join
- **Confidence Level**: High (exact matches = 1.0)

### Biomarker Categories
- Fatty acids: 8 biomarkers
- Cholesterol: 4 biomarkers
- Triglycerides: 2 biomarkers
- Other lipids: 2 biomarkers
- Free cholesterol: 1 biomarker

### Output Fields
Each mapped metabolite includes:
- `nightingale_biomarker_id`: Original Nightingale identifier
- `nightingale_name`: Biomarker name
- `kg2c_node_id`: Kraken node identifier (ChEBI format)
- `kg2c_name`: Kraken chemical name
- `kg2c_category`: Kraken categorization
- `chemical_class`: Chemical classification
- `measurement_type`: NMR measurement type
- `mapping_confidence`: Confidence score (1.0 for exact matches)
- `population_notes`: Israeli10K-specific annotations

## Validation Criteria ✅

All validation criteria from the original prompt are met:
- [x] All biomarkers processed
- [x] ChEBI mappings consistent with UKBB
- [x] NMR measurements documented
- [x] Population-specific notes included
- [x] Comparison with UKBB mappings performed
- [x] Key metabolites verified

## Technical Notes

### ID Transformation
- Nightingale ChEBI IDs: "CHEBI: 50404" → "50404" (numeric)
- Kraken ChEBI IDs: "CHEBI:50404" → "50404" (numeric)
- Direct join on cleaned numeric ChEBI IDs

### Processing Time
- Complete pipeline: ~2-3 minutes
- Step 2 (Kraken reference) takes longest due to large file size

### Dependencies
- Python 3.x
- pandas
- numpy
- Standard library modules (pathlib, datetime, json)

## Population Context
This mapping is specific to the **Israeli10K cohort** using **Nightingale NMR platform** data, providing metabolomics biomarker mappings to the **Kraken 1.0.0 Knowledge Graph** for population-specific metabolite analysis.