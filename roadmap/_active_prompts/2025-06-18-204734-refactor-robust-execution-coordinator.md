# Task: Extract `RobustExecutionCoordinator` from `MappingExecutor`

## Objective
To separate high-level execution lifecycle management (including robustness features like checkpointing and retries) from core strategy orchestration, extract this logic from `MappingExecutor` into a `RobustExecutionCoordinator` class.

## Current Implementation
`MappingExecutor` has methods like `execute_robust_yaml_strategy` which wrap the core strategy execution with additional features like checkpoint loading/saving and potentially retry mechanisms.

## Refactoring Steps

1.  **Create the `RobustExecutionCoordinator` Class:**
    *   Create a new file: `biomapper/core/engine_components/robust_execution_coordinator.py`.
    *   Define a `RobustExecutionCoordinator` class.
    *   Its `__init__` method should accept dependencies such as `StrategyOrchestrator`, `CheckpointManager`, `ProgressReporter`, and potentially `MappingExecutor`'s configuration for retries, batch sizes if these are managed at this level.

2.  **Move Robust Execution Logic:**
    *   Transfer the logic from `MappingExecutor.execute_robust_yaml_strategy` (and any helper methods exclusively used by it for robustness) into a primary method in `RobustExecutionCoordinator`, e.g., `execute_strategy_robustly(...)`.
    *   This includes:
        *   Generating execution IDs.
        *   Loading checkpoints via `CheckpointManager`.
        *   Implementing retry logic (if present or planned here).
        *   Calling the `StrategyOrchestrator` to execute the actual strategy steps.
        *   Handling high-level exceptions from the orchestration and updating checkpoint/progress status.
        *   Saving/clearing checkpoints via `CheckpointManager`.
        *   Reporting overall execution status (start, failure, completion) via `ProgressReporter`.

3.  **Update `MappingExecutor`:**
    *   In `MappingExecutor.__init__`, instantiate `RobustExecutionCoordinator` with its required dependencies.
    *   The public method in `MappingExecutor` (e.g., `execute_robust_yaml_strategy`) should now primarily delegate to the `RobustExecutionCoordinator.execute_strategy_robustly(...)` method.
    *   Remove the transferred logic from `MappingExecutor`.
    *   Update imports as necessary.

## Acceptance Criteria
*   `RobustExecutionCoordinator` class is implemented and manages the robust execution lifecycle of strategies.
*   Logic related to checkpoint integration and high-level retry/error handling for strategy execution is moved from `MappingExecutor` to this new class.
*   `MappingExecutor` uses `RobustExecutionCoordinator` for executing strategies that require these robustness features.
*   The application's strategy execution, including checkpointing, functions as before.
