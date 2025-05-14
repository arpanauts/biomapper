# Generalized Knowledge Graph Strategy

## Executive Summary

This document outlines Biomapper's strategy for implementing a generalized knowledge graph approach that ensures functionality with or without access to specific licensed knowledge graphs such as SPOKE. This abstraction layer enables users to configure their own knowledge graph sources while maintaining the benefits of Biomapper's unified mapping system.

## Motivation

While SPOKE is a valuable resource for biomedical entity mapping, several factors necessitate a more flexible, generalized approach:

1. **Licensing Considerations**: SPOKE requires licensing that not all Biomapper users may have, limiting adoption
2. **Multiple Knowledge Graph Sources**: The biomedical field has multiple valuable knowledge graphs (SPOKE, Biomedical Commons, customized datasets) 
3. **Future-Proofing**: New knowledge graph resources will continue to emerge
4. **Deployment Flexibility**: Different deployment environments may have different resources available

## Architecture Overview

The generalized knowledge graph abstraction consists of several key components:

```
┌─────────────────────────────────────┐
│   Knowledge Graph Client Protocol   │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  Schema Configuration Abstraction   │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│     Knowledge Graph Adapters        │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│      Resource Metadata System       │
└─────────────────────────────────────┘
```

### Core Components

1. **Knowledge Graph Client Protocol**
   - Defines standard interfaces for all knowledge graph clients
   - Abstracts implementation details through a common API
   - Supports both synchronous and asynchronous operations

2. **Schema Configuration Abstraction**
   - Provides a declarative format for mapping between graph schemas and ontology types
   - Enables configuration-driven adaptation to different graph structures
   - Supports runtime schema discovery and mapping

3. **Knowledge Graph Adapters**
   - Implements the client protocol for specific knowledge graph technologies
   - SPOKE adapter serves as reference implementation (optional dependency)
   - Includes adapters for ArangoDB, Neo4j, and other common graph databases

4. **Resource Metadata System**
   - Manages knowledge graph capabilities and performance metrics
   - Routes mapping requests to appropriate knowledge graph sources
   - Provides fallback mechanisms when primary sources are unavailable

## Configuration System

The configuration system is a critical component, allowing users to adapt Biomapper to their available knowledge graphs:

```yaml
knowledge_graphs:
  - name: spoke_graph
    type: arangodb
    optional: true  # System works without this source
    connection:
      host: localhost
      port: 8529
      database: spoke
    schema_mapping:
      Compound:  # Node type
        ontology_types: [chebi, hmdb, pubchem, inchikey]
        property_map:
          properties.chebi: chebi
          properties.hmdb: hmdb
      Gene:
        ontology_types: [ensembl, gene_symbol, hgnc]
        property_map:
          properties.ensembl: ensembl
          properties.symbol: gene_symbol
    capabilities:
      compound_to_gene: true
      gene_to_disease: true
      metabolite_to_pathway: true
  
  - name: custom_graph
    type: arangodb
    optional: false  # Required for operation
    connection:
      host: localhost
      port: 8529
      database: extension_graph
    schema_mapping:
      # Custom schema configuration
```

## Knowledge Graph Client Protocol

The core protocol definition ensures consistent interaction with any knowledge graph:

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

## Schema Configuration

The schema configuration system enables mapping between different knowledge graph schemas and standardized ontology types:

```python
@dataclass
class NodeTypeMapping:
    """Configuration for mapping a node type to ontology types."""
    
    node_type: str
    ontology_types: List[str]
    property_map: Dict[str, str]
    confidence: float = 1.0

@dataclass
class SchemaMapping:
    """Schema mapping configuration for a knowledge graph."""
    
    graph_name: str
    node_types: Dict[str, NodeTypeMapping]
    relationship_types: Dict[str, RelationshipMapping]
```

## Degradation Strategy

The system implements graceful degradation when knowledge graphs are unavailable:

1. **Capability-Based Routing**: Only routes queries to knowledge graphs that explicitly support the required mappings
2. **Fallback Chain**: If preferred knowledge graph is unavailable, falls back to alternatives
3. **Cache Prioritization**: Elevates cache priority when knowledge graphs are unavailable
4. **RAG Integration**: Falls back to retrieval augmented generation for unsupported mappings
5. **Mock Mode**: Can run in a mock mode for development without real knowledge graphs

## Implementation Benefits

This generalized approach provides several key benefits:

1. **Universal Accessibility**: Biomapper can be used by anyone, with or without SPOKE access
2. **Enhanced Flexibility**: Support for different knowledge graph technologies and schemas
3. **Future-Proof Design**: Easy integration of new knowledge graph sources
4. **Development Simplicity**: Developers can work with mock graphs without licenses
5. **Performance Optimization**: Routes to fastest/best resource based on metrics

## Migration Path

For existing Biomapper code that directly references SPOKE:

1. **Abstract Interface**: Add abstraction layer above existing SPOKE client
2. **Configuration Adaptation**: Create default configuration for SPOKE schema
3. **Optional Dependency**: Make SPOKE-specific components optional
4. **Reference Implementation**: Keep SPOKE adapter as reference implementation

## Conclusion

The generalized knowledge graph strategy ensures Biomapper remains flexible, accessible, and future-proof while preserving the powerful capabilities of knowledge graph integration. This approach balances the benefits of specific resources like SPOKE with the need for universal accessibility and adaptability.
