# Biomapper: Technical Architecture Review

## System Overview

Biomapper is a biological data harmonization toolkit that maps identifiers across biological databases. The core workflow follows this architecture:

```mermaid
flowchart TB
    subgraph Client Layer
        A[Client Script<br/>run_full_ukbb_hpa_mapping.py<br/>- Loads TSV files<br/>- Uses BiomapperClient SDK]
    end
    
    subgraph API Layer
        B[REST API<br/>biomapper-api<br/>FastAPI:8000<br/>POST /api/strategies/name/execute]
    end
    
    subgraph Service Layer
        C[MapperService<br/>- Loads YAML strategies directly]
        D[MappingExecutor<br/>Facade Pattern<br/>- Orchestrates execution]
    end
    
    subgraph Execution Layer
        E[StrategyOrchestrator<br/>- Executes strategy steps<br/>- Sequential processing]
        F[ActionExecutor<br/>- Action registry lookup<br/>- Shared dict passing between steps]
    end
    
    subgraph Mapping Strategy via Action Steps
        H[Load Metadata Identifiers]
        I[Conduct Mapping Operations]
        J[Provide Mapping Results, Reports, and Statistics]
    end
    
    subgraph Data Layer
        K[(metamapper.db<br/>DEPRECATED/LEGACY<br/>- Endpoint Configs<br/>- Mapping Strategies)]
        L[(mapping_cache.db<br/>DEFERRED<br/>- Future optimization<br/>- Not yet implemented)]
        G[(YAML Strategy Files<br/>configs/strategies/*.yaml<br/>- Strategy definitions<br/>- Loaded directly at runtime)]
    end
    
    subgraph Core Components
        M[Action Registry<br/>- Dynamic action loading<br/>- Type registration]
        N[Type Safety Migration<br/>- Dict to Pydantic<br/>- TypedStrategyAction]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> H
    H --> I
    I --> J
    
    C --> G
    F --> M
    F --> N
    
    style D fill:#f9f,stroke:#333,stroke-width:4px,color:#000
    style G fill:#ff9,stroke:#333,stroke-width:2px,color:#000
    style N fill:#9f9,stroke:#333,stroke-width:2px,color:#000
    style K fill:#ddd,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5,color:#000
    style L fill:#ddd,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5,color:#000
```

Example: A researcher runs `run_full_ukbb_hpa_mapping.py` which:
1. Loads UKBB protein assay IDs from a TSV file
2. Uses BiomapperClient SDK to call the API with strategy name "UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS"
3. MapperService loads the YAML strategy directly from `configs/` directory
4. MappingExecutor delegates to StrategyOrchestrator which executes steps sequentially
5. Individual actions execute with parameters defined in the YAML strategy
6. Biological data is loaded directly from CSV/TSV files using hardcoded or strategy-specified paths
7. Returns overlap analysis results (mapping_cache.db caching deferred for future)

## Computer Science Considerations (Amy)

**Architecture Design:**
The system uses a service-oriented architecture where the `MappingExecutor` serves as a facade, delegating to the `StrategyOrchestrator`. Each YAML strategy defines a directed acyclic graph (DAG) of actions that process biological identifiers through various transformations. The system has evolved from database-stored strategies to direct YAML file loading, eliminating the intermediate database step for better development agility.

**Key Algorithmic Components:**
- **Graph-based mapping paths**: Ontology relationships stored as directed graphs; currently using precomputed paths
- **Identifier resolution**: Handles 1:many mappings, historical/obsolete IDs, and composite identifiers
- **Batch processing**: Pipeline design with configurable batch sizes (200-250) to balance memory/API limits
- **Context propagation**: A shared dictionary (`Dict[str, Any]`) passed between action steps, accumulating results and state throughout strategy execution. Each action reads inputs from and writes outputs to this mutable context, enabling data flow through the pipeline

**Considerations for optimization:**
- The sequential execution model in strategies might benefit from identifying parallelizable steps
- Dynamic path-finding could potentially discover better mapping routes than precomputed paths
- The current architecture could support streaming processing for very large datasets

## Software Engineering Considerations (Drew)

**Current Implementation:**
- **FastAPI** service layer with Pydantic validation
- **MappingExecutor** as a facade pattern implementation
- **YAML-driven strategies** loaded directly from `configs/strategies/` directory
- **Async/await** throughout for I/O-bound operations
- **Database evolution**: 
  - metamapper.db: Now only used for endpoint configurations (strategy storage deprecated)
  - mapping_cache.db: Deferred for future caching optimization
- **Action Registry**: Dynamic action loading system with type registration
- **Direct file loading**: Biological data loaded from CSV/TSV files, not databases

**Type Safety Migration:**
The codebase is transitioning from `Dict[str, Any]` to Pydantic models. The new `TypedStrategyAction` base class maintains backward compatibility while introducing type safety. This includes moving from untyped context dictionaries to a typed `StrategyExecutionContext` model, though most actions still use the legacy dictionary approach.

**Architecture Considerations:**
- The facade pattern provides clean separation but adds a layer of indirection
- YAML strategies offer flexibility but lose compile-time validation and IDE support
- The service-oriented design enables scaling but may be overkill for single-machine use
- Direct YAML loading replaced database storage for strategies, improving development velocity
- The deprecated database approach shows the evolution toward simpler, file-based configuration

**Testing Challenges:**
- Integration tests depend on external biological databases
- The 80% coverage requirement is difficult with external dependencies
- Mock strategies might miss real-world edge cases in biological data

## Areas for Feedback

Some aspects that might benefit from your perspectives:

- **Scalability**: The current architecture handles thousands of identifiers well, but millions might require architectural changes
- **Flexibility vs. Simplicity**: The YAML strategy system is powerful but complex - finding the right balance
- **Performance**: Whether to optimize for throughput (batch processing) or latency (streaming)
- **Maintainability**: Managing the transition to full type safety without breaking existing integrations