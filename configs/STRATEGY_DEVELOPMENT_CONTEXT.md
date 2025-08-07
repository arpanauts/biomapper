# Strategy Development Context - Handoff Document

## Current Session Context (2025-08-06)

This document provides context for continuing strategy development work in the biomapper configs directory.

## Recently Created Strategies

### Protein Mappings to KG2c
Two new strategies were created for mapping protein datasets to the KG2c knowledge graph:

1. **`strategies/arivale_to_kg2c_proteins.yaml`**
   - Source: `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
   - Target: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`
   - Bridge: UniProt IDs (source: `uniprot` column → target: `xrefs` column as "UniProtKB:XXX")
   - Expected match rate: 80-90%

2. **`strategies/ukbb_to_kg2c_proteins.yaml`**
   - Source: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
   - Target: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`
   - Bridge: UniProt IDs (source: `UniProt` column → target: `xrefs` column)
   - Expected match rate: 85-95%
   - Special feature: Panel-specific analysis (Oncology, Neurology, etc.)

## Key Dataset Locations

All source datasets are in: `/procedure/data/local_data/MAPPING_ONTOLOGIES/`

### Protein Datasets:
- **Arivale**: `arivale/proteomics_metadata.tsv` (1,197 proteins with UniProt, gene info)
- **UKBB**: `ukbb/UKBB_Protein_Meta.tsv` (proteins with panel assignments)
- **KG2c Target**: `kg2.10.2c_ontologies/kg2c_proteins.csv` (comprehensive protein ontology)

### Dataset Characteristics:
- **Arivale**: Rich metadata (gene IDs, transcripts, descriptions), TSV format
- **UKBB**: Simple structure (Assay, UniProt, Panel), TSV format
- **KG2c**: Complex xrefs field with multiple identifier types, CSV format

## Strategy Development Pattern

The created strategies follow this pattern:
1. **Load source data** with identifier extraction
2. **Load target KG2c** and parse xrefs for UniProtKB entries
3. **Normalize UniProt IDs** (handle isoforms, variants)
4. **Primary matching** on direct UniProt correspondence
5. **Secondary resolution** via UniProt API for unmatched
6. **Calculate statistics** and quality metrics
7. **Export results** in multiple formats (TSV, JSON, HTML)

## Comprehensive Mapping Plan

### Available Datasets Inventory

#### Source Datasets (Clinical/Research)

**Arivale:**
- `proteomics_metadata.tsv` - 1,197 proteins with UniProt IDs, gene info
- `metabolomics_metadata.tsv` - Metabolite data with various identifiers
- `chemistries_metadata.tsv` - 128 clinical chemistry tests with LOINC codes

**UKBB (UK Biobank):**
- `UKBB_Protein_Meta.tsv` - Proteins with UniProt IDs and panel assignments
- `UKBB_NMR_Meta.tsv` - NMR metabolomics with field IDs and groups

**Israeli10k:**
- `israeli10k_chemistries_metadata.csv` - Clinical chemistry tests
- `israeli10k_metabolomics_metadata.csv` - Metabolomics data
- `israeli10k_lipidomics_metadata.csv` - Lipidomics data

**Function Health:**
- `function_health_tests.csv` - Health test categories and names

**ISB OSP:**
- `hpa_osps.csv` - Gene-UniProt-Organ mappings from Human Protein Atlas
- `qin_osps.csv` - Additional organ-specific protein data

#### Target Knowledge Graphs

**KG2c (Knowledge Graph 2.10.2c):**
- `kg2c_proteins.csv` - Comprehensive protein ontology with xrefs
- `kg2c_genes.csv` - Gene data with cross-references
- `kg2c_metabolites.csv` - Metabolite entities
- `kg2c_chemicals.csv` - Chemical compounds
- `kg2c_drugs.csv` - Drug entities
- `kg2c_diseases.csv` - Disease ontology
- `kg2c_phenotypes.csv` - Phenotype data
- `kg2c_pathways.csv` - Biological pathways
- `kg2c_biological_processes.csv` - GO biological processes
- `kg2c_molecular_activities.csv` - GO molecular activities
- `kg2c_cellular_components.csv` - GO cellular components

**SPOKE:**
- `spoke_proteins.csv` - Proteins with RefSeq/UniProt xrefs
- `spoke_genes.csv` - Genes with Ensembl IDs
- `spoke_metabolites.csv` - Metabolites with InChIKey, PubChem
- `spoke_diseases.csv` - Disease entities
- `spoke_pathways.csv` - Pathway data
- `spoke_clinical_labs.csv` - Clinical lab tests
- `spoke_variants.csv` - Genetic variants
- `spoke_symptoms.csv` - Clinical symptoms
- `spoke_anatomy.csv` - Anatomical entities
- `spoke_cell_types.csv` - Cell type ontology
- `spoke_ec_numbers.csv` - Enzyme commission numbers
- `spoke_organisms.csv` - Organism data

### Identified Mapping Bridges

#### Protein Mappings
- **Primary Bridge**: UniProt IDs (most reliable)
- **Secondary Bridges**: Gene symbols, Ensembl IDs, RefSeq

#### Metabolite Mappings
- **Primary Bridges**: InChIKey, PubChem CID, HMDB ID
- **Secondary Bridges**: Chemical names (with fuzzy matching), KEGG IDs

#### Clinical Test Mappings
- **Primary Bridge**: LOINC codes
- **Secondary Bridges**: Test names (standardized), Labcorp IDs

#### Gene Mappings
- **Primary Bridges**: Ensembl IDs, NCBI Gene IDs
- **Secondary Bridges**: Gene symbols, RefSeq

### Proposed Mapping Strategies

#### Completed Strategies ✅
1. `arivale_to_kg2c_proteins.yaml` - Arivale proteins → KG2c proteins
2. `ukbb_to_kg2c_proteins.yaml` - UKBB proteins → KG2c proteins

#### High Priority Strategies 🔴

**Metabolomics Mappings:**
3. `arivale_metabolomics_to_kg2c.yaml` - Arivale metabolites → KG2c metabolites
4. `ukbb_nmr_to_kg2c_metabolites.yaml` - UKBB NMR → KG2c metabolites
5. `israeli10k_metabolomics_to_kg2c.yaml` - Israeli10k metabolites → KG2c

**Clinical Chemistry Mappings:**
6. `arivale_chemistries_to_spoke_clinical.yaml` - Arivale labs → SPOKE clinical labs (via LOINC)
7. `israeli10k_chemistries_to_spoke.yaml` - Israeli10k labs → SPOKE clinical labs

**Cross-KG Mappings:**
8. `kg2c_to_spoke_proteins.yaml` - KG2c proteins → SPOKE proteins (UniProt bridge)
9. `kg2c_to_spoke_metabolites.yaml` - KG2c metabolites → SPOKE metabolites (InChIKey/PubChem)

#### Medium Priority Strategies 🟡

**Gene-Protein Mappings:**
10. `isb_osp_to_kg2c.yaml` - ISB organ-specific proteins → KG2c (UniProt + organ context)
11. `spoke_genes_to_kg2c_genes.yaml` - SPOKE genes → KG2c genes (Ensembl bridge)

**Lipidomics:**
12. `israeli10k_lipidomics_to_kg2c.yaml` - Israeli10k lipids → KG2c chemicals/metabolites

**Function Health:**
13. `function_health_to_spoke_clinical.yaml` - Function Health tests → SPOKE clinical labs

#### Low Priority/Exploratory 🟢

**Pathway & Disease Mappings:**
14. `kg2c_pathways_to_spoke_pathways.yaml` - Cross-KG pathway alignment
15. `kg2c_diseases_to_spoke_diseases.yaml` - Disease ontology alignment

**Multi-Source Integration:**
16. `unified_protein_atlas.yaml` - Combine all protein sources into unified view
17. `unified_metabolomics_atlas.yaml` - Merge all metabolomics datasets

### Implementation Order & Rationale

**Phase 1: Core Metabolomics** (Weeks 1-2)
- Strategies 3-5: Critical for multi-omics integration
- Builds on existing protein mapping patterns
- High scientific value for biomarker discovery

**Phase 2: Clinical Integration** (Week 3)
- Strategies 6-7, 13: Enable clinical data harmonization
- LOINC bridging is well-established
- Direct clinical application value

**Phase 3: Cross-KG Harmonization** (Week 4)
- Strategies 8-9: Enable KG2c ↔ SPOKE interoperability
- Foundation for unified knowledge graph queries

**Phase 4: Specialized Mappings** (Weeks 5-6)
- Strategies 10-12: Target specific research needs
- Organ-specific and lipidomics focus

**Phase 5: Advanced Integration** (Week 7+)
- Strategies 14-17: Complex multi-source unification
- Requires results from earlier phases

### Expected Match Rates

Based on initial analysis:
- **Protein mappings**: 80-95% (UniProt is reliable)
- **Metabolite mappings**: 60-80% (varied identifier coverage)
- **Clinical test mappings**: 70-85% (LOINC coverage varies)
- **Gene mappings**: 85-95% (well-standardized)
- **Cross-KG mappings**: 70-90% (depends on overlap)

## Next Steps / TODO

- [x] Document comprehensive mapping plan
- [ ] Test the arivale_to_kg2c_proteins strategy execution
- [ ] Test the ukbb_to_kg2c_proteins strategy execution
- [ ] Implement Phase 1 metabolomics strategies (3-5)
- [ ] Develop reusable action for LOINC-based matching
- [ ] Create validation framework for match quality assessment
- [ ] Build visualization dashboards for mapping results

## Working Directory Best Practice

When developing strategies, start Claude Code from this directory:
```bash
cd /home/ubuntu/biomapper/configs
claude  # Start here for strategy work
```

Benefits:
- Focused context on YAML configurations
- Reduced noise from implementation code
- Direct access to strategies/ and schemas/
- More efficient token usage

## Important Notes

1. **All strategies use the biomapper action system** - no custom Python needed
2. **Strategies are loaded dynamically** by the API from this configs/ directory
3. **No database loading required** - YAML files are read directly at runtime
4. **Use existing strategies as templates** - especially `arivale_ukbb_mapping.yaml`
5. **Follow progressive enhancement pattern** for complex mappings

## Execution Commands

```bash
# Via biomapper CLI
poetry run biomapper execute-strategy arivale_to_kg2c_proteins
poetry run biomapper execute-strategy ukbb_to_kg2c_proteins

# Via Python client
from biomapper_client import BiomapperClient
async with BiomapperClient() as client:
    result = await client.execute_strategy("ARIVALE_TO_KG2C_PROTEINS")
```

## Related Documentation

- `CLAUDE.md` - AI assistant instructions for biomapper
- `README.md` - Configuration system overview
- `docs/protein_mapping_strategy.md` - Detailed protein mapping documentation
- `schemas/metabolomics_strategy_schema.json` - Strategy validation schema

---

*This handoff document created during strategy development session on 2025-08-06*