# Biomapper Configuration Quick Reference

## File Organization

```
configs/
├── protein_config.yaml              # Entity configuration
├── metabolite_config.yaml           # Entity configuration
├── mapping_strategies_config.yaml   # Centralized strategies
└── schemas/                         # JSON schemas for validation
```

## Entity Configuration Structure

```yaml
# protein_config.yaml
entity_type: "protein"              # Required: Entity type name
version: "1.0"                      # Required: Config version

ontologies:                         # Required: Define identifier types
  PROTEIN_UNIPROTKB_AC_ONTOLOGY:
    description: "UniProtKB AC"
    identifier_prefix: "UniProtKB:"
    is_primary: true                # One must be primary

databases:                          # Required: Define data sources
  ukbb:
    endpoint:
      name: "UKBB_PROTEIN"
      type: "file_tsv"
      connection_details:
        file_path: "/path/to/data.tsv"
    properties:
      primary: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
      mappings:
        PROTEIN_UNIPROTKB_AC_ONTOLOGY:
          column: "UniProt"
          ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
    mapping_clients:
      - name: "ukbb_to_uniprot"
        # ... client config ...

mapping_paths:                      # Optional: Direct conversion paths
  - name: "UKBB_TO_UNIPROT"
    source_type: "UKBB_ID"
    target_type: "UNIPROT_ID"
    steps:
      - resource: "ukbb_to_uniprot"

# DO NOT include mapping_strategies here anymore!
```

## Strategies Configuration Structure

```yaml
# mapping_strategies_config.yaml
config_type: "mapping_strategies"   # Required: Identifies this file type
version: "1.0"                      # Required: Config version

generic_strategies:                 # Strategies for all entity types
  BRIDGE_VIA_COMMON_ID:
    description: "Use common ID as bridge"
    applicable_to: ["protein", "metabolite", "gene"]
    parameters:
      - name: "bridge_ontology_type"
        required: true
    steps:
      - step_id: "S1"
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          # ... parameters ...

entity_strategies:                  # Entity-specific strategies
  protein:
    UKBB_TO_HPA_PIPELINE:
      description: "Map UKBB to HPA proteins"
      default_source_ontology_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
      steps:
        - step_id: "S1"
          action:
            type: "CONVERT_IDENTIFIERS_LOCAL"
            endpoint_context: "SOURCE"
            output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

## Common Action Types

| Action Type | Purpose | Key Parameters |
|------------|---------|----------------|
| CONVERT_IDENTIFIERS_LOCAL | Convert IDs using local data | endpoint_context, output_ontology_type |
| EXECUTE_MAPPING_PATH | Run a predefined path | path_name |
| FILTER_IDENTIFIERS_BY_TARGET_PRESENCE | Keep only IDs in target | endpoint_context, ontology_type_to_match |
| MATCH_SHARED_ONTOLOGY | Direct matching | shared_ontology_type |

## Loading Order

1. Entity configs (alphabetically) → Creates ontologies, endpoints, paths
2. Strategies config → Creates strategies using existing components

## Migration Checklist

- [ ] Move `mapping_strategies` sections to `mapping_strategies_config.yaml`
- [ ] Categorize as generic or entity-specific
- [ ] Update any direct strategy references in code
- [ ] Run validation: `python validate_config_separation.py`
- [ ] Reload database: `python populate_metamapper_db.py --drop-all`
- [ ] Remove old `mapping_strategies` sections from entity configs

## Key Commands

```bash
# Validate configuration separation
python scripts/setup_and_configuration/validate_config_separation.py

# Reload database with new configs
python scripts/setup_and_configuration/populate_metamapper_db.py --drop-all

# Check for strategies in entity configs
grep -l "mapping_strategies:" configs/*_config.yaml
```

## Best Practices

1. **Generic strategies**: Use parameters for flexibility
2. **Entity strategies**: Include default ontology types
3. **Action types**: Keep atomic and reusable
4. **Naming**: Use descriptive, uppercase names for strategies
5. **Documentation**: Always include descriptions

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Missing entity_type" | Add `config_type: "mapping_strategies"` |
| "Duplicate strategy name" | Ensure unique names across all sections |
| "Unknown action type" | Check ACTION_TYPES_REFERENCE.md |
| "Strategy not found" | Verify moved to correct section |

## References

- [Full Configuration Guide](README.md)
- [Action Types Reference](/home/ubuntu/biomapper/docs/ACTION_TYPES_REFERENCE.md)
- [Migration Guide](/home/ubuntu/biomapper/docs/CONFIGURATION_MIGRATION_GUIDE.md)
- [Config Type Reference](/home/ubuntu/biomapper/docs/CONFIG_TYPE_FIELD_REFERENCE.md)