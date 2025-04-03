# Enhanced Entity Mappers Implementation Plan

## Overview

This document outlines the plan for enhancing Biomapper's entity mappers by integrating them with the Resource Metadata System. This integration will make the mappers more powerful, resilient, and extensible, enabling them to intelligently route mapping operations across multiple resources.

## Key Benefits

1. **Resource Agnosticism**: Mappers work with any available resources without hard dependencies
2. **Intelligent Routing**: Automatically selects the best-performing resources for each operation
3. **Graceful Degradation**: Continues functioning when some resources are unavailable
4. **Performance Optimization**: Learns from past operations to improve future performance
5. **Consistent Interface**: Provides a uniform API across different entity types
6. **Extensibility**: Makes it easy to add support for new resources and entity types

## Architecture

The enhanced mappers build on the Resource Metadata System's core components:

1. **ResourceMetadataManager**: Manages resource metadata and performance tracking
2. **MappingDispatcher**: Orchestrates mapping operations across resources
3. **ResourceAdapter interface**: Provides a consistent interface for different resources
4. **Database Schema**: Stores resource capabilities and performance metrics

### Component Relationships

```
+--------------------+    +--------------------+
| MetaboliteMapper   |    | ProteinMapper      |
| GeneMapper         +----+ DiseaseMapper      |
| PathwayMapper      |    | Custom Mappers     |
+--------+-----------+    +---------+----------+
         |                          |
         v                          v
+--------------------+    +--------------------+
| AbstractMapper     |    | MappingDispatcher  |
| (Base Class)       +----+                    |
+--------+-----------+    +---------+----------+
         |                          |
         v                          v
+--------------------+    +--------------------+
| ResourceAdapter    |    | ResourceMetadata   |
| Interface          +----+ Manager            |
+--------+-----------+    +---------+----------+
         |                          |
         v                          v
+-------------------------------------------------+
|                Resource Adapters                |
| (SQLite, SPOKE, ChEBI, RefMet, UniProt, etc.)   |
+-------------------------------------------------+
```

## Implementation Plan

### Phase 1: Base Components (Week 1)

1. Create the AbstractEntityMapper base class
2. Implement common resource setup and mapping methods
3. Develop adapter interfaces for different resource types
4. Build synchronous wrappers for backward compatibility

### Phase 2: Core Entity Mappers (Week 2)

1. Enhance MetaboliteNameMapper (highest priority)
2. Implement ProteinNameMapper
3. Develop GeneMapper
4. Create DiseaseMapper
5. Build PathwayMapper

### Phase 3: Resource Adapters (Week 3)

1. Implement SQLite Cache adapter (highest priority)
2. Create SPOKE knowledge graph adapter
3. Develop adapters for API-based resources:
   - ChEBI, RefMet, UniChem for metabolites
   - UniProt, PDB for proteins
   - NCBI Gene, Ensembl for genes
   - MONDO, DisGeNet for diseases
   - Reactome, KEGG for pathways

### Phase 4: Integration and Testing (Week 4)

1. Integrate enhanced mappers with existing Biomapper code
2. Develop comprehensive tests for all mappers
3. Create performance benchmarks
4. Document usage patterns and examples

## Next Steps

Refer to the following detailed implementation documents:
- [Enhanced MetaboliteNameMapper](./enhanced_mappers/metabolite_mapper.md)
- [ProteinNameMapper Implementation](./enhanced_mappers/protein_mapper.md)
- [AbstractEntityMapper Base Class](./enhanced_mappers/abstract_mapper.md)
- [Other Entity Mappers](./enhanced_mappers/other_mappers.md)

## Related Resources

- [Resource Metadata System Design](./architecture/resource_metadata_system.md)
- [Resource Metadata Implementation Plan](./architecture/resource_metadata_implementation_plan.md)
