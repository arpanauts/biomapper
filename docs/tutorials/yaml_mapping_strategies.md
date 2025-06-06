# YAML-Defined Mapping Strategies Tutorial

## Overview

YAML-defined mapping strategies provide a declarative way to define complex, multi-step mapping pipelines in Biomapper. Instead of writing custom Python code for each mapping scenario, you can define the sequence of operations in your configuration YAML files.

## Key Concepts

### 1. Mapping Strategy
A named sequence of steps that transforms identifiers from a source ontology type to a target ontology type.

### 2. Strategy Steps
Individual operations within a strategy, executed in order. Each step has:
- A unique `step_name`
- An `action` with specific parameters
- An optional `is_required` flag (defaults to `true`)

### 3. Action Types
Pre-defined operations that can be used in steps:
- `CONVERT_IDENTIFIERS_LOCAL`: Convert identifiers using a local database table
- `EXECUTE_MAPPING_PATH`: Execute a pre-defined mapping path
- `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`: Filter identifiers based on target resource presence

### 4. The `is_required` Field
Each step can specify whether it must succeed for the strategy to continue:
- `is_required: true` (default): Step failure stops the entire strategy
- `is_required: false`: Step failure is logged but execution continues

## Example: UKBB to HPA Protein Mapping

Here's the YAML configuration for mapping UK Biobank protein assays to HPA proteins:

```yaml
mapping_strategies:
  ukbb_to_hpa_protein:
    mapping_strategy_steps:
      - step_name: "convert_ukbb_to_uniprot"
        action: "CONVERT_IDENTIFIERS_LOCAL"
        action_parameters:
          source_column: "ukbb_protein_id"
          target_column: "uniprot_ac"
          conversion_table: "ukbb_protein_to_uniprot"
          source_id_type: "UKBB_PROTEIN_ID"
          target_id_type: "UniProt_AC"
        is_required: true
        
      - step_name: "resolve_uniprot_history"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "uniprot_history_resolver"
          source_column: "uniprot_ac"
          target_column: "resolved_uniprot_ac"
        is_required: false  # Continue even if history resolution fails
        
      - step_name: "filter_by_hpa"
        action: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
        action_parameters:
          target_resource: "HPA"
          identifier_column: "resolved_uniprot_ac"
          identifier_type: "UniProt_AC"
        is_required: false  # Optional filtering step
        
      - step_name: "convert_to_hpa_native"
        action: "CONVERT_IDENTIFIERS_LOCAL"
        action_parameters:
          source_column: "resolved_uniprot_ac"
          target_column: "hpa_protein_id"
          conversion_table: "hpa_uniprot_to_native"
          source_id_type: "UniProt_AC"
          target_id_type: "HPA_PROTEIN_ID"
        is_required: true
```

## Using YAML Strategies in Code

### Basic Usage

```python
from biomapper.core.mapping_executor import MappingExecutor

# Initialize executor
executor = MappingExecutor()
await executor.initialize()

# Execute the strategy
result = await executor.execute_yaml_strategy(
    strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
    source_endpoint_name="UKBB_PROTEIN",
    target_endpoint_name="HPA_OSP_PROTEIN",
    input_identifiers=["ADAMTS13", "ALB", "APOA1"],
    use_cache=True
)

# Process results
for source_id, mapping in result['results'].items():
    if mapping['mapped_value']:
        print(f"{source_id} -> {mapping['mapped_value']}")
```

### With Progress Tracking

```python
def progress_callback(current, total, status):
    print(f"Step {current}/{total}: {status}")

result = await executor.execute_yaml_strategy(
    strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
    source_endpoint_name="UKBB_PROTEIN",
    target_endpoint_name="HPA_OSP_PROTEIN",
    input_identifiers=identifiers,
    progress_callback=progress_callback
)
```

## Using Optional Steps

The `is_required` field allows you to create more resilient mapping strategies:

```yaml
mapping_strategies:
  flexible_mapping:
    mapping_strategy_steps:
      # Critical step - must succeed
      - step_name: "get_initial_ids"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "primary_source"
        is_required: true
        
      # Try enrichment - nice to have
      - step_name: "enrich_metadata"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "metadata_enrichment"
        is_required: false
        
      # Fallback option if primary fails
      - step_name: "alternative_mapping"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "secondary_source"
        is_required: false
```

This pattern is useful for:
- Adding optional enrichment steps
- Implementing fallback mechanisms
- Continuing despite partial data availability

## Workflow

1. **Define Strategy**: Add the strategy to your entity's config YAML file
2. **Populate Database**: Run `populate_metamapper_db.py` to load the strategy
3. **Execute Strategy**: Use `execute_yaml_strategy()` method
4. **Process Results**: Handle the mapping results and provenance

## Benefits

- **Declarative**: Define complex mappings without writing code
- **Reusable**: Strategies can be reused across different datasets
- **Traceable**: Each step's results are tracked for provenance
- **Extensible**: New action types can be added as needed

## Testing

Run the test script to verify your setup:

```bash
python scripts/test_protein_yaml_strategy.py
```

This will:
1. Check if the strategy is loaded in the database
2. Execute a test mapping
3. Display the results

## Next Steps

- Implement additional action types for your specific needs
- Create strategies for other entity types (metabolites, clinical labs)
- Integrate with bidirectional validation workflows