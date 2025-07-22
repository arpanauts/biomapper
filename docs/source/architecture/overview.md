# Biomapper Architecture

## Overview

Biomapper is a streamlined Python framework for biological data harmonization and ontology mapping. Built around YAML-based strategies and core action types, it provides flexible workflows for mapping biological entities like proteins, metabolites, and genes.

The architecture prioritizes simplicity and maintainability over complexity, focusing on the most common biological data mapping scenarios.

## Core Components

### YAML Strategy System
Configuration-driven workflow definition using simple YAML files. Strategies define sequences of actions to be executed on biological data.

### Core Action Types
Three essential actions that handle most biological data mapping scenarios:

- **LOAD_DATASET_IDENTIFIERS**: Load identifiers from CSV/TSV files with flexible column mapping
- **MERGE_WITH_UNIPROT_RESOLUTION**: Merge datasets with historical UniProt identifier resolution  
- **CALCULATE_SET_OVERLAP**: Calculate overlap statistics and generate Venn diagrams

### REST API
FastAPI-based service for remote strategy execution, providing HTTP endpoints for strategy management and execution.

### Python Client
Convenient async client library (`biomapper_client`) for API interaction with proper error handling and timeout management.

### Minimal Strategy Service
Lightweight service that loads and executes YAML strategies without database dependencies. Located at `biomapper/core/minimal_strategy_service.py`.

## Current Directory Structure

```
biomapper/
├── core/
│   ├── strategy_actions/           # Core action implementations
│   │   ├── load_dataset_identifiers.py
│   │   ├── merge_with_uniprot_resolution.py
│   │   ├── calculate_set_overlap.py
│   │   ├── typed_base.py          # Base class for type-safe actions
│   │   └── registry.py            # Action registration system
│   ├── models/                    # Pydantic models
│   │   ├── execution_context.py   # Strategy execution context
│   │   └── action_*.py           # Action parameter models
│   └── minimal_strategy_service.py # Main strategy execution service
├── biomapper-api/                 # REST API service
│   └── app/
│       ├── main.py               # FastAPI application
│       ├── api/routes/           # API endpoints
│       └── services/             # API business logic
├── biomapper_client/             # Python client library
│   └── biomapper_client/
│       └── client.py            # Async HTTP client
├── configs/                      # YAML strategy configurations
├── tests/
│   └── unit/core/strategy_actions/ # Unit tests for actions
└── docs/                        # Documentation
```

## System Architecture

```
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
```

## Data Flow

1. **Strategy Loading**: YAML files define the workflow steps and parameters
2. **Context Creation**: Shared dictionary for data passing between actions
3. **Action Execution**: Sequential step processing with type-safe parameters
4. **Result Aggregation**: Combined results with metadata and timing metrics
5. **Response Formatting**: JSON response with execution statistics

## Key Design Principles

### Simplicity First
Minimal viable functionality without unnecessary complexity. Focus on the 80% use case rather than comprehensive coverage.

### Configuration Over Code  
Define workflows in YAML rather than writing Python code. Makes the system accessible to non-programmers.

### Type Safety
Pydantic models ensure data validation throughout the system, preventing runtime errors and improving reliability.

### API-First Design
All functionality accessible via REST API, enabling remote execution and integration with other systems.

### No Database Dependencies
Strategies execute without persistent storage requirements, using file-based input/output.

### Performance Tracking
Built-in timing metrics for benchmarking and optimization analysis.

## Action System

Actions are the core building blocks of mapping strategies. Each action:

- Inherits from `TypedStrategyAction` for type safety
- Uses Pydantic models for parameter validation
- Operates on a shared context dictionary
- Returns structured results with metadata
- Is automatically registered via decorators

See [Action System](./action_system.rst) for detailed information.

## Strategy Configuration

Strategies are defined in YAML files with this structure:

```yaml
name: "STRATEGY_NAME"
description: "Strategy description"

steps:
  - name: step_name
    action:
      type: ACTION_TYPE
      params:
        parameter1: value1
        parameter2: value2
```

See [YAML Strategies](./yaml_strategies.rst) for complete documentation.

## Deployment

The system runs as a containerized FastAPI service with:
- Async HTTP handling via uvicorn
- Automatic API documentation via OpenAPI/Swagger
- Health check endpoints
- CORS support for web applications

## Future Considerations

### Planned Enhancements
- Additional action types for specialized use cases
- Performance optimizations for large datasets
- Enhanced error reporting and debugging
- Integration with more biological databases

### Scalability
The current architecture supports horizontal scaling by:
- Stateless API design
- File-based configuration
- No database dependencies
- Async request handling