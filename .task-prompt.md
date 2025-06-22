# Task: Create StrategyCoordinatorService

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171742-prompt-create-strategy-coordinator-service.md`

## 1. Task Objective
Create a new `StrategyCoordinatorService` in `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_coordinator_service.py`. This service will consolidate all strategy execution logic from `MappingExecutor`, providing a single, clean interface for running database-backed, YAML-defined, and robust strategies.

## 2. Prerequisites
- [x] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` and the various execution services it calls.
- [x] Required permissions: Write access to `/home/ubuntu/biomapper/biomapper/core/engine_components/`.

## 3. Task Decomposition
1.  **Create the new file:** Create `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_coordinator_service.py`.
2.  **Define `StrategyCoordinatorService` class:** Create the class. It should be initialized with the necessary dependencies it needs to orchestrate strategy execution (e.g., `DbStrategyExecutionService`, `YamlStrategyExecutionService`, `RobustExecutionCoordinator`).
3.  **Move `execute_strategy`:** Move the logic from `MappingExecutor.execute_strategy` into a method in the new service.
4.  **Move `execute_yaml_strategy`:** Move the logic from `MappingExecutor.execute_yaml_strategy` into a method in the new service.
5.  **Move `execute_robust_yaml_strategy`:** Move the logic from `MappingExecutor.execute_robust_yaml_strategy` into a method in the new service.
6.  **Add necessary imports:** Ensure all required types and services are imported.

## 4. Implementation Requirements
- **Input file:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- **Expected output:** A new file `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_coordinator_service.py`.
- **Code standards:** Follow existing project conventions.

## 5. Error Recovery Instructions
- **Dependency Errors:** The new service will depend on other services. Ensure its `__init__` method accepts these services as arguments.
- **Circular Dependencies:** Be mindful of potential circular dependencies. This service should call other services, not the other way around.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The file `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_coordinator_service.py` exists.
- [ ] The `StrategyCoordinatorService` class contains methods for executing all three types of strategies.
- [ ] The logic within these methods is identical to the logic in the original `MappingExecutor` methods.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-create-strategy-coordinator-service.md`
