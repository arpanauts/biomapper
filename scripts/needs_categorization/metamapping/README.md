# Metamapping Test Scripts

This directory contains scripts for testing and developing the metamapping functionality in Biomapper.

## Available Scripts

### test_relationship_mapping.py

Tests the complete metamapping workflow between MetabolitesCSV and SPOKE endpoints:

1. Creates an endpoint relationship
2. Discovers and saves mapping paths
3. Tests property extraction with health monitoring
4. Executes mappings using sample data

**Usage:**
```
./test_relationship_mapping.py
```

## CLI Commands

Biomapper also provides CLI commands for working with metamapping:

```bash
# Create a relationship between endpoints
python -m biomapper.cli.metamapper_commands create-relationship --name "MetabolitesToSPOKE" --source 7 --target 8

# List all relationships
python -m biomapper.cli.metamapper_commands list-relationships

# Discover mapping paths
python -m biomapper.cli.metamapper_commands discover-paths --source 7 --target 8

# List all mapping paths
python -m biomapper.cli.metamapper_commands list-paths

# Test mapping a specific identifier
python -m biomapper.cli.metamapper_commands test-map --source-id "HMDB0000001" --source-type "hmdb" --target-type "chebi"

# Execute relationship mapping with sample data
python -m biomapper.cli.metamapper_commands map-relationship --relationship-id 1
```

## Integration with Health Monitoring

The metamapping tests leverage the health monitoring system to track property extraction success rates and provide insights into any configuration issues.