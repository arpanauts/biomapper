# Endpoint Data Integration Architecture

## Overview

This document outlines how the Biomapper's endpoint-mapping architecture evolves from entity resolution to full data integration between endpoints. While the current architecture focuses on establishing relationships between endpoints and mapping entities across ontologies, the next evolution incorporates actual data transfer, analysis, and insight generation.

## From Entity Resolution to Data Integration

The endpoint-mapping architecture provides the foundation for entity resolution by:

1. Establishing relationships between endpoints
2. Mapping entities across different ontology systems
3. Maintaining mapping preferences and confidence metrics

Building upon this foundation, data integration adds capabilities for:

1. Transferring properties/values between mapped entities
2. Executing cross-endpoint queries using mapped relationships
3. Generating insights by combining structure (from knowledge graphs) with measurements (from data sources)
4. Building analytical pipelines that leverage both raw data and knowledge context

## Integration Patterns

### 1. Annotation Pattern

The annotation pattern enriches raw data with contextual information from knowledge sources.

**Flow:**
1. Start with raw data in a source endpoint (e.g., MetabolitesCSV)
2. Map entities to a knowledge endpoint (e.g., SPOKE)
3. Extract relevant annotations (pathways, functions, interactions)
4. Associate these annotations with the original data entities

**Example:**
```python
# Map metabolites to SPOKE entities
mappings = relationship_dispatcher.map_entities_in_relationship(
    relationship_id=metabolitescsv_to_spoke_relationship,
    source_ids=metabolites_csv.get_all_ids(),
    source_type="hmdb"
)

# For each mapping, extract annotations from SPOKE
for mapping in mappings:
    annotations = spoke_endpoint.get_entity_annotations(
        entity_id=mapping.target_id,
        annotation_types=["pathway", "disease", "biological_process"]
    )
    
    # Add annotations back to original data
    metabolites_csv.add_annotations(
        entity_id=mapping.source_id, 
        annotations=annotations
    )
```

**Benefits:**
- Preserves original data structure
- Adds interpretability to numerical measurements
- Enables filtering/grouping by knowledge graph attributes

### 2. Data Propagation Pattern

The data propagation pattern transfers numerical values or properties from data sources into knowledge graphs.

**Flow:**
1. Start with data properties in a source endpoint
2. Map entities to target endpoint nodes
3. Transfer specified properties to target entities
4. Enable knowledge-aware analysis of the numerical data

**Example:**
```python
# Get concentration values from metabolites CSV
metabolite_values = metabolites_csv.get_property_for_all(
    property_name="concentration"
)

# Map entities and transfer values to SPOKE
for metabolite_id, value in metabolite_values.items():
    # Find mapping
    mapping = relationship_dispatcher.map_entity_in_relationship(
        relationship_id=metabolitescsv_to_spoke_relationship,
        source_id=metabolite_id,
        source_type="hmdb"
    )
    
    # Transfer value to SPOKE entity
    if mapping:
        spoke_endpoint.set_property(
            entity_id=mapping.target_id,
            property_name="measured_concentration",
            property_value=value,
            metadata={"source": "metabolites_csv", "timestamp": datetime.now()}
        )
```

**Benefits:**
- Enables network algorithms to incorporate measurement data
- Allows visualization of measurements in network context
- Supports multi-modal data fusion within knowledge graphs

### 3. Query Bridging Pattern

The query bridging pattern defines subsets in one endpoint and explores their relationships in another.

**Flow:**
1. Define a subset/community in the source endpoint
2. Map this community to target endpoint entities
3. Execute queries in the target endpoint using these entities
4. Return context-enriched results

**Example:**
```python
# Extract a subset of metabolites with high measurements
elevated_metabolites = metabolites_csv.filter(
    lambda row: row["concentration"] > threshold
)

# Map to SPOKE entities
mapped_entities = relationship_dispatcher.map_entities_in_relationship(
    relationship_id=metabolitescsv_to_spoke_relationship,
    source_ids=elevated_metabolites.get_ids(),
    source_type="hmdb"
)

# Execute a graph query in SPOKE
pathways = spoke_endpoint.query(
    "MATCH (m:Metabolite)-[:PARTICIPATES_IN]->(p:Pathway) " +
    "WHERE m.id IN $mapped_ids " +
    "WITH p, COUNT(m) AS matches, SIZE((p)-[:HAS_MEMBER]->()) AS total " +
    "RETURN p.id, p.name, matches, total, matches/toFloat(total) AS coverage " +
    "ORDER BY coverage DESC",
    {"mapped_ids": [e.target_id for e in mapped_entities]}
)

# Return enriched community
return {
    "community": elevated_metabolites,
    "pathways": pathways,
    "entities": mapped_entities
}
```

**Benefits:**
- Enables pathway enrichment analysis
- Supports mechanism discovery
- Combines statistical power with structural knowledge

### 4. Bidirectional Federation Pattern

The federation pattern allows endpoints to expose a unified query interface across mapped resources.

**Flow:**
1. Define a query in the source endpoint's native format
2. Translate query to target endpoint(s) format using entity mappings
3. Execute distributed query across endpoints
4. Combine and harmonize results

**Example:**
```python
# Define a federated query - "find all pathways containing glucose 
# and their related diseases"
federated_query = FederatedQuery()

# Add metabolite constraints from CSV data
federated_query.add_constraint(
    endpoint="metabolites_csv",
    constraint="name = 'glucose'"
)

# Add pathway relationship from SPOKE
federated_query.add_relationship(
    endpoint="spoke",
    relationship="PARTICIPATES_IN",
    from_type="Compound",
    to_type="Pathway"
)

# Add disease relationship from SPOKE
federated_query.add_relationship(
    endpoint="spoke",
    relationship="ASSOCIATED_WITH",
    from_type="Pathway",
    to_type="Disease"
)

# Execute federated query
results = federated_query_engine.execute(federated_query)
```

**Benefits:**
- Provides a unified query interface
- Hides complexity of endpoint-specific query languages
- Enables complex multi-endpoint queries

## Advanced Integration Concepts

### Knowledge-Enhanced Machine Learning

The mapped ontologies and transferred data enable advanced ML models that incorporate domain knowledge.

**Approaches:**
1. **Feature Extraction**: Extract network-based features (centrality, motifs, etc.) from knowledge graphs for mapped entities
2. **Graph Neural Networks**: Apply GNNs to mapped entities with propagated numerical values
3. **Transfer Learning**: Train models on knowledge graph structure and fine-tune with numerical data
4. **Constraint-Based Learning**: Use knowledge from graphs to constrain model training

**Example:**
```python
# Map all metabolites to SPOKE
all_mappings = relationship_dispatcher.map_all_entities_in_relationship(
    relationship_id=metabolitescsv_to_spoke_relationship
)

# Extract features for each metabolite
feature_matrix = []
for original_id, mapping in all_mappings.items():
    # Extract original features
    original_features = metabolites_csv.get_features(original_id)
    
    # Extract knowledge graph features
    if mapping:
        graph_features = spoke_endpoint.extract_features(
            entity_id=mapping.target_id,
            feature_types=["network", "ontology"]
        )
    else:
        graph_features = []
    
    # Combine feature sets
    combined_features = original_features + graph_features
    feature_matrix.append(combined_features)

# Train model with enhanced feature set
model = MachineLearningModel()
model.train(
    features=feature_matrix,
    labels=metabolites_csv.get_labels()
)
```

### Temporal Dimension Integration

Integration of the temporal dimension across mapped entities.

**Capabilities:**
1. Track property changes over time for mapped entities
2. Support time-series analysis across endpoint boundaries
3. Enable temporal pattern discovery in mapped data
4. Provide versioning for mappings and propagated data

**Example:**
```python
# Define a time series study with multiple timepoints
for timepoint in timepoints:
    # Get values at this timepoint
    values = metabolites_csv.get_values_at_timepoint(timepoint)
    
    # For each entity, map and propagate with temporal context
    for entity_id, value in values.items():
        # Find mapping
        mapping = relationship_dispatcher.map_entity_in_relationship(
            relationship_id=metabolitescsv_to_spoke_relationship,
            source_id=entity_id,
            source_type="hmdb"
        )
        
        if mapping:
            # Add temporal value to SPOKE
            spoke_endpoint.add_temporal_property(
                entity_id=mapping.target_id,
                property_name="concentration",
                property_value=value,
                timestamp=timepoint
            )

# Perform temporal analysis across the knowledge graph
patterns = spoke_endpoint.analyze_temporal_patterns(
    property_name="concentration",
    time_range=[min(timepoints), max(timepoints)]
)
```

### Multi-Endpoint Integration

Approaches for integrating data across multiple endpoints simultaneously.

**Strategies:**
1. **Star Integration**: One primary endpoint with multiple satellite endpoints
2. **Mesh Integration**: Any-to-any endpoint integration
3. **Pipeline Integration**: Sequential data flow across multiple endpoints
4. **Hierarchical Integration**: Nested integration of endpoint communities

**Example:**
```python
# Create a multi-endpoint integration configuration
integration_config = {
    "primary_endpoint": "metabolites_csv",
    "knowledge_endpoints": ["spoke", "kegg_pathway", "reactome"],
    "annotation_endpoints": ["chebi", "pubchem"],
    "relationships": [
        {
            "id": metabolitescsv_to_spoke_relationship,
            "source": "metabolites_csv",
            "target": "spoke"
        },
        {
            "id": metabolitescsv_to_kegg_relationship,
            "source": "metabolites_csv",
            "target": "kegg_pathway"
        }
    ],
    "integration_strategy": "star"
}

# Initialize the multi-endpoint integrator
integrator = MultiEndpointIntegrator(integration_config)

# Execute a multi-endpoint query
results = integrator.execute_query(
    "Find all pathways enriched in elevated metabolites across SPOKE and KEGG, " +
    "with chemical property annotations from ChEBI and PubChem"
)
```

## Implementation Considerations

### Data Transfer Architecture

The system for transferring data between mapped entities should consider:

1. **Batch Operations**: Efficient transfer of properties for multiple entities
2. **Data Type Conversion**: Managing type differences across endpoints
3. **Validation Rules**: Ensuring transferred data meets target endpoint constraints
4. **Provenance Tracking**: Maintaining source information for transferred properties
5. **Conflict Resolution**: Handling multiple sources for the same property

### Query Translation Layer

A system for translating queries across endpoint-specific languages:

1. **Query Abstraction**: High-level query model independent of endpoint-specific syntax
2. **Translation Rules**: Patterns for converting between query languages
3. **Execution Planning**: Optimizing query execution across endpoints
4. **Result Harmonization**: Combining and formatting results from multiple endpoints

### Integration API Extensions

Extensions to the existing API for managing data integration:

```python
# Endpoint interface extensions
class IntegratedEndpoint(Endpoint):
    # Transfer data to mapped entities in another endpoint
    async def transfer_properties(
        self,
        relationship_id,
        properties,
        target_properties=None,
        filters=None
    )
    
    # Accept properties from another endpoint
    async def receive_properties(
        self,
        relationship_id,
        source_endpoint_id,
        property_mappings
    )
    
    # Execute a query that spans this and mapped endpoints
    async def execute_federated_query(
        self,
        query,
        endpoint_mappings
    )

# Relationship dispatcher extensions
class IntegratedRelationshipDispatcher(RelationshipDispatcher):
    # Transfer property values between mapped entities
    async def transfer_properties_in_relationship(
        self,
        relationship_id,
        property_mappings,
        source_filters=None
    )
    
    # Build a federated query across relationships
    def build_federated_query(
        self,
        base_endpoint_id,
        query_path
    )
    
    # Execute analysis that requires mapped entities
    async def execute_cross_endpoint_analysis(
        self,
        analysis_type,
        relationship_ids,
        parameters
    )
```

## Next Steps and Development Roadmap

### Phase 1: Data Transfer Foundation
- Implement property transfer between mapped entities
- Add provenance tracking for transferred data
- Create batch operations for efficient data movement

### Phase 2: Cross-Endpoint Queries
- Develop query translation mechanisms
- Create federated query executor
- Implement result merging and harmonization

### Phase 3: Knowledge-Enhanced Analysis
- Build integration with analytical tools
- Implement network-based feature extraction
- Create visualization for integrated data

### Phase 4: Advanced Integration Patterns
- Support temporal dimension in mapped entities
- Implement multi-endpoint integration strategies
- Create high-level APIs for common integration patterns

## Conclusion

The endpoint data integration architecture builds upon the entity mapping foundation to create a powerful system for harmonizing data across diverse sources. By combining the contextual knowledge of graph databases with the statistical power of raw measurements, this architecture enables advanced biomedical data analysis and discovery.

The key innovation is moving beyond simple entity resolution to true data federation, allowing researchers to seamlessly navigate and analyze connected data across endpoint boundaries while maintaining the specialized capabilities of each individual data source.
