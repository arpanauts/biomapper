# Biomapper SQLite Mapping Cache System

## Overview

The Biomapper SQLite Mapping Cache provides a high-performance, persistent storage solution for biological entity mappings. It enables bidirectional transitivity across multiple ontologies, allowing you to efficiently translate biological identifiers while minimizing API calls to external services.

This document outlines the architecture, features, and usage of the mapping cache system.

## Key Features

- **Persistent Caching**: Store mapping results in SQLite for fast retrieval and reduced API load
- **Bidirectional Mappings**: Automatically create inverse mappings for all stored relationships
- **Transitive Relationships**: Derive new mappings by combining existing relationships (e.g., A→B + B→C = A→C)
- **Confidence Scoring**: Maintain confidence scores with configurable decay for derived mappings
- **Time-To-Live (TTL)**: Automatically expire mappings after a configurable period
- **Performance Monitoring**: Track cache hit rates, API usage, and derivation statistics
- **Command-Line Interface**: Manage the cache through a simple CLI
- **Integration with Mappers**: Drop-in integration with existing Biomapper components

## Architecture

The mapping cache system consists of several integrated components:

### Database Layer (`biomapper.db`)

- **Models**: SQLAlchemy ORM models for entity mappings and related data
- **Session Management**: Connection pooling and session handling for SQLite
- **Migrations**: Schema management using Alembic

### Cache Layer (`biomapper.cache`)

- **Cache Manager**: Core class for interacting with the mapping database
- **Cached Mapper**: Mapper implementation that integrates with existing mappers
- **Configuration**: Settings for cache behavior and performance tuning
- **Monitoring**: Performance tracking and telemetry

### Transitivity Layer (`biomapper.transitivity`)

- **Transitivity Builder**: Logic for deriving new mappings from existing relationships
- **Chain Management**: Controls for managing relationship chain length and confidence

## Database Schema

The mapping cache uses the following tables:

- **entity_mappings**: Core table storing source-target entity relationships
- **mapping_metadata**: Additional properties for mappings (extensible key-value store)
- **entity_type_config**: Configuration for specific entity types
- **cache_stats**: Performance statistics aggregated by day
- **transitive_job_log**: Records of batch transitivity building operations

## Installation and Setup

### Prerequisites

- Python 3.11+
- SQLite 3.35.0+

### Initialize the Cache

```bash
# Initialize with default settings
python -m scripts.setup_cache init

# Reset existing database
python -m scripts.setup_cache init --reset

# Use custom data directory
python -m scripts.setup_cache init --data-dir /path/to/data
```

## Usage Examples

### Basic Lookup and Storage

```python
from biomapper.cache.manager import CacheManager

# Initialize cache manager
cache_manager = CacheManager()

# Add a mapping
cache_manager.add_mapping(
    source_id="HMDB0000122",
    source_type="hmdb",
    target_id="CHEBI:17234",
    target_type="chebi",
    confidence=0.95,
    mapping_source="unichem",
    metadata={"compound_name": "Glucose"}
)

# Look up mappings
results = cache_manager.lookup(
    source_id="HMDB0000122",
    source_type="hmdb"
)

print(f"Found {len(results)} mappings")
for mapping in results:
    print(f"  → {mapping['target_type']}:{mapping['target_id']} (confidence: {mapping['confidence']})")
```

### Using the Cached Mapper

```python
import asyncio
from biomapper.cache.mapper import CachedMapper
from biomapper.mapping.clients.chebi_client import ChEBIMapper
from biomapper.schemas.domain_schema import CompoundDocument

# Create base mapper
base_mapper = ChEBIMapper()

# Create cached mapper
cached_mapper = CachedMapper(
    base_mapper=base_mapper,
    document_class=CompoundDocument,
    source_type="compound_name",
    target_type="chebi",
    ttl_days=30,
    min_confidence=0.7
)

async def map_compound(name):
    # This will check cache first, then fall back to API
    result = await cached_mapper.map_entity(name)
    
    if result.mapped_entity:
        print(f"Mapped '{name}' to {result.mapped_entity.id}")
        print(f"Source: {'cache' if result.metadata.get('cache_hit') else 'api'}")
    else:
        print(f"Could not map '{name}'")

# Run mapping
asyncio.run(map_compound("glucose"))
```

### Building Transitive Relationships

```python
from biomapper.cache.manager import CacheManager
from biomapper.transitivity.builder import TransitivityBuilder

# Initialize cache manager and transitivity builder
cache_manager = CacheManager()
builder = TransitivityBuilder(
    cache_manager=cache_manager,
    min_confidence=0.7,
    max_chain_length=3,
    confidence_decay=0.9
)

# Build transitive mappings
new_mappings = builder.build_transitive_mappings()
print(f"Created {new_mappings} new transitive mappings")

# Build extended chains (length > 2)
extended_mappings = builder.build_extended_transitive_mappings()
print(f"Created {extended_mappings} extended transitive mappings")
```

### Using the CLI

```bash
# Initialize the cache
python -m biomapper.cache.cli init

# Add mapping
python -m biomapper.cache.cli add --source-id "HMDB0000122" --source-type "hmdb" \
                                  --target-id "CHEBI:17234" --target-type "chebi" \
                                  --confidence 0.95 --source "manual"

# Look up mappings
python -m biomapper.cache.cli lookup --id "HMDB0000122" --type "hmdb"

# Build transitive relationships
python -m biomapper.cache.cli build-transitive

# Clean expired mappings
python -m biomapper.cache.cli clean
```

## Performance Considerations

### Caching Strategy

- **Direct Mappings**: Stored with high confidence from authoritative sources
- **Derived Mappings**: Built from transitive relationships with decaying confidence
- **Bidirectional**: All mappings are stored bidirectionally for efficient lookup
- **TTL Management**: Different entity types can have different expiration periods

### Optimizations

- **SQLite Indexing**: Optimized indexes for common query patterns
- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Bulk operations for adding and deriving mappings
- **Task Scheduling**: Background tasks for building transitive relationships

### Monitoring

The system includes comprehensive monitoring:

```python
from biomapper.cache.monitoring import get_cache_stats

# Get cache statistics
stats = get_cache_stats()
print(f"Hit ratio: {stats['hit_ratio'] * 100:.1f}%")
print(f"Cache hits: {stats['events'].get('hit', 0)}")
print(f"Cache misses: {stats['events'].get('miss', 0)}")
print(f"API calls: {stats['events'].get('api_call', 0)}")
```

## Maintenance

### Backup and Restore

```bash
# Create backup
python -m scripts.setup_cache backup

# List backups
python -m scripts.setup_cache list-backups

# Restore from backup
python -m scripts.setup_cache restore biomapper_backup_20250325_123456.db.gz

# Run maintenance (vacuum, expire old mappings, backup)
python -m scripts.setup_cache maintain
```

### Database Optimization

```python
from biomapper.db.maintenance import DatabaseMaintenance

# Initialize maintenance utilities
maintenance = DatabaseMaintenance()

# Vacuum the database
maintenance.vacuum_database()

# Delete expired mappings
deleted_count = maintenance.delete_expired_mappings()
print(f"Deleted {deleted_count} expired mappings")

# Get database stats
stats = maintenance.get_database_stats()
print(f"Database size: {stats['file_size_mb']} MB")
print(f"Total mappings: {stats['tables']['entity_mappings']}")
```

## Integration with SPOKE Knowledge Graph

The SQLite mapping cache complements the SPOKE Knowledge Graph in the Biomapper architecture:

1. **First-Level Cache**: Provides fast access to previously resolved mappings
2. **Discovery Feed**: New mappings derived from transitive relationships feed back into the knowledge graph
3. **Fallback Mechanism**: When SPOKE doesn't contain a relationship, the cache still may
4. **Performance Layer**: Reduces load on the graph database for common mapping operations

## Contributing

Contributions to the mapping cache system are welcome! Please see the main Biomapper contribution guidelines.

## Roadmap

Future enhancements planned for the mapping cache system:

- PostgreSQL backend option for higher concurrency environments
- Distributed cache with Redis for multi-instance deployments
- Enhanced mapping invalidation based on ontology version changes
- Integration with the web API for remote cache management
