# Prompt: Implement the `MappingExecutor` as a Pure Facade

## Goal
Create the `biomapper/core/mapping_executor.py` file, defining the `MappingExecutor` class as a pure facade. This class should delegate all its operational logic to specialized coordinator services, and its constructor should be extremely lean.

## Context
The `InitializationService` is responsible for creating all low-level components, and the `MappingExecutorBuilder` is responsible for assembling them into high-level coordinators. This task is to create the final piece: a `MappingExecutor` that simply acts as a clean entry point, receiving the pre-built coordinators from the builder.

The old `mapping_executor.py` has been deleted, so you are creating this file from scratch.

## Requirements

1.  **Create the File:**
    -   Create a new file at `biomapper/core/mapping_executor.py`.

2.  **Define the `MappingExecutor` Class:**
    -   The class should inherit from `CompositeIdentifierMixin` for backward compatibility.

3.  **Implement the `__init__` Constructor:**
    -   The constructor must be lightweight.
    -   It should accept the following pre-initialized components as arguments:
        -   `lifecycle_coordinator: LifecycleCoordinator`
        -   `mapping_coordinator: MappingCoordinatorService`
        -   `strategy_coordinator: StrategyCoordinatorService`
        -   `session_manager: SessionManager`
        -   `metadata_query_service: MetadataQueryService`
    -   Store these components as instance attributes (e.g., `self.lifecycle_coordinator = lifecycle_coordinator`).

4.  **Implement Public Methods as Delegations:**
    -   All public methods should be one-line delegations to the appropriate coordinator.
    -   **Lifecycle Methods:**
        -   `async_dispose()`: Delegate to `self.lifecycle_coordinator.dispose_resources()`.
        -   `save_checkpoint(...)`: Delegate to `self.lifecycle_coordinator.save_checkpoint(...)`.
        -   `load_checkpoint(...)`: Delegate to `self.lifecycle_coordinator.load_checkpoint(...)`.
        -   `start_session(...)`: Delegate to `self.lifecycle_coordinator.start_session(...)`.
        -   `end_session(...)`: Delegate to `self.lifecycle_coordinator.end_session(...)`.
    -   **Mapping Execution Methods:**
        -   `execute_mapping(...)`: Delegate to `self.mapping_coordinator.execute_mapping(...)`.
        -   `_execute_path(...)`: Delegate to `self.mapping_coordinator.execute_path(...)`.
    -   **Strategy Execution Methods:**
        -   `execute_strategy(...)`: Delegate to `self.strategy_coordinator.execute_strategy(...)`.
        -   `execute_yaml_strategy(...)`: Delegate to `self.strategy_coordinator.execute_yaml_strategy(...)`.
        -   `execute_robust_yaml_strategy(...)`: Delegate to `self.strategy_coordinator.execute_robust_yaml_strategy(...)`.
    -   **Utility Methods:**
        -   `get_strategy(...)`: Delegate to `self.metadata_query_service.get_strategy(...)`.
        -   `get_cache_session()`: Delegate to `self.session_manager.get_async_cache_session()`.

5.  **Add Necessary Imports:**
    -   Include all necessary imports for type hints and referenced classes.

## Files to Modify
-   **Create:** `biomapper/core/mapping_executor.py`

## Success Criteria
-   The new `mapping_executor.py` file is created.
-   The `MappingExecutor` class is defined with a lean constructor as specified.
-   All public methods are implemented as simple delegations to the correct coordinator or service.
-   The code is clean, well-documented with type hints, and passes linting checks.
