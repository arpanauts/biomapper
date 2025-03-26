# Biomapper SQLite Mapping Cache Implementation Plan

## Executive Summary

This document outlines the implementation plan for integrating a SQLite-based mapping cache into the Biomapper toolkit. The mapping cache will store previously resolved entity mappings to improve performance, reduce external API calls, and provide consistent results across sessions. This implementation prioritizes bidirectional transitivity between ontologies, enabling any-to-any entity mapping with high performance. The design focuses on simplicity, portability, and ease of maintenance for individual users.

## Scope and Objectives

### Primary Goals
1. Create a persistent, local cache of entity mappings using SQLite
2. Implement bidirectional transitivity to enable any-to-any entity mapping
3. Integrate cache lookups into the existing mapping workflow with time-based validation
4. Develop utilities for cache management and maintenance
5. Provide a seamless developer experience from initial setup to ongoing use

### Non-Goals for Initial Implementation
1. Multi-user concurrent database access
2. Distributed caching
3. Complex query optimization
4. Full-text search capabilities

## Implementation Phases

### Phase 1: Database Foundation (Week 1)

1. **Schema Design and Setup**
   - Create SQLAlchemy models for mapping entities with bidirectional support
   - Design schema for storing mappings with metadata and TTL tracking
   - Implement versioning for schema migrations
   - Create initialization scripts and commands

2. **Basic Database Operations**
   - Implement CRUD operations for mappings
   - Create query interfaces for bidirectional lookup patterns
   - Add metadata storage for mapping sources and derivation paths
   - Develop connection management utilities

3. **Transitivity Framework Core**
   - Design transitive relationship builder algorithm
   - Implement bidirectional mapping storage mechanism
   - Create confidence propagation logic for derived mappings
   - Build the provenance tracking system for mapping chains

### Phase 2: Cache Integration and Transitivity (Week 2)

1. **Cache Manager Implementation**
   - Create CacheManager class to handle lookups and updates
   - Implement TTL-based validation with configurable timeframes
   - Add background refreshing for outdated mappings
   - Develop usage tracking for frequently accessed entities

2. **Transitive Relationship Builder**
   - Implement algorithm to identify potential transitive relationships
   - Create automatic derivation of new mappings from existing pairs
   - Develop confidence calculation for derived mappings
   - Build scheduled job for periodic transitive relationship discovery

3. **Mapper Service Integration**
   - Modify existing mappers to check cache first
   - Update mappers to store successful mappings bidirectionally
   - Integrate RaMP API client with cache refresh mechanisms
   - Implement entity resolution across multiple ontologies

### Phase 3: Management Tools and API Integration (Week 3)

1. **API Endpoint Integration**
   - Create an any-to-any entity resolution API endpoint
   - Add transitive mapping exploration capabilities
   - Implement timing-based cache refresh triggers
   - Create admin endpoints for cache management

2. **CLI Tools Development**
   - Create `biomapper cache init` command
   - Add `biomapper cache stats` for usage information
   - Implement `biomapper cache derive` to trigger transitive relationship building
   - Develop `biomapper cache export/import` for sharing derived mappings

3. **Advanced Transitivity Features**
   - Implement multi-hop relationship traversal
   - Add confidence thresholds for transitive mappings
   - Create visualization tools for mapping relationships
   - Build mapping conflict resolution mechanisms

### Phase 4: Testing and Refinement (Week 4)

1. **Testing Suite Development**
   - Create unit tests for cache operations and transitivity
   - Develop integration tests for complex mapping scenarios
   - Implement performance benchmarking across different ontologies
   - Add edge case testing for cyclic relationships

2. **Performance Optimization**
   - Profile query performance for complex transitive lookups
   - Implement bulk operations for bidirectional updates
   - Add specialized indexes for transitive query patterns
   - Optimize storage efficiency with batched operations

3. **Documentation and Finalization**
   - Complete developer documentation with transitivity examples
   - Create user guides for leveraging transitive mappings
   - Document ontology compatibility matrix
   - Finalize configuration options for transitivity behavior

## Technical Specifications

### Database Schema

```sql
-- Core mapping table with bidirectional support
CREATE TABLE entity_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,           -- Original identifier
    source_type TEXT NOT NULL,         -- Ontology type (e.g., "HMDB", "ChEBI")
    target_id TEXT NOT NULL,           -- Mapped identifier
    target_type TEXT NOT NULL,         -- Target ontology (e.g., "CHEBI", "PUBCHEM")
    confidence FLOAT,                  -- Mapping confidence score
    mapping_source TEXT,               -- Where the mapping came from (api, spoke, rag, ramp, etc.)
    is_derived BOOLEAN DEFAULT 0,      -- Flag for transitively derived mappings
    derivation_path TEXT,              -- JSON array of mapping IDs used to derive this mapping
    last_updated TIMESTAMP,            -- When mapping was last refreshed from source
    usage_count INTEGER DEFAULT 1,     -- Track frequently used mappings
    expires_at TIMESTAMP,              -- When this mapping should be rechecked against source
    UNIQUE(source_id, source_type, target_id, target_type)
);

-- Indexes for fast bidirectional lookups
CREATE INDEX idx_source_lookup ON entity_mappings(source_id, source_type);
CREATE INDEX idx_target_lookup ON entity_mappings(target_id, target_type);
CREATE INDEX idx_usage_count ON entity_mappings(usage_count DESC);
CREATE INDEX idx_expiration ON entity_mappings(expires_at);

-- Metadata table for additional mapping information
CREATE TABLE mapping_metadata (
    mapping_id INTEGER,
    key TEXT NOT NULL,                 -- Metadata key (e.g., "common_name", "formula")
    value TEXT,                        -- Metadata value
    FOREIGN KEY(mapping_id) REFERENCES entity_mappings(id) ON DELETE CASCADE,
    PRIMARY KEY(mapping_id, key)
);

-- Entity type configuration for TTL settings
CREATE TABLE entity_type_config (
    source_type TEXT,                  -- Ontology or entity type
    target_type TEXT,                  -- Can be NULL for all targets of a source
    ttl_days INTEGER DEFAULT 365,      -- How long until refresh needed
    confidence_threshold FLOAT DEFAULT 0.7, -- Minimum confidence for derived mappings
    PRIMARY KEY(source_type, target_type)
);

-- Cache statistics and management
CREATE TABLE cache_stats (
    stats_date DATE PRIMARY KEY,
    hits INTEGER DEFAULT 0,
    misses INTEGER DEFAULT 0,
    direct_lookups INTEGER DEFAULT 0,
    derived_lookups INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    transitive_derivations INTEGER DEFAULT 0
);

-- Derived mapping job tracking
CREATE TABLE transitive_job_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_date TIMESTAMP,
    mappings_processed INTEGER,
    new_mappings_created INTEGER,
    duration_seconds FLOAT,
    status TEXT
);
```

### Key Classes and Components

1. **Models**
   - `EntityMapping`: SQLAlchemy model for bidirectional mappings
   - `MappingMetadata`: Model for additional mapping data
   - `EntityTypeConfig`: Configuration for different entity type pairs
   - `CacheStats`: Model for tracking cache performance
   - `TransitiveJobLog`: Records transitive relationship building jobs

2. **Core Components**
   - `MappingStore`: Primary interface for database operations
   - `CacheManager`: High-level cache management logic
   - `TransitiveRelationshipBuilder`: Discovers and creates transitive mappings
   - `MigrationManager`: Handles database schema changes
   - `TTLManager`: Manages expiration of cached mappings

3. **Service Layer**
   - `EntityResolutionService`: Provides any-to-any entity mapping
   - `MappingService`: Integrates with existing mappers
   - `CacheStatsService`: Collects and manages statistics
   - `MaintenanceService`: Handles cleanup and optimization
   - `RaMPIntegrationService`: Interfaces with RaMP-DB

4. **CLI Commands**
   - `cache init`: Initialize the cache database
   - `cache stats`: Show cache usage statistics and transitivity metrics
   - `cache derive`: Manually trigger transitive relationship building
   - `cache clear`: Clear all or specific cache entries
   - `cache export/import`: Save/load cache data
   - `cache refresh`: Force refresh of expired mappings

### File Structure

```
biomapper/
├── biomapper/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── engine.py           # Database connection management
│   │   ├── migrations/         # Schema migration files
│   │   │   ├── __init__.py
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   └── alembic.ini         # Migration configuration
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── manager.py          # Cache management logic
│   │   ├── store.py            # Database operations
│   │   ├── ttl.py              # Time-to-live management
│   │   └── maintenance.py      # Cleanup and optimization
│   ├── transitivity/
│   │   ├── __init__.py
│   │   ├── builder.py          # Transitive relationship builder
│   │   ├── confidence.py       # Confidence propagation
│   │   ├── scheduler.py        # Jobs for relationship discovery
│   │   └── graph.py            # Graph traversal utilities
│   ├── resolution/
│   │   ├── __init__.py
│   │   ├── entity_resolver.py  # Any-to-any resolution
│   │   ├── strategy.py         # Resolution strategies
│   │   └── providers.py        # Source providers (RaMP, APIs)
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── cache.py        # CLI commands for cache
│   │       └── transitivity.py # Commands for transitivity
│   ├── api/
│   │   ├── __init__.py
│   │   ├── entity.py           # Entity resolution endpoints
│   │   └── admin.py            # Admin endpoints
│   └── config/
│       ├── __init__.py
│       └── settings.py         # Configuration options
└── scripts/
    ├── cache_utils/            # Helper scripts
    │   ├── __init__.py
    │   ├── backup.py           # Backup utilities
    │   └── stats.py            # Advanced statistics
    └── transitivity/           # Transitivity utilities
        ├── __init__.py
        ├── batch_derive.py     # Batch derivation script
        └── visualization.py    # Graph visualization
```

## Transitivity Mechanism

### Derivation Algorithm

The transitive relationship builder follows these steps:

1. **Identify Candidate Pairs**:
   - Find mappings where `entity_mappings.target_id` in ontology A matches `entity_mappings.source_id` in ontology B
   - This creates potential chains: X → Y (mapping 1) and Y → Z (mapping 2)

2. **Create Derived Mappings**:
   - Generate new mappings X → Z with:
     - `source_id` = mapping1.source_id
     - `source_type` = mapping1.source_type
     - `target_id` = mapping2.target_id
     - `target_type` = mapping2.target_type
     - `is_derived` = 1
     - `derivation_path` = JSON array containing [mapping1.id, mapping2.id]
     - `confidence` = mapping1.confidence * mapping2.confidence * CONFIDENCE_FACTOR
   - Also create the reverse mapping Z → X for bidirectional support

3. **Multi-hop Extension**:
   - Recursively apply the algorithm to discover longer chains (configurable depth)
   - Track derivation paths to avoid cycles and maintain provenance
   - Apply confidence thresholds to prevent low-confidence transitive mappings

4. **Scheduled Execution**:
   - Run as a background job after new mappings are added
   - Schedule regular full rebuilds to catch all potential relationships
   - Record metrics in the `transitive_job_log` table

### Confidence Propagation

Confidence scores are propagated through the derivation chain:

1. **Basic Algorithm**: Multiply confidence scores along the chain
2. **Confidence Factor**: Apply a discount factor for derived mappings to reflect increased uncertainty
3. **Threshold Filtering**: Only create derived mappings above the configured confidence threshold
4. **Conflict Resolution**: When multiple derivation paths exist, select the highest confidence path

### Entity Resolution Process

When resolving an entity across ontologies:

1. **Direct Lookup**: Check for a direct mapping between source and target
2. **Derived Lookup**: Check for derived mappings if direct lookup fails
3. **Online Resolution**: If cache fails, check external sources (RaMP, APIs)
4. **Transitive Discovery**: Schedule a background task to derive new relationships
5. **Result Aggregation**: Return mapping with confidence scores and provenance

## Integration Points

### Integration with Existing Biomapper Components

1. **MetaboliteNameMapper**
   - Modify to check cache before API calls
   - Update to store successful mappings in cache
   - Add configuration for cache behavior

2. **SPOKEMapper**
   - Integrate cache lookups before graph queries
   - Store relationship paths in cache
   - Add versioning information for SPOKE data

3. **RAG Components**
   - Store successful RAG mappings with confidence scores
   - Add LLM source information for provenance
   - Implement selective cache usage based on confidence

### Web UI Integration

1. **API Endpoints**
   - Modify `/api/map` endpoint to use cache
   - Add cache statistics to response metadata
   - Create admin endpoints for cache management

2. **Frontend Components**
   - Add cache indicators to mapping results
   - Display confidence scores from cache
   - Create optional cache management panel

## Developer Experience and Maintenance

### Initial Setup Process

For a new developer cloning the repository:

```bash
# Clone and install
git clone <repo>
cd biomapper
pip install -e .

# Initialize database (creates SQLite file in user data directory)
biomapper cache init

# Optional: Pre-populate with common mappings
biomapper cache seed
```

### Configuration Options

The cache system will use a configuration file with the following options:

```python
# Example configuration
CACHE_CONFIG = {
    # Path settings
    "db_path": "~/.biomapper/cache.db",  # Default location, or None for in-memory
    "backup_dir": "~/.biomapper/backups",
    
    # Cache behavior
    "ttl_days": 30,  # Default expiration time
    "min_confidence": 0.7,  # Minimum confidence to cache
    "enable_cache": True,  # Master switch
    
    # Maintenance
    "auto_vacuum": True,  # Automatic database optimization
    "backup_before_migrations": True,
    "max_size_mb": 500,  # Size limit warning
}
```

### Maintenance Procedures

1. **Routine Maintenance**
   - Automated TTL-based expiration of old mappings
   - Periodic database vacuuming for optimization
   - Statistics collection for performance monitoring

2. **Manual Management**
   - Clear specific entity types: `biomapper cache clear --type metabolite`
   - Export cache for sharing: `biomapper cache export --file mappings.json`
   - Rebuild indices: `biomapper cache optimize`

3. **Versioning and Updates**
   - Automatic schema migrations on version updates
   - Pre-migration backups for safety
   - Version compatibility checks

## Testing Strategy

1. **Unit Testing**
   - Test database operations in isolation
   - Mock external components for focused testing
   - Test cache hit/miss logic

2. **Integration Testing**
   - Test full mapping workflow with cache
   - Verify correct integration with existing mappers
   - Test migration procedures

3. **Performance Testing**
   - Benchmark mapping operations with and without cache
   - Test with various dataset sizes
   - Measure memory consumption

## Success Metrics

1. **Performance Improvement**
   - >90% speed improvement for repeated mappings
   - >50% reduction in external API calls

2. **Reliability**
   - Zero data loss during migrations
   - Consistent results between cache and fresh mappings

3. **User Experience**
   - Seamless integration requiring zero user configuration
   - Clear indicators of mapping sources in UI

## Future Enhancements

While not part of the initial implementation, these features could be considered for future versions:

1. **Advanced Caching Strategies**
   - Implement predictive caching based on usage patterns
   - Add support for partial results caching

2. **Performance Optimizations**
   - Full-text search for name-based lookups
   - Advanced indexing strategies for complex queries

3. **Expansion to PostgreSQL**
   - Create adapter for PostgreSQL support
   - Add multi-user concurrency support
   - Implement shared caching for team environments
