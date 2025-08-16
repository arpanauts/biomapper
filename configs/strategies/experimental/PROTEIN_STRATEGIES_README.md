# Protein Mapping Strategies

## Overview

This directory contains 7 protein mapping strategies for harmonizing proteomics data across multiple cohorts and knowledge graphs.

## Strategies

### 1. Cross-Cohort Comparisons
- `prot_arv_ukb_comparison_uniprot_v1_base.yaml` - Direct Arivale to UKBB comparison

### 2. Arivale Mappings
- `prot_arv_to_kg2c_uniprot_v1_base.yaml` - Arivale → KG2C proteins
- `prot_arv_to_spoke_uniprot_v1_base.yaml` - Arivale → SPOKE proteins

### 3. UKBB Mappings  
- `prot_ukb_to_kg2c_uniprot_v1_base.yaml` - UKBB → KG2C proteins
- `prot_ukb_to_spoke_uniprot_v1_base.yaml` - UKBB → SPOKE proteins

### 4. Multi-Source Integration
- `prot_multi_to_unified_uniprot_v1_enhanced.yaml` - Comprehensive 4-way harmonization (Arivale + UKBB + KG2C + SPOKE)
- `multi_prot_met_pathway_analysis_v1_base.yaml` - Protein-metabolite pathway integration

## Actions Used

All strategies use the newly type-safe protein actions:
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from compound xref fields
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize UniProt accessions (remove versions, isoforms)
- `PROTEIN_MULTI_BRIDGE` - Multi-method protein matching (UniProt, gene symbol, Ensembl)

## Data Sources

### Input Data
- **Arivale**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- **UKBB**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`

### Target Ontologies
- **KG2C**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`
- **SPOKE**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`

## Usage

```bash
# Execute a strategy
poetry run biomapper execute prot_arv_to_kg2c_uniprot_v1_base

# Or using the client
from biomapper_client.client_v2 import BiomapperClient
client = BiomapperClient()
result = client.execute_strategy("prot_arv_to_kg2c_uniprot_v1_base")
```

## Strategy Pattern

All protein strategies follow this general pattern:
1. **Load** source and target datasets
2. **Extract** UniProt IDs from complex fields (if needed)
3. **Normalize** accessions to canonical form
4. **Filter** to valid proteins only
5. **Bridge** using multiple matching methods
6. **Calculate** overlap statistics
7. **Export** results to TSV

## Expected Match Rates

- Arivale → KG2C: ~85%
- Arivale → SPOKE: ~82%
- UKBB → KG2C: ~87%
- UKBB → SPOKE: ~84%
- Arivale ↔ UKBB: ~75% overlap

## Validation Status

✅ All strategies validated (2025-01-13)
- All actions exist and are type-safe
- CALCULATE_THREE_WAY_OVERLAP confirmed available
- Data paths need environment-specific updates

## Notes

- All protein actions were migrated to TypedStrategyAction pattern
- Full type safety with Pydantic models
- Backward compatible with existing YAML structure