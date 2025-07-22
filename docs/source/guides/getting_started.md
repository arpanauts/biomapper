# Getting Started with Biomapper

## Installation

Biomapper requires Python 3.11 or later. Clone the repository and install using Poetry:

```bash
# Clone the repository
git clone https://github.com/your-org/biomapper.git
cd biomapper

# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install Biomapper with all dependencies
poetry install --with dev,docs,api

# Activate the virtual environment
poetry shell
```

## Basic Usage

Biomapper uses YAML-based strategies executed through a REST API. Here's the basic workflow:

### 1. Start the API Server

```bash
cd biomapper-api
poetry run uvicorn main:app --reload
```

The API will be available at http://localhost:8000

### 2. Create a Strategy

Create a YAML file `my_strategy.yaml`:

```yaml
name: "PROTEIN_ANALYSIS"
description: "Load and analyze protein data"

steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/path/to/proteins.csv"
        identifier_column: "uniprot"
        output_key: "proteins"
        dataset_name: "My Proteins"
```

### 3. Execute the Strategy

Using the Python client:

```python
import asyncio
from biomapper_client import BiomapperClient

async def main():
    async with BiomapperClient() as client:
        result = await client.execute_strategy_file("my_strategy.yaml")
        print(f"Status: {result['status']}")
        print(f"Results: {result['results']}")

asyncio.run(main())
```

Or use curl:

```bash
curl -X POST http://localhost:8000/api/strategies/PROTEIN_ANALYSIS/execute
```

## Core Concepts

### Actions

Biomapper currently ships with three foundational actions, with the architecture designed to support additional specialized actions:

- **LOAD_DATASET_IDENTIFIERS**: Load data from CSV/TSV files
- **MERGE_WITH_UNIPROT_RESOLUTION**: Merge datasets with UniProt resolution  
- **CALCULATE_SET_OVERLAP**: Calculate overlap statistics and Venn diagrams

The extensible action system allows for easy development of new actions to support more sophisticated mapping approaches as requirements evolve.

### YAML Strategies

Strategies define workflows as sequences of actions:

```yaml
name: "DATASET_COMPARISON"
description: "Compare two protein datasets"

steps:
  - name: load_first
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/proteins_a.csv"
        identifier_column: "uniprot"
        output_key: "proteins_a"

  - name: load_second
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/proteins_b.csv"
        identifier_column: "uniprot"
        output_key: "proteins_b"

  - name: merge_datasets
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "proteins_a"
        target_dataset_key: "proteins_b"
        source_id_column: "uniprot"
        target_id_column: "uniprot"
        output_key: "merged_data"

  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        merged_dataset_key: "merged_data"
        source_name: "Dataset A"
        target_name: "Dataset B"
        output_key: "overlap_analysis"
```

### Data Flow

Data flows between actions through a shared context:

1. Actions store results using their `output_key`
2. Subsequent actions reference previous results by key
3. Context persists throughout strategy execution

## Example Use Cases

### Simple Data Loading

```yaml
name: "LOAD_PROTEINS"
steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/my_proteins.tsv"
        identifier_column: "UniProt"
        output_key: "my_proteins"
```

### Dataset Comparison

```yaml
name: "COMPARE_STUDIES"
steps:
  - name: load_study_a
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/study_a.csv"
        identifier_column: "protein_id"
        output_key: "study_a"
        
  - name: load_study_b
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/study_b.csv"
        identifier_column: "protein_id"
        output_key: "study_b"
        
  - name: merge_studies
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "study_a"
        target_dataset_key: "study_b"
        source_id_column: "protein_id"
        target_id_column: "protein_id"
        output_key: "merged_studies"
        
  - name: analyze_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        merged_dataset_key: "merged_studies"
        source_name: "Study A"
        target_name: "Study B"
        output_key: "overlap_stats"
        output_directory: "results/"
```

## Testing Your Setup

Verify your installation works:

```bash
# Check API health
curl http://localhost:8000/api/health

# List available strategies
curl http://localhost:8000/api/strategies/

# Run tests
poetry run pytest tests/unit/
```

## Next Steps

- See [Configuration Guide](../configuration.rst) for detailed strategy syntax
- Check [Action Reference](../actions/) for complete parameter documentation
- View [API Documentation](../api/) for REST endpoint details
- Try the [First Mapping Tutorial](first_mapping.rst) for a complete example