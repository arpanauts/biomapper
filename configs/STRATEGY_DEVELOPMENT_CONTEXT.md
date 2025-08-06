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

## Next Steps / TODO

- [ ] Test the arivale_to_kg2c_proteins strategy execution
- [ ] Test the ukbb_to_kg2c_proteins strategy execution
- [ ] Verify match rates meet expectations
- [ ] Consider additional mappings if other datasets need KG2c integration
- [ ] Optimize performance for large-scale execution if needed

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