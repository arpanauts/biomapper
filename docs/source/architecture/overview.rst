BioMapper Architecture Overview
===============================

BioMapper is a YAML-based workflow platform built on a self-registering action system. While originally designed for biological data harmonization (proteins, metabolites, chemistry), its extensible architecture supports any workflow that can be expressed as a sequence of actions operating on shared execution context.

Core Design Principles
----------------------

* **Modularity** - Each action is independent, reusable, and self-contained
* **Type Safety** - Pydantic models provide runtime validation and compile-time type checking
* **Extensibility** - New actions self-register via decorators without modifying core code
* **Reproducibility** - YAML strategies ensure consistent, version-controlled execution
* **Fault Tolerance** - Job persistence and checkpointing enable recovery from failures
* **AI-Ready** - Built for integration with Claude Code and LLM-assisted development

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

**MinimalStrategyService** (``biomapper/core/services/strategy_service_v2_minimal.py``)
  Lightweight execution engine that:
  
  * Loads YAML strategies from ``configs/strategies/`` at runtime
  * Executes actions sequentially with error handling
  * Manages execution context throughout workflow
  * Supports variable substitution (parameters, environment, metadata)
  * No database dependencies - pure business logic

**Execution Context**
  Shared state dictionary containing:
  
  * ``datasets`` - Named data collections
  * ``current_identifiers`` - Active identifier set
  * ``statistics`` - Accumulated metrics
  * ``output_files`` - Generated file paths

**TypedStrategyAction** (``biomapper/core/strategy_actions/typed_base.py``)
  Generic base class providing:
  
  * Pydantic parameter validation with field descriptions
  * Standardized async execution interface
  * Type-safe result handling with ActionResult
  * Automatic error handling and context preservation
  * Backward compatibility with dict-based interface

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

Example Action Implementation
-----------------------------

.. code-block:: python

    from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
    from biomapper.core.strategy_actions.registry import register_action
    from pydantic import BaseModel, Field
    from typing import Dict, Any
    
    class MyActionParams(BaseModel):
        input_key: str = Field(..., description="Input dataset key")
        threshold: float = Field(0.8, ge=0.0, le=1.0, description="Filter threshold")
        output_key: str = Field(..., description="Output dataset key")
    
    @register_action("MY_ACTION")
    class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
        """Process biological data with threshold filtering."""
        
        def get_params_model(self) -> type[MyActionParams]:
            return MyActionParams
        
        async def execute_typed(
            self, 
            params: MyActionParams, 
            context: Dict[str, Any]
        ) -> ActionResult:
            # Access input data from shared context
            input_data = context["datasets"].get(params.input_key, [])
            
            # Apply threshold filtering
            filtered = [item for item in input_data 
                       if item.get("score", 0) >= params.threshold]
            
            # Store results in context for next action
            context["datasets"][params.output_key] = filtered
            
            return ActionResult(
                success=True,
                message=f"Filtered {len(input_data)} to {len(filtered)} items",
                data={"filtered_count": len(filtered)}
            )

Key Architectural Patterns
--------------------------

**Registry Pattern**
  Actions self-register at import time via ``@register_action`` decorator, eliminating manual registration and enabling plugin-style extensibility.

**Strategy Pattern**
  YAML configurations define workflows as pluggable action sequences, separating business logic from orchestration.

**Pipeline Pattern**
  Actions process data through shared execution context, enabling complex multi-step workflows with data persistence between steps.

**Type Safety Pattern**
  Pydantic models provide compile-time type hints and runtime validation throughout the system, catching errors early.

**Repository Pattern**
  SQLite persistence layer abstracts job storage, enabling checkpoint recovery and progress tracking.

Performance Considerations
--------------------------

* **Chunking** - Large datasets processed in configurable chunks (default 1000 rows)
* **Async Execution** - Actions run asynchronously for better throughput
* **Caching** - Results cached in SQLite for recovery and reuse
* **SSE Streaming** - Real-time progress updates without polling
* **Memory Management** - Streaming file operations for large datasets

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

* ``biomapper/core/services/strategy_service_v2_minimal.py`` (Core execution engine)
* ``biomapper/core/strategy_actions/typed_base.py`` (Base action class)
* ``biomapper/core/strategy_actions/registry.py`` (Action registry)
* ``biomapper-api/app/core/mapper_service.py`` (Job orchestration)
* ``README.md`` (Architecture overview)
* ``CLAUDE.md`` (Design patterns and guidelines)