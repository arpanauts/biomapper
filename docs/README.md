# Biomapper Documentation

This directory contains the complete documentation for the Biomapper biological data harmonization framework.

## Documentation Structure

The documentation is built using Sphinx and located in `/source/`:

### Core Documentation
- **Getting Started**: `source/guides/` - Installation, quickstart, and first mapping tutorial
- **Actions Reference**: `source/actions/` - Complete documentation for foundational actions
- **API Documentation**: `source/api/` - REST API endpoints and usage
- **Architecture**: `source/architecture/` - System design and extensible action architecture

### Building Documentation
```bash
# Install dependencies
pip install -r requirements.txt

# Build HTML documentation  
make html

# View documentation
open build/html/index.html
```

## Architecture Overview

Biomapper uses an **extensible action-based architecture**:

### Foundational Actions
- `LOAD_DATASET_IDENTIFIERS` - Load data from CSV/TSV files
- `MERGE_WITH_UNIPROT_RESOLUTION` - Merge datasets with historical UniProt ID resolution
- `CALCULATE_SET_OVERLAP` - Calculate overlap statistics and generate Venn diagrams

### Key Design Principles
- **Extensible**: New specialized actions can be easily added to support sophisticated mapping approaches
- **Configuration-Driven**: YAML strategies define workflows without coding
- **Type-Safe**: Pydantic models ensure validation throughout
- **API-First**: REST API for strategy execution with async Python client

## Directory Structure

```
docs/
├── source/           # Complete Sphinx documentation
│   ├── guides/       # Getting started and tutorials
│   ├── actions/      # Action reference documentation
│   ├── api/          # API documentation
│   └── architecture/ # System architecture and design
├── build/            # Built documentation output
├── Makefile         # Sphinx build configuration
└── requirements.txt # Documentation dependencies
```

## Quick Links

- **[Getting Started Guide](source/guides/getting_started.md)** - Start here for basic usage
- **[First Mapping Tutorial](source/guides/first_mapping.rst)** - Complete step-by-step example
- **[Action System Architecture](source/architecture/action_system.rst)** - Learn about extensible actions
- **[API Documentation](source/api/rest_endpoints.rst)** - REST API reference