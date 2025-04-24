# Biomapper: Unified Toolkit for Biological Data Harmonization

## Overview & Objectives

- **Purpose**: Unified Python toolkit for biological entity mapping and data integration
- **Core Problem**: Biological data fragmentation across different ontologies and databases
- **Solution**: Single, standardized interface for entity mapping across ontologies
- **Goals**:
  - Simplify multi-omic data integration
  - Make biological data harmonization more accessible and reproducible
  - Improve mapping accuracy through innovative techniques
  - Provide high-performance solutions with intelligent caching

## Core Architecture

### Dual Database Architecture

#### Configuration Database (`metamapper.db`)
- Stores core configuration and knowledge:
  - Endpoints (data sources)
  - Mapping resources 
  - Ontology preferences
  - Mapping paths
  - Performance metrics
- Typically shared across users via Git
- Located at `/home/ubuntu/biomapper/data/metamapper.db`
- Generated from configuration files using `biomapper load` commands

#### Mapping Cache Database (`mapping_cache.db`) 
- Stores runtime mapping results
- Acts as a performance cache to avoid re-computing expensive mappings
- Located in user's home directory: `~/.biomapper/data/mapping_cache.db`
- Not tracked in Git due to size and user-specific content
- Includes expiration times for cached mappings
- Supports bidirectional transitivity for maximum efficiency

### System Components

- **Resource Metadata System**: Central orchestrator routing mapping operations
- **Enhanced Mappers**: Entity-specific mappers built on common foundation
  - Metabolite Mapper
  - Protein Mapper
  - Gene Mapper
- **Resource Adapters**: Connect system to various data sources
  - API Adapters
  - Database Connectors
  - Knowledge Graph Interfaces

## Smart Mapping System

### Ontology Preferences
- Each endpoint defines preferred ontologies (CHEBI, HMDB, PUBCHEM, etc.)
- Preferences have priority levels
- Stored in `endpoint_ontology_preferences` table

### Mapping Paths
- Pre-defined routes between different identifier systems
- Example: CHEBI → INCHIKEY → PUBCHEM
- Scored based on:
  - Performance metrics (speed, success rate)
  - Endpoint preferences
  - Path length
- System tracks successful paths and prioritizes them over time

### Mapping Workflow
1. **Path Selection**
   - Determine source ontology type
   - Find target endpoint's preferred ontologies
   - Select optimal mapping path based on preferences and historical performance

2. **Cache Check**
   - Query mapping cache for existing results
   - Return cached mapping if found with sufficient confidence

3. **Mapping Execution**
   - Execute each step in the mapping path
   - Transform entity ID through intermediate ontologies if needed
   - Apply confidence scoring at each step

4. **Validation & Caching**
   - Validate mapping results when possible
   - Store successful mappings in cache
   - Update usage statistics for paths

## Advanced Features

### RAG-Based Mapping
- Utilizes Retrieval Augmented Generation techniques
- Combines traditional mapping with AI-powered approaches
- Particularly valuable for complex or ambiguous mappings

### Multi-Provider RAG
- Integrates multiple data sources for improved mapping accuracy
- Uses specialized providers for different entity types
- Dynamically weights provider inputs based on confidence

### Metamapping
- Automatic discovery and execution of multi-step mapping paths
- Finds connections between seemingly disparate ontologies
- Supports novel data integration workflows

### Performance-Based Prioritization
- Resources prioritized based on historical performance
- Self-optimizing system learns from successful mappings
- Adapts to changing data landscapes and resource availability

## Supported Systems

### Knowledge Graph & Caching
- SPOKE Knowledge Graph
- SQLite Mapping Cache

### ID Standardization Tools
- RaMP-DB

### Mapping Services
- ChEBI
- UniChem
- UniProt
- RefMet
- KEGG
- PubChem

## Ontological Coverage

- **Metabolites**: HMDB, ChEBI, PubChem, KEGG, InChIKey
- **Genes**: Entrez, Ensembl, HGNC, Gene Symbol
- **Proteins**: UniProt, PDB, InterPro
- **Pathways**: Reactome, KEGG, Gene Ontology
- **Diseases**: MONDO, DOID, MeSH, OMIM
- **Plus**: Anatomy, Food, Pharmacologic entities, Chemical properties

## User Interfaces

1. **Command-Line Interface (CLI)**
   - Quick, scriptable entity mapping
   - Batch processing capabilities

2. **Python SDK**
   - Programmatic interface for developers
   - Integration into data science workflows

3. **FastAPI Web Interface** (in development)
   - Browser-based mapping interface
   - Interactive visualization of mapping paths

## Implementation Timeline

- **SQLite Mapping Cache**: 90% Complete (Q1 2025)
- **Resource Metadata System**: Planning (Q2 2025)
- **Web UI MVP**: Planning (Q2 2025)
- **UKBB Dataset Integration**: Not Started (Q3 2025)
- **Arivale Dataset Integration**: Not Started (Q3 2025)

## Key Benefits

- **Efficiency**: Avoids re-computation of expensive mappings
- **Adaptability**: Learns from successful mappings to improve over time
- **Portability**: Configuration database can be shared while keeping user-specific cache separate
- **Flexibility**: Supports multiple mapping strategies between ontologies
- **Performance Tracking**: Monitors and optimizes mapping paths based on real-world usage
- **Accessibility**: Makes complex biological data integration more approachable
- **Reproducibility**: Ensures consistent entity mapping across research projects

## Presentation Slide Organization

### Slide 1: Title
- **Title**: Biomapper: Unified Toolkit for Biological Data Harmonization

### Slide 2: The Problem
- Biological data is fragmented across different ontologies and databases
- Multi-omic data integration requires extensive manual mapping
- Current approaches lack standardization and reproducibility
- Time-consuming, error-prone process for researchers

### Slide 3: Our Solution
- **Purpose**: Unified Python toolkit for biological entity mapping and data integration
- **Solution**: Single, standardized interface for mapping across ontologies
- **Goals**:
  - Simplify multi-omic data integration
  - Make biological data harmonization more accessible and reproducible
  - Improve mapping accuracy through innovative techniques

### Slide 4: Core Architecture
- **Dual Database Architecture**:
  - Configuration Database: Shared knowledge and configuration
  - Mapping Cache Database: Performance-optimized storage
- **System Components**:
  - Resource Metadata System: Central orchestrator
  - Enhanced Mappers: Entity-specific implementations
  - Resource Adapters: Connections to diverse data sources

### Slide 5: Smart Mapping System
- **Ontology Preferences**: Priority-based ontology selection
- **Mapping Paths**: Optimized routes between identifier systems
- **Workflow**:
  1. Path Selection
  2. Cache Check  
  3. Mapping Execution
  4. Validation & Caching

### Slide 6: Advanced Features
- **RAG-Based Mapping**: AI-powered entity resolution
- **Multi-Provider RAG**: Combining multiple data sources
- **Metamapping**: Automatic multi-step path discovery
- **Performance-Based Prioritization**: Self-optimizing system

### Slide 7: Supported Systems & Coverage
- **Knowledge Graph & Caching**: SPOKE, SQLite Cache
- **ID Standardization**: RaMP-DB
- **Mapping Services**: ChEBI, UniChem, UniProt, RefMet, KEGG, PubChem
- **Ontological Coverage**:
  - Metabolites, Genes, Proteins, Pathways, Diseases, etc.

### Slide 8: User Interfaces
- **Command-Line Interface**: Scriptable entity mapping
- **Python SDK**: Programmatic integration
- **Web Interface**: Browser-based mapping (in development)

### Slide 9: Implementation Timeline
- **SQLite Mapping Cache**: 90% Complete (Q1 2025)
- **Resource Metadata System**: Planning (Q2 2025)
- **Web UI MVP**: Planning (Q2 2025)
- **Dataset Integrations**: UKBB, Arivale (Q3 2025)

### Slide 10: Key Benefits
- **Efficiency**: Avoids re-computation of expensive mappings
- **Adaptability**: Self-learning mapping system
- **Portability**: Shared configuration with user-specific caches  
- **Accessibility**: Makes data integration more approachable
- **Reproducibility**: Ensures consistent entity mapping