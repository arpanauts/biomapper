# Config Type Field Reference

## Overview

The `config_type` field is used to distinguish between different types of configuration files in the Biomapper system. This enables the `populate_metamapper_db.py` script to handle each configuration type appropriately.

## Configuration Types

### 1. Entity Configuration (Default)

**Characteristics**:
- No `config_type` field (implicitly entity configuration)
- Contains `entity_type` field (e.g., "protein", "metabolite")
- Defines ontologies, databases, mapping paths, and resources

**Example**:
```yaml
entity_type: "protein"
version: "1.0"
ontologies:
  PROTEIN_UNIPROTKB_AC_ONTOLOGY:
    description: "UniProtKB Accession Numbers"
databases:
  ukbb:
    endpoint:
      name: "UKBB_PROTEIN"
    # ...
```

### 2. Mapping Strategies Configuration

**Characteristics**:
- Explicit `config_type: "mapping_strategies"`
- No `entity_type` field at top level
- Contains `generic_strategies` and/or `entity_strategies`

**Example**:
```yaml
config_type: "mapping_strategies"
version: "1.0"
generic_strategies:
  BRIDGE_VIA_COMMON_ID:
    description: "Map using common identifier"
    # ...
entity_strategies:
  protein:
    UKBB_TO_HPA_PROTEIN_PIPELINE:
      description: "UKBB to HPA mapping"
      # ...
```

## How Config Type Detection Works

The `populate_metamapper_db.py` script uses the following logic:

```python
if config_data.get('config_type') == 'mapping_strategies':
    # Process as strategies configuration
    return self._validate_strategies_config(config_data)
else:
    # Process as entity configuration
    # Requires: entity_type, version, ontologies, databases
```

## Validation Differences

### Entity Configuration Validation

Required fields:
- `entity_type`
- `version`
- `ontologies` (with at least one primary)
- `databases` (with endpoints and properties)

Optional fields:
- `mapping_paths`
- `additional_resources`
- `ontology_preferences`
- `cross_entity_references`

### Strategies Configuration Validation

Required fields:
- `config_type` (must be "mapping_strategies")
- `version`
- At least one of:
  - `generic_strategies`
  - `entity_strategies`

Optional fields:
- `composition_rules`
- `selection_hints`
- `future_categories`

## Processing Order

The system processes configurations in this order:

1. **Entity configurations first** (alphabetically by filename)
   - Loads ontologies, databases, mapping paths
   - Creates all foundational data

2. **Strategies configuration second**
   - Can reference mapping paths from entity configs
   - Can use ontology types defined in entity configs

This order ensures all dependencies are available when strategies are loaded.

## Best Practices

### 1. File Naming

- Entity configs: `<entity>_config.yaml` (e.g., `protein_config.yaml`)
- Strategies config: `mapping_strategies_config.yaml`

### 2. When to Use Each Type

**Use Entity Configuration for**:
- Defining new biological entity types
- Adding data sources (databases/endpoints)
- Defining identifier types (ontologies)
- Creating simple mapping paths

**Use Strategies Configuration for**:
- Complex multi-step pipelines
- Reusable mapping logic
- Cross-entity mapping patterns
- Experimental or alternative approaches

### 3. Migration Path

If you have strategies in entity configs:

1. Check if strategy is generic or entity-specific
2. Move to appropriate section in strategies config
3. Test to ensure it still works
4. Remove from entity config

## Future Config Types

The system is designed to support additional config types:

```yaml
config_type: "validation_rules"  # Potential future type
version: "1.0"
rules:
  protein_id_format:
    pattern: "^[A-Z][0-9]{5}$"
    # ...
```

## Troubleshooting

### Common Issues

1. **"Missing required top-level key: 'entity_type'"**
   - File is being processed as entity config
   - Add `config_type: "mapping_strategies"` if it's a strategies file

2. **"Unknown config_type"**
   - Only "mapping_strategies" is currently supported
   - Check for typos in the config_type value

3. **"Strategies config must contain 'generic_strategies' or 'entity_strategies'"**
   - Strategies config needs at least one strategy section
   - Add appropriate strategies or change config_type

### Debug Tips

1. Check the log output from `populate_metamapper_db.py`:
   ```
   Processing configuration file: configs/protein_config.yaml
   Processing configuration file: configs/mapping_strategies_config.yaml
   Processing mapping strategies configuration
   ```

2. Use the validation script:
   ```bash
   python scripts/setup_and_configuration/validate_config_separation.py
   ```

## Schema Validation

The config_type field affects which JSON schema is applied:

- Entity configs: Use entity-specific schemas (e.g., `protein_config_schema.json`)
- Strategies configs: Use `mapping_strategies_schema.json` (if defined)

This allows for type-specific validation rules and constraints.