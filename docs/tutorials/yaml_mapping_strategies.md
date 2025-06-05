# YAML-Defined Mapping Strategies Tutorial

## Overview

YAML-defined mapping strategies provide a declarative way to define complex, multi-step mapping pipelines in Biomapper. Instead of writing custom Python code for each mapping scenario, you can define the sequence of operations in your configuration YAML files.

## Key Concepts

### 1. Mapping Strategy
A named sequence of steps that transforms identifiers from a source ontology type to a target ontology type.

### 2. Strategy Steps
Individual operations within a strategy, executed in order. Each step has:
- A unique `step_id`
- A `description` 
- An `action` with a `type` and parameters

### 3. Action Types
Pre-defined operations that can be used in steps:
- `CONVERT_IDENTIFIERS_LOCAL`: Convert identifiers using data within an endpoint
- `EXECUTE_MAPPING_PATH`: Execute a pre-defined mapping path
- `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`: Filter identifiers based on target endpoint data

## Example: UKBB to HPA Protein Mapping

Here's the YAML configuration for mapping UK Biobank protein assays to HPA proteins:

```yaml
mapping_strategies:
  UKBB_TO_HPA_PROTEIN_PIPELINE:
    description: "Maps UKBB protein assay IDs to HPA OSP native IDs via UniProt AC"
    default_source_ontology_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
    default_target_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
    steps:
      - step_id: "S1_UKBB_NATIVE_TO_UNIPROT"
        description: "Convert UKBB Assay IDs to UniProt ACs"
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "SOURCE"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          
      - step_id: "S2_RESOLVE_UNIPROT_HISTORY"
        description: "Resolve UniProt ACs via API"
        action:
          type: "EXECUTE_MAPPING_PATH"
          path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
          
      - step_id: "S3_FILTER_BY_HPA_PRESENCE"
        description: "Filter to keep only those in HPA"
        action:
          type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
          endpoint_context: "TARGET"
          ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          
      - step_id: "S4_HPA_UNIPROT_TO_NATIVE"
        description: "Convert to HPA native IDs"
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "TARGET"
          input_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          output_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
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