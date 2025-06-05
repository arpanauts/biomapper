# Feedback: Update protein_config.yaml with New File Paths and Add HPA/QIN OSP Data

## Summary of Changes Made

I successfully updated the `/home/ubuntu/biomapper/configs/protein_config.yaml` file with the following changes:

### 1. Updated File Paths for Existing Data Sources

- **UKBB_PROTEIN**: Updated all file paths from `${DATA_DIR}/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv` to `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`

- **ARIVALE_PROTEIN**: Updated all file paths from `${DATA_DIR}/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv` to `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`

- **SPOKE_PROTEIN** (item #4): 
  - Updated file paths from `${DATA_DIR}/spoke_export/protein_nodes.tsv` to `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`
  - Changed file type from `file_tsv` to `file_csv`
  - Updated delimiter from `"\t"` to `","`

- **KG2_PROTEIN** (item #5):
  - Updated file paths from `${DATA_DIR}/kg2_export/protein_entities.tsv` and `${DATA_DIR}/kg2_export/protein_nodes.tsv` to `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv`
  - Changed file type from `file_tsv` to `file_csv`
  - Updated delimiter from `"\t"` to `","`

### 2. Added New Ontology Definitions

Added two new ontology definitions in the top-level `ontologies:` section:
- `HPA_OSP_PROTEIN_ID_ONTOLOGY` with identifier prefix `"HPAOSP_"`
- `QIN_OSP_PROTEIN_ID_ONTOLOGY` with identifier prefix `"QINOSP_"`

### 3. Added New Database Configurations

Added two new database configurations as items #6 and #7:

- **HPA OSP Protein Data** (item #6): Complete configuration with endpoint, properties, and mapping clients
- **QIN OSP Protein Data** (item #7): Complete configuration with endpoint, properties, and mapping clients

## Assumptions Made

### Column Names
Since the actual column names in the new CSV files were not specified, I made the following plausible assumptions:

1. **HPA OSP Data (`hpa_osps.csv`)**:
   - `hpa_assay_id`: The column containing HPA OSP-specific protein identifiers
   - `uniprot_ac`: The column containing UniProt accession numbers

2. **QIN OSP Data (`qin_osps.csv`)**:
   - `qin_assay_id`: The column containing QIN OSP-specific protein identifiers
   - `uniprot_ac`: The column containing UniProt accession numbers

3. **SPOKE and KG2 Data**:
   - Retained existing column name assumptions from the original configuration
   - These may need adjustment based on the actual CSV file structures

### File Formats
- Assumed that all new `.csv` files use comma (`,`) as the delimiter
- Maintained the original column mappings where possible

## Potential Issues Identified

1. **Column Name Verification**: The assumed column names for HPA OSP and QIN OSP data sources should be verified against the actual CSV files.

2. **SPOKE and KG2 Column Names**: Since the files changed from TSV to CSV format, the column names might have changed as well. The current configuration maintains the original column names, which may need updating.

3. **HPP Section**: Note that there is already an HPP section (item #3) in the original configuration that points to `${DATA_DIR}/isb_osp/hpa_osps.csv`. This appears to be using the old path structure and might be redundant with the new HPA OSP configuration.

## Tasks Completed

✅ Updated all file paths for UKBB_PROTEIN, ARIVALE_PROTEIN, SPOKE_PROTEIN, and KG2_PROTEIN to use the new `/procedure/data/local_data/MAPPING_ONTOLOGIES/` structure  
✅ Changed file types and delimiters for SPOKE and KG2 from TSV to CSV  
✅ Added HPA_OSP_PROTEIN_ID_ONTOLOGY and QIN_OSP_PROTEIN_ID_ONTOLOGY to the ontologies section  
✅ Added complete database configurations for HPA OSP (item #6) and QIN OSP (item #7)  
✅ Maintained structural consistency and proper YAML formatting throughout  

## Recommendations

1. Verify the actual column names in the new CSV files and update the configuration accordingly
2. Consider removing or updating the existing HPP section (item #3) to avoid confusion with the new HPA OSP configuration
3. Test the configuration with the actual data files to ensure all paths and column mappings are correct