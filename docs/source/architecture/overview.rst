Architecture Overview
====================

Biomapper is built around a streamlined architecture focused on YAML-based strategies and core action types.

Core Components
---------------

**YAML Strategy System**
  Configuration-driven workflow definition using simple YAML files.

**Core Action Types**
  Three core actions that handle most biological data mapping scenarios:
  
  * LOAD_DATASET_IDENTIFIERS
  * MERGE_WITH_UNIPROT_RESOLUTION  
  * CALCULATE_SET_OVERLAP

**REST API**
  FastAPI-based service for remote strategy execution.

**Python Client**
  Convenient async client library for API interaction.

**Minimal Strategy Service**
  Lightweight service that loads and executes YAML strategies without database dependencies.

System Architecture
-------------------

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
              │ Action Registry │
              │ & Execution     │
              └─────────────────┘

Data Flow
---------

1. **Strategy Loading**: YAML files define the workflow
2. **Context Creation**: Shared dictionary for data passing
3. **Action Execution**: Sequential step processing  
4. **Result Aggregation**: Combined results with metadata
5. **Response Formatting**: JSON response with timing metrics

Key Design Principles
---------------------

**Simplicity First**
  Minimal viable functionality without unnecessary complexity.

**Configuration Over Code**  
  Define workflows in YAML rather than writing Python code.

**Type Safety**
  Pydantic models ensure data validation throughout.

**API-First Design**
  All functionality accessible via REST API.

**No Database Dependencies**
  Strategies execute without persistent storage requirements.