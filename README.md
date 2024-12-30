# biomapper

A unified Python toolkit for biological data harmonization and ontology mapping. `biomapper` provides a single interface for standardizing identifiers and mapping between various biological ontologies, making multi-omic data integration more accessible and reproducible.

## Features

### Core Functionality
- **ID Standardization**: Unified interface for standardizing biological identifiers
- **Ontology Mapping**: Comprehensive ontology mapping using major biological databases and AI-powered techniques
- **Data Validation**: Robust validation of input data and mappings
- **Extensible Architecture**: Easy integration of new data sources and mapping services

### Supported Systems

#### ID Standardization Tools
- RaMP-DB: Integration with the Rapid Mapping Database for metabolites and pathways

#### Mapping Services
- ChEBI: Chemical Entities of Biological Interest database integration
- UniChem: Cross-referencing of chemical structure identifiers
- UniProt: Protein-focused mapping capabilities
- RefMet: Reference list of metabolite names and identifiers
- RAG-Based Mapping: AI-powered mapping using Retrieval Augmented Generation
- Multi-Provider RAG: Combining multiple data sources for improved mapping accuracy

## Installation

### Using pip
```bash
pip install biomapper
```

### Development Setup

1. Install Python 3.11 with pyenv (if not already installed):
```bash
# Install pyenv dependencies
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl

# Install pyenv
curl https://pyenv.run | bash

# Add to your shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# Reload shell configuration
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.7
pyenv local 3.11.7
```

2. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

3. Clone and set up the project:
```bash
git clone https://github.com/yourusername/biomapper.git
cd biomapper

# Install dependencies with Poetry
poetry install
```

## Quick Start

```python
from biomapper.mapping import UniProtFocusedMapper, MetaboliteNameMapper
from biomapper.standardization import RaMPClient

# Example 1: Using UniProt-focused mapping
uniprot_mapper = UniProtFocusedMapper()
protein_mapping = uniprot_mapper.map_identifier("P12345")

# Example 2: Using Metabolite Name Mapping
metabolite_mapper = MetaboliteNameMapper()
metabolite_mapping = metabolite_mapper.map_name("glucose")

# Example 3: Using RaMP-DB
# Initialize the RaMP client
ramp_client = RaMPClient()

# Get database versions
versions = ramp_client.get_source_versions()

# Get pathways for metabolites
# Example: Get pathways for Creatine (HMDB0000064)
pathways = ramp_client.get_pathways_from_analytes(["hmdb:HMDB0000064"])

# Example 4: Using RAG-based mapping
from biomapper.mapping import RagMapper

rag_mapper = RagMapper()
rag_results = rag_mapper.map_name("alpha-D-glucose")
```

## Development

### Using Poetry

```bash
# Activate virtual environment
poetry shell

# Run a command in the virtual environment
poetry run python script.py

# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show currently installed packages
poetry show

# Build the package
poetry build
```

### Running Tests
```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=biomapper
```

### Code Quality
```bash
# Format code with black
poetry run black .

# Run linting
poetry run flake8 .

# Type checking
poetry run mypy .
```

## Project Structure

```
biomapper/
├── biomapper/           # Main package directory
│   ├── core/           # Core functionality
│   │   ├── metadata.py # Metadata handling
│   │   └── validators.py # Data validation
│   ├── standardization/# ID standardization components
│   ├── mapping/        # Ontology mapping components
│   ├── utils/          # Utility functions
│   └── schemas/        # Data schemas and models
├── tests/              # Test files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── pyproject.toml      # Poetry configuration and dependencies
└── poetry.lock        # Lock file for dependencies
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub issue tracker.

## Roadmap

- [x] Initial release with core functionality
- [x] Implement RAG-based mapping capabilities
- [x] Add support for major chemical/biological databases (ChEBI, UniChem, UniProt)
- [ ] Add caching layer for improved performance
- [ ] Expand RAG capabilities with more specialized models
- [ ] Add batch processing capabilities
- [ ] Develop REST API interface

## Acknowledgments

- [RaMP-DB](http://rampdb.org/)
- [ChEBI](https://www.ebi.ac.uk/chebi/)
- [UniChem](https://www.ebi.ac.uk/unichem/)
- [UniProt](https://www.uniprot.org/)
- [RefMet](https://refmet.metabolomicsworkbench.org/)