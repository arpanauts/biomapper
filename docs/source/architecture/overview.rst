BioMapper Architecture
======================

BioMapper is a workflow platform with an extensible architecture designed for data processing pipelines, with specialized support for biological data harmonization.

Core Design Principles
----------------------

* **Modularity** - Each action is independent and reusable
* **Type Safety** - Pydantic models ensure data validation
* **Extensibility** - New actions self-register without core changes
* **Reproducibility** - YAML strategies ensure consistent execution

System Architecture
-------------------

.. code-block:: text

    ┌─────────────────────────────────────────────────────┐
    │                   Client Layer                      │
    │  • BiomapperClient (Python)                        │
    │  • CLI Scripts                                     │
    │  • Jupyter Notebooks                               │
    └───────────────────┬─────────────────────────────────┘
                        │ HTTP/REST
    ┌───────────────────▼─────────────────────────────────┐
    │                    API Layer                        │
    │  • FastAPI Server (port 8000)                      │
    │  • MapperService (job orchestration)               │
    │  • Background job processing                        │
    │  • SQLite persistence (biomapper.db)               │
    └───────────────────┬─────────────────────────────────┘
                        │
    ┌───────────────────▼─────────────────────────────────┐
    │                   Core Layer                        │
    │  • MinimalStrategyService (execution engine)       │
    │  • ACTION_REGISTRY (global action registry)        │
    │  • TypedStrategyAction (base class)                │
    │  • Execution Context (shared state)                │
    └─────────────────────────────────────────────────────┘

Component Details
-----------------

**ACTION_REGISTRY**
  Global dictionary mapping action names to classes. Actions self-register at import time using the ``@register_action`` decorator.

**MinimalStrategyService**
  Lightweight execution engine that:
  
  * Loads YAML strategies from ``configs/strategies/``
  * Executes actions sequentially
  * Manages execution context throughout workflow
  * No database dependencies

**Execution Context**
  Shared state dictionary containing:
  
  * ``datasets`` - Named data collections
  * ``current_identifiers`` - Active identifier set
  * ``statistics`` - Accumulated metrics
  * ``output_files`` - Generated file paths

**TypedStrategyAction**
  Base class providing:
  
  * Pydantic parameter validation
  * Standardized execution interface
  * Type-safe result handling
  * Automatic error handling

Data Flow
---------

1. **Strategy Definition** - User creates YAML workflow
2. **Client Request** - BiomapperClient sends strategy to API
3. **Job Creation** - MapperService creates background job
4. **Strategy Loading** - MinimalStrategyService loads YAML
5. **Action Execution** - Each action processes data sequentially
6. **Context Updates** - Actions read/write shared context
7. **Result Persistence** - Results saved to SQLite
8. **Client Response** - Results returned via REST/SSE

Action Organization
-------------------

Actions are organized by biological entity type:

.. code-block:: text

    strategy_actions/
    ├── entities/
    │   ├── proteins/        # UniProt, Ensembl
    │   ├── metabolites/     # HMDB, InChIKey, CHEBI
    │   └── chemistry/       # LOINC, clinical tests
    ├── algorithms/          # Reusable algorithms
    ├── utils/              # General utilities
    └── io/                 # Import/export actions

Example Action
--------------

.. code-block:: python

    from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
    from biomapper.core.strategy_actions.registry import register_action
    from pydantic import BaseModel
    
    class MyActionParams(BaseModel):
        input_key: str
        threshold: float = 0.8
    
    @register_action("MY_ACTION")
    class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
        def get_params_model(self):
            return MyActionParams
        
        async def execute_typed(self, params, context):
            # Process data from context
            data = context["datasets"][params.input_key]
            # ... processing logic ...
            return ActionResult(success=True)

Key Patterns
------------

**Registry Pattern**
  Actions self-register, eliminating manual registration and enabling plugin-style extensibility.

**Strategy Pattern**
  YAML configurations define workflows as pluggable action sequences.

**Pipeline Pattern**
  Actions process data through shared context, enabling complex multi-step workflows.

**Type Safety Pattern**
  Pydantic models provide compile-time and runtime validation throughout the system.