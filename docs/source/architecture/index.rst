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

Core Concepts
-------------

**Three-Layer Architecture:**

1. **Client Layer** - User interfaces (Python client, CLI, notebooks)
2. **API Layer** - REST API with job management
3. **Core Layer** - Business logic and action execution

**Key Design Patterns:**

* **Registry Pattern** - Self-registering actions
* **Strategy Pattern** - YAML-based workflows
* **Pipeline Pattern** - Shared execution context
* **Type Safety** - Pydantic validation throughout

Quick Architecture Overview
---------------------------

.. code-block:: text

    User → BiomapperClient → FastAPI → MinimalStrategyService
                                ↓               ↓
                          MapperService   ACTION_REGISTRY
                                ↓               ↓
                          SQLite DB      Action Classes
                                         (self-registered)

Component Responsibilities
--------------------------

**BiomapperClient**
  Python client library providing synchronous and async interfaces.

**FastAPI Server**
  REST API handling HTTP requests, validation, and response formatting.

**MapperService**
  Orchestrates job execution, manages background tasks, handles persistence.

**MinimalStrategyService**
  Core execution engine that loads YAML strategies and executes actions.

**ACTION_REGISTRY**
  Global dictionary where actions self-register at import time.

**Execution Context**
  Shared state passed between actions containing datasets and metadata.

Action System
-------------

Actions are the fundamental units of work in BioMapper:

* **Self-Registration** - Use ``@register_action`` decorator
* **Type Safety** - Inherit from ``TypedStrategyAction``
* **Parameter Validation** - Pydantic models for inputs
* **Entity Organization** - Grouped by biological entity type

Example action structure:

.. code-block:: python

    @register_action("MY_ACTION")
    class MyAction(TypedStrategyAction[ParamsModel, ResultModel]):
        def get_params_model(self):
            return ParamsModel
        
        async def execute_typed(self, params, context):
            # Action implementation
            return ResultModel(success=True)

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