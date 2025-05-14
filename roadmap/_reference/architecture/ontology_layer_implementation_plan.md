# Biomapper Ontology Layer Implementation Plan

## Executive Summary

This document outlines the implementation plan for enhancing Biomapper with a generalized hybrid graph-based ontology layer that works with multiple knowledge graph sources, including but not limited to SPOKE (Scalable Precision Medicine Open Knowledge Engine). This architecture will provide comprehensive coverage of biological entity mappings while ensuring performance, flexibility, and independence from any specific licensed knowledge graph.

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Architecture Overview](#architecture-overview)
3. [Component Specifications](#component-specifications)
4. [Implementation Phases](#implementation-phases)
5. [Technical Requirements](#technical-requirements)
6. [Testing Strategy](#testing-strategy)
7. [Integration with Existing Codebase](#integration-with-existing-codebase)
8. [Future Enhancements](#future-enhancements)
9. [Appendix: Data Sources](#appendix-data-sources)

## Current State Assessment

### Existing Biomapper Capabilities

The current Biomapper implementation:
- Provides direct mapping for metabolites via API clients (ChEBI, RefMet, etc.)
- Includes basic knowledge graph integration capabilities (initially focused on SPOKE)
- Uses retrieval augmented generation (RAG) for semantic mapping
- Lacks a centralized mapping registry for persistent storage of discovered mappings
- Has no abstraction layer for different knowledge graph sources

### Limitations to Address

- Repeated API calls to external services for the same mapping requests
- No persistent storage of mapping relationships
- Limited capability to work with different knowledge graph sources
- Dependency on specific knowledge graphs that may require licenses
- No standardized configuration for knowledge graph schema mapping

## Architecture Overview

### High-Level Design

```
┌─────────────────┐    ┌────────────────────┐    ┌─────────────────┐
│                 │    │                    │    │                 │
│  Knowledge      │    │  Extension Graph   │    │  Custom         │
│  Graph Sources  │<-->│  (ArangoDB)        │<-->│  Knowledge      │
│  (Configurable) │    │                    │    │  Graphs         │
└─────────────────┘    └────────────────────┘    └─────────────────┘
         ↑                       ↑                        ↑
         │                       │                        │
         ↓                       ↓                        ↓
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│               Generalized Knowledge Graph Layer               │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                              ↑
                              │
                              ↓
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│                 Unified Ontology Layer                        │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                              ↑
                              │
                              ↓
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│               SQLite/PostgreSQL Mapping Cache                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Knowledge Graph Integration**: Abstracted connection to various knowledge graph sources
2. **Extension Graph**: Custom ArangoDB instance for supplemental ontologies
3. **Generalized Knowledge Graph Layer**: Abstraction layer for different graph implementations
4. **Unified Ontology Layer**: Coordinating layer between graphs and applications
5. **Mapping Cache**: SQL-based storage for performance optimization
6. **Configuration System**: Tools to manage different knowledge graph schemas

## Component Specifications

### 1. Knowledge Graph Integration Layer

**Purpose**: Provide a generalized interface to connect to and query various knowledge graph sources

**Key Classes**:
- `KnowledgeGraphClient`: Protocol for all graph clients (abstract base)
- `ArangoDBGraphClient`: Implementation for ArangoDB-based graphs
- `SPOKEGraphClient`: Reference implementation for SPOKE (extends ArangoDBGraphClient)
- `GraphConfigurationManager`: Manages configuration for different graph sources

**Features**:
- Pluggable client implementation system
- Standard query interface across different graph sources
- Configuration-driven schema mapping
- Error handling and resilience
- Connection pooling for performance

### 2. Extension Graph

**Purpose**: Store supplemental ontologies and relationships not covered by other knowledge graphs

**Key Classes**:
- `ExtensionGraphClient`: Client for custom ArangoDB instance
- `EntityManager`: CRUD operations for nodes and edges
- `DataImporter`: Tools for importing external ontologies

**Features**:
- Compatible schema with configurable mapping
- Support for custom ontologies (UNII, etc.)
- Automated data import pipelines
- Versioning of imported datasets
- Ability to function as a standalone knowledge graph

### 3. Generalized Knowledge Graph Layer

**Purpose**: Provide abstraction over various knowledge graph implementations

**Key Classes**:
- `KnowledgeGraphFactory`: Creates appropriate client implementations based on configuration
- `SchemaMapper`: Maps between different graph schemas based on configuration
- `GraphQueryBuilder`: Builds appropriate queries for different graph implementations
- `GraphClientRegistry`: Registry of available graph clients and capabilities

**Features**:
- Abstraction of specific knowledge graph implementations
- Dynamic client creation based on configuration
- Standard query interface regardless of underlying graph
- Runtime capability discovery

### 4. Unified Ontology Layer

**Purpose**: Provide a single interface for ontology operations across all graph sources

**Key Classes**:
- `UnifiedOntologyLayer`: Primary API for applications
- `MappingResolver`: Handles mapping requests across different graphs
- `PathFinder`: Discovers relationships between entities
- `OntologyRegistry`: Central registry of available ontologies

**Features**:
- Single interface for all mapping operations
- Transparent routing to appropriate knowledge graph
- Cross-graph path discovery
- Prioritization strategies for conflicting mappings
- Fallback mechanisms when primary sources are unavailable
- Graceful degradation when licensed sources aren't available

### 5. Mapping Cache

**Purpose**: Optimize performance through SQL-based caching

**Key Classes**:
- `MappingStore`: SQL database interface
- `CacheManager`: Cache invalidation and refresh
- `MappingSchema`: Database schema definition
- `StatisticsCollector`: Records performance metrics by source

**Features**:
- Fast lookups for frequent mappings
- Source tracking for each mapping
- Confidence scoring
- TTL-based expiration
- Performance metrics to inform intelligent routing

### 6. Configuration System

**Purpose**: Manage configuration for different knowledge graph sources

**Key Classes**:
- `KnowledgeGraphConfig`: Configuration for knowledge graph connections
- `SchemaConfiguration`: Mapping between graph schemas and standardized ontologies
- `CapabilityRegistry`: Tracks which ontologies are available in which knowledge graphs
- `ConfigurationValidator`: Validates configuration syntax and semantics

**Features**:
- Declarative configuration of knowledge graph sources
- Schema mapping configuration
- Environment-specific overrides
- Dynamic reconfiguration
- Version compatibility tracking

## Implementation Phases

### Phase 1: Knowledge Graph Abstraction (Weeks 1-4)

1. **Design Knowledge Graph Client Protocol**
   - Define abstract interfaces for knowledge graph operations
   - Create configuration schema for knowledge graph mapping
   - Implement validation for configuration formats

2. **Implement Reference Graph Clients**
   - Create ArangoDBGraphClient as base implementation
   - Implement SPOKEGraphClient as reference (optional dependency)
   - Develop testing mock clients for development without licensed resources

3. **Create Mapping Cache**
   - Design and implement SQL schema
   - Create MappingStore class
   - Add caching to existing mappers

### Phase 2: Core Functionality (Weeks 5-8)

1. **Develop Generalized Knowledge Graph Layer**
   - Build factory pattern for client creation
   - Implement schema mapping based on configuration
   - Create unified query interface

2. **Implement Unified Ontology Layer**
   - Build primary API interface
   - Implement routing logic with fallbacks
   - Create relationship discovery tools
   - Add graceful degradation when knowledge graphs are unavailable

3. **Configure Extension Graph**
   - Set up ArangoDB instance with configurable schema
   - Implement standalone operation capability
   - Create data import pipelines
   - Test with and without SPOKE availability

### Phase 3: Integration and Enhancement (Weeks 9-12)

1. **Integrate with Existing Biomapper Components**
   - Modify MetaboliteNameMapper to use ontology layer
   - Update RAG components to leverage unified mappings
   - Create adapter for legacy interfaces

2. **Add Advanced Features**
   - Implement cross-graph path finding
   - Create mapping confidence scoring
   - Add relationship inference algorithms

3. **Performance Optimization**
   - Implement connection pooling
   - Add query caching
   - Optimize common mapping patterns

### Phase 4: Testing and Refinement (Weeks 13-16)

1. **Comprehensive Testing**
   - Unit and integration testing
   - Performance benchmarking
   - Simulated SPOKE updates

2. **Documentation and Examples**
   - API documentation
   - Usage examples
   - Migration guides

3. **Final Optimization**
   - Address performance bottlenecks
   - Fine-tune caching strategies
   - Optimize memory usage

## Technical Requirements

### Software Dependencies

- **ArangoDB**: 3.9+ for both SPOKE and extension graph
- **Python**: 3.11+
- **Database Libraries**:
  - `python-arango`: For ArangoDB integration
  - `sqlalchemy`: For mapping cache
  - `alembic`: For database migrations
- **Utilities**:
  - `pydantic`: For data validation
  - `asyncio`: For asynchronous operations
  - `tenacity`: For resilient API calls

### Hardware Recommendations

- **Development**: Standard development environment
- **Testing**: 8GB+ RAM, SSD storage
- **Production**: 16GB+ RAM, SSD storage, distributed architecture

### External APIs and Services

- SPOKE API access
- ChEBI, RefMet, and other existing Biomapper sources
- FDA UNII API or data download access

## Testing Strategy

### Unit Testing

- Test each component in isolation
- Mock external dependencies
- Achieve 90%+ code coverage

### Integration Testing

- Test component interactions
- Verify cross-graph operations
- Validate cache consistency

### Performance Testing

- Benchmark mapping operations
- Test with large datasets (10K+ entities)
- Verify cache effectiveness

### Version Migration Testing

- Test with historical SPOKE releases
- Verify mapping preservation
- Measure migration time and accuracy

## Integration with Existing Codebase

### Integration Points

1. **MetaboliteNameMapper**:
   - Modify to use UnifiedOntologyLayer
   - Maintain backward compatibility

2. **SPOKEDBClient and SPOKEMapper**:
   - Enhance with version awareness
   - Connect to new unified layer

3. **RAG Components**:
   - Update to leverage cached mappings
   - Add hooks for relationship discovery

### Code Structure Changes

```
biomapper/
├── biomapper/
│   ├── core/
│   ├── ...
│   ├── ontology/           # New module
│   │   ├── __init__.py
│   │   ├── layer.py        # UnifiedOntologyLayer
│   │   ├── cache.py        # MappingStore
│   │   ├── extension/      # Extension graph
│   │   └── version.py      # Version management
│   ├── spoke/              # Enhanced module
│   │   ├── __init__.py
│   │   ├── client.py       # Existing file
│   │   ├── adapter.py      # New version adapter
│   │   └── mapper.py       # Enhanced mapper
│   └── ...
```

## Future Enhancements

### Phase 5: Advanced Features (Future)

1. **Semantic Matching**:
   - Enhance RAG with graph embeddings
   - Add fuzzy matching capabilities
   - Implement ML-powered mapping suggestions

2. **Additional Ontologies**:
   - LOINC clinical laboratory tests
   - SNOMED clinical terms
   - GO gene ontology

3. **User Interface**:
   - Visual graph explorer
   - Mapping dashboard
   - Relationship browser

4. **Enterprise Features**:
   - Multi-user support
   - Access control
   - Audit logging

## Appendix: Data Sources

### Primary Ontologies

1. **SPOKE**: Main knowledge graph
   - Source: http://spoke.ucsf.edu/
   - Update frequency: Variable

2. **FDA UNII**: Drug ingredients
   - Source: https://fdasis.nlm.nih.gov/srs/
   - Update frequency: Monthly

3. **ChEBI**: Chemical entities
   - Source: https://www.ebi.ac.uk/chebi/
   - Update frequency: Monthly

4. **RefMet**: Metabolite reference
   - Source: https://www.metabolomicsworkbench.org/
   - Update frequency: Quarterly

### Additional Ontologies

1. **LOINC**: Laboratory tests
   - Source: https://loinc.org/
   - Update frequency: Biannually

2. **UniProt**: Protein database
   - Source: https://www.uniprot.org/
   - Update frequency: Monthly

3. **KEGG**: Pathway database
   - Source: https://www.genome.jp/kegg/
   - Update frequency: Monthly
