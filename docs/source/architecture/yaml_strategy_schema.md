# YAML Strategy Schema Documentation

## Overview

This document provides a comprehensive schema reference for defining mapping strategies in YAML configuration files. The YAML strategy system allows users to create flexible, multi-step mapping workflows that can be executed by the `MappingExecutor`.

## Schema Structure

### Top-Level Configuration

```yaml
ontologies:
  # Ontology definitions (required)

databases:
  # Database configurations (required)

mapping_clients:
  # Client configurations (required)

mapping_strategies:
  # Strategy definitions (optional)
  strategy_name:
    mapping_strategy_steps:
      - # Step definition
```

### Mapping Strategy Definition

Each mapping strategy consists of a list of steps that are executed sequentially:

```yaml
mapping_strategies:
  strategy_name:
    mapping_strategy_steps:
      - step_name: "descriptive_name"
        action: "ACTION_TYPE"
        action_parameters:
          # Parameters specific to the action type
        is_required: true  # Optional, defaults to true
```

### Step Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `step_name` | string | Yes | - | A descriptive name for the step |
| `action` | string | Yes | - | The action type to execute |
| `action_parameters` | object | Yes | - | Parameters specific to the action type |
| `is_required` | boolean | No | `true` | Whether the step must succeed for the strategy to continue |

### The `is_required` Field

The `is_required` field controls the execution flow when a step fails:

- **`is_required: true` (default)**: If the step fails, the entire strategy execution stops and returns the results collected so far.
- **`is_required: false`**: If the step fails, the strategy continues with the next step. This is useful for optional enrichment steps or fallback mechanisms.

Example:
```yaml
mapping_strategy_steps:
  - step_name: "primary_mapping"
    action: "EXECUTE_MAPPING_PATH"
    action_parameters:
      mapping_path: "path1"
    is_required: true  # Must succeed
    
  - step_name: "optional_enrichment"
    action: "EXECUTE_MAPPING_PATH"
    action_parameters:
      mapping_path: "enrichment_path"
    is_required: false  # Can fail without stopping execution
```

## Action Types

### CONVERT_IDENTIFIERS_LOCAL

Converts identifiers from one type to another using a local database table.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_column` | string | Yes | The column containing source identifiers |
| `target_column` | string | Yes | The column name for converted identifiers |
| `conversion_table` | string | Yes | The database table to use for conversion |
| `source_id_type` | string | Yes | The type of the source identifiers |
| `target_id_type` | string | Yes | The desired target identifier type |

**Example:**
```yaml
- step_name: "convert_gene_to_uniprot"
  action: "CONVERT_IDENTIFIERS_LOCAL"
  action_parameters:
    source_column: "gene_id"
    target_column: "uniprot_id"
    conversion_table: "gene_to_uniprot"
    source_id_type: "HGNC"
    target_id_type: "UniProt"
  is_required: true
```

### EXECUTE_MAPPING_PATH

Executes a predefined mapping path to map identifiers between resources.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mapping_path` | string | Yes | The name of the mapping path to execute |
| `source_column` | string | No | Override the default source column |
| `target_column` | string | No | Override the default target column |

**Example:**
```yaml
- step_name: "map_to_target_resource"
  action: "EXECUTE_MAPPING_PATH"
  action_parameters:
    mapping_path: "uniprot_to_ensembl"
    source_column: "protein_id"
    target_column: "gene_id"
  is_required: true
```

### FILTER_IDENTIFIERS_BY_TARGET_PRESENCE

Filters the dataset to only include rows where identifiers exist in the target resource.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_resource` | string | Yes | The target resource to check against |
| `identifier_column` | string | Yes | The column containing identifiers to check |
| `identifier_type` | string | Yes | The type of identifiers being checked |

**Example:**
```yaml
- step_name: "filter_existing_proteins"
  action: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
  action_parameters:
    target_resource: "HPA"
    identifier_column: "protein_id"
    identifier_type: "UniProt"
  is_required: false  # Optional filtering step
```

## Complete Example

Here's a complete example of a YAML configuration with a multi-step mapping strategy:

```yaml
ontologies:
  UKBB:
    db: "ukbb_db"
    name: "UK Biobank"
    
  HPA:
    db: "hpa_db"
    name: "Human Protein Atlas"

databases:
  ukbb_db:
    connection_string: "postgresql://..."
    
  hpa_db:
    connection_string: "postgresql://..."

mapping_clients:
  uniprot_client:
    type: "uniprot"
    config:
      api_url: "https://www.uniprot.org"

mapping_strategies:
  ukbb_to_hpa_protein:
    mapping_strategy_steps:
      # Step 1: Convert gene symbols to UniProt IDs
      - step_name: "gene_to_uniprot"
        action: "CONVERT_IDENTIFIERS_LOCAL"
        action_parameters:
          source_column: "gene_symbol"
          target_column: "uniprot_primary"
          conversion_table: "gene_uniprot_mapping"
          source_id_type: "HGNC"
          target_id_type: "UniProt"
        is_required: true  # Must have UniProt IDs to continue
        
      # Step 2: Try primary mapping path
      - step_name: "primary_path"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "uniprot_to_hpa_direct"
          source_column: "uniprot_primary"
          target_column: "hpa_id"
        is_required: false  # Continue if this fails
        
      # Step 3: Fallback mapping path
      - step_name: "fallback_path"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "uniprot_to_hpa_via_ensembl"
          source_column: "uniprot_primary"
          target_column: "hpa_id_fallback"
        is_required: false  # Optional fallback
        
      # Step 4: Filter to only proteins in HPA
      - step_name: "filter_hpa_proteins"
        action: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
        action_parameters:
          target_resource: "HPA"
          identifier_column: "hpa_id"
          identifier_type: "HPA"
        is_required: false  # Optional filtering
```

## Best Practices

1. **Use descriptive step names**: Make it clear what each step does
2. **Order matters**: Steps are executed sequentially, so plan accordingly
3. **Use `is_required` wisely**: 
   - Mark critical steps as required (default)
   - Use `is_required: false` for optional enrichment or fallback steps
4. **Test incrementally**: Test each step individually before combining them
5. **Document your strategies**: Add comments to explain complex logic

## Error Handling

When a required step fails:
- Execution stops immediately
- Previous successful steps' results are preserved
- An error message indicates which step failed

When an optional step fails:
- A warning is logged
- Execution continues with the next step
- The final results indicate which optional steps were skipped

## See Also

- [YAML Mapping Strategies Tutorial](../tutorials/yaml_mapping_strategies.md)
- [MappingExecutor Architecture](./mapping_executor_architecture.md)
- [Iterative Mapping Strategy](../../../roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md)