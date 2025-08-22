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
├── source/           # Sphinx documentation source
│   ├── guides/       # Getting started and tutorials
│   ├── actions/      # Action reference documentation
│   ├── api/          # API documentation
│   └── architecture/ # System architecture and design
├── guides/           # User and developer guides
│   ├── API setup and usage guides
│   └── Integration guides (Google Drive, OAuth2)
├── frameworks/       # Framework and architecture docs
│   ├── Framework Triad architecture
│   └── Surgical framework patterns
├── workflows/        # Complete workflow implementations
│   ├── Metabolomics pipelines
│   └── Protein mapping strategies
├── reports/          # Validation and analysis reports
│   ├── Test execution results
│   ├── Coverage analysis
│   └── Feasibility studies
├── integrations/     # External service integrations
│   └── LIPID MAPS, HMDB, UniProt, etc.
├── planning/         # Development plans and strategies
│   └── Fix plans and migration strategies
├── build/            # Built documentation output (gitignored)
├── Makefile         # Sphinx build configuration
└── requirements.txt # Documentation dependencies
```

## Quick Navigation

### For New Users
- Start with [Getting Started Guide](source/guides/getting_started.md)
- Review [Workflow Examples](workflows/)
- Check [Integration Guides](guides/) for external services

### For Developers
- [Architecture Documentation](frameworks/)
- [Action Development](source/actions/)
- [API Reference](guides/API_METHODS.md)

### For Data Scientists
- [Metabolomics Workflows](workflows/)
- [Protein Mapping Strategies](workflows/protein_mapping_strategy.md)
- [Validation Reports](reports/) for performance metrics

## Quick Links

- **[Getting Started Guide](source/guides/getting_started.md)** - Start here for basic usage
- **[First Mapping Tutorial](source/guides/first_mapping.rst)** - Complete step-by-step example
- **[Action System Architecture](source/architecture/action_system.rst)** - Learn about extensible actions
- **[API Documentation](source/api/rest_endpoints.rst)** - REST API reference