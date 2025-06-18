# Task: Create Unit Tests for `StrategyOrchestrator`

## Objective
To ensure the core mapping strategy execution engine is robust, create unit tests for the `StrategyOrchestrator`. The tests will validate the orchestration logic and its interaction with other components.

## Location for Tests
Create a new test file: `tests/core/engine_components/test_strategy_orchestrator.py`

## Test Strategy
The `StrategyOrchestrator` is a high-level component that depends on many other parts of the engine. The tests should heavily utilize mocking to isolate the orchestration logic.

Mock the following dependencies:
*   `ActionExecutor`
*   `ClientManager`
*   `MappingResultBundle`
*   `PlaceholderResolver`

## Test Cases

1.  **Test Successful Strategy Execution**: Provide a mock strategy with several steps. Mock the `ActionExecutor` to return successful results for each step. Assert that the orchestrator executes all steps in order and returns a completed `MappingResultBundle`.
2.  **Test Strategy Failure**: Mock a strategy where one of the actions fails. Assert that the `StrategyOrchestrator` stops execution at the point of failure and correctly updates the `MappingResultBundle` with a 'failed' status and error message.
3.  **Test Placeholder Resolution**: Provide a strategy with placeholders (e.g., `${DATA_DIR}`). Mock the `PlaceholderResolver` and verify that `_resolve_placeholders_in_strategy` is called and that the placeholders are correctly resolved before actions are executed.
4.  **Test Context Updates**: Verify that the `execution_context` is correctly passed to and updated by each action during the strategy execution.
5.  **Test Result Bundle Finalization**: Ensure that the `MappingResultBundle.finalize()` method is called at the end of the execution, both on success and failure.

## Acceptance Criteria
*   A new test file `tests/core/engine_components/test_strategy_orchestrator.py` is created.
*   The tests effectively isolate and validate the orchestration logic of `StrategyOrchestrator`.
*   All tests pass successfully.
