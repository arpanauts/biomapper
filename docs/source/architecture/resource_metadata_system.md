# Resource Metadata System

## Overview

The Resource Metadata System is a core architectural component of Biomapper that orchestrates mapping operations across multiple resources. It intelligently routes queries to the most appropriate resources based on capabilities, performance metrics, and availability.

This system makes Biomapper highly adaptable and resilient, allowing it to work effectively with or without specific resources (such as proprietary knowledge graphs like SPOKE). It enables consistent performance even when individual resources are unavailable or underperforming.

## Key Components

### ResourceMetadataManager

The ResourceMetadataManager is responsible for:

- Registering and tracking available resources
- Recording ontology coverage for each resource
- Collecting and analyzing performance metrics
- Providing prioritized lists of resources for operations

```python
# Example: Registering a resource
metadata_manager = ResourceMetadataManager()
metadata_manager.register_resource(
    name="sqlite_cache",
    resource_type="cache",
    connection_info={"db_path": "/path/to/cache.db"},
    priority=10
)
```

### MappingDispatcher

The MappingDispatcher orchestrates mapping operations by:

- Routing requests to the most appropriate resources
- Implementing fallback strategies when preferred resources fail
- Collecting performance metrics to optimize future routing decisions
- Updating the cache with newly discovered mappings

```python
# Example: Performing a mapping operation
dispatcher = MappingDispatcher(metadata_manager)
results = await dispatcher.map_entity(
    source_id="glucose",
    source_type="compound_name",
    target_type="chebi"
)
```

### ResourceAdapter Interface

The ResourceAdapter interface provides a unified API for interacting with different types of resources:

- SQLite mapping cache
- Knowledge graphs (SPOKE, Neo4j, ArangoDB)
- External APIs (ChEBI, RefMet, UniChem)
- Custom data sources

Each adapter translates the common interface into operations specific to its resource.

```python
# Example: Implementing a resource adapter
class MyResourceAdapter(BaseResourceAdapter):
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        # Implementation specific to this resource
        pass
```

### KnowledgeGraphClient Interface

The KnowledgeGraphClient interface standardizes interactions with graph databases:

- Provides consistent access to different graph database implementations
- Abstracts away differences in query languages and data models
- Enables seamless integration of multiple knowledge graphs

### MetamappingEngine

The MetamappingEngine enables multi-step mappings when no direct path exists between ontologies:

- Discovers paths between ontology types using a breadth-first search algorithm
- Executes mapping operations along the discovered path
- Combines and propagates confidence scores across multiple steps
- Caches both intermediate and complete mapping results

```python
# Example: Finding and executing a multi-step mapping path
metamapping_engine = MetamappingEngine(dispatcher)

# Find a path from PubChem to HMDB
path = await metamapping_engine.find_mapping_path("pubchem", "hmdb")

# Execute the path for a specific compound
results = await metamapping_engine.execute_mapping_path(
    source_id="CID123456",
    mapping_path=path
)
```

#### Breadth-First Search (BFS) Algorithm

The metamapping engine uses the BFS algorithm to find the shortest path between two ontology types:

```python
# Simplified BFS implementation for path discovery
def find_mapping_path(source_type, target_type):
    # Queue for BFS, each entry contains (current_type, path_so_far)
    queue = deque([(source_type, [])])
    visited = {source_type}  # Track visited ontology types
    
    while queue:
        current_type, path = queue.popleft()
        
        # Check if we've reached the target
        if current_type == target_type and path:
            return path
        
        # Find all possible next steps
        for next_type in metadata_manager.get_all_ontology_types():
            if next_type in visited:
                continue
                
            # Check if there's a resource that can perform this mapping step
            resources = metadata_manager.find_resources_by_capability(
                source_type=current_type,
                target_type=next_type
            )
            
            if resources:
                # Add this step to the path
                new_path = path + [{
                    "source_type": current_type,
                    "target_type": next_type,
                    "resources": resources
                }]
                
                # If we've reached the target, return the path
                if next_type == target_type:
                    return new_path
                
                # Otherwise, add to queue for further exploration
                queue.append((next_type, new_path))
                visited.add(next_type)
    
    # No path found
    return None
```

This algorithm ensures that:

1. The shortest path (fewest steps) is always found first
2. Cycles are avoided by tracking visited ontology types
3. Only paths with available resources are considered
4. The search space is efficiently explored

## Database Interactions

The Resource Metadata System interacts with SQLite databases in two key ways:

### 1. Metadata Database

Used to store and retrieve information about resources, their capabilities, and performance:

- **Resource registration**: Stores resource information and capabilities
- **Capability queries**: Finds resources that can perform specific mappings
- **Performance metrics**: Tracks success rates and response times
- **Ontology coverage**: Records which ontologies each resource supports

The `ResourceMetadataManager` provides an interface to this database, abstracting the underlying SQL operations:

```python
# Example: Using the metadata database
with metadata_manager:
    # Find resources that can map from ChEBI to HMDB
    resources = metadata_manager.find_resources_by_capability(
        source_type="chebi",
        target_type="hmdb"
    )
    
    # Record performance for a mapping operation
    metadata_manager.record_performance(
        resource_name="unichem_api",
        operation_type="map",
        source_type="chebi",
        target_type="hmdb",
        success=True,
        response_time=235  # milliseconds
    )
```

### 2. Mapping Cache Database

Stores the results of mapping operations to avoid redundant external API calls:

- **Lookup**: Checks if a mapping has been previously performed
- **Storage**: Saves results from successful mappings
- **Metamapping cache**: Stores both intermediate and complete path results

The `CacheResourceAdapter` provides access to this database:

```python
# Example: Interacting with the mapping cache
cache_adapter = CacheResourceAdapter(config)

# Check cache for existing mapping
results = await cache_adapter.map_entity(
    source_id="CHEBI:15377",
    source_type="chebi",
    target_type="hmdb"
)

# Store new mapping in cache
await cache_adapter.store_mapping(
    source_id="CHEBI:15377",
    source_type="chebi",
    target_id="HMDB0000122",
    target_type="hmdb",
    confidence=1.0,
    metadata={"source": "unichem_api"}
)
```

## Database Schema

The system uses a SQLite database with these core tables:

1. **resource_metadata**: Stores information about available resources
2. **ontology_coverage**: Tracks which ontologies each resource supports
3. **performance_metrics**: Records timing and success rates for operations
4. **operation_logs**: Maintains a history of mapping operations for analysis

## Workflow

### Initialization

The Resource Metadata System is initialized once during setup:

```python
# Initialize the database schema
initialize_metadata_system("/path/to/metadata.db")
```

### Registration

Resources are registered with their capabilities and connection information:

```python
# Register a resource
metadata_manager.register_resource(name="my_resource", ...)

# Register ontology coverage
metadata_manager.register_ontology_coverage(
    resource_name="my_resource",
    ontology_type="chebi",
    support_level="full"
)
```

### Operations

Mapping operations are performed through the dispatcher:

```python
# Map an entity
results = await dispatcher.map_entity(
    source_id="glucose",
    source_type="compound_name",
    target_type="chebi"
)
```

The dispatcher handles all the complexity of:
1. Determining which resources to query
2. Trying resources in priority order
3. Handling failures and timeouts
4. Updating the cache with new mappings

### Performance Monitoring

The system continuously monitors performance:

```python
# Get performance metrics for resources
metrics = metadata_manager.get_performance_summary()
```

These metrics can be used to:
- Adjust resource priorities
- Identify problematic resources
- Optimize the system configuration

## Command-Line Interface

The system includes a CLI for management tasks:

```bash
# Initialize the metadata system
biomapper metadata init

# Register resources from a configuration file
biomapper metadata register --config-file=resources.yaml

# List registered resources
biomapper metadata list

# Show performance statistics
biomapper metadata stats
```

## Configuration

Resources are configured using YAML or JSON files:

```yaml
resources:
  sqlite_cache:
    type: cache
    connection_info:
      data_dir: ~/.biomapper/data
      db_name: mappings.db
    priority: 10
    ontologies:
      chebi:
        support_level: full
      hmdb:
        support_level: full
```

## Integration

### With Existing Mappers

The Resource Metadata System integrates with existing mappers:

```python
class MetaboliteNameMapper:
    def __init__(self):
        self.metadata_manager = ResourceMetadataManager()
        self.dispatcher = MappingDispatcher(self.metadata_manager)
        
    async def map_name_to_chebi(self, metabolite_name):
        return await self.dispatcher.map_entity(
            source_id=metabolite_name,
            source_type="compound_name",
            target_type="chebi"
        )
```

### With Web UI

The system provides REST endpoints for the web UI:

```python
@app.get("/api/resources")
async def list_resources():
    with ResourceMetadataManager() as manager:
        return manager.get_resources_by_priority()

@app.post("/api/map")
async def map_entity(request: MapRequest):
    dispatcher = MappingDispatcher(ResourceMetadataManager())
    return await dispatcher.map_entity(
        request.source_id, 
        request.source_type, 
        request.target_type
    )
```

## Benefits

The Resource Metadata System provides several key benefits:

1. **Intelligent Routing**: Automatically selects the best resource for each operation
2. **Resilience**: Continues functioning when individual resources are unavailable
3. **Performance Optimization**: Learns from past operations to improve future performance
4. **Extensibility**: New resources can be added without changing existing code
5. **Unified Interface**: Provides consistent access to diverse resources
6. **Configurability**: Resources can be configured and prioritized without code changes
7. **Transparency**: Provides visibility into performance characteristics

## Further Reading

- [Resource Metadata System Design](https://github.com/arpanauts/biomapper/blob/main/roadmap/architecture/resource_metadata_system.md)
- [Implementation Plan](https://github.com/arpanauts/biomapper/blob/main/roadmap/architecture/resource_metadata_implementation_plan.md)
- [API Reference](../api/mapping/metadata.md)
