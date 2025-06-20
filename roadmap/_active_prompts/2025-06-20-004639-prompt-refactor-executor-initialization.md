# Task: Refactor MappingExecutor Initialization Logic

## 1. Task Objective
To simplify the `MappingExecutor` constructor (`__init__`) and asynchronous factory (`create`) by delegating the responsibility of component initialization and dependency injection to the existing `MappingExecutorInitializer` service. This will reduce the parameter count of the executor's constructor and centralize the setup logic, improving maintainability.

## 2. Context and Background
`biomapper/core/mapping_executor.py` is overly complex, with its `__init__` method taking a large number of parameters for configuration and component setup. An initializer class, `MappingExecutorInitializer`, already exists in `biomapper/core/engine_components/mapping_executor_initializer.py` but is not being fully utilized. This task is to complete the delegation of initialization logic to this service.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Target Service:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/mapping_executor_initializer.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- The `MappingExecutor.__init__` method's parameter list is significantly reduced. It should primarily accept pre-initialized service components, not configuration values.
- The `MappingExecutorInitializer` is responsible for creating instances of `ClientManager`, `ConfigLoader`, `StrategyHandler`, `PathFinder`, `CheckpointManager`, etc.
- The `MappingExecutor.create` static method uses `MappingExecutorInitializer` to build the executor instance.
- All existing tests related to `MappingExecutor` instantiation must pass after the refactoring.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`, `mapping_executor_initializer.py`
- **Expected outputs:** Modified versions of the input files.
- **Code standards:** Adhere to existing project formatting, use type hints, and ensure all logic is asynchronous where appropriate.

## 6. Error Recovery Instructions
- If you encounter import errors, ensure all new service dependencies are correctly imported.
- If tests fail, it is likely due to incorrect dependency injection. Trace the creation of the failed component back to the `MappingExecutorInitializer` and ensure it's being constructed with the correct parameters.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-initialization.md`
- **Content:**
    - **Completed Subtasks:** Checklist of modifications made to `MappingExecutor` and `MappingExecutorInitializer`.
    - **Issues Encountered:** Document any challenges with dependency injection or test failures.
    - **Next Action Recommendation:** Suggest any further cleanup related to initialization.
    - **Confidence Assessment:** High. This is a structural refactoring with clear boundaries.
