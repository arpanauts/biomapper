# Task: Refactor InitializationService

**Task Objective:**
Refactor the `biomapper.core.engine_components.initialization_service.InitializationService` to be the single source of truth for creating *all* individual, low-level service components from a configuration dictionary. The goal is to centralize component instantiation logic, making the system easier to configure and test.

**Prerequisites:**
- The file `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py` must exist.
- The file `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_executor_initializer.py` must exist.

**Input Context:**
- `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`: The primary file to be modified.
- `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_executor_initializer.py`: This class will likely be deprecated or heavily simplified, with its logic moving into `InitializationService`.
- `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`: Review its `__init__` method to understand all components that need to be created.

**Expected Outputs:**
1.  A modified `initialization_service.py` where the `InitializationService` class has a method (e.g., `create_components_from_config(config: dict)`) that returns a dictionary of all initialized low-level services (e.g., `session_manager`, `client_manager`, `cache_manager`, `path_finder`, etc.).
2.  The `MappingExecutorInitializer` class in `mapping_executor_initializer.py` should be marked as deprecated and its logic fully migrated to `InitializationService`.

**Success Criteria:**
- `InitializationService` can successfully instantiate all required services from a single configuration dictionary without errors.
- The `MappingExecutorInitializer` is no longer responsible for component creation.
- All existing unit tests that rely on the old initializer must be updated to use the new `InitializationService` and must pass.

**Error Recovery Instructions:**
- If circular dependencies are discovered during refactoring, document them and refactor the services to use dependency injection rather than direct instantiation.
- If tests fail, revert the changes to the specific component causing the failure and add comments explaining the issue for later review.

**Environment Requirements:**
- Access to the `biomapper` codebase.
- `poetry` environment fully installed and operational.

**Task Decomposition:**
1.  Analyze `MappingExecutor.__init__` and `MappingExecutorInitializer` to list every component that is created.
2.  Modify `InitializationService` to include creation methods for each of these components.
3.  Create a primary method in `InitializationService` that takes a config dict and calls the individual creation methods, returning a complete dictionary of components.
4.  Refactor `MappingExecutorInitializer` to delegate to `InitializationService`, or remove it entirely and mark it as deprecated.
5.  Update all call sites (especially in tests) that used `MappingExecutorInitializer` to now use `InitializationService`.
6.  Run the full test suite using `poetry run pytest` to ensure no regressions.

**Validation Checkpoints:**
- After modifying `InitializationService`, write a temporary test to ensure it can create all components without error.
- After updating call sites, run the test suite to validate the changes.

**Source Prompt Reference:**
- `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-204511-prompt-1-refactor-initializer.md`

**Context from Previous Attempts:**
- This is the first attempt at this specific refactoring task.
