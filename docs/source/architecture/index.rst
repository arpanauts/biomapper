Architecture Documentation
==========================

Comprehensive documentation of BioMapper's architecture and design patterns.

.. toctree::
   :maxdepth: 2
   :caption: Architecture Topics
   
   overview
   action_system
   yaml_strategies
   typed_strategy_actions
   testing
   yaml_strategy_schema
   uniprot_historical_id_resolution

Core Concepts
-------------

**Three-Layer Architecture:**

1. **Client Layer** - Python client library (``biomapper_client``), CLI tools, and Jupyter notebooks
2. **API Layer** - FastAPI REST service with background job management and SSE progress tracking
3. **Core Layer** - Business logic with self-registering actions and strategy execution engine

**Key Design Patterns:**

* **Registry Pattern** - Actions self-register via ``@register_action`` decorator at import time
* **Strategy Pattern** - YAML configurations define workflows as sequences of pluggable actions
* **Pipeline Pattern** - Actions process data through shared execution context
* **Type Safety** - Pydantic models provide runtime validation and compile-time type checking

Quick Architecture Overview
---------------------------

.. code-block:: text

    Client Request → BiomapperClient → FastAPI Server → MapperService → MinimalStrategyService
                                                                     ↓
                                                    ACTION_REGISTRY (Global Dict)
                                                                     ↓
                                              Self-Registering Action Classes
                                                                     ↓
                                                 Execution Context (Dict[str, Any])

Component Responsibilities
--------------------------

**BiomapperClient** (``biomapper_client/biomapper_client/client_v2.py``)
  Python client library providing synchronous wrapper and async interfaces. Primary entry point for programmatic access.

**FastAPI Server** (``biomapper-api/app/main.py``)
  REST API handling HTTP requests, validation, response formatting, and Server-Sent Events (SSE) for progress tracking.

**MapperService** (``biomapper-api/app/services/mapper_service.py``)
  Orchestrates job execution, manages background tasks, handles SQLite persistence, and checkpoint recovery.

**MinimalStrategyService** (``biomapper/core/minimal_strategy_service.py``)
  Core execution engine that loads YAML strategies from ``src/biomapper/configs/strategies/`` and executes actions sequentially.

**ACTION_REGISTRY** (``biomapper/actions/registry.py``)
  Global dictionary where actions self-register at import time using the ``@register_action`` decorator.

**Execution Context**
  Shared state (``Dict[str, Any]``) passed between actions containing:
  
  * ``datasets`` - Named datasets from previous actions
  * ``current_identifiers`` - Active identifier set
  * ``statistics`` - Accumulated metrics
  * ``output_files`` - Generated file paths

Action System
-------------

Actions are the fundamental units of work in BioMapper:

* **Self-Registration** - Use ``@register_action("ACTION_NAME")`` decorator
* **Type Safety** - Inherit from ``TypedStrategyAction[ParamsModel, ResultModel]``
* **Parameter Validation** - Pydantic models for inputs with field descriptions
* **Entity Organization** - Grouped by biological entity type (proteins, metabolites, chemistry)

Example action implementation:

.. code-block:: python

    from biomapper.actions.typed_base import TypedStrategyAction
    from biomapper.actions.registry import register_action
    from pydantic import BaseModel, Field
    from typing import Dict, Any
    
    class MyActionParams(BaseModel):
        input_key: str = Field(..., description="Input dataset key")
        threshold: float = Field(0.8, ge=0.0, le=1.0)
        output_key: str = Field(..., description="Output dataset key")
    
    # ActionResult is typically defined within each action module
    class ActionResult(BaseModel):
        success: bool
        message: str = ""
        data: Dict[str, Any] = Field(default_factory=dict)
    
    @register_action("MY_ACTION")
    class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
        def get_params_model(self) -> type[MyActionParams]:
            return MyActionParams
        
        async def execute_typed(self, params: MyActionParams, context: Dict[str, Any]) -> ActionResult:
            # Access input data
            input_data = context["datasets"].get(params.input_key)
            # Process and store results
            processed_data = input_data  # Processing logic here
            context["datasets"][params.output_key] = processed_data
            return ActionResult(success=True, message="Processed successfully")

YAML Strategy System
--------------------

Strategies define workflows as YAML configurations:

.. code-block:: yaml

    name: my_strategy
    description: Example strategy
    
    parameters:
      input_file: "${DATA_DIR}/input.csv"
      threshold: 0.8
    
    steps:
      - name: load_step
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "${parameters.input_file}"
            output_key: "data"

Variable substitution supports:

* ``${parameters.key}`` - Strategy parameters
* ``${env.VAR}`` - Environment variables
* ``${metadata.field}`` - Metadata fields

Performance Considerations
--------------------------

**Chunking**
  Large datasets are processed in chunks to manage memory.

**Caching**
  Results cached in SQLite for recovery and reuse.

**Async Processing**
  Actions run asynchronously for better performance.

**Job Persistence**
  Jobs persist to database enabling recovery from failures.

Testing Architecture
--------------------

**Test Levels:**

1. **Unit Tests** - Individual action testing
2. **Integration Tests** - Complete workflow testing
3. **API Tests** - REST endpoint testing
4. **E2E Tests** - Full system testing

**Test Organization:**

.. code-block:: text

    tests/
    ├── unit/
    │   └── core/
    │       └── strategy_actions/
    ├── integration/
    │   └── strategies/
    └── api/
        └── endpoints/

Security Considerations
-----------------------

* **Input Validation** - Pydantic models validate all inputs
* **Path Traversal** - File paths validated and sandboxed
* **SQL Injection** - SQLAlchemy ORM prevents injection
* **Rate Limiting** - API endpoints rate limited
* **Error Handling** - Sensitive data scrubbed from errors

Future Architecture Goals
-------------------------

1. **Plugin System** - Dynamic action loading from external packages
2. **Distributed Execution** - Celery/RQ for distributed processing
3. **Stream Processing** - Real-time data stream support
4. **GraphQL API** - Alternative API interface
5. **Kubernetes Support** - Cloud-native deployment

---

---

## Verification Sources
*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- `/biomapper/src/biomapper/actions/registry.py` (Action registry implementation with global ACTION_REGISTRY)
- `/biomapper/src/biomapper/actions/typed_base.py` (TypedStrategyAction base class with execute() wrapper)
- `/biomapper/src/biomapper/core/minimal_strategy_service.py` (Strategy execution engine with dual context support)
- `/biomapper/src/biomapper/api/main.py` (FastAPI server with background job management)
- `/biomapper/src/biomapper/client/client_v2.py` (BiomapperClient synchronous wrapper)
- `/biomapper/README.md` (Project overview and 37+ available actions)
- `/biomapper/CLAUDE.md` (TDD development guidelines and 2025 standardizations)
- `/biomapper/pyproject.toml` (Poetry dependencies and test configuration)