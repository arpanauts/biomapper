# BioMapper Architecture

## Overview
BioMapper is designed to standardize biological entity names using a combination of API-based mapping and RAG (Retrieval Augmented Generation) approaches. The architecture follows a modular, domain-driven design with clear separation of concerns.

## Directory Structure
```
biomapper/
├── core/                      # Core abstractions and base classes
│   ├── base_client.py        # Base API client interface
│   ├── base_mapper.py        # Base mapping interfaces
│   ├── base_pipeline.py      # Base pipeline interface
│   ├── base_rag.py          # RAG-specific base classes
│   └── base_store.py        # Vector store interfaces
│
├── pipelines/                # Domain-specific implementations
│   ├── compounds/           # Compound/metabolite mapping
│   │   ├── compound_mapper.py
│   │   └── compound_pipeline.py
│   ├── proteins/            # Protein mapping
│   │   ├── protein_mapper.py
│   │   └── protein_pipeline.py
│   └── labs/                # Lab test mapping (future)
│
├── schemas/                  # Data models and schemas
├── monitoring/              # Metrics and monitoring
└── mapping/                # Legacy code (to be migrated)
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
