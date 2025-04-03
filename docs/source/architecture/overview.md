# BioMapper Architecture

## Overview
BioMapper is designed to standardize biological entity names and facilitate mapping between different biological ontologies. It combines traditional database-driven approaches, API-based mapping, and modern RAG (Retrieval Augmented Generation) techniques. The architecture follows a modular, domain-driven design with clear separation of concerns and leverages the Resource Metadata System for intelligent mapping orchestration.

## Core Components

### Resource Metadata System
The Resource Metadata System is a central component that orchestrates mapping operations across multiple resources. It tracks resource capabilities, performance metrics, and ontology coverage to enable intelligent routing of mapping requests.

- **ResourceMetadataManager**: Manages resource registration and performance tracking
- **MappingDispatcher**: Routes mapping operations to appropriate resources
- **MetamappingEngine**: Handles multi-step mappings when direct mappings aren't available

### Enhanced Mappers
A hierarchy of entity-specific mappers built on a common foundation:

- **AbstractEntityMapper**: Base class for all entity mappers with common functionality
- **MetaboliteNameMapper**: Maps metabolite names to standard identifiers
- **ProteinNameMapper**: Maps protein names and identifiers
- **GeneMapper**: Maps gene identifiers across different nomenclatures
- **DiseaseMapper**: Maps disease terms to standard ontologies
- **PathwayMapper**: Maps pathway names to standard identifiers

### Resource Adapters
Adapters connect the mapping system to various data sources:

- **CacheResourceAdapter**: Interfaces with the SQLite mapping cache
- **SpokeResourceAdapter**: Connects to the SPOKE knowledge graph
- **APIResourceAdapter**: Generic adapter for external API clients

## Directory Structure
```
biomapper/
├── core/                      # Core abstractions and base classes
│   ├── base_client.py        # Base API client interface
│   └── base_store.py        # Vector store interfaces
│
├── mapping/                 # Enhanced mapping functionality
│   ├── base_mapper.py       # AbstractEntityMapper base class
│   ├── metabolite_mapper.py # Enhanced metabolite name mapper
│   ├── protein_mapper.py    # Protein name mapper
│   ├── gene_mapper.py       # Gene identifier mapper
│   ├── adapters/            # Resource adapters
│   │   ├── cache_adapter.py # SQLite cache adapter
│   │   ├── spoke_adapter.py # SPOKE knowledge graph adapter
│   │   └── api_adapter.py   # Generic API adapter
│   ├── metadata/            # Resource metadata system
│   │   ├── manager.py       # ResourceMetadataManager
│   │   ├── dispatcher.py    # MappingDispatcher
│   │   ├── metamapping.py   # MetamappingEngine
│   │   └── initialize.py    # Database initialization
│   ├── clients/             # API clients
│   │   ├── chebi_client.py  # ChEBI API client
│   │   ├── hmdb_client.py   # HMDB API client
│   │   └── unichem_client.py# UniChem API client
│   └── rag/                 # RAG components
│
├── llm/                      # LLM integration
├── pipelines/                # Processing pipelines
├── schemas/                  # Data models and schemas
├── monitoring/               # Metrics and monitoring
└── cli/                     # Command-line interface
```

## Core Abstractions

### Base Classes
1. `BaseAPIClient` - Common interface for API clients
   - Async HTTP requests
   - Batch processing
   - Error handling
   - Session management

2. `BaseMapper` - Interface for entity mapping
   - API-based mapping (`APIMapper`)
   - RAG-based mapping (`RAGMapper`)
   - Common mapping result types

3. `BasePipeline` - Pipeline orchestration
   - Entity mapping workflow
   - RAG integration
   - Metrics collection

4. `BaseVectorStore` - Vector storage interface
   - Document storage
   - Similarity search
   - Generic typing support

### Domain-Specific Implementation Pattern
Each domain (compounds, proteins, labs) follows this structure:

1. `{domain}_mapper.py`:
   - `{Domain}Document` - Domain-specific document type
   - `{Domain}Mapper` - Domain-specific mapping logic

2. `{domain}_pipeline.py`:
   - `{Domain}NameMapper` - Domain-specific name mapping
   - `{Domain}MappingPipeline` - Domain-specific pipeline

## Key Architectural Patterns

### Resource Metadata System

The Resource Metadata System introduces several key patterns:

1. **Capability-Based Routing**: Resources register their capabilities (which mappings they can perform), and mapping operations are routed to appropriate resources.

2. **Performance-Based Prioritization**: Resources are prioritized based on their historical performance for specific mapping types.

3. **Metamapping**: When no direct mapping is available, the system can automatically discover and execute multi-step mapping paths.

4. **Resource Adapters**: A common interface for different types of resources (databases, APIs, knowledge graphs).

### Data Flow

```
User Request → Entity Mapper → MappingDispatcher → Resource Adapters → External Resources
                                     ↑                                        ↓
                                     └── ResourceMetadataManager ← Performance Metrics
```

## Advanced Features

### Metamapping

The metamapping system enables complex multi-step mappings:

1. **Path Discovery**: Uses breadth-first search to find paths between ontologies
2. **Confidence Propagation**: Multiplies confidence scores across steps
3. **Result Caching**: Caches both intermediate and final results

See [Metamapping](./metamapping.md) for detailed documentation.

### Integration with SPOKE Knowledge Graph

Biomapper integrates with the SPOKE Knowledge Graph to leverage its rich biological relationships:

1. **Direct Querying**: Efficiently retrieves entity mappings from the graph database
2. **Path Discovery**: Uses graph traversal for efficient metamapping
3. **Extensibility**: Complements SPOKE with additional mappings when needed

Refer to [Resource Metadata System](./resource_metadata_system.md) for more details on the overall architecture.

## Naming Conventions

### Files and Directories
- Use lowercase with underscores
- Include domain prefix for domain-specific files
- Use descriptive suffixes (_mapper, _pipeline, etc.)
- Examples:
  - `compound_mapper.py`
  - `protein_pipeline.py`

### Classes
- Use PascalCase
- Include domain prefix for domain-specific classes
- Use descriptive suffixes (Mapper, Pipeline, etc.)
- Examples:
  - `CompoundDocument`
  - `ProteinMappingPipeline`

### Methods and Functions
- Use snake_case
- Use descriptive verbs
- Examples:
  - `map_entity`
  - `process_names`

## Workflow

### Entity Mapping Process
1. Input: List of entity names
2. Initial API-based mapping
3. Confidence scoring
4. RAG-based mapping for low-confidence matches
5. Result aggregation and metrics collection

### RAG Integration
1. Vector store initialization
2. Document embedding
3. Similarity search
4. LLM-based mapping
5. Confidence scoring and validation

## Future Considerations

### Planned Domains
- Lab Tests
- Diseases
- Phenotypes
- Clinical Measurements

### Optimizations
- Batch processing improvements
- Caching strategies
- Parallel processing

### Monitoring
- Performance metrics
- Mapping success rates
- RAG effectiveness tracking

## Migration Guide

### From Legacy Code
1. Identify domain-specific code
2. Create new domain directory in `pipelines/`
3. Implement domain-specific mapper and pipeline
4. Update imports and dependencies
5. Add tests and documentation
6. Remove legacy code

### Best Practices
1. Follow naming conventions strictly
2. Implement all abstract methods
3. Add comprehensive docstrings
4. Include type hints
5. Add unit tests
6. Update documentation
