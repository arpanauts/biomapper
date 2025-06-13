# Biomapper Configuration Schemas

This directory contains modular configuration schemas for the Biomapper project, organized by concern to improve maintainability and clarity.

## Structure

### Entity-Specific Configurations
- `protein_config.yaml` - Main protein entity configuration (ontologies, databases, mapping paths)
- `protein_mapping_strategies.yaml` - YAML-based multi-step mapping pipelines for proteins

### Future Files (as needed)
- `metabolite_config.yaml` - Metabolite entity configuration
- `metabolite_mapping_strategies.yaml` - Metabolite mapping strategies
- `clinical_lab_config.yaml` - Clinical lab entity configuration
- etc.

## Configuration Components

### Main Entity Config (e.g., `protein_config.yaml`)
Contains:
- **ontologies**: Definitions of all ontology types for the entity
- **databases**: Database endpoints and their mapping clients
- **mapping_paths**: Direct mapping paths between ontologies
- **ontology_preferences**: Preferences for iterative mapping strategy
- **additional_resources**: External API clients and resources
- **cross_entity_references**: References to other entity types

### Mapping Strategies (e.g., `protein_mapping_strategies.yaml`)
Contains:
- **mapping_strategies**: Complex multi-step mapping pipelines
  - Each strategy defines a sequence of actions
  - Actions include conversions, filtering, API calls, etc.
  - Used by the YAML strategy executor

## Usage

These configuration files are loaded by the Biomapper system to:
1. Define available ontologies and their relationships
2. Configure database connections and mapping clients
3. Specify mapping paths and strategies
4. Guide the iterative mapping algorithm

## Maintenance

When adding new entities or mapping strategies:
1. Create appropriate config files following the existing patterns
2. Ensure all ontology types are properly defined
3. Document complex mapping strategies with clear descriptions
4. Test configurations with the mapping executor