# Task: Create MappingExecutorBuilder

**Task Objective:**
Create a new `MappingExecutorBuilder` class in a new file. This builder will be responsible for constructing a fully-configured `MappingExecutor` instance. It will use the `InitializationService` to create low-level components and will then be responsible for instantiating and wiring together the high-level coordinator and manager services.

**Prerequisites:**
- The `InitializationService` has been refactored to be the single source for creating low-level components (as per `prompt-1-refactor-initializer.md`).

**Input Context:**
- `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`: To be used by the builder.
- `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`: The class that the builder will construct.

**Expected Outputs:**
1.  A new file: `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_executor_builder.py`.
2.  This file will contain the `MappingExecutorBuilder` class.
3.  The builder will have a `build()` method that:
    a. Takes configuration parameters in its `__init__`.
    b. Uses `InitializationService` to get base components.
    c. Instantiates `StrategyCoordinatorService`, `MappingCoordinatorService`, and `LifecycleManager`, providing them with their dependencies from the component dictionary.
    d. Returns a fully assembled `MappingExecutor` instance.

**Success Criteria:**
- The `MappingExecutorBuilder` can successfully build a `MappingExecutor` instance that is fully functional.
- The builder correctly wires all dependencies between services and coordinators.
- The creation of the `MappingExecutor` is now entirely handled by the builder, separating construction from operation.

**Error Recovery Instructions:**
- If dependency injection becomes complex, clearly document the dependency graph in the code comments.
- If the builder cannot resolve a dependency, ensure the `InitializationService` is providing it correctly.

**Environment Requirements:**
- Access to the `biomapper` codebase.
- `poetry` environment fully installed and operational.

**Task Decomposition:**
1.  Create the new file `mapping_executor_builder.py`.
2.  Define the `MappingExecutorBuilder` class with an `__init__` that accepts configuration.
3.  Implement the `build` method.
4.  Inside `build`, first call `InitializationService` to get the dictionary of base components.
5.  Instantiate the high-level coordinators (`StrategyCoordinatorService`, `MappingCoordinatorService`) and `LifecycleManager`, passing the required components to their constructors.
6.  Instantiate the `MappingExecutor` (note: its `__init__` will be simplified in a parallel task), passing the fully-wired coordinators and managers.
7.  Return the `MappingExecutor` instance.
8.  Create a new unit test file `tests/core/engine_components/test_mapping_executor_builder.py` to verify the builder works as expected.

**Validation Checkpoints:**
- After implementing the `build` method, write a unit test to confirm it returns a `MappingExecutor` instance without errors.
- The unit test should assert that the executor's coordinator attributes are correctly assigned.

**Source Prompt Reference:**
- `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-204511-prompt-2-create-builder.md`

**Context from Previous Attempts:**
- This is the first attempt to create the builder class.
