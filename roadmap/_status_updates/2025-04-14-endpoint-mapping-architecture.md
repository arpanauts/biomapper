# Biomapper Endpoint-Mapping Architecture Status Update

## 1. Recent Accomplishments

- Created comprehensive API documentation for six key resources:
  - UniChem API documentation
  - KEGG API documentation
  - RefMet/Metabolomics Workbench API documentation
  - ChEBI API documentation
  - RaMP DB API documentation
  - PubChem API documentation

- Consolidated documentation structure in `/home/ubuntu/biomapper/docs/resources/`
  - Removed redundant ontology documentation files
  - Updated the README.md to reflect the API-focused documentation approach
  - Added resource IDs to documentation for clear reference

- Conceptualized and implemented an enhanced architecture for endpoint-to-endpoint mapping
  - Developed clear separation between endpoints and mapping resources
  - Created a relationship-based design for flexible multi-endpoint connections
  - Designed and implemented database schema enhancements to support this approach
  - Established property extraction configurations for endpoints

- Implemented key components for the new architecture:
  - Created migration script (`20250414_endpoint_mapping_schema.py`) for the new schema
  - Developed direct schema creation script (`create_endpoint_mapping_tables.py`)
  - Implemented sample data setup script (`setup_endpoint_mapping.py`) 
  - Updated `resource_metadata_system.md` to reflect the new architecture

## 2. Current Project State

- **Documentation Layer**: Complete and well-structured API documentation for all mapping resources
  - All six mapping resources have detailed documentation with examples and property extraction patterns
  - README provides a clear overview of available resources and their capabilities
  - Architecture documentation updated to reflect the relationship-based design

- **Implemented Architecture**: Enhanced design for endpoint-mapping relationships
  - Clear distinction between endpoints (data sources) and mapping resources (ontology translation tools)
  - Support for multi-endpoint relationships beyond simple A→B mapping
  - Flexible preference system for ontology types within endpoints
  - Detailed endpoint property extraction configurations

- **Database Schema**: Fully implemented schema for enhanced mapping relationships
  - Successfully created all tables for the new endpoint-mapping architecture
  - Separation of endpoints and mapping resources in the database schema
  - Support for endpoint-to-endpoint relationships with multiple members
  - Reusable mapping cache entries across different endpoint relationships
  - Sample data populated for MetabolitesCSV-to-SPOKE mapping relationship

- **Data Integration Plan**: Created forward-looking document on data integration patterns
  - Documented various integration patterns in `/roadmap/architecture/endpoint_data_integration.md`
  - Outlined annotation, data propagation, query bridging, and federation patterns
  - Explored advanced integration concepts for machine learning and temporal data

- **Outstanding Issues**:
  - Need to implement the core management classes (EndpointManager, RelationshipDispatcher)
  - Need to update existing components to use the new endpoint/resource distinction
  - Testing required for complex mapping paths between endpoints

## 3. Technical Context

### Key Architectural Decisions

1. **Separation of Endpoints and Mapping Resources**: 
   - Endpoints (like MetabolitesCSV, SPOKE) are distinctly different from mapping resources (like UniChem, KEGG)
   - This separation clarifies the conceptual model and allows for more appropriate metadata

2. **Relationship-Based Mapping Architecture**:
   - Mappings occur within the context of endpoint relationships
   - The same mapping can be reused across different endpoint relationships
   - Each relationship can involve multiple endpoints with different roles

3. **Preference-Based Ontology Selection**:
   - Endpoints can specify preferred ontology types for each relationship
   - This guides the mapping path discovery to prioritize certain ontology types

### Core Database Schema Enhancements

```sql
-- Defines actual data sources/endpoints (not mapping tools)
CREATE TABLE endpoints (
    endpoint_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT,
    endpoint_type TEXT,
    connection_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP
);

-- Maintains list of mapping resources (not endpoints)
CREATE TABLE mapping_resources (
    resource_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    resource_type TEXT,
    connection_info TEXT,
    priority INTEGER,
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
    endpoint_id INTEGER,
    role TEXT,
    priority INTEGER,
    FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id),
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id),
    PRIMARY KEY (relationship_id, endpoint_id)
);

-- Preferred ontologies for endpoints
CREATE TABLE endpoint_ontology_preferences (
    endpoint_id INTEGER,
    ontology_type TEXT,
    preference_level INTEGER,
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id),
    PRIMARY KEY (endpoint_id, ontology_type)
);

-- Links mapping cache entries to endpoint relationships
CREATE TABLE relationship_mappings (
    relationship_id INTEGER,
    mapping_id INTEGER,
    FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id),
    FOREIGN KEY (mapping_id) REFERENCES mapping_cache(mapping_id),
    PRIMARY KEY (relationship_id, mapping_id)
);
```

### Key Algorithms

The MetamappingEngine's breadth-first search algorithm would be enhanced to:

1. Consider endpoint ontology preferences when finding paths
2. Prioritize shorter paths with higher confidence scores
3. Cache discovered paths for reuse within endpoint relationships

## 4. Next Steps

### Immediate Tasks

1. **Implement Core Management Classes**:
   - Create `EndpointManager` class for managing endpoints and relationships
   - Develop `RelationshipDispatcher` to handle mapping within relationship contexts
   - Implement `EndpointAdapter` system for different endpoint types (CSV, Graph)

2. **Build RelationshipMetamappingEngine**:
   - Implement the enhanced BFS algorithm with preference weighting
   - Create path discovery optimized for endpoint relationships
   - Integrate with the endpoint property extraction system

3. **Develop Adapters for Different Endpoint Types**:
   - Create `CSVEndpointAdapter` for CSV-based endpoints like MetabolitesCSV
   - Implement `GraphEndpointAdapter` for SPOKE integration
   - Develop abstract base class with common functionality

4. **Enhance Relationship Mapping Cache**:
   - Implement caching system for relationship-specific mappings
   - Create methods for checking/storing mappings within relationships
   - Develop cache invalidation strategy for outdated mappings

### Priorities for Coming Week

1. Implement the `EndpointManager` class with relationship management capabilities
2. Develop the `RelationshipMetamappingEngine` with the enhanced BFS algorithm
3. Create a concrete implementation of endpoint adapters for CSV and Graph endpoints
4. Update the CLI to support endpoint and relationship management commands

### Potential Challenges

- Ensuring the enhanced BFS algorithm performs efficiently with complex preference calculations
- Managing the complexity of endpoint adapters for diverse data sources
- Balancing caching strategies to maximize performance without excessive memory usage
- Seamlessly integrating the new architecture with existing code and workflows

## 5. Open Questions & Considerations

1. **Confidence Scoring**:
   - How should confidence scores be calculated for multi-step mapping paths?
   - Should different ontology types have inherent confidence modifiers?
   - How can we incorporate feedback to improve confidence scores over time?

2. **Caching Strategy**:
   - What's the optimal balance between caching mapping results vs. recalculating?
   - Should we implement time-based expiration for cached mappings?
   - How do we handle updates to underlying resources?

3. **Scaling Considerations**:
   - How will this approach scale with hundreds or thousands of endpoints?
   - Should we implement batch processing for large-scale mapping operations?
   - How can we optimize the discovery of mapping paths for very large networks?

4. **Relationship Complexity**:
   - How do we best represent and manage complex relationships involving many endpoints?
   - What visualization approaches could help users understand mapping paths?
   - Should we implement a DSL for describing complex mapping operations?

5. **Integration with Existing Systems**:
   - How does the new `RelationshipMetamappingEngine` integrate with the existing MappingDispatcher?
   - What's the best strategy for transitioning from the ResourceMetadataManager to the EndpointManager?
   - How can we ensure backward compatibility while encouraging adoption of the new paradigm?
   - What's the best approach for gradually migrating existing cached mappings to the relationship-based structure?

6. **Property Extraction for Endpoints**:
   - How can we optimize the property extraction configurations for diverse endpoint types?
   - What are the best patterns for extracting ontology IDs from complex data sources?
   - Should transform functions be standardized or customizable per endpoint?
   - How do we handle missing or incomplete ontology IDs in endpoints?
