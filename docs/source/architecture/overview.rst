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
  * Executes actions sequentially with comprehensive error handling
  * Manages execution context throughout workflow lifecycle
  * Supports variable substitution: ``${parameters.key}``, ``${env.VAR}``, ``${metadata.field}``, ``${VAR:-default}``
  * No database dependencies - pure business logic implementation

**Execution Context**
  Shared state dictionary containing:
  
  * ``datasets`` - Named data collections
  * ``current_identifiers`` - Active identifier set
  * ``statistics`` - Accumulated metrics
  * ``output_files`` - Generated file paths

**TypedStrategyAction** (``biomapper/core/strategy_actions/typed_base.py``)
  Generic base class providing:
  
  * Pydantic parameter validation with field descriptions and constraints
  * Standardized async execution interface (execute_typed method)
  * Type-safe result handling with ActionResult model
  * Automatic error handling and context preservation
  * Backward compatibility with dict-based interface via execute() wrapper
  * Support for ``extra="allow"`` in Pydantic models for migration flexibility

Data Flow
---------

1. **Strategy Definition** - User creates YAML workflow
2. **Client Request** - BiomapperClient sends strategy name or YAML to API
3. **Job Creation** - MapperService creates background job with unique job_id
4. **Strategy Loading** - MinimalStrategyService loads YAML from configs/ or direct string
5. **Action Execution** - Each action processes data sequentially via ACTION_REGISTRY lookup
6. **Context Updates** - Actions read/write shared context dictionary
7. **Result Persistence** - Results and checkpoints saved to SQLite (biomapper.db)
8. **Client Response** - Results returned via REST API or Server-Sent Events (SSE) stream

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
            
            # Update statistics
            context.setdefault("statistics", {})["filtered_count"] = len(filtered)
            
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

* **Chunking** - Large datasets processed in configurable chunks via CHUNK_PROCESSOR action
* **Async Execution** - All actions implement async execute_typed() for better throughput
* **Caching** - Job results and checkpoints cached in SQLite for recovery and reuse
* **SSE Streaming** - Real-time progress updates via Server-Sent Events without polling overhead
* **Memory Management** - Streaming file operations and iterative processing for large datasets
* **Connection Pooling** - Database connection pooling for concurrent job execution

---

Verification Sources
--------------------
*Last verified: 2025-08-14*

This documentation was verified against the following project resources:

- ``/biomapper/biomapper/core/services/strategy_service_v2_minimal.py`` (MinimalStrategyService execution engine implementation)
- ``/biomapper/biomapper/core/strategy_actions/typed_base.py`` (TypedStrategyAction generic base class)
- ``/biomapper/biomapper/core/strategy_actions/registry.py`` (Global ACTION_REGISTRY and self-registration)
- ``/biomapper/biomapper-api/app/core/mapper_service.py`` (MapperService job orchestration with SQLite persistence)
- ``/biomapper/biomapper-api/app/main.py`` (FastAPI server configuration and middleware)
- ``/biomapper/README.md`` (High-level architecture overview)
- ``/biomapper/CLAUDE.md`` (Design patterns, TDD approach, and migration guidelines)