# YAML Strategy Schema Documentation

## Overview

This document provides the complete schema reference for defining mapping strategies in YAML configuration files. The YAML strategy system allows users to create flexible, multi-step mapping workflows using the three core actions.

## Schema Structure

### Top-Level Configuration

```yaml
name: "STRATEGY_NAME"
description: "Brief description of what this strategy does"

steps:
  - name: "step_name"
    action:
      type: "ACTION_TYPE"
      params:
        # Parameters specific to the action type
```

### Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Strategy identifier (uppercase with underscores) |
| `description` | string | No | Human-readable strategy description |
| `steps` | array | Yes | List of steps to execute sequentially |

### Step Structure

Each step in the `steps` array has this structure:

```yaml
- name: "descriptive_step_name"
  action:
    type: "ACTION_TYPE"
    params:
      parameter1: value1
      parameter2: value2
```

#### Step Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Descriptive name for the step |
| `action.type` | string | Yes | One of the three core action types |
| `action.params` | object | Yes | Parameters specific to the action type |

## Core Action Types

### LOAD_DATASET_IDENTIFIERS

Loads identifiers from CSV/TSV files with flexible column mapping.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Absolute path to the data file |
| `identifier_column` | string | Yes | - | Column name containing identifiers |
| `output_key` | string | Yes | - | Key to store results in context |
| `dataset_name` | string | No | - | Human-readable name for logging |
| `strip_prefix` | string | No | - | Prefix to remove from identifiers |
| `filter_column` | string | No | - | Column to apply filtering on |
| `filter_values` | array | No | - | Values/patterns to filter by |
| `filter_mode` | string | No | "include" | "include" or "exclude" |
| `drop_empty_ids` | boolean | No | true | Drop rows with empty identifiers |

**Example:**

```yaml
- name: load_ukbb_proteins
  action:
    type: LOAD_DATASET_IDENTIFIERS
    params:
      file_path: "/data/ukbb_proteins.tsv"
      identifier_column: "UniProt"
      output_key: "ukbb_proteins"
      dataset_name: "UK Biobank Proteins"
      drop_empty_ids: true
```

### MERGE_WITH_UNIPROT_RESOLUTION

Merges two datasets with historical UniProt identifier resolution.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_dataset_key` | string | Yes | - | Context key of source dataset |
| `target_dataset_key` | string | Yes | - | Context key of target dataset |
| `source_id_column` | string | Yes | - | Column name in source data |
| `target_id_column` | string | Yes | - | Column name in target data |
| `output_key` | string | Yes | - | Key to store merged results |
| `enable_api_resolution` | boolean | No | true | Enable UniProt API for unmatched IDs |
| `source_suffix` | string | No | "_source" | Suffix for source columns |
| `target_suffix` | string | No | "_target" | Suffix for target columns |
| `confidence_threshold` | number | No | 0.0 | Minimum confidence for matches |
| `composite_separator` | string | No | "_" | Separator for composite identifiers |

**Example:**

```yaml
- name: merge_datasets
  action:
    type: MERGE_WITH_UNIPROT_RESOLUTION
    params:
      source_dataset_key: "ukbb_proteins"
      target_dataset_key: "hpa_proteins"
      source_id_column: "UniProt"
      target_id_column: "uniprot"
      output_key: "merged_dataset"
      enable_api_resolution: true
      confidence_threshold: 0.5
```

### CALCULATE_SET_OVERLAP

Calculates overlap statistics between two datasets and generates Venn diagrams.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `merged_dataset_key` | string | Yes | - | Context key of merged dataset |
| `source_name` | string | Yes | - | Display name for source dataset |
| `target_name` | string | Yes | - | Display name for target dataset |
| `output_key` | string | Yes | - | Key to store overlap results |
| `mapping_combo_id` | string | No | - | Unique identifier for this mapping |
| `confidence_threshold` | number | No | 0.0 | Minimum confidence for high-quality matches |
| `output_directory` | string | No | "data/results" | Directory for output files |

**Example:**

```yaml
- name: calculate_overlap
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      merged_dataset_key: "merged_dataset"
      source_name: "UKBB"
      target_name: "HPA"
      output_key: "overlap_statistics"
      mapping_combo_id: "UKBB_HPA_ANALYSIS"
      confidence_threshold: 0.7
      output_directory: "data/results/UKBB_HPA"
```

## Complete Example

Here's a complete strategy that loads two protein datasets, merges them, and calculates overlap:

```yaml
name: "UKBB_HPA_PROTEIN_COMPARISON"
description: "Compare protein coverage between UK Biobank and Human Protein Atlas"

steps:
  # Step 1: Load UK Biobank protein data
  - name: load_ukbb_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/ukbb_proteins.tsv"
        identifier_column: "UniProt"
        output_key: "ukbb_proteins"
        dataset_name: "UK Biobank Proteins"

  # Step 2: Load Human Protein Atlas data  
  - name: load_hpa_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/hpa_proteins.csv"
        identifier_column: "uniprot"
        output_key: "hpa_proteins" 
        dataset_name: "Human Protein Atlas"

  # Step 3: Merge datasets with UniProt resolution
  - name: merge_protein_data
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "ukbb_proteins"
        target_dataset_key: "hpa_proteins"
        source_id_column: "UniProt"
        target_id_column: "uniprot"
        output_key: "merged_proteins"
        enable_api_resolution: true
        confidence_threshold: 0.5

  # Step 4: Calculate overlap statistics
  - name: analyze_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        merged_dataset_key: "merged_proteins"
        source_name: "UKBB"
        target_name: "HPA" 
        output_key: "overlap_analysis"
        mapping_combo_id: "UKBB_HPA_COMPARISON"
        confidence_threshold: 0.7
        output_directory: "data/results/UKBB_HPA"
```

## Data Flow Between Steps

The context dictionary passes data between steps using the `output_key` from one step as input keys for subsequent steps:

```
Step 1: LOAD_DATASET_IDENTIFIERS → context["ukbb_proteins"]
Step 2: LOAD_DATASET_IDENTIFIERS → context["hpa_proteins"] 
Step 3: MERGE_WITH_UNIPROT_RESOLUTION → context["merged_proteins"]
Step 4: CALCULATE_SET_OVERLAP → context["overlap_analysis"]
```

## File Path Considerations

- **Absolute paths recommended**: Use full paths like `/data/proteins.csv`
- **Relative paths supported**: Relative to the working directory where the strategy is executed
- **Environment variables**: Can be used in paths (resolved by the system)
- **Output directories**: Created automatically if they don't exist

## Validation

The YAML strategy is validated when loaded:

- **Schema validation**: Ensures all required fields are present
- **Parameter validation**: Uses Pydantic models for type checking
- **Reference validation**: Checks that referenced context keys exist
- **File path validation**: Verifies input files exist (at execution time)

## Error Handling

When a step fails:
- Execution stops immediately
- Error details are logged
- Previous steps' results are preserved in context
- API returns error information with context state

## Best Practices

### Naming Conventions
- **Strategy names**: UPPERCASE_WITH_UNDERSCORES
- **Step names**: lowercase_with_underscores, descriptive
- **Output keys**: descriptive, reflect data content
- **Dataset names**: Human-readable for logging

### Strategy Design
- **Sequential steps**: Each step builds on previous results
- **Descriptive names**: Make the workflow self-documenting
- **Logical grouping**: Group related operations
- **Error consideration**: Plan for missing files or empty datasets

### File Organization
```
configs/
├── simple_strategies/
│   ├── load_single_dataset.yaml
│   └── basic_comparison.yaml
├── protein_strategies/
│   ├── ukbb_hpa_comparison.yaml
│   └── multi_source_analysis.yaml
└── production_strategies/
    └── comprehensive_protein_mapping.yaml
```

## Performance Considerations

- **File sizes**: Large files (>1M rows) may require increased timeouts
- **API calls**: UniProt resolution adds significant time for unmatched IDs
- **Memory usage**: Large datasets are processed in memory
- **Output files**: Venn diagrams and CSV files are generated for each analysis

## Integration with API

Strategies are executed via the REST API:

```python
import asyncio
from biomapper_client import BiomapperClient

async def run_strategy():
    async with BiomapperClient() as client:
        result = await client.execute_strategy(
            strategy_name="UKBB_HPA_PROTEIN_COMPARISON"
        )
        print(f"Analysis completed: {result['status']}")

asyncio.run(run_strategy())
```

## See Also

- [Core Actions Reference](../actions/)
- [API Documentation](../api/)
- [Usage Examples](../usage.rst)