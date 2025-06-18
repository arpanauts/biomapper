# Task: Generate Unit Tests for `ExecutionTraceLogger`

## Objective
To ensure the `ExecutionTraceLogger` service correctly creates, populates, and saves execution trace records (e.g., `EntityMapping`, `MappingPathExecutionLog`, `MappingSession`, `ExecutionMetric`) to the cache database.

## Component to Test
`biomapper.core.services.execution_trace_logger.ExecutionTraceLogger`
(Assuming this path after refactoring)

## Test File Target
`tests/core/services/test_execution_trace_logger.py`

## Key Functionalities to Test
*   Logging of mapping session start and end events (`log_mapping_session_start`, `log_mapping_session_end`).
*   Logging of individual mapping path executions (`log_path_execution`).
*   Logging of entity mappings and their provenance (`log_entity_mappings`).
*   Logging of execution metrics (`log_execution_metric`).
*   Correct creation and population of SQLAlchemy models for cache DB tables.
*   Proper use of `SessionManager` to obtain `AsyncSession` for the cache database.
*   Correct interaction with `AsyncSession` (e.g., `add`, `add_all`, `commit`, `refresh`).
*   Error handling for database operations.

## Mocking Strategy
*   Mock `SessionManager` to control `AsyncSession` instances provided to the service.
*   Mock `AsyncSession` methods (`add`, `add_all`, `commit`, `refresh`, `begin`).
*   Mock the constructors of SQLAlchemy models from `biomapper.db.cache_models` (e.g., `EntityMapping`, `MappingPathExecutionLog`, `MappingSession`, `ExecutionMetric`) to inspect data passed to them.
*   Use `unittest.mock.AsyncMock` for asynchronous methods and context managers.
*   Use `unittest.mock.patch` to replace model classes if needed.

## Test Cases

1.  **`__init__`:**
    *   Test that `ExecutionTraceLogger` initializes correctly with a `SessionManager` instance.

2.  **`log_mapping_session_start` (or equivalent method):**
    *   Provide sample session data.
    *   Verify a `MappingSession` model instance is created with the correct data.
    *   Verify `session.add` and `session.commit` are called.
    *   Verify the created `MappingSession` object (or its ID) is returned.

3.  **`log_mapping_session_end` (or equivalent method):**
    *   Provide a session ID, status, and metrics.
    *   Verify the correct `MappingSession` record is fetched/updated (or a new record is made if design dictates).
    *   Verify `session.commit` is called.

4.  **`log_path_execution` (or equivalent method):**
    *   Provide sample path execution data.
    *   Verify a `MappingPathExecutionLog` model instance is created with correct data.
    *   Verify `session.add` and `session.commit` are called.

5.  **`log_entity_mappings` (or equivalent method):**
    *   Provide a list of sample entity mapping data and provenance data.
    *   Verify `EntityMapping` and `EntityMappingProvenance` model instances are created correctly for each mapping.
    *   Verify relationships between them are established if applicable.
    *   Verify `session.add_all` (or multiple `add`) and `session.commit` are called.

6.  **`log_execution_metric` (or equivalent method):**
    *   Provide sample metric data.
    *   Verify an `ExecutionMetric` model instance is created with correct data.
    *   Verify `session.add` and `session.commit` are called.

7.  **Database Interaction:**
    *   Verify that `SessionManager.get_session()` is called to obtain a session for the cache DB.
    *   Verify that session commit/rollback is handled correctly, especially within a `session.begin()` context if used.

8.  **Error Handling:**
    *   Test behavior when `session.commit()` or other DB operations raise a `SQLAlchemyError` (e.g., `CacheTransactionError` should be raised or handled).
    *   Test graceful handling if input data is malformed (though primary validation might be elsewhere).

## Acceptance Criteria
*   All specified test cases pass.
*   Tests cover the logging of all relevant execution trace events.
*   Mocks are used effectively to isolate `ExecutionTraceLogger` from actual database writes.
*   Correct data mapping to SQLAlchemy models is verified.
*   Tests confirm correct interaction with `SessionManager` and `AsyncSession` for the cache database.
*   Error handling during database operations is verified.
