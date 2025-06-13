# Biomapper Configs - AI Assistant Instructions

## Overview

This directory contains YAML configuration files that define all data sources, mappings, and strategies for the Biomapper system. These configs are loaded into `metamapper.db` and drive all mapping operations.

## Key Concepts

### 1. Configuration-Driven Architecture
- **No hardcoded paths or columns** - Everything is defined in YAML
- Scripts query `metamapper.db` for configuration at runtime
- Changes to data sources require only YAML updates, not code changes

### 2. Core Components
- **Ontologies**: Define identifier types (e.g., UniProt ACs, Gene names)
- **Databases**: Define data sources with file paths and column mappings
- **Mapping Paths**: Multi-step conversion sequences
- **Mapping Strategies**: Complex pipelines using action types
- **Action Types**: Building blocks that correspond to MappingExecutor methods

### 3. Action Types
See `/home/ubuntu/biomapper/docs/ACTION_TYPES_REFERENCE.md` for full documentation.

Current action types:
- `CONVERT_IDENTIFIERS_LOCAL` - Convert using local data files
- `EXECUTE_MAPPING_PATH` - Run a predefined mapping path
- `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` - Keep only IDs that exist in target
- `MATCH_SHARED_ONTOLOGY` - Direct matching via shared identifier type

## Important Files

- `protein_config.yaml` - Main protein configuration
- `schemas/protein_config_schema.json` - JSON schema for validation (simplified version)
- `schemas/README.md` - Explains schema purpose and design

## Current Work Context

### Recent Updates
1. Simplified the JSON schema to focus on practical validation
2. Made scripts fully configuration-driven (no hardcoded paths)
3. Created documentation for action types

### Future Considerations
1. **Separate mapping strategies** - Move strategies to their own config file for cross-entity reuse
2. **New action types** - Will be added as needed (e.g., TRANSFORM_IDENTIFIERS, MERGE_IDENTIFIER_SETS)
3. **Generic strategies** - Develop strategies that work across entity types

## Common Tasks

### Adding a New Data Source
1. Add endpoint definition under `databases` section
2. Define property mappings (column to ontology type)
3. Add any mapping clients needed
4. Run `populate_metamapper_db.py` to load changes

### Creating a New Strategy
1. Review available action types in the reference doc
2. Design the pipeline steps
3. Add strategy definition to `mapping_strategies` section
4. Test with sample data

### Debugging Configuration Issues
1. Check JSON schema validation errors
2. Verify ontology types are defined
3. Ensure referenced resources exist (mapping paths, clients)
4. Check column names match actual data files

## Best Practices

1. **Test configurations** - Always validate YAML against schema before loading
2. **Document strategies** - Include clear descriptions of what each strategy does
3. **Keep actions atomic** - Each action type should do one thing well
4. **Consider reusability** - Design for use across different datasets

## Notes on Architecture Evolution

The system is moving toward:
- Clearer separation between data configuration and logic
- More reusable components across entity types
- Better documentation of available building blocks
- Simplified maintenance through configuration-driven design