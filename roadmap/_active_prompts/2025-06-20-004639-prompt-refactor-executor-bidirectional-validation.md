# Task: Decompose Bidirectional Validation from `execute_mapping`

## 1. Task Objective
Extract the logic for bidirectional validation from the `MappingExecutor.execute_mapping` method into a new, self-contained service. This service will handle the process of re-running mappings in the reverse direction to validate the initial results.

## 2. Context and Background
Within the large `execute_mapping` method, there is a conditional block that, if `bidirectional_validation` is enabled, triggers a recursive or secondary mapping process in the reverse direction. This is a distinct and complex feature that should reside in its own specialized service.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- A new service class (e.g., `BidirectionalValidationService`) is created in a new file under `biomapper/core/services/`.
- The service encapsulates the logic for performing the reverse mapping and comparing the results against the forward mapping.
- The `MappingExecutor.execute_mapping` method is simplified by replacing the inline validation logic with a call to this new service.
- The new service may need to call back into the `MappingExecutor` or its sub-services to run the reverse mapping, so the dependency structure should be carefully designed.
- All tests related to bidirectional validation must pass.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`
- **Expected outputs:** A new service file (e.g., `biomapper/core/services/bidirectional_validation_service.py`) and a modified `mapping_executor.py`.
- **Code standards:** Pay attention to dependency injection to avoid circular dependencies if the new service needs to invoke mapping functionality.

## 6. Error Recovery Instructions
- The main risk is creating a circular dependency. If the `BidirectionalValidationService` needs to run a mapping, it should likely call a public method on the `MappingExecutor` rather than trying to replicate the logic internally. Ensure this interaction is clean.
- Test failures will likely indicate that the validation results are different. This could be due to incorrect state being passed to the validation service.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-bidirectional-validation.md`
- **Content:**
    - **Completed Subtasks:** Detail the creation of the validation service and the changes in `MappingExecutor`.
    - **Issues Encountered:** Describe any challenges with circular dependencies or state management.
    - **Next Action Recommendation:** Confirm the successful modularization of this feature.
    - **Confidence Assessment:** Medium. The potential for circular dependencies requires careful design.
