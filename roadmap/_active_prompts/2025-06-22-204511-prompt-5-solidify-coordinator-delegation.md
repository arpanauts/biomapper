# Task: Solidify Coordinator Delegation in MappingExecutor

**Task Objective:**
Ensure that all public operational methods in `MappingExecutor` (e.g., `execute_mapping`, `execute_strategy`, `_execute_path`) are purely delegating calls to the appropriate coordinator service (`MappingCoordinatorService` or `StrategyCoordinatorService`). No business logic should remain in the `MappingExecutor` methods themselves.

**Prerequisites:**
- The `MappingExecutor` has been refactored to receive its coordinators via its `__init__` method (as per `prompt-3-refactor-executor-facade.md`).
- The `MappingCoordinatorService` and `StrategyCoordinatorService` exist.

**Input Context:**
- `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`: The file to be modified.
- `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_coordinator_service.py`: A target for delegation.
- `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_coordinator_service.py`: A target for delegation.

**Expected Outputs:**
1.  A modified `mapping_executor.py` file where the implementations of `execute_mapping`, `execute_strategy`, and `_execute_path` consist of a single line: a call to the corresponding method on the appropriate coordinator.
2.  Any logic, parameter transformation, or default value handling that currently exists in the `MappingExecutor` methods will be moved into the respective coordinator service method.

**Success Criteria:**
- The `MappingExecutor` methods are simple, one-line delegations.
- The facade pattern is strictly enforced.
- All logic resides within the service layer (the coordinators), not the facade.
- The application's behavior remains unchanged, and all tests pass.

**Error Recovery Instructions:**
- If moving logic to a coordinator requires that coordinator to have a new dependency, update the `MappingExecutorBuilder` to inject that dependency correctly.
- If a method seems to not fit in any existing coordinator, consider if a new coordinator service is needed. Document this for future work.

**Environment Requirements:**
- Access to the `biomapper` codebase.
- `poetry` environment fully installed and operational.

**Task Decomposition:**
1.  Review the implementation of `execute_mapping` in `MappingExecutor`. Move any logic into `MappingCoordinatorService.execute_mapping`. Ensure the executor method is a simple `return self.mapping_coordinator.execute_mapping(...)`.
2.  Review the implementation of `execute_strategy` in `MappingExecutor`. Move any logic into `StrategyCoordinatorService.execute_strategy`. Ensure the executor method is a simple `return self.strategy_coordinator.execute_strategy(...)`.
3.  Review the implementation of `_execute_path` in `MappingExecutor`. Move any logic into `MappingCoordinatorService.execute_path`. Ensure the executor method is a simple `return self.mapping_coordinator.execute_path(...)`.
4.  Update the unit tests for `MappingExecutor` to use mocks for the coordinators. The tests should now verify that the correct coordinator method is called with the correct parameters, rather than testing the logic itself.
5.  Run all tests.

**Validation Checkpoints:**
- After refactoring each method, run the relevant tests.
- A code review should confirm that the `MappingExecutor` methods are one-line delegations.

**Source Prompt Reference:**
- `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-204511-prompt-5-solidify-coordinator-delegation.md`

**Context from Previous Attempts:**
- This is the first attempt at this specific refactoring.
