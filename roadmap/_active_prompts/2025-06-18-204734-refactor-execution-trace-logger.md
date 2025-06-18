# Task: Create `ExecutionTraceLogger` Service

## Objective
To centralize and manage the logging of detailed execution traces, metrics, and provenance data to the cache database, extract this functionality from `MappingExecutor` into a dedicated `ExecutionTraceLogger` service.

## Current Implementation
`MappingExecutor` imports various SQLAlchemy models from `biomapper.db.cache_models` (e.g., `EntityMapping`, `EntityMappingProvenance`, `MappingPathExecutionLog`, `MappingSession`, `ExecutionMetric`). Logic for creating, populating, and saving records to these tables is likely embedded within `MappingExecutor`'s methods related to path and strategy execution.

## Refactoring Steps

1.  **Create the `ExecutionTraceLogger` Class:**
    *   Create a new file: `biomapper/core/services/execution_trace_logger.py` (or `biomapper/core/engine_components/execution_trace_logger.py`).
    *   Define an `ExecutionTraceLogger` class.
    *   Its `__init__` method should accept a `SessionManager` instance to obtain database sessions for the cache database.

2.  **Consolidate Logging Logic:**
    *   Identify all sections in `MappingExecutor` (and potentially in components like `PathExecutionManager` or the future `StrategyOrchestrator`/`ActionExecutor` if they directly write to cache tables) where records for `EntityMapping`, `EntityMappingProvenance`, `MappingPathExecutionLog`, `MappingSession`, `ExecutionMetric`, etc., are created and saved.
    *   Create specific public methods in `ExecutionTraceLogger` for different logging events, for example:
        *   `log_mapping_session_start(self, session_data: dict) -> MappingSession`
        *   `log_mapping_session_end(self, session_id, status: str, metrics: dict)`
        *   `log_path_execution(self, path_data: dict) -> MappingPathExecutionLog`
        *   `log_entity_mappings(self, mappings: List[dict], provenance_data: dict)`
        *   `log_execution_metric(self, metric_data: dict)`
    *   These methods will encapsulate the logic of creating SQLAlchemy model instances and committing them to the cache database using an `AsyncSession`.

3.  **Update `MappingExecutor` and Other Components:**
    *   In `MappingExecutor.__init__` (or `MappingExecutorInitializer`), instantiate `ExecutionTraceLogger`.
    *   Replace direct database write operations for trace/log data in `MappingExecutor` (and other relevant components) with calls to the appropriate methods in `ExecutionTraceLogger`.
    *   The `ExecutionTraceLogger` instance would be passed as a dependency to other components that need to log trace information (e.g., `RobustExecutionCoordinator`, `StrategyOrchestrator`, `ActionExecutor`, `PathExecutionManager`).
    *   Update imports as necessary.

## Acceptance Criteria
*   `ExecutionTraceLogger` class is implemented and handles writing execution traces, metrics, and provenance to the cache database.
*   Logic for creating and saving records to cache log tables (e.g., `EntityMapping`, `MappingPathExecutionLog`, `MappingSession`) is moved from `MappingExecutor` (and other components) to `ExecutionTraceLogger`.
*   Relevant components use `ExecutionTraceLogger` for all detailed execution logging to the database.
*   The application's ability to log execution details is preserved and centralized.
