# Biomapper Ontology Layer Implementation Plan

## Executive Summary

This document outlines the implementation plan for enhancing Biomapper with a hybrid graph-based ontology layer that combines SPOKE (Scalable Precision Medicine Open Knowledge Engine) with a custom extension graph. This architecture will provide comprehensive coverage of biological entity mappings while ensuring performance, flexibility, and resilience to SPOKE updates.

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
- Includes basic SPOKE integration via SPOKEDBClient and SPOKEMapper
- Uses retrieval augmented generation (RAG) for semantic mapping
- Lacks a centralized mapping registry for persistent storage of discovered mappings
- Has no mechanism to handle SPOKE version updates

### Limitations to Address

- Repeated API calls to external services for the same mapping requests
- No persistent storage of mapping relationships
- No supplementation for ontologies missing from SPOKE (e.g., FDA UNII)
- No mechanism to maintain mappings across SPOKE version updates

## Architecture Overview

### High-Level Design

```
┌─────────────────┐    ┌────────────────────┐
│                 │    │                    │
│  SPOKE Graph    │    │  Extension Graph   │
│  (ArangoDB)     │<-->│  (ArangoDB)        │
│                 │    │                    │
└─────────────────┘    └────────────────────┘
         ↑                       ↑
         │                       │
         ↓                       ↓
┌─────────────────────────────────────────┐
│                                         │
│         Unified Ontology Layer          │
│                                         │
└─────────────────────────────────────────┘
                   ↑
                   │
                   ↓
┌─────────────────────────────────────────┐
│                                         │
│     SQLite/PostgreSQL Mapping Cache     │
│                                         │
└─────────────────────────────────────────┘
```

### Key Components

1. **SPOKE Integration**: Connection to SPOKE knowledge graph
2. **Extension Graph**: Custom ArangoDB instance for supplemental ontologies
3. **Unified Ontology Layer**: Coordinating layer between graphs and applications
4. **Mapping Cache**: SQL-based storage for performance optimization
5. **Version Management**: Tools to handle SPOKE updates

## Component Specifications

### 1. SPOKE Integration Layer

**Purpose**: Connect to and query SPOKE knowledge graph

**Key Classes**:
- `SPOKEDBClient`: Client for ArangoDB connections (existing)
- `SPOKEVersionAdapter`: Interface for version-specific SPOKE queries
- `SPOKENodeFetcher`: Utility for retrieving and parsing SPOKE nodes

**Features**:
- Version detection and adaptation
- Query optimization for common entity types
- Error handling and resilience
- Connection pooling for performance

### 2. Extension Graph

**Purpose**: Store supplemental ontologies and relationships not covered by SPOKE

**Key Classes**:
- `ExtensionGraphClient`: Client for custom ArangoDB instance
- `EntityManager`: CRUD operations for nodes and edges
- `DataImporter`: Tools for importing external ontologies

**Features**:
- Schema compatible with SPOKE for seamless integration
- Support for custom ontologies (UNII, etc.)
- Automated data import pipelines
- Versioning of imported datasets

### 3. Unified Ontology Layer

**Purpose**: Provide unified access to both SPOKE and extension graph

**Key Classes**:
- `UnifiedOntologyLayer`: Primary API for applications
- `MappingResolver`: Handles mapping requests across graphs
- `PathFinder`: Discovers relationships between entities
- `OntologyRegistry`: Central registry of available ontologies

**Features**:
- Single interface for all mapping operations
- Transparent routing to appropriate graph
- Cross-graph path discovery
- Prioritization strategies for conflicting mappings

### 4. Mapping Cache

**Purpose**: Optimize performance through SQL-based caching

**Key Classes**:
- `MappingStore`: SQL database interface
- `CacheManager`: Cache invalidation and refresh
- `MappingSchema`: Database schema definition

**Features**:
- Fast lookups for frequent mappings
- Source tracking for each mapping
- Confidence scoring
- TTL-based expiration

### 5. Version Management

**Purpose**: Handle SPOKE version updates

**Key Classes**:
- `VersionDetector`: Detects SPOKE version
- `OntologyMigrator`: Migrates mappings between versions
- `ValidationService`: Validates mappings against new versions

**Features**:
- Automated version change detection
- Selective cache invalidation
- Validation of existing mappings
- Metrics on version compatibility

## Implementation Phases

### Phase 1: Foundation (Weeks 1-4)

1. **Implement SPOKE Version Adapter**
   - Create version detection mechanism
   - Develop adapter for current SPOKE version
   - Test with existing SPOKEDBClient

2. **Create Mapping Cache**
   - Design and implement SQL schema
   - Create MappingStore class
   - Add caching to existing mappers

3. **Set Up Extension Graph**
   - Configure ArangoDB instance
   - Define compatible schema
   - Create client and basic CRUD operations

### Phase 2: Core Functionality (Weeks 5-8)

1. **Develop Unified Ontology Layer**
   - Build primary API interface
   - Implement routing logic
   - Create relationship discovery tools

2. **Add First Supplemental Ontology**
   - Import FDA UNII data to extension graph
   - Create drug-ingredient mappings
   - Test cross-graph queries

3. **Implement Version Management**
   - Create version detection
   - Build basic migration tools
   - Test with simulated version change

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
