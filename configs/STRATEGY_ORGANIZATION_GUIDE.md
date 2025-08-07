# Biomapper Strategy Organization Guide

## Overview

This guide establishes a scalable organizational system for biomapper mapping strategies, designed to manage 100+ strategies with clear hierarchy, versioning, and quality tracking.

## Naming Convention

### Format
```
[EntityType]_[Source]_to_[Target]_[BridgeType]_[Version]_[Variant].yaml
```

### Components

**Entity Types:**
- `prot` - Proteins
- `met` - Metabolites  
- `chem` - Clinical chemistries/labs
- `gene` - Genes
- `path` - Pathways
- `dis` - Diseases

**Source Codes:**
- `arv` - Arivale
- `ukb` - UK Biobank
- `isr` - Israeli10k
- `fnh` - Function Health
- `osp` - ISB OSP
- `multi` - Multiple sources

**Target Codes:**
- `kg2c` - KG2.10.2c ontologies
- `spoke` - SPOKE ontologies
- `unified` - Unified/merged target

**Bridge Types:**
- `uniprot` - UniProt ID bridge
- `inchikey` - InChIKey bridge
- `pubchem` - PubChem CID bridge
- `loinc` - LOINC code bridge
- `ensembl` - Ensembl ID bridge
- `hmdb` - HMDB ID bridge
- `semantic` - AI/semantic matching
- `multi` - Multiple bridge types

**Version:** `v1`, `v2`, `v3` (major versions only)

**Variant:** `base`, `strict`, `fuzzy`, `enhanced`

### Examples from Current Mappings

Based on your 21 mappings:

1. `prot_arv_to_kg2c_uniprot_v1_base.yaml` (Row 9: Arivale proteins → KG2c proteins)
2. `prot_ukb_to_kg2c_uniprot_v1_base.yaml` (Row 10: UKBB proteins → KG2c proteins)
3. `met_arv_to_kg2c_multi_v1_base.yaml` (Row 7: Arivale metabolites → KG2c metabolites)
4. `met_isr_to_spoke_inchikey_v1_base.yaml` (Row 12: Israeli10k metabolites → SPOKE)
5. `chem_arv_to_spoke_loinc_v1_base.yaml` (Row 8: Arivale chemistries → SPOKE clinical labs)
6. `met_ukb_to_kg2c_nmr_v1_base.yaml` (Row 11: UKBB NMR → KG2c metabolites)
7. `chem_isr_to_spoke_loinc_v1_base.yaml` (Row 15: Israeli10k chemistries → SPOKE)
8. `prot_arv_to_spoke_uniprot_v1_base.yaml` (Row 18: Arivale proteins → SPOKE)
9. `prot_ukb_to_spoke_uniprot_v1_base.yaml` (Row 19: UKBB proteins → SPOKE)
10. `met_multi_to_unified_semantic_v1_enhanced.yaml` (Future: Multi-source harmonization)

## Directory Structure

```
configs/
├── strategies/
│   ├── production/          # Production-ready strategies
│   │   ├── prot_arv_to_kg2c_uniprot_v1_base.yaml
│   │   └── prot_ukb_to_kg2c_uniprot_v1_base.yaml
│   ├── experimental/        # Under development
│   │   └── met_multi_to_unified_semantic_v1_enhanced.yaml
│   ├── deprecated/          # Superseded strategies (kept for reference)
│   │   └── prot_arv_to_kg2c_uniprot_v0_legacy.yaml
│   └── templates/           # Reusable templates
│       ├── protein_mapping_template.yaml
│       ├── metabolite_mapping_template.yaml
│       └── chemistry_mapping_template.yaml
├── metadata/                # Strategy metadata files
│   └── strategy_registry.json
├── benchmarks/             # Performance and validation data
│   └── validation_results/
└── docs/                   # Strategy documentation
    └── strategy_guides/
```

## Strategy Metadata Standard

Every strategy file must include:

```yaml
metadata:
  # Required fields
  id: "prot_arv_to_kg2c_uniprot_v1_base"
  name: "Arivale Proteins to KG2c via UniProt"
  version: "1.0.0"
  created: "2025-01-08"
  author: "biomapper-team"
  entity_type: "proteins"
  source_dataset: "arivale"
  target_dataset: "kg2c"
  bridge_type: ["uniprot"]
  
  # Quality tracking
  quality_tier: "experimental"  # experimental | validated | production | gold_standard
  validation_status: "pending"
  expected_match_rate: 0.85
  actual_match_rate: null
  
  # Data tracking
  source_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv"
      last_updated: "2024-06-01"
      row_count: 1197
  target_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv"
      last_updated: "2024-10-01"
      row_count: 45000
  
  # Optional fields
  description: "Maps Arivale proteomics data to KG2c protein ontology using UniProt accessions"
  tags: ["proteomics", "uniprot", "kg2c", "arivale"]
  dependencies: []  # Other strategies this depends on
  supersedes: null  # ID of strategy this replaces
  citation: null    # DOI or publication reference
  
# Parameters that can be overridden at runtime
parameters:
  output_dir: "${OUTPUT_DIR:-/tmp/biomapper/outputs}"
  min_confidence: 0.8
  enable_fuzzy_matching: false
  max_retries: 3

# The actual strategy steps
steps:
  - name: load_source
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "uniprot"
        output_key: "source_proteins"
  # ... additional steps
```

## Quality Tiers

### Tier Progression
1. **experimental** - Initial implementation, not validated
2. **validated** - Tested with known test sets, metrics collected
3. **production** - Approved for production use, stable
4. **gold_standard** - Extensively validated, serves as benchmark

### Promotion Criteria
- **experimental → validated**: 
  - Successful execution on test data
  - Match rate meets expectations (±10%)
  - Code review completed
  
- **validated → production**:
  - Tested on full dataset
  - Performance benchmarks acceptable
  - Documentation complete
  - Approved by team lead
  
- **production → gold_standard**:
  - Used successfully in published research
  - Community validated
  - Serves as reference implementation

## Version Management

### Semantic Versioning
- **Major (v1 → v2)**: Breaking changes, different bridge type, incompatible output
- **Minor (1.0 → 1.1)**: New features, additional outputs, backward compatible
- **Patch (1.0.0 → 1.0.1)**: Bug fixes, performance improvements

### Deprecation Process
1. Mark strategy as deprecated in metadata
2. Add `deprecation_notice` with reason and replacement
3. Move to `deprecated/` folder after 6 months
4. Keep for historical reference

## Handling Special Cases

### Multi-Source Mappings
```yaml
# For mappings that combine multiple sources
met_multi_to_kg2c_semantic_v1_enhanced.yaml

metadata:
  source_dataset: ["arivale", "ukbb", "israeli10k"]
  # List all source files
  source_files:
    - path: "arivale/metabolomics_metadata.tsv"
    - path: "ukbb/UKBB_NMR_Meta.tsv"
    - path: "israeli10k/israeli10k_metabolomics_metadata.csv"
```

### Bidirectional Mappings
```yaml
# Single strategy can handle both directions
prot_kg2c_spoke_bidirectional_v1_base.yaml

metadata:
  bidirectional: true
  forward_direction: "kg2c_to_spoke"
  reverse_direction: "spoke_to_kg2c"
```

### Pipeline Compositions
```yaml
# Complex multi-step pipelines
unified_multiomics_pipeline_v1_comprehensive.yaml

metadata:
  pipeline_components:
    - prot_arv_to_kg2c_uniprot_v1_base
    - met_arv_to_kg2c_multi_v1_base
    - chem_arv_to_spoke_loinc_v1_base
```

## Performance Tracking

### Benchmarks to Track
```yaml
benchmarks:
  execution_time_seconds: 45.2
  memory_usage_mb: 512
  input_records: 1197
  output_records: 1023
  match_rate: 0.854
  false_positive_rate: 0.02
  false_negative_rate: 0.05
  timestamp: "2025-01-08T10:30:00Z"
```

## Registry Management

### Strategy Registry (`metadata/strategy_registry.json`)
```json
{
  "strategies": {
    "prot_arv_to_kg2c_uniprot_v1_base": {
      "status": "production",
      "location": "strategies/production/prot_arv_to_kg2c_uniprot_v1_base.yaml",
      "last_validated": "2025-01-07",
      "usage_count": 156,
      "average_runtime": 42.3,
      "success_rate": 0.98
    }
  },
  "total_strategies": 21,
  "last_updated": "2025-01-08"
}
```

## Implementation Checklist

For each new strategy:
- [ ] Follow naming convention exactly
- [ ] Include all required metadata fields
- [ ] Add to appropriate quality tier folder
- [ ] Create unit tests
- [ ] Run validation benchmarks
- [ ] Document in strategy registry
- [ ] Update this guide if new patterns emerge
- [ ] Request peer review
- [ ] Tag with appropriate version

## Migration Plan

To migrate existing strategies:
1. Rename files following new convention
2. Add complete metadata sections
3. Move to appropriate tier folders
4. Update any references in code
5. Run validation suite
6. Update registry

## Best Practices

1. **Start in experimental/** - All new strategies begin here
2. **Use templates** - Copy from templates/ for consistency
3. **Document bridge logic** - Explain how identifiers are matched
4. **Track data freshness** - Note when source data was updated
5. **Version liberally** - Create new versions for significant changes
6. **Benchmark everything** - Measure performance and accuracy
7. **Peer review** - Have strategies reviewed before production
8. **Keep deprecated strategies** - Maintain history for reproducibility

---

*This organizational system is designed to scale to 100+ strategies while maintaining clarity, traceability, and quality control.*