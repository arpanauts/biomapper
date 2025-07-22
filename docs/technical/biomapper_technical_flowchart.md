# Biomapper Technical Architecture Analysis

## Current Flow (Working MVP)

```
User/Client Script
    ↓
BiomapperClient (HTTP)
    ↓
FastAPI (biomapper-api)
    ↓
MapperService
    ↓
MapperServiceForStrategies
    ├── Loads YAML strategies from /configs/*.yaml
    └── MappingExecutor (via MappingExecutorBuilder)
        ↓
    StrategyCoordinatorService
        ↓
    YamlStrategyExecutionService
        ↓
    StrategyHandler
        ↓
    ActionExecutor
        ↓
    MVP Actions (LOAD_DATASET_IDENTIFIERS, MERGE_WITH_UNIPROT_RESOLUTION, CALCULATE_SET_OVERLAP)
```

## Components Analysis

### ✅ ACTIVELY USED Components:
1. **biomapper-api/** - FastAPI service
   - MapperService
   - MapperServiceForStrategies
   - Strategy model validation

2. **Strategy Execution Chain**:
   - StrategyCoordinatorService
   - YamlStrategyExecutionService  
   - StrategyHandler
   - ActionExecutor
   - StrategyExecutionContext

3. **MVP Actions**:
   - LOAD_DATASET_IDENTIFIERS
   - MERGE_WITH_UNIPROT_RESOLUTION
   - CALCULATE_SET_OVERLAP

4. **External Clients**:
   - UniProtHistoricalResolverClient (for protein resolution)

### ❌ NOT USED / LEGACY Components:

1. **Database Components** (metamapper.db):
   - SessionManager (creates DB sessions but not used by MVP actions)
   - MetadataQueryService
   - IdentifierLoader (loads from DB endpoints)
   - Database models in biomapper/db/models.py

2. **Mapping Path Components**:
   - MappingPathExecutionService
   - EXECUTE_MAPPING_PATH action
   - Endpoint-based mapping logic

3. **Lifecycle Components**:
   - LifecycleCoordinator
   - Checkpointing functionality
   - Session management

4. **Other Legacy Components**:
   - IterativeExecutionService
   - CompositeIdentifierMixin
   - Relationship mapping
   - RAG components
   - LLM integration

## Key Findings:

1. **The MVP completely bypasses the database** - YAML strategies load data directly from files
2. **MappingExecutor is built but most of its functionality is unused** 
3. **The working flow is: YAML → Strategy Actions → Direct file/API access**
4. **metamapper.db is only used during initialization but not during execution**

## Recommendations:

### Phase 1: Document Current Working System
- Document the YAML strategy execution flow
- Document the three MVP actions
- Create clear examples

### Phase 2: Remove Database Dependencies
- Remove metamapper.db references from MappingExecutor
- Remove SessionManager from strategy execution
- Remove unused database models

### Phase 3: Simplify Architecture
- Remove unused coordinators (Lifecycle, Mapping)
- Simplify MappingExecutor to only handle YAML strategies
- Remove legacy action types

### Phase 4: Clean Codebase
- Remove /biomapper/mapping/ (old client implementations)
- Remove /biomapper/rag/ and /biomapper/llm/
- Remove legacy CLI commands
- Update tests to match new architecture