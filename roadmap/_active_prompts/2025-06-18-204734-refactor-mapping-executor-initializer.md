# Task: Create `MappingExecutorInitializer`

## Objective
To simplify the instantiation and setup of `MappingExecutor`, extract the complex initialization logic, including database table creation, into a `MappingExecutorInitializer` (or Factory) class.

## Current Implementation
`MappingExecutor` has a static `create` method that handles asynchronous instantiation and initialization, including calling `_init_db_tables`. The `__init__` method itself is also quite large.

## Refactoring Steps

1.  **Create the `MappingExecutorInitializer` Class:**
    *   Create a new file: `biomapper/core/engine_components/mapping_executor_initializer.py` (or `biomapper/core/factories/mapping_executor_factory.py`).
    *   Define a `MappingExecutorInitializer` class.

2.  **Move Initialization Logic:**
    *   Move the logic from the static `MappingExecutor.create` method into a method in `MappingExecutorInitializer`, e.g., `async create_executor(...)`.
    *   Move the `MappingExecutor._init_db_tables` method into `MappingExecutorInitializer` as a helper method, or integrate its logic directly into `create_executor`.
    *   The `create_executor` method will be responsible for:
        *   Creating database engines (perhaps by instantiating `SessionManager` first, or if `SessionManager` also needs complex setup, this initializer could handle that too).
        *   Ensuring database tables are created for both metamapper and cache DBs.
        *   Instantiating all necessary components that `MappingExecutor` depends on (e.g., `SessionManager`, `ClientManager`, `ConfigLoader`, `IdentifierLoader`, `ProgressReporter`, `CacheManager`, `PathFinder`, `StrategyOrchestrator`, `CheckpointManager`, and the newly proposed services like `MetadataQueryService`, `RobustExecutionCoordinator`, `ExecutionTraceLogger`).
        *   Finally, instantiating `MappingExecutor` itself, passing all its dependencies to a (now potentially simpler) `__init__` method.

3.  **Simplify `MappingExecutor`:**
    *   Remove the static `create` method from `MappingExecutor`.
    *   Remove the `_init_db_tables` method from `MappingExecutor`.
    *   Simplify `MappingExecutor.__init__` to primarily accept already instantiated dependencies. It should no longer create engines or other components itself, but receive them as arguments.

4.  **Update Usage:**
    *   Anywhere `MappingExecutor.create(...)` was called, it should now instantiate `MappingExecutorInitializer` and call its `create_executor(...)` method.

## Acceptance Criteria
*   `MappingExecutorInitializer` class is implemented and handles the creation and setup of `MappingExecutor` instances.
*   Database table initialization logic is moved to `MappingExecutorInitializer`.
*   `MappingExecutor.__init__` is simplified, primarily accepting pre-configured dependencies.
*   The static `create` method is removed from `MappingExecutor`.
*   The application can still correctly instantiate and use `MappingExecutor` instances via the new initializer.
