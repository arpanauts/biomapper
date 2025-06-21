# Task: Decompose Iterative Secondary Mapping from `execute_mapping`

## 1. Task Objective
Extract the complex iterative mapping loop from the `MappingExecutor.execute_mapping` method into a new, specialized service class. This service will manage the state and execution of secondary path finding and mapping for identifiers that were not mapped in the initial direct pass.

## 2. Context and Background
The core of the monolithic `execute_mapping` method is a large `while` loop that iteratively finds and executes secondary mapping paths for unmapped identifiers. This stateful and complex process is a prime candidate for extraction into its own service to significantly simplify the `MappingExecutor`.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- A new service class (e.g., `IterativeMappingService`) is created in a new file under `biomapper/core/services/`.
- This service contains the logic of the iterative mapping loop, including finding alternative paths, executing them, and managing the set of unmapped identifiers.
- The `MappingExecutor.execute_mapping` method is updated to delegate the iterative mapping phase to this new service.
- The `execute_mapping` method should be dramatically shorter and simpler after this refactoring.
- All relevant integration tests must pass, ensuring the behavior of the iterative mapping process is preserved.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`
- **Expected outputs:** A new service file (e.g., `biomapper/core/services/iterative_mapping_service.py`) and a modified `mapping_executor.py`.
- **Code standards:** The new service should be designed to be stateful if necessary to manage the iterative process. Use async methods and pass dependencies via the constructor.

## 6. Error Recovery Instructions
- The main challenge will be managing the state (e.g., `unmapped_from_source`, `mapped_results`, `tested_paths`) that was previously local to the `execute_mapping` method. Ensure this state is correctly passed to, managed within, and returned from the new service.
- Test failures will likely point to incorrect state management. Debug by comparing the state at each iteration between the old and new implementations.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-iterative-mapping.md`
- **Content:**
    - **Completed Subtasks:** Detail the creation of the `IterativeMappingService` and the removal of the loop from `execute_mapping`.
    - **Issues Encountered:** Describe challenges related to state management during the extraction.
    - **Next Action Recommendation:** State readiness for subsequent `execute_mapping` refactoring tasks.
    - **Confidence Assessment:** Medium. The logic is complex and stateful, requiring careful extraction.
