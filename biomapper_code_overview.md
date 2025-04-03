# Biomapper: Biological Data Harmonization and Ontology Mapping Toolkit

## Purpose and Overview
Biomapper is a unified Python toolkit designed for standardizing biological identifiers and mapping between various biological ontologies. It facilitates multi-omic data integration by providing a consistent interface for working with biological entities, particularly metabolites. The library includes both traditional database-driven approaches and modern AI-powered techniques.

## Core Components

### 1. Resource Metadata System
- **`ResourceMetadataManager`**: Central class for managing resource capabilities, performance metrics, and ontology coverage
- **`MappingDispatcher`**: Orchestrates mapping operations across resources based on capabilities and performance
- **`MetamappingEngine`**: Handles multi-step mapping paths when direct mappings aren't available
- Provides intelligent routing of mapping operations and optimizes performance

### 2. Enhanced Entity Mappers
- **`AbstractEntityMapper`**: Base class for all entity mappers with common functionality
- **`MetaboliteNameMapper`**: Maps metabolite names to standard identifiers (ChEBI, HMDB, etc.)
- **`ProteinNameMapper`**: Maps protein names and identifiers (UniProt, PDB, etc.)
- **`GeneMapper`**: Maps gene symbols and identifiers (Entrez, Ensembl, etc.)
- **`DiseaseMapper`**: Maps disease terms to standard ontologies (MONDO, DOID, etc.)
- **`PathwayMapper`**: Maps pathway names to standard identifiers (Reactome, KEGG, etc.)

### 3. Resource Adapters
- **`CacheResourceAdapter`**: Interfaces with the SQLite mapping cache
- **`SpokeResourceAdapter`**: Connects to the SPOKE knowledge graph
- **`APIResourceAdapter`**: Generic adapter for external API clients
  - **`ChEBIAdapter`**: Chemical Entities of Biological Interest database integration
  - **`HMDBAdapter`**: Human Metabolome Database integration
  - **`UniChemAdapter`**: Cross-referencing of chemical structure identifiers
  - **`UniProtAdapter`**: Universal Protein Resource integration

### 4. API Clients
- **`ChEBIClient`**: Client for the ChEBI database
- **`RefMetClient`**: Client for the RefMet database
- **`UniChemClient`**: Client for the UniChem service
- **`UniProtClient`**: Client for the UniProt database

### 5. RAG Components
- **`ChromaCompoundStore`**: Vector database for storing compound information
- **`PromptManager`**: Manages prompts for LLM-based mapping
- **`RAGMapper`**: Mapping using retrieval augmented generation

### 6. Utilities
- Monitoring tools for tracking performance
- Optimization utilities for LLM prompts
- Data loaders and processors

## Key Technologies
- **Knowledge Graphs**: SPOKE Knowledge Graph integration for biological relationships
- **SQLite Database**: Performance tracking and mapping cache
- **Vector Databases**: ChromaDB for embedding storage and retrieval
- **LLM Integration**: Support for OpenAI (GPT-4) and other models
- **Embedding Models**: Sentence transformers for semantic search
- **Biological Databases**: ChEBI, HMDB, PubChem, RefMet, UniChem, UniProt and others

## Project Structure
```
biomapper/
├── biomapper/          # Main package source code
│   ├── core/           # Core abstract classes and base functionality
│   ├── llm/            # LLM integration components
│   ├── loaders/        # Data loading utilities
│   ├── mapping/        # Ontology mapping components
│   │   ├── adapters/   # Resource adapters (cache, spoke, api)
│   │   ├── metadata/   # Resource metadata system
│   │   │   ├── manager.py      # ResourceMetadataManager
│   │   │   ├── dispatcher.py   # MappingDispatcher
│   │   │   ├── metamapping.py  # MetamappingEngine
│   │   │   └── initialize.py   # Database initialization
│   │   ├── clients/    # Database API clients
│   │   ├── rag/        # Retrieval augmented generation tools
│   │   ├── base_mapper.py      # AbstractEntityMapper
│   │   ├── metabolite_mapper.py# Enhanced MetaboliteNameMapper
│   │   ├── protein_mapper.py   # ProteinNameMapper
│   │   └── gene_mapper.py      # GeneMapper
│   ├── monitoring/     # Performance monitoring tools
│   ├── pipelines/      # Data processing pipelines
│   ├── schemas/        # Data schemas and models
│   ├── spoke/          # SPOKE database integration
│   └── utils/          # Utility functions
├── docs/               # Documentation
│   └── source/         # Source documentation files
│       └── architecture/# Architecture documentation
│           ├── resource_metadata_system.md # Metadata system docs
│           ├── metamapping.md              # Metamapping docs
│           └── overview.md                 # Architecture overview
├── examples/           # Example scripts and tutorials
├── tests/              # Test suite
└── roadmap/            # Implementation plans and roadmaps
```

## Workflow Examples

### 1. Enhanced Metabolite Mapping with Resource Metadata System
```python
from biomapper.mapping import MetaboliteNameMapper

# Initialize the enhanced mapper
mapper = MetaboliteNameMapper()

# Map a metabolite name to ChEBI ID
results = await mapper.map_name_to_chebi("glucose")

# Or synchronously if preferred
results = mapper.map_name_to_chebi_sync("glucose")

# Access results
for result in results:
    print(f"ChEBI ID: {result['target_id']}, Confidence: {result['confidence']}")
    
# Map using a preferred resource
results = await mapper.map_entity(
    source_id="caffeine",
    source_type="metabolite_name",
    target_type="hmdb",
    preferred_resource="unichem_api"
)
```

### 2. Multi-Step Mapping (Metamapping)
```python
from biomapper.mapping import MetaboliteNameMapper

# Initialize the mapper
mapper = MetaboliteNameMapper()

# This will automatically use metamapping if needed
# (e.g., PubChem → ChEBI → HMDB if no direct mapping exists)
results = await mapper.map_entity(
    source_id="CID123456",
    source_type="pubchem",
    target_type="hmdb"
)

# Check if result came from metamapping
for result in results:
    if result["source"] == "metamapping":
        # View the path that was used
        path = result["metadata"]["mapping_path"]
        for step in path:
            print(f"{step['source_id']} ({step['source_type']}) → "
                  f"{step['target_id']} ({step['target_type']}) "
                  f"via {step['resource']}")
```

### 3. LLM-Based Mapping
```python
from biomapper.mapping.llm_mapper import LLMMapper

mapper = LLMMapper(model="gpt-4")
result = mapper.map_term("ATP", target_ontology="CHEBI")
```

### 4. RAG-Based Mapping
```python
# Requires setup of ChromaDB and configuration
from biomapper.mapping.rag.store import ChromaCompoundStore
from biomapper.mapping.rag.mapper import RAGMapper

store = ChromaCompoundStore()
mapper = RAGMapper(vector_store=store)
result = mapper.map_compound("caffeine")
```

## Dependencies
- Python 3.11+
- Key libraries: pandas, numpy, requests, chromadb, openai, dspy-ai, rdkit
- Development tools: pytest, mypy, ruff, sphinx

## Configuration
- Uses environment variables for API keys (OpenAI, etc.)
- Configuration for vector stores and other components via `.env` files

## Key Features

### Resource Metadata System
- **Capability Registration**: Resources register what mappings they can perform
- **Performance Tracking**: System learns which resources work best for specific mapping types
- **Intelligent Routing**: Mapping requests are routed to the most appropriate resources
- **Fallback Mechanism**: System automatically tries alternative resources if preferred ones fail

### Metamapping
- **Path Discovery**: Finds paths between ontologies when no direct mapping exists
- **Multi-Step Execution**: Executes mappings through intermediate ontologies
- **Confidence Propagation**: Calculates combined confidence scores across steps
- **Path Caching**: Caches discovered paths and intermediate results

### Hybrid Architecture
- **SPOKE Knowledge Graph**: Primary source of biological relationships
- **Extension Graph**: Fills gaps in SPOKE's coverage
- **SQL-Based Mapping Cache**: Optimizes performance for frequently used mappings
- **API Integration**: Connects to numerous biological databases

## Roadmap
- Expand entity coverage to more biological types
- Enhance visualization of mapping paths
- Improve confidence scoring algorithms
- Develop parallel path execution for metamapping
- Create a unified web interface for mapping operations
- Add support for more pathway databases (KEGG, Reactome)
- Implement advanced caching strategies
