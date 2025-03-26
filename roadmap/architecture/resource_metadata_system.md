# Resource Metadata System for Biomapper

## Executive Summary

This document outlines the design and implementation plan for a Resource Metadata System in Biomapper. This system will orchestrate the flow of mapping operations across multiple resources, including the SQLite cache, SPOKE knowledge graph, and external APIs. By maintaining metadata about each resource's capabilities, the system can intelligently route queries to the most appropriate resource, optimizing for performance, availability, and data freshness.

## Background and Motivation

During the implementation of the SQLite mapping cache and its integration with SPOKE, we identified a need for a more structured approach to resource management. The key observations were:

1. Different resources have varying strengths and weaknesses:
   - SQLite cache: Fast direct lookups, but limited to previously seen mappings
   - SPOKE graph: Rich relationships but slower for simple lookups
   - External APIs: Comprehensive but rate-limited and potentially costly

2. We need a systematic way to determine:
   - Which resource to query first for a given mapping task
   - When to sync data between resources
   - How to measure and optimize performance

## System Design

### Core Components

1. **ResourceMetadataManager**
   - Central registry of all mapping resources
   - Maintains metadata about resource capabilities and performance
   - Makes intelligent routing decisions

2. **MappingDispatcher**
   - Orchestrates mapping operations across resources
   - Implements fallback logic when preferred resources fail
   - Collects performance metrics to inform future routing decisions

3. **SQLite Metadata Schema**
   - Extends the existing mapping cache database
   - Stores resource capabilities, ontology coverage, and performance metrics

### Database Schema

The metadata will be stored in the existing SQLite cache database with the following additional tables:

```sql
-- Resources available to the system
CREATE TABLE resource_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_name TEXT NOT NULL UNIQUE,
    resource_type TEXT NOT NULL,  -- 'cache', 'graph', 'api', etc.
    connection_info TEXT,         -- JSON with connection details
    priority INTEGER DEFAULT 0,   -- Default priority
    is_active BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ontology types supported by each resource
CREATE TABLE ontology_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    ontology_type TEXT NOT NULL,  -- e.g., 'chebi', 'hmdb', etc.
    support_level TEXT NOT NULL,  -- 'full', 'partial', 'none'
    entity_count INTEGER,         -- Approximate count if available
    last_updated TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resource_metadata(id),
    UNIQUE (resource_id, ontology_type)
);

-- Performance metrics for operations
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    operation_type TEXT NOT NULL,  -- 'lookup', 'map', etc.
    source_type TEXT,
    target_type TEXT,
    avg_response_time_ms REAL,
    success_rate REAL,             -- 0.0 to 1.0
    sample_count INTEGER,
    last_updated TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resource_metadata(id),
    UNIQUE (resource_id, operation_type, source_type, target_type)
);

-- Mapping operation logs (for performance analysis)
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    operation_type TEXT NOT NULL,
    source_type TEXT,
    target_type TEXT,
    query TEXT,                   -- Simplified query representation
    response_time_ms INTEGER,
    status TEXT,                  -- 'success', 'error', etc.
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resource_metadata(id)
);
```

## Implementation Plan

### Phase 1: Metadata Infrastructure (Week 1)

1. **Schema Implementation**
   - Add metadata tables to the SQLite schema
   - Create SQLAlchemy models
   - Implement migration scripts

2. **Core Classes**
   - Implement ResourceMetadataManager
   - Implement MappingDispatcher
   - Create resource registration mechanism

3. **Initial Resource Adapters**
   - SQLite cache adapter
   - SPOKE graph adapter
   - External API adapter interface

### Phase 2: Integration and Optimization (Week 2)

1. **Performance Tracking**
   - Implement metrics collection
   - Create analysis utilities
   - Develop optimization algorithms

2. **Resource Synchronization**
   - Implement bidirectional sync between cache and SPOKE
   - Add configurable sync policies
   - Create sync scheduling system

3. **Smart Routing**
   - Implement adaptive routing based on performance history
   - Add fallback mechanisms
   - Develop failure recovery strategies

### Phase 3: Dataset Integration (Week 3)

1. **Dataset Resource Type**
   - Implement dataset resource adapter
   - Create dataset metadata schema
   - Develop dataset import/export utilities

2. **Specific Dataset Integration**
   - Arivale dataset integration
   - UKBB dataset integration
   - Custom mapping transformations

## Usage Examples

### Configuration

```python
# Initialize and configure the system
metadata_manager = ResourceMetadataManager()

# Register resources
metadata_manager.register_resource(
    name="sqlite_cache",
    resource_type="cache",
    connection_info={"data_dir": "/path/to/data", "db_name": "mappings.db"},
    priority=10  # Highest priority
)

metadata_manager.register_resource(
    name="spoke_graph",
    resource_type="graph",
    connection_info={"host": "localhost", "port": 8529, "db": "spoke23_human"},
    priority=5
)

metadata_manager.register_resource(
    name="chebi_api",
    resource_type="api",
    connection_info={"base_url": "https://www.ebi.ac.uk/chebi/webservices/"},
    priority=1
)

# Register ontology coverage
metadata_manager.register_ontology_coverage(
    resource_name="sqlite_cache",
    ontology_type="chebi",
    support_level="full"
)
```

### Mapping Operations

```python
# Create dispatcher with registered resources
dispatcher = MappingDispatcher(metadata_manager)

# Map an entity - automatically uses the best resource
result = await dispatcher.map_entity(
    source_id="glucose",
    source_type="compound_name",
    target_type="chebi"
)

# Force use of a specific resource
result = await dispatcher.map_entity(
    source_id="glucose",
    source_type="compound_name",
    target_type="chebi",
    resource_name="chebi_api"  # Override automatic selection
)
```

### Synchronization

```python
# Synchronize resources
sync_manager = ResourceSyncManager(metadata_manager)

# Sync specific entity types
await sync_manager.sync_resources(
    source="spoke_graph",
    target="sqlite_cache",
    entity_types=["Compound", "Protein"],
    bidirectional=True
)

# Schedule regular syncs
sync_manager.schedule_sync(
    source="sqlite_cache",
    target="spoke_graph",
    interval_hours=24,
    entity_types=["chebi", "hmdb"],
    only_new=True
)
```

## Integration with Existing Components

The metadata system will integrate with:

1. **SQLite Mapping Cache**
   - First resource to be queried for direct mappings
   - Performance benefits from indexed lookups

2. **SPOKE Knowledge Graph**
   - Secondary resource for complex relationship queries
   - Source of new mappings to populate the cache

3. **Cache-Aware Mapper**
   - Will use the dispatcher for intelligent resource selection
   - Better performance through optimized routing

4. **Biomapper API**
   - Will expose resource metadata through management endpoints
   - Allows configuration of resource priorities

## Conclusion

The Resource Metadata System transforms Biomapper from a collection of individual components into an intelligent, self-optimizing system that automatically leverages the best resource for each task. It provides a foundation for seamless integration of new datasets and resources while maintaining consistent performance and reliability.

## Roadmap Status

- [ ] Schema implementation
- [ ] Core manager and dispatcher classes
- [ ] Initial resource adapters
- [ ] Performance tracking
- [ ] Resource synchronization
- [ ] Smart routing capabilities
- [ ] Dataset integration
