# Strategy Configuration - Claude Code Instructions

## Overview
YAML strategy files defining biological data processing pipelines. Strategies are executed via the API without wrapper scripts.

## Mandatory Validation
Before declaring ANY strategy complete:
```bash
python scripts/check_yaml_params.py src/configs/strategies/your_strategy.yaml
```

## Strategy Naming Convention
`entity_source_to_target_method_vX.Y.yaml`
- entity: prot|met|chem
- source: arv|ukbb|nightingale
- target: kg2c|spoke|ukbb
- method: uniprot|hmdb|progressive
- version: v1.0, v2.0, etc.

## Parameter Standards (CRITICAL)
```yaml
parameters:
  # ALWAYS use these standard names
  input_key: source_data       # NOT dataset_key
  output_key: results          # NOT output_dataset  
  file_path: /path/to/file     # NOT filepath
  
  # Use environment variables with defaults
  output_dir: ${OUTPUT_DIR:-/tmp/results}
  api_key: ${UNIPROT_API_KEY}  # Required env var
```

## Progressive Mapping Pattern
```yaml
steps:
  # Stage 1: Direct matching
  - name: stage_1_direct
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        input_key: loaded_data
        output_key: stage_1_matched
        
  # Stage 2: Fuzzy matching on unmatched
  - name: stage_2_fuzzy
    action:
      type: FUZZY_STRING_MATCH
      params:
        input_key: stage_1_unmatched  # From previous stage
        output_key: stage_2_matched
        
  # Combine results
  - name: combine_all
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys: [stage_1_matched, stage_2_matched]
        output_key: final_results
```

## Action Selection Guide
- **Proteins**: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS, PARSE_COMPOSITE_IDENTIFIERS
- **Metabolites**: NIGHTINGALE_NMR_MATCH, CTS_ENRICHED_MATCH, HMDB_VECTOR_MATCH
- **Chemistry**: CHEMISTRY_EXTRACT_LOINC, FUZZY_TEST_MATCH
- **I/O**: LOAD_DATASET_IDENTIFIERS, EXPORT_DATASET, SYNC_TO_GOOGLE_DRIVE

## Testing Your Strategy
```bash
# Quick validation
poetry run biomapper validate strategy_name

# Full execution with timing
poetry run biomapper run strategy_name --profile

# Debug with verbose output
poetry run biomapper run strategy_name --debug
```

## Common Pitfalls
- L Hardcoded paths - Use ${parameters.x}
- L Missing error handling - Add validation steps
- L No progress tracking - Enable progressive_tracking
- L Ignoring unmatched - Always track and report
- L No final export - Always EXPORT_DATASET