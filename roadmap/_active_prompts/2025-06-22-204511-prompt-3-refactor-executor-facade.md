# Task: Refactor MappingExecutor into a Pure Facade

**Task Objective:**
Refactor the `MappingExecutor` class to be a pure facade. Its `__init__` method should be drastically simplified to only accept pre-constructed, high-level components (coordinators and managers) from the `MappingExecutorBuilder`. All internal component creation logic must be removed.

**Prerequisites:**
- The `MappingExecutorBuilder` has been created and can assemble all necessary components (as per `prompt-2-create-builder.md`).

**Input Context:**
- `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`: The primary file to be modified.
- `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_executor_builder.py`: The builder that will now be responsible for constructing the executor.

**Expected Outputs:**
1.  A modified `mapping_executor.py` where `MappingExecutor.__init__` is simplified.
    - The new `__init__` will accept `strategy_coordinator`, `mapping_coordinator`, `lifecycle_manager`, and any other directly required services as arguments.
    - It will *not* instantiate any classes itself. It will only assign the provided arguments to `self`.
2.  The `MappingExecutor.create` class method will be updated to use the `MappingExecutorBuilder` to construct and return the executor instance.

**Success Criteria:**
- `MappingExecutor.__init__` contains no logic other than assigning arguments to instance attributes.
- `MappingExecutor` is no longer responsible for creating its own dependencies.
- The `MappingExecutor.create` method successfully uses the `MappingExecutorBuilder`.
- All existing tests for `MappingExecutor` are refactored to use the builder for setup and they all pass.

**Error Recovery Instructions:**
- If a method in `MappingExecutor` requires a low-level component that is no longer available, refactor it to call a method on one of its high-level coordinators instead.
- If tests are difficult to refactor, it may indicate that the `MappingExecutor` is still doing too much work. Re-evaluate its methods for further delegation.

**Environment Requirements:**
- Access to the `biomapper` codebase.
- `poetry` environment fully installed and operational.

**Task Decomposition:**
1.  Modify the signature of `MappingExecutor.__init__` to accept the high-level coordinator and manager services.
2.  Remove all component instantiation logic from `__init__`.
3.  Update the `MappingExecutor.create` class method to instantiate `MappingExecutorBuilder` and call its `build()` method.
4.  Go through every method in `MappingExecutor` and ensure it can still access its dependencies through the new high-level components.
5.  Refactor the unit tests for `MappingExecutor`. The setup for these tests will now involve using the `MappingExecutorBuilder` to create the object under test.
6.  Run the refactored tests to ensure they all pass.

**Validation Checkpoints:**
- After refactoring `__init__`, confirm that no services are being created within the method.
- After updating `create`, test it manually or via a unit test to ensure it returns a valid executor.
- After refactoring the tests, run the entire test suite.

**Source Prompt Reference:**
- `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-204511-prompt-3-refactor-executor-facade.md`

**Context from Previous Attempts:**
- This is the first attempt at this specific refactoring.
