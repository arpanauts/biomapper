# Prompt: Create Unit Tests for the `MappingExecutor` Facade

## Goal
Create unit tests for the new, lean `MappingExecutor` facade. The tests should not test any underlying business logic, but instead verify that each public method of the facade correctly delegates its call to the appropriate mocked coordinator or service.

## Context
The `MappingExecutor` class (to be created in `biomapper/core/mapping_executor.py`) is being refactored into a pure facade. Its only job is to forward calls. This task is to create the tests that enforce this pattern and ensure the wiring is correct.

## Requirements

1.  **Create Test File:**
    -   Create a new file at `tests/unit/core/test_mapping_executor.py`.

2.  **Test Structure:**
    -   Use `pytest` and `unittest.mock`.
    -   In your test setup, create mock objects for each of the coordinators and services that the `MappingExecutor` will take in its constructor (`LifecycleCoordinator`, `MappingCoordinatorService`, `StrategyCoordinatorService`, etc.).
    -   Instantiate the `MappingExecutor` with these mocks.

3.  **Test Scenarios (one test per method):**
    -   For each public method in `MappingExecutor` (e.g., `execute_mapping`, `save_checkpoint`, `async_dispose`):
        -   Create a dedicated test function (e.g., `test_execute_mapping_delegates_correctly`).
        -   Call the method on the `MappingExecutor` instance with sample arguments.
        -   Assert that the corresponding method on the correct mock coordinator/service was called exactly once.
        -   Assert that it was called with the same arguments that were passed to the facade method.

    -   **Example for `execute_mapping`:**
        ```python
        def test_execute_mapping_delegates_to_mapping_coordinator(self):
            # Arrange
            source_name = "test_source"
            # ... other args

            # Act
            self.executor.execute_mapping(source_endpoint_name=source_name, ...)

            # Assert
            self.mock_mapping_coordinator.execute_mapping.assert_called_once_with(
                source_endpoint_name=source_name, ...
            )
        ```

4.  **Coverage:**
    -   Ensure every public, delegating method in the `MappingExecutor` facade has a corresponding test to verify its delegation.

## Files to Modify
-   **Create:** `tests/unit/core/test_mapping_executor.py`

## Success Criteria
-   The new test file is created.
-   Tests are written for all public methods of the `MappingExecutor` facade.
-   Each test successfully verifies that the method call is delegated to the correct underlying service with the correct parameters.
-   All tests pass when run with `pytest`.
