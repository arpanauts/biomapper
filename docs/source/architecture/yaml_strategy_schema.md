# YAML Strategy Schema Documentation

## Overview

This document provides the complete schema reference for defining mapping strategies in YAML configuration files. The YAML strategy system allows users to create flexible, multi-step mapping workflows using the 37+ self-registering actions available in BioMapper.

## Schema Structure

### Top-Level Configuration

```yaml
name: "STRATEGY_NAME"
description: "Brief description of what this strategy does"

metadata:
  id: "unique_strategy_identifier"
  entity_type: "proteins|metabolites|chemistry"
  quality_tier: "experimental|production|test"
  version: "1.0.0"
  author: "author@institution.edu"
  tags: ["tag1", "tag2"]

parameters:
  param_name: "${ENV_VAR:-default_value}"
  # User-configurable parameters

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
| `metadata` | object | No | Strategy metadata including version, author, tags |
| `parameters` | object | No | User-configurable parameters with variable substitution |
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
| `action.type` | string | Yes | One of the 37+ registered action types |
| `action.params` | object | Yes | Parameters specific to the action type (validated by Pydantic) |

## Common Action Types

### Data Loading Actions

#### LOAD_DATASET_IDENTIFIERS

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

### Protein Actions

#### PROTEIN_NORMALIZE_ACCESSIONS

Normalizes and validates UniProt accessions.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_key` | string | Yes | - | Context key of input dataset |
| `output_key` | string | Yes | - | Key to store normalized results |
| `remove_isoforms` | boolean | No | true | Remove isoform suffixes (-1, -2, etc.) |
| `validate_format` | boolean | No | true | Validate UniProt accession format |

#### MERGE_WITH_UNIPROT_RESOLUTION

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

### Analysis Actions

#### CALCULATE_SET_OVERLAP

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

Here's a complete strategy that loads two protein datasets, normalizes them, merges them, and calculates overlap:

```yaml
name: "UKBB_HPA_PROTEIN_COMPARISON"
description: "Compare protein coverage between UK Biobank and Human Protein Atlas"

metadata:
  id: "ukbb_hpa_protein_comparison_v1"
  entity_type: "proteins"
  quality_tier: "production"
  version: "1.0.0"
  author: "researcher@institution.edu"
  tags: ["ukbb", "hpa", "proteins", "overlap"]

parameters:
  ukbb_file: "${UKBB_FILE:-/data/ukbb_proteins.tsv}"
  hpa_file: "${HPA_FILE:-/data/hpa_proteins.csv}"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"

steps:
  # Step 1: Load UK Biobank protein data
  - name: load_ukbb_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.ukbb_file}"
        identifier_column: "UniProt"
        output_key: "ukbb_proteins_raw"
        dataset_name: "UK Biobank Proteins"

  # Step 2: Normalize UK Biobank proteins
  - name: normalize_ukbb
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "ukbb_proteins_raw"
        output_key: "ukbb_proteins"
        remove_isoforms: true
        validate_format: true

  # Step 3: Load Human Protein Atlas data  
  - name: load_hpa_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.hpa_file}"
        identifier_column: "uniprot"
        output_key: "hpa_proteins_raw" 
        dataset_name: "Human Protein Atlas"

  # Step 4: Normalize HPA proteins
  - name: normalize_hpa
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "hpa_proteins_raw"
        output_key: "hpa_proteins"
        remove_isoforms: true
        validate_format: true

  # Step 5: Merge datasets with UniProt resolution
  - name: merge_protein_data
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "ukbb_proteins"
        target_dataset_key: "hpa_proteins"
        source_id_column: "identifier"
        target_id_column: "identifier"
        output_key: "merged_proteins"
        enable_api_resolution: true
        confidence_threshold: 0.5

  # Step 6: Calculate overlap statistics
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
        output_directory: "${parameters.output_dir}/UKBB_HPA"

  # Step 7: Export results
  - name: export_results
    action:
      type: EXPORT_DATASET_V2
      params:
        input_key: "overlap_analysis"
        output_file: "${parameters.output_dir}/overlap_results.csv"
        format: "csv"
```

## Data Flow Between Steps

The context dictionary passes data between steps using the `output_key` from one step as input keys for subsequent steps:

```
Step 1: LOAD_DATASET_IDENTIFIERS → context["datasets"]["ukbb_proteins_raw"]
Step 2: PROTEIN_NORMALIZE_ACCESSIONS → context["datasets"]["ukbb_proteins"]
Step 3: LOAD_DATASET_IDENTIFIERS → context["datasets"]["hpa_proteins_raw"]
Step 4: PROTEIN_NORMALIZE_ACCESSIONS → context["datasets"]["hpa_proteins"]
Step 5: MERGE_WITH_UNIPROT_RESOLUTION → context["datasets"]["merged_proteins"]
Step 6: CALCULATE_SET_OVERLAP → context["datasets"]["overlap_analysis"]
Step 7: EXPORT_DATASET_V2 → context["output_files"].append("overlap_results.csv")
```

## Variable Substitution

The strategy system supports multiple variable substitution patterns:

- **`${parameters.key}`**: Access strategy parameters
- **`${env.VAR_NAME}`**: Access environment variables explicitly
- **`${VAR_NAME}`**: Shorthand for environment variables
- **`${metadata.field}`**: Access metadata fields
- **`${VAR:-default}`**: Provide default value if variable not set

## File Path Considerations

- **Absolute paths recommended**: Use full paths like `/data/proteins.csv`
- **Relative paths supported**: Relative to the working directory where the strategy is executed
- **Variable substitution**: Use `${parameters.file_path}` for configurable paths
- **Output directories**: Created automatically if they don't exist

## Validation

The YAML strategy is validated at multiple levels:

- **Schema validation**: Ensures all required fields are present
- **Parameter validation**: Uses Pydantic models for type checking and constraints
- **Action validation**: Verifies action type exists in ACTION_REGISTRY
- **Reference validation**: Checks that referenced context keys exist during execution
- **File path validation**: Verifies input files exist at execution time

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

Strategies are executed via the REST API or Python client:

### Using Python Client (Synchronous)

```python
from biomapper_client.client_v2 import BiomapperClient

client = BiomapperClient(base_url="http://localhost:8000")

# Execute with custom parameters
result = client.run(
    strategy_name="UKBB_HPA_PROTEIN_COMPARISON",
    parameters={
        "ukbb_file": "/custom/path/ukbb.tsv",
        "hpa_file": "/custom/path/hpa.csv",
        "output_dir": "/custom/output"
    }
)

print(f"Job ID: {result['job_id']}")
print(f"Status: {result['status']}")
print(f"Results: {result['results']}")
```

### Using REST API Directly

```bash
curl -X POST "http://localhost:8000/api/strategies/v2/" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "UKBB_HPA_PROTEIN_COMPARISON",
    "parameters": {
      "ukbb_file": "/data/ukbb.tsv",
      "hpa_file": "/data/hpa.csv"
    }
  }'
```

## Available Actions Reference

BioMapper provides 37+ self-registering actions organized by entity type:

### Protein Actions
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize UniProt identifiers
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from compound fields
- `PROTEIN_MULTI_BRIDGE` - Multi-source protein resolution
- `MERGE_WITH_UNIPROT_RESOLUTION` - Historical UniProt ID mapping

### Metabolite Actions
- `METABOLITE_CTS_BRIDGE` - Chemical Translation Service
- `METABOLITE_NORMALIZE_HMDB` - Standardize HMDB formats
- `NIGHTINGALE_NMR_MATCH` - Nightingale platform matching
- `SEMANTIC_METABOLITE_MATCH` - AI-powered matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity matching

### Chemistry Actions
- `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes
- `CHEMISTRY_FUZZY_TEST_MATCH` - Fuzzy clinical test matching
- `CHEMISTRY_VENDOR_HARMONIZATION` - Harmonize vendor codes

### Analysis Actions
- `CALCULATE_SET_OVERLAP` - Jaccard similarity analysis
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset comparison
- `GENERATE_METABOLOMICS_REPORT` - Comprehensive reports

## See Also

- [Action System Architecture](action_system.rst)
- [API Documentation](../api/)
- [Usage Examples](../usage.rst)