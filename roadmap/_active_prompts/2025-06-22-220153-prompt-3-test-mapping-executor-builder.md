# Prompt: Create Unit Tests for `MappingExecutorBuilder`

## Goal
Create a comprehensive suite of unit tests for the new `MappingExecutorBuilder` located at `biomapper/core/engine_components/mapping_executor_builder.py`. This builder orchestrates the entire assembly of the `MappingExecutor` and needs robust testing.

## Context
The `MappingExecutorBuilder` is a new component responsible for using the `InitializationService` to get low-level components, wiring them into high-level coordinators, and constructing the final `MappingExecutor` facade. It also handles resolving circular dependencies post-construction. Your task is to test this entire orchestration process.

## Requirements

1.  **Create Test File:**
    -   Create a new file at `tests/unit/core/engine_components/test_mapping_executor_builder.py`.

2.  **Test Structure:**
    -   Use `pytest` and `unittest.mock`.
    -   Mock the dependencies of the builder, primarily `InitializationService` and the `MappingExecutor` itself, to isolate the builder's logic.

3.  **Test Scenarios:**
    -   **Test `build` Method Orchestration:**
        -   Mock `InitializationService.create_components` to return a dictionary of mocked services.
        -   Mock the constructors for the three coordinators (`LifecycleCoordinator`, `MappingCoordinatorService`, `StrategyCoordinatorService`).
        -   Mock the constructor for `MappingExecutor`.
        -   Call `builder.build()`.
        -   Assert that `create_components` was called.
        -   Assert that each coordinator was instantiated correctly, receiving the right mocked components.
        -   Assert that the final `MappingExecutor` was instantiated with the newly created coordinators.
    -   **Test Post-Build Reference Setting:**
        -   In the test above, verify that the `_set_composite_handler_references` method was called.
        -   Check that the `set_composite_handler` method was called on the appropriate mocked services (e.g., `strategy_orchestrator`, `iterative_execution_service`).
    -   **Test `build_async` Method:**
        -   Mock the `build` method of the builder to return a mocked `executor`.
        -   Mock the `DatabaseSetupService`.
        -   Call `await builder.build_async()`.
        -   Assert that `builder.build()` was called.
        -   Assert that `db_setup_service.initialize_tables` was called twice (once for metamapper, once for cache) with the correct arguments.

## Files to Modify
-   **Create:** `tests/unit/core/engine_components/test_mapping_executor_builder.py`

## Success Criteria
-   The new test file is created with comprehensive unit tests for the builder.
-   The tests validate the entire build orchestration, including component creation, coordinator wiring, and final facade construction.
-   The tests verify that circular dependencies are resolved correctly after the build.
-   All tests pass when run with `pytest`.
