:orphan:

# Getting Started with Biomapper

## Installation

Biomapper requires Python 3.11 or later. Clone the repository and install using Poetry:

```bash
# Clone the repository
git clone https://github.com/arpanauts/biomapper.git
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
# Start directly from project root (no separate directory needed)
poetry run uvicorn api.main:app --reload --port 8000
```

The API will be available at:
- Interactive docs: http://localhost:8000/api/docs  
- API health: http://localhost:8000/api/health

### 2. Create a Strategy

Create a YAML file in `src/configs/strategies/` or locally:

```yaml
name: "protein_harmonization"
description: "Load and harmonize protein identifiers"

parameters:
  input_file: "/path/to/proteins.csv"
  output_dir: "/results"

steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.input_file}"
        identifier_column: "uniprot_id"
        output_key: "proteins"
```

### 3. Execute the Strategy

Using the Python client (located in `src/client/`):

```python
from client.client_v2 import BiomapperClient

# Simple synchronous execution (recommended)
client = BiomapperClient(base_url="http://localhost:8000")
result = client.run("protein_harmonization", parameters={
    "input_file": "/path/to/your/data.csv",
    "output_dir": "/path/to/output"
})
print(f"Success: {result.get('success', False)}")
print(f"Job ID: {result.get('job_id')}")

# Or async with progress tracking
import asyncio

async def main():
    async with BiomapperClient() as client:
        result = await client.execute_strategy("protein_harmonization")
        print(f"Success: {result.get('success', False)}")

asyncio.run(main())
```

Or use the CLI:

```bash
# Check available commands
poetry run biomapper --help

# Basic health check
poetry run biomapper health

# List available strategies
poetry run biomapper strategies
```

## Core Concepts

### Actions

Biomapper ships with 30+ self-registering actions organized by entity type in `src/actions/`:

**Core Data Operations:**
- **LOAD_DATASET_IDENTIFIERS**: Load biological identifiers from CSV/TSV files
- **MERGE_DATASETS**: Combine multiple datasets with deduplication
- **FILTER_DATASET**: Apply filtering criteria to datasets
- **EXPORT_DATASET_V2**: Export results to TSV/CSV/JSON formats
- **CUSTOM_TRANSFORM_EXPRESSION**: Apply Python expressions to transform data

**Protein Mapping** (`entities/proteins/`):
- **PROTEIN_EXTRACT_UNIPROT_FROM_XREFS**: Extract UniProt IDs from compound reference fields
- **PROTEIN_NORMALIZE_ACCESSIONS**: Standardize protein accession formats
- **PROTEIN_MULTI_BRIDGE**: Multi-source protein identifier resolution
- **MERGE_WITH_UNIPROT_RESOLUTION**: Map identifiers to UniProt accessions

**Metabolite Mapping** (`entities/metabolites/`):
- **METABOLITE_CTS_BRIDGE**: Chemical Translation Service API integration
- **NIGHTINGALE_NMR_MATCH**: Nightingale NMR platform matching
- **SEMANTIC_METABOLITE_MATCH**: AI-powered semantic matching
- **VECTOR_ENHANCED_MATCH**: Vector embedding similarity matching
- **METABOLITE_EXTRACT_IDENTIFIERS**: Extract metabolite IDs from text fields

**Chemistry Operations** (`entities/chemistry/`):
- **CHEMISTRY_EXTRACT_LOINC**: Extract LOINC codes from clinical data
- **CHEMISTRY_FUZZY_TEST_MATCH**: Fuzzy matching for clinical test names

**Analysis & Reporting:**
- **CALCULATE_SET_OVERLAP**: Calculate Jaccard similarity between datasets
- **CALCULATE_THREE_WAY_OVERLAP**: Three-way dataset comparison
- **CALCULATE_MAPPING_QUALITY**: Assess mapping quality metrics

The self-registering action system using `@register_action("ACTION_NAME")` decorators allows easy development of new actions.

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
# Check CLI installation
poetry run biomapper health

# Test core imports
poetry run biomapper test-import

# Check API health (if API server is running)
curl http://localhost:8000/api/health

# View API documentation
open http://localhost:8000/api/docs

# Run tests with coverage
poetry run pytest --cov=biomapper

# Run quick unit tests only
poetry run pytest tests/unit/
```

## Next Steps

- See [Configuration Guide](../configuration.rst) for detailed strategy syntax
- Check [Action Reference](../actions/) for complete parameter documentation
- View [API Documentation](../api/) for REST endpoint details
- Try the [First Mapping Tutorial](first_mapping.rst) for a complete example

---
## Verification Sources
*Last verified: 2025-01-17*

This documentation was verified against the following project resources:

- `/biomapper/src/api/main.py` (FastAPI server configuration with /api/docs endpoint)
- `/biomapper/src/actions/registry.py` (ACTION_REGISTRY and @register_action decorator)
- `/biomapper/src/client/client_v2.py` (BiomapperClient with run() and execute_strategy() methods)
- `/biomapper/src/cli/minimal.py` (biomapper CLI commands: health, test-import, strategies)
- `/biomapper/src/configs/strategies/` (strategy YAML files location)
- `/biomapper/pyproject.toml` (Python 3.11+ requirement, repository URL, CLI script definition)
- `/biomapper/CLAUDE.md` (essential commands and project conventions)