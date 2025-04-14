# Endpoint and Resource Metadata System

## Overview

The Endpoint and Resource Metadata System is a core architectural component of Biomapper that orchestrates mapping operations between endpoints using specialized mapping resources. The system distinguishes between:

- **Endpoints**: Data sources or targets (like MetabolitesCSV and SPOKE) that need to be connected through ontology mapping
- **Mapping Resources**: Tools and services (like UniChem, KEGG, and RefMet) that translate between different ontology types

The system establishes relationships between endpoints and intelligently routes mapping operations through the most appropriate resources based on capabilities, performance metrics, and availability.

This architecture makes Biomapper highly adaptable and resilient, allowing it to create complex mapping paths across multiple resources. It enables consistent performance even when individual mapping resources are unavailable or underperforming, and supports reusable mapping across different endpoint relationships.

## Key Components

### EndpointMetadataManager

The EndpointMetadataManager is responsible for:

- Registering and managing endpoints (data sources/targets)
- Creating and maintaining relationships between endpoints
- Recording ontology preferences for each endpoint
- Managing endpoint connection information

```python
# Example: Registering an endpoint
metadata_manager = EndpointMetadataManager()
endpoint_id = metadata_manager.register_endpoint(
    name="metabolites_csv",
    endpoint_type="file",
    connection_info={"file_path": "/path/to/metabolites.csv"}
)

# Example: Creating an endpoint relationship
relationship_id = metadata_manager.create_endpoint_relationship(
    name="MetabolitesCSV-to-SPOKE",
    description="Maps metabolites from CSV data to SPOKE entities"
)

# Add members to the relationship
metadata_manager.add_relationship_member(
    relationship_id=relationship_id,
    endpoint_id=1,  # MetabolitesCSV
    role="source"
)
metadata_manager.add_relationship_member(
    relationship_id=relationship_id,
    endpoint_id=2,  # SPOKE
    role="target"
)
```

### ResourceMetadataManager

The ResourceMetadataManager is responsible for:

- Registering and tracking available mapping resources
- Recording ontology coverage for each mapping resource
- Collecting and analyzing performance metrics
- Providing prioritized lists of resources for operations

```python
# Example: Registering a mapping resource
resource_manager = ResourceMetadataManager()
resource_manager.register_mapping_resource(
    name="unichem_api",
    resource_type="api",
    connection_info={"base_url": "https://www.ebi.ac.uk/unichem/"},
    priority=10
)
```

### RelationshipMappingDispatcher

The RelationshipMappingDispatcher orchestrates mapping operations within the context of endpoint relationships:

- Routing requests through optimal mapping paths based on endpoint preferences
- Implementing fallback strategies when preferred resources fail
- Collecting performance metrics to optimize future routing decisions
- Updating the cache with newly discovered mappings
- Associating mapping results with endpoint relationships

```python
# Example: Performing a mapping operation within a relationship context
dispatcher = RelationshipMappingDispatcher(endpoint_manager, resource_manager)
results = await dispatcher.map_entity_in_relationship(
    relationship_id=1,  # MetabolitesCSV-to-SPOKE relationship
    source_id="glucose",
    source_type="compound_name",
    context={"confidence_threshold": 0.8}
)
```

### ResourceAdapter Interface

The ResourceAdapter interface provides a unified API for interacting with different types of mapping resources:

- External APIs (UniChem, ChEBI, RefMet, KEGG)
- Database resources (SQLite mapping cache, RaMP DB)
- Web services (PubChem PUG REST)
- Custom mapping services

Each adapter translates the common interface into operations specific to its resource.

```python
# Example: Implementing a mapping resource adapter
class UniChemAdapter(BaseResourceAdapter):
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        # Implementation specific to UniChem API
        pass
```

### EndpointAdapter Interface

The EndpointAdapter interface provides a unified API for interacting with different types of endpoints:

- File-based data sources (CSV, Excel, JSON)
- Database endpoints (SQLite, PostgreSQL)
- Knowledge graphs (SPOKE, Neo4j, ArangoDB)
- API endpoints (REST, GraphQL)

Each adapter handles the specific operations needed to query and update its endpoint.

```python
# Example: Implementing an endpoint adapter
class SpokeAdapter(BaseEndpointAdapter):
    async def get_entity(self, entity_id, entity_type, **kwargs):
        # Implementation specific to SPOKE graph database
        pass
```

### KnowledgeGraphClient Interface

The KnowledgeGraphClient interface standardizes interactions with graph databases:

- Provides consistent access to different graph database implementations
- Abstracts away differences in query languages and data models
- Enables seamless integration of multiple knowledge graphs

### RelationshipMetamappingEngine

The RelationshipMetamappingEngine enables multi-step mappings within the context of endpoint relationships:

- Discovers optimal paths between endpoints based on ontology preferences
- Considers endpoint ontology preferences when selecting paths
- Executes mapping operations along the discovered path
- Combines and propagates confidence scores across multiple steps
- Caches both intermediate and complete mapping results
- Associates mapping results with endpoint relationships

```python
# Example: Finding and executing a mapping within a relationship
metamapping_engine = RelationshipMetamappingEngine(dispatcher, endpoint_manager)

# Find optimal path for a specific relationship
path = await metamapping_engine.find_optimal_path_for_relationship(
    relationship_id=1,  # MetabolitesCSV-to-SPOKE relationship
    source_entity_id="HMDB0000122",
    source_ontology_type="hmdb"
)

# Execute the path for a specific compound
results = await metamapping_engine.execute_relationship_mapping_path(
    source_id="HMDB0000122",
    relationship_id=1,
    mapping_path=path
)
```

#### Enhanced Breadth-First Search (BFS) Algorithm

The metamapping engine uses an enhanced BFS algorithm that considers endpoint ontology preferences when finding mapping paths:

```python
# Relationship-aware BFS implementation for path discovery
def find_optimal_path_for_relationship(relationship_id, source_ontology_type):
    # Get the relationship details
    relationship = endpoint_manager.get_relationship(relationship_id)
    source_endpoint = relationship.get_member_by_role("source")
    target_endpoint = relationship.get_member_by_role("target")
    
    # Get ontology preferences for target endpoint
    target_ontologies = endpoint_manager.get_ontology_preferences(
        endpoint_id=target_endpoint.id
    )
    
    # Queue for BFS, each entry contains (current_type, path_so_far, confidence)
    queue = deque([(source_ontology_type, [], 1.0)])
    visited = {source_ontology_type}  # Track visited ontology types
    
    # Track the best path to each ontology type
    best_paths = {}
    
    while queue:
        current_type, path, cumulative_confidence = queue.popleft()
        
        # Check if we've reached a target ontology type
        if current_type in target_ontologies:
            # Weight by target endpoint's preference level
            preference_level = endpoint_manager.get_ontology_preference_level(
                endpoint_id=target_endpoint.id,
                ontology_type=current_type
            )
            
            # Calculate a preference-weighted confidence
            weighted_confidence = cumulative_confidence * (1.0 / preference_level)
            
            # If this is the best path so far to this target ontology, save it
            if current_type not in best_paths or weighted_confidence > best_paths[current_type]["confidence"]:
                best_paths[current_type] = {
                    "path": path,
                    "confidence": weighted_confidence
                }
            
            # Continue exploring (might find better paths to other target ontologies)
        
        # Find all possible next steps
        for next_type in resource_manager.get_all_ontology_types():
            if next_type in visited:
                continue
                
            # Check if there's a resource that can perform this mapping step
            resources = resource_manager.find_resources_by_capability(
                source_type=current_type,
                target_type=next_type
            )
            
            if resources:
                # Calculate step confidence based on resource performance
                best_resource = resources[0]  # Assuming resources are sorted by performance
                step_confidence = resource_manager.get_resource_confidence(
                    resource_id=best_resource.id,
                    source_type=current_type,
                    target_type=next_type
                )
                
                # Propagate confidence
                new_confidence = cumulative_confidence * step_confidence
                
                # Add this step to the path
                new_path = path + [{
                    "source_type": current_type,
                    "target_type": next_type,
                    "resources": resources,
                    "confidence": step_confidence
                }]
                
                # Add to queue for further exploration
                queue.append((next_type, new_path, new_confidence))
                visited.add(next_type)
    
    # Return the best path among all target ontologies
    if not best_paths:
        return None
    
    # Find the highest confidence path
    best_target = max(best_paths.items(), key=lambda x: x[1]["confidence"])
    return {
        "target_ontology": best_target[0],
        "path": best_target[1]["path"],
        "confidence": best_target[1]["confidence"]
    }
```

This enhanced algorithm ensures that:

1. Endpoint ontology preferences are considered when finding paths
2. Confidence scores are propagated and weighted by preference levels
3. The algorithm finds the optimal path based on both path length and confidence
4. Multiple target ontologies are considered and ranked
5. Resource performance metrics influence path selection

## Database Interactions

The Endpoint and Resource Metadata System interacts with SQLite databases in three key ways:

### 1. Endpoint Metadata Database

Used to store and retrieve information about endpoints and their relationships:

- **Endpoint registration**: Stores endpoint information and connection details
- **Relationship management**: Creates and manages relationships between endpoints
- **Ontology preferences**: Records preferred ontology types for each endpoint
- **Relationship members**: Maps which endpoints participate in each relationship

The `EndpointMetadataManager` provides an interface to this database:

```python
# Example: Using the endpoint metadata database
with endpoint_manager:
    # Find all relationships involving a specific endpoint
    relationships = endpoint_manager.find_relationships_by_endpoint(
        endpoint_id=1  # MetabolitesCSV
    )
    
    # Set ontology preferences for an endpoint
    endpoint_manager.set_ontology_preference(
        endpoint_id=1,  # MetabolitesCSV
        ontology_type="hmdb",
        preference_level=1  # Primary preference
    )
```

### 2. Resource Metadata Database

Used to store and retrieve information about mapping resources, their capabilities, and performance:

- **Resource registration**: Stores mapping resource information and capabilities
- **Capability queries**: Finds resources that can perform specific mappings
- **Performance metrics**: Tracks success rates and response times
- **Ontology coverage**: Records which ontologies each resource supports

The `ResourceMetadataManager` provides an interface to this database:

```python
# Example: Using the resource metadata database
with resource_manager:
    # Find resources that can map from ChEBI to HMDB
    resources = resource_manager.find_resources_by_capability(
        source_type="chebi",
        target_type="hmdb"
    )
    
    # Record performance for a mapping operation
    resource_manager.record_performance(
        resource_id=10,  # UniChem API (ID 10)
        operation_type="map",
        source_type="chebi",
        target_type="hmdb",
        success=True,
        response_time=235  # milliseconds
    )
```

### 3. Relationship Mapping Cache

Stores the results of mapping operations within endpoint relationships:

- **Lookup**: Checks if a mapping has been previously performed within a relationship
- **Storage**: Saves results from successful mappings
- **Metamapping cache**: Stores both intermediate and complete path results
- **Relationship context**: Associates mappings with specific endpoint relationships

The `RelationshipCacheAdapter` provides access to this database:

```python
# Example: Interacting with the relationship mapping cache
cache_adapter = RelationshipCacheAdapter(config)

# Check cache for existing mapping within a relationship
results = await cache_adapter.get_mapping_in_relationship(
    relationship_id=1,  # MetabolitesCSV-to-SPOKE relationship
    source_id="CHEBI:15377",
    source_type="chebi"
)

# Store new mapping in relationship cache
await cache_adapter.store_relationship_mapping(
    relationship_id=1,  # MetabolitesCSV-to-SPOKE relationship
    source_id="CHEBI:15377",
    source_type="chebi",
    target_id="HMDB0000122",
    target_type="hmdb",
    confidence=1.0,
    metadata={"source": "unichem_api"}
)
```

## Database Schema

The system uses a SQLite database (metamapper.db) with these core tables:

### Endpoint and Relationship Schema

```sql
-- Defines actual data sources/endpoints (not mapping tools)
CREATE TABLE endpoints (
    endpoint_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,             -- e.g., "MetabolitesCSV", "SPOKE"
    description TEXT,
    endpoint_type TEXT,           -- e.g., "database", "file", "api", "graph"
    connection_info TEXT,         -- JSON with connection details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP
);

-- Defines relationships between endpoints
CREATE TABLE endpoint_relationships (
    relationship_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Maps endpoints to relationships
CREATE TABLE endpoint_relationship_members (
    relationship_id INTEGER,
    endpoint_id INTEGER,          -- References endpoints
    role TEXT,                    -- e.g., "source", "target", "intermediate"
    priority INTEGER,
    FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id),
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id),
    PRIMARY KEY (relationship_id, endpoint_id)
);

-- Preferred ontologies for endpoints
CREATE TABLE endpoint_ontology_preferences (
    endpoint_id INTEGER,          -- References endpoints
    ontology_type TEXT,           -- e.g., "hmdb", "chebi"
    preference_level INTEGER,
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id),
    PRIMARY KEY (endpoint_id, ontology_type)
);
```

### Mapping Resource Schema

```sql
-- Maintains list of mapping resources
CREATE TABLE mapping_resources (
    resource_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,             -- e.g., "UniChem", "KEGG", "RefMet"
    resource_type TEXT,           -- e.g., "api", "database", "local"
    connection_info TEXT,         -- JSON with connection details
    priority INTEGER,             -- Default priority for this resource
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP
);

-- Ontology coverage for mapping resources
CREATE TABLE ontology_coverage (
    resource_id INTEGER,          -- References mapping_resources
    source_type TEXT,             -- e.g., "hmdb", "chebi"
    target_type TEXT,             -- e.g., "pubchem", "kegg"
    support_level TEXT,           -- e.g., "full", "partial"
    FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id),
    PRIMARY KEY (resource_id, source_type, target_type)
);

-- Performance metrics for mapping resources
CREATE TABLE performance_metrics (
    metric_id INTEGER PRIMARY KEY,
    resource_id INTEGER,          -- References mapping_resources
    source_type TEXT,
    target_type TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_response_time REAL,       -- In milliseconds
    last_updated TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id)
);
```

### Mapping Cache Schema

```sql
-- Mapping results cache
CREATE TABLE mapping_cache (
    mapping_id INTEGER PRIMARY KEY,
    source_id TEXT,               -- Source identifier
    source_type TEXT,             -- Source ontology type
    target_id TEXT,               -- Target identifier
    target_type TEXT,             -- Target ontology type
    confidence REAL,              -- Confidence score (0-1)
    mapping_path TEXT,            -- JSON describing the path taken
    resource_id INTEGER,          -- Which resource performed this mapping
    created_at TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id)
);

-- Links mapping cache entries to endpoint relationships
CREATE TABLE relationship_mappings (
    relationship_id INTEGER,
    mapping_id INTEGER,
    FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id),
    FOREIGN KEY (mapping_id) REFERENCES mapping_cache(mapping_id),
    PRIMARY KEY (relationship_id, mapping_id)
);

-- Stores discovered mapping paths between ontology types
CREATE TABLE mapping_paths (
    path_id INTEGER PRIMARY KEY,
    source_type TEXT,
    target_type TEXT,
    path_steps TEXT,              -- JSON array of steps
    confidence REAL,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    discovered_date TIMESTAMP
);
```

This schema currently supports the following resources (configured in metamapper.db):

1. **ChEBI** (ID 5): Chemical Entities of Biological Interest (mapping resource)
2. **PubChem** (ID 6): NCBI chemical compound database (mapping resource)
3. **MetabolitesCSV** (ID 7): CSV file with metabolite data (endpoint)
4. **SPOKE** (ID 8): Biomedical knowledge graph (endpoint)
5. **KEGG** (ID 9): Metabolic pathway and compound information (mapping resource)
6. **UniChem** (ID 10): EBI's compound identifier mapping service (mapping resource)
7. **RefMet** (ID 11): Reference metabolite nomenclature (mapping resource)
8. **RaMP DB** (ID 12): Rapid Mapping Database for metabolites and pathways (mapping resource)

## Workflow

### Initialization

The Endpoint and Resource Metadata System is initialized during setup:

```python
# Initialize the database schema
initialize_metadata_system("/path/to/metamapper.db")
```

### Endpoint Registration

Endpoints (data sources and targets) are registered with their connection details:

```python
# Register an endpoint
endpoint_id = endpoint_manager.register_endpoint(
    name="metabolites_csv",
    endpoint_type="file",
    connection_info={"file_path": "/path/to/metabolites.csv"},
    description="CSV file containing metabolite measurements"
)

# Set ontology preferences for the endpoint
endpoint_manager.set_ontology_preference(
    endpoint_id=endpoint_id,
    ontology_type="hmdb",
    preference_level=1  # Primary preference
)
```

### Mapping Resource Registration

Mapping resources are registered with their capabilities:

```python
# Register a mapping resource
resource_id = resource_manager.register_mapping_resource(
    name="unichem_api",
    resource_type="api",
    connection_info={"base_url": "https://www.ebi.ac.uk/unichem/"}
)

# Register ontology coverage
resource_manager.register_ontology_coverage(
    resource_id=resource_id,
    source_type="chebi",
    target_type="hmdb",
    support_level="full"
)
```

### Relationship Creation

Relationships between endpoints are established:

```python
# Create an endpoint relationship
relationship_id = endpoint_manager.create_endpoint_relationship(
    name="MetabolitesCSV-to-SPOKE",
    description="Maps metabolites from CSV data to SPOKE entities"
)

# Add members to the relationship
endpoint_manager.add_relationship_member(
    relationship_id=relationship_id,
    endpoint_id=7,  # MetabolitesCSV (ID 7)
    role="source"
)

endpoint_manager.add_relationship_member(
    relationship_id=relationship_id,
    endpoint_id=8,  # SPOKE (ID 8)
    role="target"
)
```

### Mapping Operations

Mapping operations are performed through the relationship-aware dispatcher:

```python
# Map entities within a relationship context
results = await relationship_dispatcher.map_entity_in_relationship(
    relationship_id=relationship_id,
    source_id="glucose",
    source_type="compound_name",
    context={"confidence_threshold": 0.8}
)
```

The dispatcher handles all the complexity of:
1. Determining the optimal mapping path based on endpoint preferences
2. Trying mapping resources in priority order
3. Handling failures and timeouts
4. Updating the relationship cache with new mappings
5. Tracking which mappings belong to which relationships

### Performance Monitoring

The system continuously monitors performance:

```python
# Get performance metrics for mapping resources
metrics = resource_manager.get_performance_summary()

# Get mapping success rates for a specific relationship
relationship_metrics = relationship_manager.get_relationship_metrics(
    relationship_id=relationship_id
)
```

These metrics can be used to:
- Adjust resource priorities
- Identify problematic mapping paths
- Optimize endpoint ontology preferences
- Improve relationship-specific mapping strategies

## Command-Line Interface

The system includes a CLI for endpoint and mapping resource management:

```bash
# Initialize the metadata system
biomapper metadata init

# Register endpoints from a configuration file
biomapper endpoints register --config-file=endpoints.yaml

# Register mapping resources from a configuration file
biomapper resources register --config-file=resources.yaml

# Create an endpoint relationship
biomapper relationship create --name="MetabolitesCSV-to-SPOKE" \
    --source=7 --target=8 \
    --description="Maps metabolites to SPOKE entities"

# List registered endpoints
biomapper endpoints list

# List mapping resources
biomapper resources list

# List endpoint relationships
biomapper relationships list

# List available mapping paths between endpoints
biomapper paths list --relationship-id=1

# Test a mapping path
biomapper paths test --relationship-id=1 --entity="glucose" --type="name"

# Show performance statistics
biomapper metadata stats
```

## Configuration

The system uses YAML or JSON configuration files for both endpoints and mapping resources:

### Endpoint Configuration

```yaml
endpoints:
  metabolites_csv:
    type: file
    connection_info:
      file_path: "~/data/metabolites.csv"
      format: "csv"
      delimiter: ","
    description: "CSV file with metabolite measurements"
    ontology_preferences:
      hmdb: 1  # Primary preference
      pubchem: 2  # Secondary preference
      smiles: 3  # Tertiary preference

  spoke_graph:
    type: graph
    connection_info:
      url: "http://spoke-api.example.org"
      auth_token: "${SPOKE_TOKEN}"
    description: "SPOKE biomedical knowledge graph"
    ontology_preferences:
      uniprot: 1
      chebi: 1
      pubchem: 2
```

### Mapping Resource Configuration

```yaml
resources:
  unichem_api:
    type: api
    connection_info:
      base_url: "https://www.ebi.ac.uk/unichem/"
      timeout_ms: 5000
    priority: 1
    ontologies:
      chebi:
        support_level: full
      hmdb:
        support_level: full
      pubchem:
        support_level: full
        
  mapping_cache:
    type: cache
    connection_info:
      data_dir: ~/.biomapper/data
      db_name: metamapper.db
    priority: 10
    ontologies:
      # Can potentially map any ontology if cached
      chebi:
        support_level: full
      hmdb:
        support_level: full
```

### Relationship Configuration

```yaml
relationships:
  - name: "MetabolitesCSV-to-SPOKE"
    description: "Maps metabolites from CSV to SPOKE entities"
    members:
      - endpoint: "metabolites_csv"
        role: "source"
      - endpoint: "spoke_graph"
        role: "target"
    mapping_preferences:
      confidence_threshold: 0.8
      max_path_length: 3
```

## Integration with Existing Systems

The Endpoint and Resource Metadata System is designed to integrate smoothly with existing data pipelines and workflows:

### Python API

The system provides a Python API for integration with data science workflows:

```python
from biomapper.endpoints import EndpointManager, RelationshipManager
from biomapper.resources import ResourceManager
from biomapper.mapping import RelationshipDispatcher, RelationshipMetamappingEngine

# Set up managers
endpoint_manager = EndpointManager("/path/to/metamapper.db")
resource_manager = ResourceManager("/path/to/metamapper.db")
relationship_manager = RelationshipManager("/path/to/metamapper.db")

# Create dispatcher with both managers
dispatcher = RelationshipDispatcher(endpoint_manager, resource_manager)

# Create metamapping engine
engine = RelationshipMetamappingEngine(dispatcher, endpoint_manager)

# Use in data pipeline
async def process_metabolites(metabolites_df):
    # Get the MetabolitesCSV-to-SPOKE relationship
    relationship = relationship_manager.get_relationship_by_name("MetabolitesCSV-to-SPOKE")
    
    results = []
    for _, row in metabolites_df.iterrows():
        # Map each metabolite to SPOKE entities
        mapping = await dispatcher.map_entity_in_relationship(
            relationship_id=relationship.id,
            source_id=row["metabolite_id"],
            source_type="hmdb"
        )
        results.append(mapping)
    
    return results
```

### REST API

The system also offers a REST API for integration with web applications and microservices:

```bash
# Map an entity within a relationship
curl -X POST "http://biomapper-api/v1/relationships/1/map" \
  -H "Content-Type: application/json" \
  -d '{"source_id":"HMDB0000122","source_type":"hmdb"}'

# Retrieve information about a mapping resource
curl -X GET "http://biomapper-api/v1/resources/10"

# Get statistics for a specific relationship
curl -X GET "http://biomapper-api/v1/relationships/1/stats"
```

### Web Interface

A web interface is provided for manual exploration of mappings and relationship management:

- **Relationship Dashboard**: Visualize and manage endpoint relationships
- **Mapping Explorer**: Interactively explore mapping paths between ontologies
- **Performance Monitor**: Track mapping success rates and identify bottlenecks
- **Configuration Manager**: Edit endpoint and resource configurations

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
