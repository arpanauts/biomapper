# Configuration Migration Guide: Separating Mapping Strategies

This guide explains how to migrate from the old configuration structure (where mapping strategies were embedded in entity configs) to the new separated structure.

## Why Separate Mapping Strategies?

1. **Reusability**: Generic strategies can be used across different entity types
2. **Maintainability**: Centralized strategies are easier to update and manage
3. **Clarity**: Entity configs focus on data sources, strategy configs focus on logic
4. **Scalability**: Adding new strategies doesn't require modifying entity configs

## Migration Steps

### 1. Identify Existing Strategies

Check your entity config files for `mapping_strategies` sections:

```bash
grep -l "mapping_strategies:" configs/*_config.yaml
```

### 2. Extract Strategy Definitions

For each entity config with strategies:

#### Old Structure (in `protein_config.yaml`):
```yaml
entity_type: "protein"
# ... ontologies, databases, etc ...

mapping_strategies:
  UKBB_TO_HPA_PROTEIN_PIPELINE:
    description: "Maps UKBB protein assay IDs to HPA OSP native IDs"
    steps:
      - step_id: "S1_CONVERT"
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          # ...
```

#### New Structure (in `mapping_strategies_config.yaml`):
```yaml
config_type: "mapping_strategies"
version: "1.0"

entity_strategies:
  protein:
    UKBB_TO_HPA_PROTEIN_PIPELINE:
      description: "Maps UKBB protein assay IDs to HPA OSP native IDs"
      steps:
        - step_id: "S1_CONVERT"
          action:
            type: "CONVERT_IDENTIFIERS_LOCAL"
            # ...
```

### 3. Categorize Strategies

Determine if each strategy is:

- **Generic**: Can work with any entity type → Place in `generic_strategies`
- **Entity-Specific**: Only works with one entity type → Place in `entity_strategies.<entity_type>`

### 4. Update References

If any code directly references strategy names, ensure they still work with the new structure.

### 5. Test the Migration

```bash
# Validate the new configuration
python scripts/setup_and_configuration/validate_config_separation.py

# Reload the database
python scripts/setup_and_configuration/populate_metamapper_db.py --drop-all
```

### 6. Clean Up Old Configs

Once verified, remove `mapping_strategies` sections from entity configs:

```yaml
# Remove this entire section from entity configs:
mapping_strategies:
  # ... all strategies ...
```

## Configuration Type Detection

The system automatically detects configuration type:

### Entity Configuration:
```yaml
entity_type: "protein"  # No config_type field
version: "1.0"
ontologies:
  # ...
databases:
  # ...
```

### Strategies Configuration:
```yaml
config_type: "mapping_strategies"  # Explicit type
version: "1.0"
generic_strategies:
  # ...
entity_strategies:
  # ...
```

## Backward Compatibility

The system maintains backward compatibility:

1. **Warning Only**: If strategies are found in entity configs, a warning is logged
2. **Still Processed**: The strategies are still loaded and work correctly
3. **No Breaking Changes**: Existing pipelines continue to function

## Best Practices

### For Generic Strategies

1. **Use Parameters**: Make strategies flexible with parameters
```yaml
generic_strategies:
  BRIDGE_VIA_COMMON_ID:
    parameters:
      - name: "bridge_ontology_type"
        description: "The ontology type to use as bridge"
        required: true
```

2. **Document Applicability**: Clearly state which entity types can use the strategy
```yaml
applicable_to: ["protein", "metabolite", "clinical_lab"]
```

### For Entity-Specific Strategies

1. **Include Defaults**: Specify default ontology types when applicable
```yaml
default_source_ontology_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
default_target_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
```

2. **Reference Mapping Paths**: Use EXECUTE_MAPPING_PATH for reusability
```yaml
action:
  type: "EXECUTE_MAPPING_PATH"
  path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
```

## Validation

The `populate_metamapper_db.py` script validates:

1. **No Duplicate Names**: Strategy names must be unique across all categories
2. **Valid References**: Action types and mapping paths must exist
3. **Required Fields**: Each strategy must have steps with valid actions
4. **Ontology Types**: Referenced ontology types must be defined

## Example: Complete Migration

### Before (protein_config.yaml):
```yaml
entity_type: "protein"
ontologies:
  PROTEIN_UNIPROTKB_AC_ONTOLOGY:
    description: "UniProtKB Accession"
databases:
  ukbb:
    # ... database config ...
mapping_strategies:
  SIMPLE_MATCH:
    description: "Direct match via UniProt"
    steps:
      - step_id: "S1"
        action:
          type: "MATCH_SHARED_ONTOLOGY"
          shared_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### After:

**protein_config.yaml**:
```yaml
entity_type: "protein"
ontologies:
  PROTEIN_UNIPROTKB_AC_ONTOLOGY:
    description: "UniProtKB Accession"
databases:
  ukbb:
    # ... database config ...
# mapping_strategies section removed
```

**mapping_strategies_config.yaml**:
```yaml
config_type: "mapping_strategies"
version: "1.0"
generic_strategies:
  SIMPLE_MATCH:
    description: "Direct match via shared ontology"
    applicable_to: ["protein", "metabolite", "gene"]
    parameters:
      - name: "shared_ontology_type"
        required: true
    steps:
      - step_id: "S1"
        action:
          type: "MATCH_SHARED_ONTOLOGY"
          shared_ontology_type: "${shared_ontology_type}"
```

## Troubleshooting

### Common Issues

1. **"Strategy not found" errors**
   - Ensure strategy was moved to the correct section in mapping_strategies_config.yaml
   - Check for typos in strategy names

2. **"Duplicate strategy name" errors**
   - Strategy names must be globally unique
   - Rename if necessary

3. **"Unknown action type" warnings**
   - Verify action types match those in ACTION_TYPES_REFERENCE.md
   - Check for typos in action type names

### Getting Help

- Check logs from `populate_metamapper_db.py` for specific validation errors
- Use `validate_config_separation.py` to check configuration integrity
- Review the example configurations in the configs directory

## Future Enhancements

The separated configuration structure enables:

1. **Strategy Libraries**: Share strategies across projects
2. **Version Control**: Track strategy evolution independently
3. **Dynamic Loading**: Load strategies from multiple files
4. **Strategy Composition**: Build complex strategies from simpler ones