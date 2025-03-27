# Knowledge Graph Integration Implementation Plan

## Executive Summary

This document outlines the implementation plan for Biomapper's generalized knowledge graph integration strategy. This plan details how to implement the abstraction layer that enables Biomapper to work with multiple knowledge graph sources, including but not limited to SPOKE. The approach ensures that Biomapper maintains its full functionality regardless of whether specific licensed knowledge graphs are available.

## Implementation Goals

1. **Knowledge Graph Independence**
   - Enable Biomapper to function with or without access to SPOKE
   - Support multiple knowledge graph sources simultaneously
   - Provide degradation paths when primary sources are unavailable

2. **Performance Optimization**
   - Leverage SQL-based cache for frequently accessed mappings
   - Intelligently route queries based on resource capabilities and performance
   - Minimize network calls to knowledge graph servers

3. **Extensibility**
   - Make adding new knowledge graph sources straightforward
   - Support different graph database technologies (ArangoDB, Neo4j, etc.)
   - Enable runtime discovery and registration of capabilities

4. **Compatibility**
   - Maintain backward compatibility with existing code
   - Provide migration paths for SPOKE-specific implementations
   - Ensure seamless integration with the resource metadata system

## Architecture Overview

The implementation builds on Biomapper's hybrid architecture that combines:

1. **Knowledge Graph Layer**
   - Primary: SPOKE Knowledge Graph (ArangoDB)
   - Supplementary: Extension Graph (ArangoDB)
   - Additional future sources (e.g., Google's Biomedical Commons)

2. **Abstraction Components**
   - Knowledge Graph Client Protocol
   - Schema Configuration System
   - Capability Registry
   - Resource Adapter Layer

3. **Performance Layer**
   - SQL-based Mapping Cache (SQLite/PostgreSQL)
   - Performance Metrics Collection
   - Adaptive Query Routing

4. **Integration Layer**
   - Resource Metadata System
   - Unified Ontology Mapping

## Implementation Phases

### Phase 1: Knowledge Graph Client Protocol (Current Phase)

- [x] Define the base `KnowledgeGraphClient` protocol
- [x] Implement `SPOKEDBClient` as reference implementation
- [x] Create default schema mapping for SPOKE
- [x] Implement basic exploration tools
- [ ] Finalize capability definition format
- [ ] Create adapter registration mechanism

### Phase 2: Resource Metadata Integration

- [ ] Enhance Resource Metadata Manager to support knowledge graph capability registry
- [ ] Implement configuration-driven resource initialization
- [ ] Create performance metrics collection system
- [ ] Develop capability-based routing logic
- [ ] Add support for fallback chains when resources are unavailable

### Phase 3: SQL Cache Integration

- [ ] Implement bidirectional caching for knowledge graph mappings
- [ ] Create cache invalidation strategies
- [ ] Add cache performance monitoring
- [ ] Implement cache warming for common mappings
- [ ] Develop adaptive cache prioritization based on usage patterns

### Phase 4: Extension Graph Support

- [ ] Implement Extension Graph Client
- [ ] Create schema mapping for Extension Graph
- [ ] Develop synchronization between SPOKE and Extension Graph
- [ ] Add conflict resolution policies for overlapping mappings
- [ ] Create tools for extending the graph with new data sources

## Component Specifications

### 1. Knowledge Graph Client Protocol

```python
class KnowledgeGraphClient(Protocol):
    """Protocol for knowledge graph clients."""
    
    async def query_nodes(
        self,
        node_type: str,
        properties: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query nodes in the knowledge graph."""
        ...
    
    async def query_relationships(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query relationships in the knowledge graph."""
        ...
        
    async def map_entity(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Map an entity from source to target type."""
        ...
```

### 2. Resource Adapter Specification

```python
class KnowledgeGraphResourceAdapter:
    """Adapter for knowledge graph resources."""
    
    def __init__(self, client: KnowledgeGraphClient, config: Dict[str, Any]):
        """Initialize the adapter with a client and configuration."""
        ...
    
    async def map_entity(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Map an entity using the knowledge graph."""
        ...
    
    def get_capabilities(self) -> List[ResourceCapability]:
        """Get the capabilities of this adapter."""
        ...
    
    def get_schema_mapping(self) -> Dict[str, Any]:
        """Get the schema mapping for this adapter."""
        ...
```

### 3. Schema Configuration Format

The schema configuration follows this format:

```yaml
knowledge_graphs:
  - name: spoke
    type: arangodb
    optional: true
    connection:
      host: localhost
      port: 8529
      database: spoke
    schema_mapping:
      node_types:
        Compound:
          ontology_types: [chebi, hmdb, pubchem]
          property_map:
            properties.chebi: chebi
            properties.hmdb: hmdb
      capabilities:
        - name: compound_to_gene
          description: Map compounds to genes
          confidence: 0.9
```

### 4. Resource Registration Mechanism

```python
def register_knowledge_graph(
    name: str,
    client_factory: Callable[..., KnowledgeGraphClient],
    schema_mapping: Dict[str, Any],
    config: Dict[str, Any],
    optional: bool = False
) -> None:
    """Register a knowledge graph with the resource metadata system."""
    ...
```

## Technical Considerations

### Database Connections

- Use connection pooling for ArangoDB connections
- Implement retry mechanisms with exponential backoff
- Provide circuit breakers for unavailable services
- Support both synchronous and asynchronous access patterns

### Schema Mapping

- Support runtime schema discovery when possible
- Fall back to default schemas when discovery fails or times out
- Allow partial schema updates without requiring full reinitialization
- Validate schema mappings against actual database structure

### Error Handling

- Provide detailed error information for debugging
- Implement graceful degradation when knowledge graphs are unavailable
- Log performance issues and timeout patterns
- Support notifying administrators of persistent issues

## Testing Strategy

1. **Unit Tests**
   - Test protocol implementations in isolation
   - Mock knowledge graph servers for testing
   - Validate schema configuration parsing
   - Test adapter behavior with various inputs

2. **Integration Tests**
   - Test with actual ArangoDB instances when available
   - Verify performance metrics collection
   - Test fallback chains and degradation
   - Validate caching behavior

3. **Load Tests**
   - Measure performance under concurrent load
   - Test caching effectiveness
   - Assess memory usage patterns
   - Profile critical mapping operations

## Implementation Timeline

1. **Phase 1: Protocol Implementation** - 2 weeks
   - Finalize protocol definitions
   - Implement SPOKE client reference
   - Create schema configuration system

2. **Phase 2: Resource Metadata Integration** - 2 weeks
   - Enhance resource registration
   - Implement capability routing
   - Add performance metrics collection

3. **Phase 3: SQL Cache Integration** - 2 weeks
   - Implement bidirectional caching
   - Create cache invalidation strategy
   - Add performance monitoring

4. **Phase 4: Extension Graph Support** - 2 weeks
   - Implement Extension Graph client
   - Create schema mapping
   - Develop synchronization tools

## Next Steps

1. **Finalize Knowledge Graph Client Protocol**
   - Complete the protocol interface
   - Document expected behavior
   - Create reference implementation tests

2. **Implement Schema Configuration System**
   - Build parser for schema configuration
   - Create validation tools
   - Implement runtime discovery features

3. **Integrate with Resource Metadata System**
   - Connect to existing resource manager
   - Implement capability registration
   - Create performance metrics collection
