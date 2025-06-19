# Task 2: Create `StrategyExecutionService`

## Objective
Extract the high-level logic for executing YAML-defined mapping strategies from `MappingExecutor` into a dedicated `StrategyExecutionService`. This service will be the primary entry point for running complex, multi-step mapping workflows.

## Rationale
Strategy execution is a distinct and complex workflow that involves orchestration, robust execution (retries, checkpointing), and progress tracking. Separating this into its own service clarifies its role, decouples it from simpler path execution, and makes `MappingExecutor` a cleaner facade.

## New Component Location
- Create a new file: `biomapper/core/services/strategy_execution_service.py`
- Define the class: `StrategyExecutionService`

## Core Responsibilities of `StrategyExecutionService`
- Load and validate a mapping strategy by name.
- Orchestrate the execution of the strategy's steps using the `StrategyOrchestrator`.
- Coordinate robust execution, including checkpointing and retries, using the `RobustExecutionCoordinator`.
- Manage progress reporting for the entire strategy execution.

## Methods to Move/Refactor from `MappingExecutor`

The logic from the following `MappingExecutor` methods should be moved to `StrategyExecutionService`:

1.  `execute_strategy_by_name`: This will become the main public method of the new service.
2.  `execute_strategy`: This method contains the core orchestration logic and will be moved and likely made a private helper within the new service, called by the new `execute_strategy_by_name`.

## `StrategyExecutionService` `__init__`
The constructor should accept the components it depends on, which will be injected by `MappingExecutor`:

- `logger`
- `config_loader: ConfigLoader`
- `robust_execution_coordinator: RobustExecutionCoordinator`
- `session_manager: SessionManager`
- `identifier_loader: IdentifierLoader`
- `progress_reporter: ProgressReporter`

## Refactoring Steps
1.  **Create the File and Class:** Create `biomapper/core/services/strategy_execution_service.py` and define the `StrategyExecutionService` class.
2.  **Define `__init__`:** Implement the constructor to accept its dependencies.
3.  **Move and Adapt Methods:**
    - Move the entire `execute_strategy_by_name` and `execute_strategy` methods from `MappingExecutor` to `StrategyExecutionService`.
    - Refactor the methods to work in the new class. Update `self.` references to access dependencies passed into the service's constructor.
    - The main public method should be `async def execute(...)` or similar, which takes the `strategy_name`, `input_identifiers`, etc.
4.  **Update `MappingExecutor`:**
    - In `MappingExecutor`, remove the `execute_strategy_by_name` and `execute_strategy` methods.
    - Instantiate `StrategyExecutionService` in `MappingExecutor.__init__` and store it as `self.strategy_execution_service`.
    - Add a new public method to `MappingExecutor` named `execute_strategy` which simply delegates the call to `self.strategy_execution_service.execute(...)`.

## Acceptance Criteria
- The new `StrategyExecutionService` is created and contains the complete logic for executing a YAML-defined mapping strategy.
- `MappingExecutor` no longer contains strategy execution logic; it delegates calls to the new service.
- All existing integration tests for strategy execution are updated to call the new `MappingExecutor.execute_strategy` method and continue to pass, verifying the refactoring was successful.
- New unit tests for `StrategyExecutionService` should be created to test its logic in isolation.
