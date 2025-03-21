# Biomapper: Biological Data Harmonization and Ontology Mapping Toolkit

## Purpose and Overview
Biomapper is a unified Python toolkit designed for standardizing biological identifiers and mapping between various biological ontologies. It facilitates multi-omic data integration by providing a consistent interface for working with biological entities, particularly metabolites. The library includes both traditional database-driven approaches and modern AI-powered techniques.

## Core Components

### 1. Standardization
- `MetaboliteNameMapper`: Central class for mapping metabolite names to standard identifiers
- `RaMPClient`: Legacy interface for the Rapid Mapping Database for metabolites and pathways
- Includes classification and parsing of various metabolite naming patterns

### 2. Mapping
- **API Clients**: Interfaces to various biological databases
  - `ChEBIClient`: Chemical Entities of Biological Interest database integration
  - `RefMetClient`: Reference list of metabolite names and identifiers
  - `UniChemClient`: Cross-referencing of chemical structure identifiers
- **RAG Components**: AI-powered mapping tools
  - `ChromaCompoundStore`: Vector database for storing compound information
  - `PromptManager`: Manages prompts for LLM-based mapping
  - Utilizes retrieval augmented generation with multiple data sources

### 3. Core Architecture
- `BaseClient`: Foundation for all API clients
- `BaseMapper`: Abstract base for mapping implementations
- `BasePipeline`: Framework for building data processing pipelines
- `BaseRAG`: Base class for retrieval augmented generation components
- `BaseStore`: Interface for vector storage systems

### 4. Utilities
- Monitoring tools for tracking performance
- Optimization utilities for LLM prompts
- Data loaders and processors

## Key Technologies
- **Vector Databases**: ChromaDB for embedding storage and retrieval
- **LLM Integration**: Support for OpenAI (GPT-4) and other models
- **Embedding Models**: Sentence transformers for semantic search
- **Biological Databases**: ChEBI, RefMet, UniChem, and others

## Project Structure
```
biomapper/
├── biomapper/          # Main package source code
│   ├── core/           # Core abstract classes and base functionality
│   ├── llm/            # LLM integration components
│   ├── loaders/        # Data loading utilities
│   ├── mapping/        # Ontology mapping components
│   │   ├── clients/    # Database API clients
│   │   ├── rag/        # Retrieval augmented generation tools
│   ├── monitoring/     # Performance monitoring tools
│   ├── pipelines/      # Data processing pipelines
│   ├── processors/     # Data processing utilities
│   ├── schemas/        # Data schemas and models
│   ├── spoke/          # SPOKE database integration
│   ├── standardization/# ID standardization components
│   └── utils/          # Utility functions
├── docs/               # Documentation
├── examples/           # Example scripts and tutorials
├── tests/              # Test suite
└── scripts/            # Utility scripts
```

## Workflow Examples
1. **Basic Metabolite Mapping**:
   ```python
   from biomapper import MetaboliteNameMapper
   
   mapper = MetaboliteNameMapper()
   result = mapper.map_single_name("glucose")
   ```

2. **LLM-Based Mapping**:
   ```python
   from biomapper.mapping.llm_mapper import LLMMapper
   
   mapper = LLMMapper(model="gpt-4")
   result = mapper.map_term("ATP", target_ontology="CHEBI")
   ```

3. **RAG-Based Mapping**:
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

## Roadmap
- Enhance RAG-based mapping with additional data sources
- Improve compound name normalization
- Add support for pathway databases (KEGG, Reactome)
- Expand test coverage and documentation
