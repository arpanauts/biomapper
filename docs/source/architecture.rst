Architecture Overview
=====================

Biomapper is built around an **extensible action-based architecture** that prioritizes simplicity and maintainability while allowing for sophisticated mapping approaches. The system currently ships with three foundational actions and is designed for easy expansion with additional specialized actions through YAML-based strategy configuration.

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

    from biomapper.core.minimal_strategy_service import MinimalStrategyService
    
    # Initialize with strategies directory
    service = MinimalStrategyService("configs/")
    
    # Execute a strategy
    result = await service.execute_strategy("UKBB_HPA_COMPARISON")

Core Actions
~~~~~~~~~~~~

The system currently includes three foundational actions, with the architecture designed to support additional specialized actions as mapping requirements grow:

**LOAD_DATASET_IDENTIFIERS**
  Loads identifiers from CSV/TSV files with flexible column mapping and filtering options.

**MERGE_WITH_UNIPROT_RESOLUTION**  
  Merges datasets with historical UniProt identifier resolution using direct matching, composite handling, and API fallback.

**CALCULATE_SET_OVERLAP**
  Calculates comprehensive overlap statistics and generates Venn diagrams for dataset comparison.

REST API (FastAPI)
~~~~~~~~~~~~~~~~~~~

The REST API provides HTTP endpoints for:

- Strategy execution
- Health checks  
- Strategy listing
- File uploads (if needed)

.. code-block:: python

    # API endpoint for strategy execution
    @app.post("/strategies/{strategy_name}/execute")
    async def execute_strategy(strategy_name: str):
        service = MinimalStrategyService("configs/")
        result = await service.execute_strategy(strategy_name)
        return result

Python Client
~~~~~~~~~~~~~~

The async Python client (``biomapper_client``) provides a convenient interface:

- Async HTTP client using httpx
- Automatic timeout handling (3+ hours for large datasets)
- Proper error handling and retries
- Context manager pattern

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
    │   ├── strategy_actions/           # Three core actions
    │   │   ├── load_dataset_identifiers.py
    │   │   ├── merge_with_uniprot_resolution.py
    │   │   ├── calculate_set_overlap.py
    │   │   ├── typed_base.py          # Base class
    │   │   └── registry.py            # Action registration
    │   ├── models/                    # Pydantic models
    │   └── minimal_strategy_service.py # Main service
    ├── biomapper-api/                 # REST API
    ├── biomapper_client/             # Python client
    ├── configs/                      # YAML strategies
    └── tests/unit/core/strategy_actions/ # Tests

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

- **Memory Usage**: Datasets loaded entirely in memory for processing
- **I/O Patterns**: Direct file read/write without database overhead
- **Network**: UniProt API calls for unmatched identifiers (configurable)
- **CPU**: Primarily pandas operations and CSV processing
- **Time Complexity**: Linear with dataset size for most operations

The extensible action-based architecture provides excellent performance for common use cases while maintaining the flexibility to add sophisticated new actions for complex biological data mapping scenarios as they arise.