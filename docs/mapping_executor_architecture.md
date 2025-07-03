# Biomapper Architecture Guide

## Overview

Biomapper uses a modern facade-based architecture that provides a clean, simple interface while delegating complex operations to specialized coordinator services. This design promotes separation of concerns, maintainability, and extensibility.

## Core Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                         MappingExecutor                          │
│                          (Facade)                                │
├─────────────────────────────────────────────────────────────────┤
│  Simple public interface:                                        │
│  - initialize()                                                  │
│  - execute_yaml_strategy()                                       │
│  - execute_composite_strategy()                                  │
│  - execute_db_strategy()                                         │
│  - execute()                                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Coordinator Services                          │
├─────────────────────────┬─────────────────┬────────────────────┤
│ StrategyCoordinator     │ SessionManager   │ LifecycleCoord.    │
│ ExecutionCoordinator    │ ActionExecutor   │ CompositeCoord.    │
│ IterativeMappingService │ ActionLoader     │ CheckpointManager  │
└─────────────────────────┴─────────────────┴────────────────────┘
```

## Key Components

### 1. MappingExecutor (Facade)

The `MappingExecutor` class serves as the main entry point for all mapping operations. It follows the facade pattern, providing a simple interface while delegating all actual work to specialized services.

```python
from biomapper.core import MappingExecutor, MappingExecutorBuilder

# Create executor using builder pattern
executor = MappingExecutorBuilder.create(
    db_config=db_config,
    cache_config=cache_config,
    rag_config=rag_config,
    llm_config=llm_config
)

# Initialize (async)
await executor.initialize()

# Execute a strategy
result = await executor.execute_yaml_strategy(
    strategy_file="path/to/strategy.yaml",
    input_data=data,
    options={}
)
```

### 2. MappingExecutorBuilder

The builder pattern is used to construct the MappingExecutor with all its dependencies:

- Validates configurations
- Creates database connections
- Initializes cache systems
- Sets up RAG components
- Configures LLM clients
- Wires together all coordinator services

### 3. Coordinator Services

#### StrategyCoordinatorService
- Loads strategies from YAML files or database
- Validates strategy structure
- Manages strategy metadata
- Handles strategy caching

#### ExecutionCoordinatorService
- Orchestrates the execution of strategy actions
- Manages execution context flow
- Handles error recovery
- Coordinates checkpoint/resume functionality

#### SessionManager
- Manages database sessions
- Handles transaction boundaries
- Ensures proper session lifecycle
- Provides session to services that need it

#### LifecycleCoordinator
- Manages initialization of all services
- Handles graceful shutdown
- Coordinates resource cleanup
- Manages service dependencies

#### ActionExecutor
- Executes individual strategy actions
- Manages action context
- Handles action-level error recovery
- Collects execution metrics

#### ActionLoader
- Dynamically loads action classes
- Maintains action registry
- Validates action interfaces
- Handles action instantiation

### 4. Strategy Actions

Strategy actions are the building blocks of mapping operations. Each action:
- Inherits from `BaseStrategyAction`
- Implements an `execute()` method
- Registered via `@register_action` decorator
- Can access shared context and services

```python
from biomapper.core.strategy_actions import BaseStrategyAction, register_action

@register_action("MY_CUSTOM_ACTION")
class MyCustomAction(BaseStrategyAction):
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Action implementation
        return {"result": processed_data}
```

## Data Flow

1. **Strategy Loading**: YAML file → StrategyCoordinator → Strategy object
2. **Execution Planning**: Strategy → ExecutionCoordinator → Execution plan
3. **Action Execution**: ActionLoader → ActionExecutor → Individual actions
4. **Context Flow**: Each action receives context, modifies it, passes to next
5. **Result Collection**: Final context → Result formatting → User

## Service Dependencies

```
MappingExecutor
    ├── StrategyCoordinatorService
    │   └── SessionManager
    ├── ExecutionCoordinatorService
    │   ├── ActionExecutor
    │   │   └── ActionLoader
    │   └── CheckpointManager
    ├── CompositeCoordinatorService
    │   └── ExecutionCoordinatorService
    ├── IterativeMappingService
    │   └── ExecutionCoordinatorService
    └── LifecycleCoordinator
        └── All services
```

## Configuration Management

The system uses Pydantic models for all configuration:

```python
class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = 5
    echo: bool = False

class CacheConfig(BaseModel):
    backend: Literal["redis", "memory", "disk"]
    ttl: int = 3600
    max_size: Optional[int] = None

class MappingExecutorConfig(BaseModel):
    database: DatabaseConfig
    cache: CacheConfig
    rag: Optional[RAGConfig] = None
    llm: Optional[LLMConfig] = None
```

## Extension Points

### Adding New Actions

1. Create a new class inheriting from `BaseStrategyAction`
2. Implement the `execute()` method
3. Use `@register_action` decorator
4. Place in `biomapper/core/strategy_actions/`

### Adding New Coordinators

1. Create service implementing coordinator interface
2. Add to MappingExecutorBuilder
3. Register with LifecycleCoordinator
4. Update executor facade if new public methods needed

### Custom Cache Backends

1. Implement cache interface
2. Register in cache factory
3. Update CacheConfig options

### LLM Providers

1. Implement LLM client interface
2. Add to LLM factory
3. Update LLMConfig options

## Best Practices

1. **Always use the facade**: Don't directly access coordinator services
2. **Async all the way**: All operations are async for consistency
3. **Context immutability**: Actions should not modify input context directly
4. **Error handling**: Use custom exceptions from `biomapper.core.exceptions`
5. **Configuration validation**: Use Pydantic models for all configs
6. **Testing**: Mock at the coordinator level, not individual services

## Migration from Legacy Architecture

If migrating from the old database-driven mapping paths:

1. Convert mapping paths to YAML strategies
2. Replace direct client usage with strategy actions
3. Update initialization to use MappingExecutorBuilder
4. Convert synchronous code to async
5. Update error handling to use new exception hierarchy

## See Also

- [Strategy Action Development Guide](./strategy_action_development.md)
- [YAML Strategy Schema](./source/architecture/yaml_strategy_schema.md)
- [Configuration Reference](./CONFIG_TYPE_FIELD_REFERENCE.md)
- [API Documentation](./api/README.md)