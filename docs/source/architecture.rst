:orphan:

Architecture Overview
=====================

Biomapper is built around an **extensible action-based architecture** that prioritizes simplicity and maintainability while allowing for sophisticated mapping approaches. The system currently ships with over 30 self-registering actions covering proteins, metabolites, chemistry, and general data operations, all configurable through YAML-based strategies.

Core Architectural Principles
------------------------------

1. **Simplicity First**: Minimal viable functionality without unnecessary complexity
2. **Configuration Over Code**: Define workflows in YAML rather than writing Python code  
3. **API-First Design**: All functionality accessible via REST API
4. **Type Safety**: Pydantic models ensure data validation throughout
5. **No Database Dependencies**: Strategies execute without persistent storage requirements

High-Level Architecture
-----------------------

.. code-block:: text

    ┌─────────────────┐    ┌─────────────────┐
    │  Client Script  │    │  Python Client  │
    │                 │    │   (async/await) │
    └─────────┬───────┘    └─────────┬───────┘
              │                      │
              └──────┬───────────────┘
                     │ HTTP requests
                     ▼
              ┌─────────────────┐
              │   REST API      │
              │   (FastAPI)     │
              └─────────┬───────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Strategy        │
              │ Service         │
              └─────────┬───────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Core Actions    │
              │ Registry        │
              └─────────────────┘

Key Components
--------------

Minimal Strategy Service
~~~~~~~~~~~~~~~~~~~~~~~~

The ``MinimalStrategyService`` is the core orchestrator that:

- Loads YAML strategy definitions from the filesystem
- Maintains a registry of available actions
- Executes strategies by running actions sequentially
- Manages data flow between actions through a shared context

.. code-block:: python

    from biomapper.core.services.strategy_service_v2_minimal import MinimalStrategyService
    
    # Initialize service (loads strategies from configs/strategies/)
    service = MinimalStrategyService()
    
    # Execute a strategy by name
    context = {"datasets": {}, "statistics": {}, "output_files": []}
    result = await service.execute_strategy("protein_mapping_template", context)

Core Actions
~~~~~~~~~~~~

The system includes over 30 self-registering actions organized by category:

**Data Operations**
  - ``LOAD_DATASET_IDENTIFIERS``: Load biological identifiers from CSV/TSV files
  - ``MERGE_DATASETS``: Combine multiple datasets with deduplication
  - ``FILTER_DATASET``: Apply filtering criteria to datasets
  - ``EXPORT_DATASET``: Export data to various formats
  - ``CUSTOM_TRANSFORM``: Apply Python expressions to transform data

**Protein Actions**
  - ``MERGE_WITH_UNIPROT_RESOLUTION``: Historical UniProt ID resolution
  - ``PROTEIN_EXTRACT_UNIPROT``: Extract UniProt IDs from compound fields
  - ``PROTEIN_NORMALIZE_ACCESSIONS``: Standardize protein identifiers
  - ``PROTEIN_MULTI_BRIDGE``: Cross-dataset protein resolution

**Metabolite Actions**
  - ``CTS_ENRICHED_MATCH``: Chemical Translation Service matching
  - ``SEMANTIC_METABOLITE_MATCH``: AI-powered semantic matching
  - ``VECTOR_ENHANCED_MATCH``: Vector similarity matching
  - ``NIGHTINGALE_NMR_MATCH``: Nightingale NMR reference matching
  - ``COMBINE_METABOLITE_MATCHES``: Merge multiple matching approaches

**Chemistry Actions**
  - ``CHEMISTRY_EXTRACT_LOINC``: Extract LOINC codes from clinical data
  - ``CHEMISTRY_FUZZY_TEST_MATCH``: Fuzzy matching for test names
  - ``CHEMISTRY_VENDOR_HARMONIZATION``: Harmonize vendor-specific data

**Analysis Actions**
  - ``CALCULATE_SET_OVERLAP``: Jaccard similarity and Venn diagrams
  - ``CALCULATE_THREE_WAY_OVERLAP``: Three-dataset comparison
  - ``CALCULATE_MAPPING_QUALITY``: Assess mapping quality metrics
  - ``GENERATE_METABOLOMICS_REPORT``: Comprehensive analysis reports

REST API (FastAPI)
~~~~~~~~~~~~~~~~~~~

The REST API provides HTTP endpoints for:

- Strategy execution
- Health checks  
- Strategy listing
- File uploads (if needed)

.. code-block:: python

    # API endpoint for strategy execution (simplified)
    @app.post("/api/v2/strategies/{strategy_name}/execute")
    async def execute_strategy(
        strategy_name: str,
        request: StrategyExecutionRequest
    ):
        service = get_mapper_service()  # Dependency injection
        result = await service.execute_strategy(
            strategy_name, 
            request.context,
            request.parameters
        )
        return result

Python Client
~~~~~~~~~~~~~~

The Python client (``biomapper_client``) provides both sync and async interfaces:

- Synchronous ``run()`` method for simple usage
- Async ``execute_strategy_async()`` for advanced users
- Automatic timeout handling with configurable limits
- Proper error handling and automatic retries
- Context manager pattern for resource management
- Progress tracking with SSE events

Data Flow
---------

Strategy execution follows a simple linear flow:

1. **Strategy Loading**: YAML file parsed and validated
2. **Context Initialization**: Empty dictionary created for data passing
3. **Sequential Execution**: Actions run in order, each modifying the context
4. **Result Aggregation**: Final context contains all results and metadata
5. **Response Formatting**: Results serialized as JSON response

.. code-block:: python

    context = {}  # Shared data structure
    
    for step in strategy.steps:
        action = action_registry[step.action.type]
        params = validate_params(step.action.params)
        
        # Action modifies context in-place
        result = await action.execute(params, context)
        
        # Context now contains action's output
        # Available to subsequent actions

Directory Structure
-------------------

The simplified architecture reflects a focused directory structure:

.. code-block:: text

    biomapper/
    ├── core/
    │   ├── strategy_actions/           # 30+ self-registering actions
    │   │   ├── entities/               # Entity-specific actions
    │   │   │   ├── proteins/           # UniProt, Ensembl, gene symbols
    │   │   │   ├── metabolites/        # HMDB, InChIKey, CHEBI, KEGG
    │   │   │   └── chemistry/          # LOINC, clinical tests
    │   │   ├── algorithms/             # Reusable algorithms
    │   │   ├── workflows/              # High-level orchestration
    │   │   ├── io/                     # Data input/output
    │   │   ├── reports/                # Analysis & reporting
    │   │   ├── typed_base.py           # TypedStrategyAction base
    │   │   └── registry.py             # Global ACTION_REGISTRY
    │   ├── models/                     # Pydantic models
    │   └── services/
    │       └── strategy_service_v2_minimal.py  # Main executor
    ├── biomapper-api/                  # FastAPI REST service
    │   └── app/
    │       ├── main.py                 # Application entry
    │       ├── api/routes/             # API endpoints
    │       └── services/               # Business logic
    ├── biomapper_client/               # Python client library
    │   └── biomapper_client/
    │       ├── client_v2.py            # BiomapperClient
    │       └── models.py               # Request/response models
    ├── configs/                        # Configuration files
    │   ├── strategies/                 # YAML strategy definitions
    │   │   ├── templates/              # Reusable templates
    │   │   └── experimental/           # Advanced strategies
    │   └── clients/                    # External API configs
    └── tests/                          # Comprehensive test suite

YAML Strategy System
--------------------

Strategies are defined using simple YAML configuration:

.. code-block:: yaml

    name: "PROTEIN_COMPARISON"
    description: "Compare protein datasets"
    
    steps:
      - name: load_source
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/proteins_a.csv"
            identifier_column: "uniprot"
            output_key: "proteins_a"
      
      - name: load_target  
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/proteins_b.csv"
            identifier_column: "uniprot"
            output_key: "proteins_b"
            
      - name: merge_data
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "proteins_a"
            target_dataset_key: "proteins_b"
            source_id_column: "uniprot"
            target_id_column: "uniprot"
            output_key: "merged_data"
            
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            merged_dataset_key: "merged_data"
            source_name: "Dataset A"
            target_name: "Dataset B"
            output_key: "overlap_stats"

Type Safety
-----------

The system uses Pydantic models throughout for data validation:

- **Parameter Models**: Each action has typed parameter classes
- **Result Models**: Standardized result structures
- **Context Validation**: Runtime type checking where needed
- **API Validation**: Request/response validation

.. code-block:: python

    class LoadDatasetIdentifiersParams(BaseModel):
        file_path: str = Field(..., description="Path to data file")
        identifier_column: str = Field(..., description="Column name")
        output_key: str = Field(..., description="Context key for results")

Benefits of the Architecture
----------------------------

1. **Simplicity**: Easy to understand and maintain
2. **Flexibility**: YAML strategies can be modified without code changes  
3. **Reliability**: Type safety prevents runtime errors
4. **Scalability**: Stateless design supports horizontal scaling
5. **Testability**: Each action is independently testable
6. **Performance**: Direct file-based I/O without database overhead

Adding New Actions
------------------

The architecture supports extension through new actions:

1. **Create Action Class**:

   .. code-block:: python

       @register_action("NEW_ACTION")
       class NewAction(TypedStrategyAction[NewParams, ActionResult]):
           def get_params_model(self):
               return NewParams
           
           async def execute_typed(self, params, context, ...):
               # Implementation here
               return ActionResult(...)

2. **Define Parameter Model**:

   .. code-block:: python

       class NewParams(BaseModel):
           input_key: str
           output_key: str
           custom_param: int = 100

3. **Use in Strategy**:

   .. code-block:: yaml

       - name: use_new_action
         action:
           type: NEW_ACTION
           params:
             input_key: "some_data"
             output_key: "processed_data"
             custom_param: 200

Deployment Considerations
-------------------------

The architecture supports various deployment patterns:

**Single Server**
  Run API server with all strategies in one process.

**Containerized**
  Docker container with FastAPI + strategies directory.

**Serverless**
  Function-as-a-Service for individual strategy execution.

**Scaled**
  Multiple API instances with shared strategy configurations.

Performance Characteristics
---------------------------

- **Memory Usage**: Datasets loaded in memory with chunking support for large files
- **I/O Patterns**: Direct file read/write with streaming for large datasets
- **Network**: External API calls (UniProt, CTS, etc.) with caching and retry logic
- **CPU**: Pandas operations, vector computations, and semantic analysis
- **Time Complexity**: Linear for most operations, with parallelization for independent tasks
- **Concurrency**: Async/await throughout for non-blocking I/O operations

The extensible action-based architecture provides excellent performance for common use cases while maintaining the flexibility to add sophisticated new actions for complex biological data mapping scenarios as they arise.

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper/core/strategy_actions/registry.py`` (Action registration system)
- ``biomapper/core/services/strategy_service_v2_minimal.py`` (Strategy executor)
- ``biomapper-api/app/main.py`` (API endpoints and routing)
- ``biomapper_client/biomapper_client/client_v2.py`` (Client implementation)
- ``configs/strategies/templates/*.yaml`` (Strategy templates)
- ``README.md`` (Architecture overview)
- ``CLAUDE.md`` (Current action list and patterns)