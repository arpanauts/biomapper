# Biomapper

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Overview

**Biomapper** is a streamlined Python framework for biological data harmonization and ontology mapping. Built around YAML-based strategies and MVP action types, it provides flexible workflows for mapping biological entities like proteins, metabolites, and genes.

### Problem it Solves

Biological research often faces significant challenges in data integration:
- **Data Silos**: Biological data is scattered across numerous databases with different identifier systems
- **Identifier Ambiguity**: The same biological entity may have multiple identifiers across different databases
- **Manual Mapping**: Time-consuming and error-prone manual mapping processes
- **Reproducibility Issues**: Difficulty reproducing and sharing mapping workflows

## Key Features

- **🔧 YAML Strategy Configuration**: Define mapping workflows using simple YAML files
- **🎯 MVP Action Types**: Three core actions handle most mapping scenarios
- **🌐 API-First Design**: REST API for executing strategies remotely  
- **📊 Multi-Dataset Support**: Load and compare data from multiple biological sources
- **🔒 Type Safety**: Pydantic models ensure data validation throughout
- **⏱️ Performance Tracking**: Built-in timing metrics for benchmarking

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/biomapper.git
cd biomapper

# Install dependencies
poetry install --with dev,docs,api

# Activate the environment
poetry shell
```

### Start the API Server

```bash
cd biomapper-api
poetry run uvicorn main:app --reload
```

### Your First Mapping

1. Create a strategy file `my_mapping.yaml`:

```yaml
name: "BASIC_PROTEIN_MAPPING"
description: "Load and analyze protein data"

steps:
  - name: load_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/path/to/proteins.csv"
        identifier_column: "uniprot"
        output_key: "proteins"
```

2. Execute using Python:

```python
import asyncio
from biomapper_client import BiomapperClient

async def main():
    async with BiomapperClient() as client:
        result = await client.execute_strategy_file("my_mapping.yaml")
        print(f"Loaded {result['results']['proteins']['count']} proteins")

asyncio.run(main())
```

## MVP Actions

Biomapper provides three core action types:

### LOAD_DATASET_IDENTIFIERS
Load identifiers from CSV/TSV files with flexible column mapping.

### MERGE_WITH_UNIPROT_RESOLUTION  
Merge datasets with historical UniProt identifier resolution.

### CALCULATE_SET_OVERLAP
Calculate overlap statistics and generate Venn diagrams.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  Client Script  │    │  Python Client  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────┬───────────────┘
                 │ HTTP requests
                 ▼
          ┌─────────────────┐
          │   REST API      │
          │   (FastAPI)     │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ YAML Strategy   │
          │ Execution       │  
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ MVP Actions     │
          │ Registry        │
          └─────────────────┘
```

## Example Use Cases

### Protein Dataset Comparison
Compare protein coverage between UK Biobank and Human Protein Atlas:

```yaml
name: "UKBB_HPA_COMPARISON"
description: "Compare UKBB and HPA protein datasets"

steps:
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/UKBB_Protein_Meta.tsv" 
        identifier_column: "UniProt"
        output_key: "ukbb_proteins"
  
  - name: load_hpa
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/hpa_osps.csv"
        identifier_column: "uniprot" 
        output_key: "hpa_proteins"
  
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset_a_key: "ukbb_proteins"
        dataset_b_key: "hpa_proteins"
        output_key: "overlap_analysis"
```

### Multi-Dataset Analysis
Analyze overlaps across multiple biological databases:

```yaml
name: "MULTI_DATASET_ANALYSIS"
description: "Compare proteins across Arivale, QIN, and KG2C"

steps:
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/arivale/proteomics_metadata.tsv"
        identifier_column: "uniprot"
        output_key: "arivale_proteins"
  
  - name: load_qin
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/qin_osps.csv" 
        identifier_column: "uniprot"
        output_key: "qin_proteins"
        
  - name: arivale_vs_qin
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset_a_key: "arivale_proteins"
        dataset_b_key: "qin_proteins"
        output_key: "arivale_qin_overlap"
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/core/strategy_actions/test_load_dataset_identifiers.py

# Run with coverage
poetry run pytest --cov=biomapper
```

### Code Quality

```bash
# Linting
poetry run ruff check .
poetry run ruff format .

# Type checking  
poetry run mypy biomapper biomapper-api biomapper_client
```

### API Development

```bash
# Start API server with auto-reload
cd biomapper-api
poetry run uvicorn main:app --reload

# Access interactive docs
# http://localhost:8000/docs
```

## Configuration

### Strategy Files
Strategies are defined in YAML files in the `configs/` directory:

```
configs/
├── ukbb_hpa_mapping.yaml
├── arivale_qin_mapping.yaml  
├── kg2c_spoke_mapping.yaml
└── multi_dataset_analysis.yaml
```

### Data Requirements
- CSV/TSV files with headers
- Identifier columns (UniProt, gene symbols, etc.)
- UTF-8 encoding
- Absolute file paths in strategy configurations

## Documentation

Comprehensive documentation is available at [ReadTheDocs](https://biomapper.readthedocs.io/):

- **Getting Started**: Installation and first mapping tutorial
- **User Guide**: Detailed usage patterns and examples  
- **API Reference**: Complete REST endpoint documentation
- **Action Reference**: Detailed parameter documentation for each MVP action
- **Architecture**: System design and component overview

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite: `poetry run pytest`
5. Submit a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/biomapper.git
cd biomapper

# Install with development dependencies
poetry install --with dev,docs,api

# Install pre-commit hooks (optional)
pre-commit install
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: https://biomapper.readthedocs.io/
- **Issues**: https://github.com/your-org/biomapper/issues
- **Discussions**: https://github.com/your-org/biomapper/discussions