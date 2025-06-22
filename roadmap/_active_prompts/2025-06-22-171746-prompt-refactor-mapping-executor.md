# Task: Refactor MappingExecutor to be a Lean Facade

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171746-prompt-refactor-mapping-executor.md`

## 1. Task Objective
Refactor the `MappingExecutor` in `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` to delegate all its functionality to the newly created services. The goal is to make `MappingExecutor` a pure, simple facade with minimal internal logic.

## 2. Prerequisites
- [x] All previous service creation tasks must be complete.
- [x] The new service files must exist: `initialization_service.py`, `strategy_coordinator_service.py`, `mapping_coordinator_service.py`, `lifecycle_manager.py`.
- [x] The `metadata_query_service.py` must be enhanced.

## 3. Task Decomposition
1.  **Update `MappingExecutor.__init__`:**
    *   Remove all the logic from `__init__`.
    *   Call the new `InitializationService.initialize_components` method.
    *   Store the returned dictionary of components in a single attribute, e.g., `self.services`.
    *   Instantiate the new coordinator services (`StrategyCoordinatorService`, `MappingCoordinatorService`, `LifecycleManager`) and pass them their dependencies from the `self.services` dictionary.
2.  **Refactor Execution Methods:**
    *   Rewrite `execute_strategy`, `execute_yaml_strategy`, etc., to be one-line calls that delegate to the corresponding method in `StrategyCoordinatorService`.
    *   Rewrite `execute_mapping` and `_execute_path` to delegate to `MappingCoordinatorService`.
3.  **Refactor Lifecycle Methods:**
    *   Rewrite `async_dispose`, checkpointing methods, and progress reporting to delegate to `LifecycleManager`.
4.  **Refactor Metadata Methods:**
    *   Rewrite `_get_endpoint_by_name` and `get_strategy` to delegate to the enhanced `MetadataQueryService`.
5.  **Clean Up:**
    *   Remove all the now-unused private methods and properties from `MappingExecutor`.
    *   Remove unused imports.

## 4. Implementation Requirements
- **Input file:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- **Expected output:** A much shorter and simpler `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` file.
- **Code standards:** The final class should be a clean, easy-to-read facade.

## 5. Error Recovery Instructions
- **Testing:** This is a major refactoring. After this step, it is critical to run the project's test suite to ensure no functionality was broken.
- **Dependency Injection:** Ensure all services are correctly initialized and passed to the services that depend on them.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] `MappingExecutor.__init__` is significantly shorter and uses `InitializationService`.
- [ ] All major methods in `MappingExecutor` are simple one-line delegations to the appropriate service.
- [ ] The `mapping_executor.py` file is less than half its original length.
- [ ] All project tests pass after the refactoring.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-mapping-executor.md`
