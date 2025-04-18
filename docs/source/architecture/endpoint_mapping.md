# Endpoint to Endpoint Mapping System

This document explains the endpoint-to-endpoint mapping system in Biomapper, which enables mapping between different endpoints through a relationship-based approach.

## Overview

The endpoint mapping system follows a vertical integration approach with several components working together:

1. **Relationship and Endpoint Definition**:
   - Endpoints are defined with their own connection information and property configurations
   - Relationships connect endpoints and define what should be mapped (e.g., MetabolitesCSV to SPOKE)

2. **Mapping Path Discovery and Management**:
   - The `RelationshipPathFinder` discovers and stores optimal mapping paths between ontology types
   - Paths are stored in the `relationship_mapping_paths` table, linking to `mapping_paths`

3. **Mapping Execution**:
   - The `RelationshipMappingExecutor` executes discovered mapping paths
   - Single-step or multi-step mappings are supported
   - Results are cached in the `mapping_cache` table and linked through `relationship_mappings`

4. **Resource Adapters**:
   - Resources like UniChem and KEGG provide the actual mapping functionality
   - Each resource has specific capabilities defined in its `ResourceAdapter` implementation

## Database Structure

The database (`metamapper.db`) contains the following key tables:

- `endpoints`: Defines the data sources/targets (e.g., MetabolitesCSV, SPOKE)
- `endpoint_relationships`: Defines the mapping relationships between endpoints
- `endpoint_property_configs`: Defines how to extract ontology IDs from endpoints
- `mapping_paths`: Stores the available paths between ontology types
- `relationship_mapping_paths`: Links relationships to mapping paths
- `mapping_cache`: Caches mapping results
- `relationship_mappings`: Links relationships to cached mappings
- `mapping_resources`: Defines available mapping resources (UniChem, KEGG, etc.)

## Mapping Flow

The typical flow for mapping between endpoints is:

1. **Define Relationship**: Create a relationship between source and target endpoints
2. **Discover Paths**: Find viable mapping paths between ontology types
3. **Execute Mapping**: Map values using the discovered paths
4. **Cache Results**: Store successful mappings for future use

Example flow for mapping a metabolite name from MetabolitesCSV to SPOKE:

```
MetabolitesCSV Entry ("1-Methylhistidine")
↓
Extract HMDB ID ("HMDB0000001") from MetabolitesCSV
↓
Map HMDB ID to PubChem ID using UniChem (HMDB -> PubChem)
↓
Map PubChem ID to CHEBI ID using KEGG (PubChem -> CHEBI)
↓
Find SPOKE entity using CHEBI ID
↓
Return mapped SPOKE entity
```

## Components

### RelationshipPathFinder

The `RelationshipPathFinder` discovers and manages mapping paths between ontology types for a relationship:

- `discover_relationship_paths(relationship_id)`: Discovers all possible mapping paths
- `get_best_mapping_path(relationship_id, source_ontology, target_ontology)`: Gets the optimal path

### RelationshipMappingExecutor

The `RelationshipMappingExecutor` executes the mapping paths:

- `map_with_relationship(relationship_id, source_id, source_type, target_type)`: Maps using a relationship
- `map_endpoint_value(relationship_id, value, source_endpoint_id, target_endpoint_id)`: Maps from source to target endpoint
- `check_cache(source_id, source_type, target_type, relationship_id)`: Checks for cached mappings

### ResourceAdapter

Resource adapters implement the `ResourceAdapter` interface to provide mapping functionality:

- `map_id(source_id, source_type, target_type)`: Maps between ontology types
- `get_supported_mappings()`: Returns supported mapping combinations
- `get_resource_info()`: Returns information about the resource

Currently implemented adapters:
- `UniChemAdapter`: Maps between chemical identifiers using UniChem
- `KEGGAdapter`: Maps between KEGG and other ontologies

## CLI Commands

The system includes CLI commands for working with endpoint mappings:

- `python -m biomapper.cli.metamapper_commands discover-paths --relationship 1`: Discover mapping paths
- `python -m biomapper.cli.metamapper_commands map-value --relationship 1 --value "HMDB0000001" --source-type hmdb --target-type chebi`: Map a value
- `python -m biomapper.cli.metamapper_commands map-endpoint-value --relationship 1 --value "HMDB0000001"`: Map between endpoints
- `python -m biomapper.cli.metamapper_commands check-cache --source-id "HMDB0000001" --source-type hmdb --target-type chebi`: Check cache

## Testing

A test script is provided to validate the vertical integration:

```bash
python /home/ubuntu/biomapper/scripts/tests/test_relationship_mapping.py
```

This script tests:
- Relationship mapping path discovery
- Mapping execution
- Cache verification

## Future Enhancements

Planned enhancements to the system include:

1. **Performance Metrics Collection**: Collect and analyze mapping performance
2. **Adaptive Path Selection**: Dynamically select paths based on success rates
3. **Resource Fallbacks**: Try alternative resources when primary ones fail
4. **Parallel Mapping**: Execute multiple paths in parallel for faster results
5. **Health Monitoring**: Monitor and improve extraction and mapping health