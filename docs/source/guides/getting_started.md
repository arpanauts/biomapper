# Getting Started with Biomapper

## Installation

Biomapper requires Python 3.11 or later. Clone the repository and install using Poetry:

```bash
# Clone the repository
git clone https://github.com/your-org/biomapper.git
cd biomapper

# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install Biomapper with all dependencies
poetry install --with dev,docs,api

# Activate the virtual environment
poetry shell
```

## Basic Usage

Biomapper uses an asynchronous API. Here's a quick example of mapping biological entities:

```python
import asyncio
from biomapper.core import MappingExecutor, MappingExecutorBuilder
from biomapper.core.models import DatabaseConfig, CacheConfig

async def main():
    # Configure the executor
    db_config = DatabaseConfig(url="sqlite+aiosqlite:///data/mapping.db")
    cache_config = CacheConfig(backend="memory")
    
    # Build and initialize the executor
    executor = MappingExecutorBuilder.create(
        db_config=db_config,
        cache_config=cache_config
    )
    await executor.initialize()
    
    try:
        # Map metabolite names
        metabolites = ["glucose", "ATP", "NADH"]
        result = await executor.execute(
            entity_names=metabolites,
            entity_type="metabolite"
        )
        
        # Print results
        for mapping in result.mappings:
            print(f"{mapping.query_id} -> {mapping.mapped_id}")
            
    finally:
        # Clean up resources
        await executor.shutdown()

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
```

## Using YAML Strategies

The recommended way to use Biomapper is with YAML-defined mapping strategies:

```python
async def use_yaml_strategy():
    # Initialize executor (as shown above)
    executor = await create_executor()
    
    # Execute a predefined strategy
    result = await executor.execute_yaml_strategy(
        strategy_file="configs/strategies/metabolite_mapping.yaml",
        input_data={
            "entities": ["glucose", "fructose", "sucrose"],
            "entity_type": "metabolite"
        }
    )
    
    # Process results
    if result.success:
        for item in result.data:
            print(f"Mapped: {item}")
```

## Example YAML Strategy

Create a file `configs/strategies/metabolite_mapping.yaml`:

```yaml
name: metabolite_comprehensive_mapping
description: Map metabolite names using multiple databases
version: "1.0"
entity_type: metabolite

actions:
  - type: LOAD_INPUT_DATA
    name: load_metabolites
    config:
      source_field: entities
      
  - type: API_RESOLVER
    name: chebi_lookup
    config:
      api_endpoint: chebi
      search_fields: ["name", "synonym"]
      confidence_threshold: 0.8
      
  - type: API_RESOLVER
    name: pubchem_fallback
    config:
      api_endpoint: pubchem
      search_fields: ["name"]
      only_unmapped: true
      
  - type: SAVE_RESULTS
    name: save_mappings
    config:
      output_format: json
      include_metadata: true
```

## Command Line Interface

Biomapper also provides a CLI for common operations:

```bash
# Check system health
poetry run biomapper health

# List available strategies
poetry run biomapper metadata list

# View strategy details
poetry run biomapper metadata show metabolite_mapping

# Execute a mapping from CSV file
poetry run biomapper metamapper execute \
    --strategy metabolite_mapping \
    --input metabolites.csv \
    --output results.json
```

## Next Steps

- Review the [Usage Guide](../usage.rst) for more detailed examples
- Learn about [YAML Mapping Strategies](../tutorials/yaml_mapping_strategies.md)
- Explore available [Mapping Clients](../tutorials/name_resolution_clients.md)
- Check the [API Documentation](../api/README.md) for building web services

## Getting Help

- Check the [Documentation](https://biomapper.readthedocs.io)
- Report issues on [GitHub](https://github.com/your-org/biomapper/issues)
- Join the community discussions