# MetaMapper Database CLI

## Overview

A comprehensive command-line interface for managing and querying the metamapper.db configuration database. This tool provides essential functionality for inspecting mapping resources, discovering mapping paths, and validating client implementations.

## Problem Statement

The metamapper database contains critical configuration data for biological entity mapping, including mapping resources, paths, and ontology relationships. Previously, there was no convenient way to query this database, validate configurations, or discover available mapping paths without writing custom scripts.

## Solution

Implemented a full-featured CLI tool with the following capabilities:
- List and inspect mapping resources with detailed configuration information
- Discover mapping paths between different ontology types
- Validate client class implementations
- Support for both human-readable and JSON output formats
- Async database operations for optimal performance

## Key Components

- **Main CLI Module**: `/home/ubuntu/biomapper/biomapper/cli/metamapper_db_cli.py`
- **Test Suite**: `/home/ubuntu/biomapper/tests/cli/test_metamapper_db_cli.py`
- **Database Population Script**: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`

## Technical Details

### Command Structure
```
biomapper metamapper-db
├── resources
│   ├── list [--json] [--detailed]
│   └── show <resource_name> [--json]
├── paths
│   └── find --from <source> --to <target> [--json]
└── validate
    └── clients [--json]
```

### Key Features
- Async SQLAlchemy session management
- Modular command organization using Click
- Comprehensive error handling
- Dual output modes (human-readable and JSON)
- Integration with existing biomapper CLI infrastructure

## Usage Examples

```bash
# Set the database path
export METAMAPPER_DB_URL="sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db"

# List all mapping resources
poetry run python -m biomapper.cli.main metamapper-db resources list

# Find mapping paths
poetry run python -m biomapper.cli.main metamapper-db paths find --from UNIPROTKB_AC --to ARIVALE_PROTEIN_ID

# Validate client implementations
poetry run python -m biomapper.cli.main metamapper-db validate clients
```

## Implementation Date

May 23, 2025

## Status

Completed and tested successfully