# Biomapper

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Overview / Introduction

**Biomapper** is a unified Python toolkit for biological data harmonization and ontology mapping. It provides a flexible, configuration-driven framework for mapping and integrating diverse biological entity identifiers from various data sources.

### Problem it Solves

Biological research often faces significant challenges in data integration:
- **Data Silos**: Biological data is scattered across numerous databases with different identifier systems
- **Identifier Ambiguity**: The same biological entity may have multiple identifiers across different databases
- **Lack of Standardized Tools**: Few tools exist that provide a comprehensive, extensible framework for biological entity mapping
- **Reproducibility Issues**: Manual mapping processes are error-prone and difficult to reproduce

### Key Goals

- **Standardize and automate** the mapping of biological entities across different databases and ontologies
- **Provide a flexible and extensible system** for defining complex mapping strategies through configuration
- **Enable robust and reproducible** mapping pipelines with features like checkpointing and retry logic
- **Facilitate integration** of disparate biological datasets for comprehensive analysis

## Key Features

- **🔧 Configuration-Driven**: Define data sources, ontologies, clients, and mapping strategies using intuitive YAML configurations
- **🏗️ Modular Architecture**: Built on core components like `MappingExecutor`, `StrategyHandler`, `ActionLoader`, and customizable `StrategyAction`s
- **🔌 Extensible**: Easily add custom data sources, clients, and mapping actions to support new biological databases
- **💪 Robustness**: Built-in checkpointing, retry logic, and batch processing for handling large-scale mapping operations
- **🗄️ Database Integration**: Uses `metamapper.db` for storing configurations, metadata, and mapping relationships
- **🧬 Multiple Entity Types**: Support for various biological entities including:
  - Proteins (UniProt, HPA, UKBB)
  - Metabolites (ChEBI, PubChem)
  - Genes (HGNC, Ensembl)
  - And more through extensible architecture
- **🤖 AI-Enhanced Mapping**: Integration with LLMs (OpenAI, Anthropic) and RAG systems for intelligent entity resolution
- **🔍 Semantic Search**: Vector database integration (ChromaDB, Qdrant, FAISS) for similarity-based mapping

## Getting Started

### Prerequisites

- **Python 3.11 or higher**
- **Poetry** (for dependency management)
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/arpanauts/biomapper.git
   cd biomapper
   ```

2. **Set up a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies using Poetry**:
   ```bash
   pip install poetry
   poetry install
   ```

   Or install with optional API extras:
   ```bash
   poetry install --extras api
   ```

### Initial Configuration

1. **Set up environment variables**:
   ```bash
   cp .env.example .env  # If example exists, or create a new .env file
   ```

   Add essential environment variables:
   ```bash
   # Data directories
   DATA_DIR=/home/ubuntu/biomapper/data
   OUTPUT_DIR=/home/ubuntu/biomapper/output
   
   # API Keys (if using AI-enhanced mapping)
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

2. **Initialize the metadata database**:
   ```bash
   python scripts/setup_and_configuration/populate_metamapper_db.py
   ```
   This command reads all configuration files from `configs/*.yaml` and populates the metadata database.

### Running an Example Pipeline

Run the UKBB to HPA protein mapping pipeline:
```bash
python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
```

This example:
- Maps proteins from the UK Biobank (UKBB) dataset to Human Protein Atlas (HPA) identifiers
- Demonstrates checkpointing and batch processing capabilities
- Saves results to `data/results/ukbb_hpa_mapping_results_YYYYMMDD_HHMMSS.csv`

## Project Structure

```
biomapper/
├── biomapper/              # Core library code
│   ├── core/              # Main executor, handlers, and actions
│   │   ├── mapping_executor.py
│   │   ├── strategy_handler.py
│   │   └── strategy_actions/
│   ├── config_loader/     # YAML parsing and validation
│   ├── db/               # Database models and session management
│   ├── mapping_clients/  # Clients for accessing data sources
│   ├── rag/             # RAG (Retrieval Augmented Generation) components
│   └── utils/           # Utility functions
├── configs/             # YAML configuration files
│   ├── protein_config.yaml
│   └── mapping_strategies_config.yaml
├── data/               # Input data files (not tracked in git)
├── docs/               # Project documentation
├── notebooks/          # Jupyter notebooks for examples and analysis
├── output/             # Pipeline output directory (not tracked in git)
├── scripts/            # Helper and pipeline scripts
│   ├── main_pipelines/
│   └── setup_and_configuration/
├── tests/              # Unit and integration tests
├── roadmap/            # Project planning and development notes
├── pyproject.toml      # Project dependencies and metadata
└── LICENSE            # Apache 2.0 license
```

## Usage

### Configuring Data Sources

Add new data sources by creating YAML configuration files in the `configs/` directory:

```yaml
# Example: configs/my_protein_db_config.yaml
protein:
  my_protein_db:
    name: "My Protein Database"
    url: "https://api.myproteindb.org"
    id_types:
      - my_protein_id
      - my_accession
```

### Defining Mapping Strategies

Create mapping strategies in `configs/mapping_strategies_config.yaml`:

```yaml
strategies:
  my_mapping_strategy:
    description: "Maps identifiers from source to target database"
    actions:
      - action_type: "FetchFromSource"
        params:
          source: "my_protein_db"
      - action_type: "MapIdentifiers"
        params:
          target: "uniprot"
      - action_type: "ValidateResults"
```

### Running Pipelines

Execute mapping strategies using the main pipeline scripts:

```python
# Example pipeline script
from biomapper.core import MappingExecutor

executor = MappingExecutor()
results = executor.execute_strategy(
    strategy_name="my_mapping_strategy",
    input_data=my_data,
    checkpoint_enabled=True
)
```

### Using the CLI

After installation, use the `biomapper` CLI tool:

```bash
# Check system health
biomapper health check

# Populate metadata database
biomapper metamapper populate

# List available strategies
biomapper metadata list-strategies
```

## Contributing

We welcome contributions to the Biomapper project! Here's how you can help:

### Contribution Guidelines

1. **Report bugs or suggest features**:
   - Use [GitHub Issues](https://github.com/arpanauts/biomapper/issues) to report bugs or request features
   - Provide clear descriptions and reproducible examples

2. **Code contributions**:
   - Fork the repository and create a feature branch
   - Follow PEP 8 coding standards
   - Add docstrings to all functions and classes
   - Include type hints for better code clarity
   - Write tests for all new functionality
   - Submit a pull request with a clear description of changes

3. **Development setup**:
   ```bash
   # Install development dependencies
   poetry install --with dev
   
   # Run tests
   pytest
   
   # Run linting
   flake8 biomapper/
   black biomapper/ --check
   ```

### Areas for Contribution

- **New StrategyActions**: Implement actions for additional mapping logic
- **Database Clients**: Add support for new biological databases
- **Documentation**: Improve documentation and add tutorials
- **Test Coverage**: Expand test cases for existing functionality
- **Performance**: Optimize mapping algorithms for large datasets
- **Visualization**: Create tools for visualizing mapping results

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

Biomapper builds upon the collective efforts of the biological data community and integrates with numerous public databases including:
- UniProt
- Human Protein Atlas (HPA)
- ChEBI
- PubChem
- HGNC
- And many others

Special thanks to all contributors and the open-source community for making this project possible.

## Contact / Support

- **Issues**: [GitHub Issues](https://github.com/arpanauts/biomapper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/arpanauts/biomapper/discussions)
- **Email**: [Contact maintainers](mailto:biomapper@arpanauts.com)