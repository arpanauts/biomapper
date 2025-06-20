# Task: Refactor `_execute_mapping_step` into a Dedicated Service

## 1. Task Objective
Extract the logic from the `MappingExecutor._execute_mapping_step` method into a new `MappingStepExecutionService`. This will isolate the responsibility of executing a single step of a mapping path, including client interaction, caching, and error handling.

## 2. Context and Background
The `_execute_mapping_step` method in `MappingExecutor` is responsible for the fine-grained details of running one step in a `MappingPath`. This includes loading the correct client, calling its `map` method, handling reverse execution, and interacting with the cache. Separating this into its own service improves cohesion and simplifies the executor.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- A new `MappingStepExecutionService` class is created in a new file under `biomapper/core/services/`.
- The logic from `_execute_mapping_step` is moved into a method within this new service (e.g., `execute_step`).
- The `MappingExecutor`'s internal path execution logic is updated to use this new service, simplifying its own code.
- The new service should be injectable into other services that might need to execute a single step (like the `PathExecutionService`).
- All tests related to executing mapping paths must pass.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`
- **Expected outputs:** A new service file (e.g., `biomapper/core/services/mapping_step_execution_service.py`) and a modified `mapping_executor.py`.
- **Code standards:** The new service should be injected with dependencies it needs, such as the `ClientManager` and `CacheManager`.

## 6. Error Recovery Instructions
- Ensure that all context required by the step execution logic (e.g., `is_reverse` flag, input values, the `MappingPathStep` object) is passed correctly to the new service.
- Failures in mapping path tests will likely be due to an incomplete or incorrect transfer of logic or state to the new service.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-step-execution.md`
- **Content:**
    - **Completed Subtasks:** Report on the creation of the new service and the refactoring of the executor.
    - **Issues Encountered:** Document any challenges in isolating the step execution logic.
    - **Next Action Recommendation:** Confirm that this refactoring simplifies the main path execution loop.
    - **Confidence Assessment:** High. This is a well-defined piece of logic to extract.
