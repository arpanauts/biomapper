# Task: Decompose Initial Direct Mapping from `execute_mapping`

## 1. Task Objective
Extract the initial 'direct mapping' logic from the beginning of the `MappingExecutor.execute_mapping` method into a new, dedicated service class. This is the first step in breaking down the monolithic `execute_mapping` method.

## 2. Context and Background
The `execute_mapping` method in `biomapper/core/mapping_executor.py` is over 600 lines long. The first major block of logic in this method attempts to perform a direct mapping between the source and target using a primary shared ontology. This self-contained logic is an ideal candidate for extraction.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- A new service class (e.g., `DirectMappingService`) is created in a new file under `biomapper/core/services/`.
- The new service has a primary public method (e.g., `execute_direct_mapping`) that encapsulates the logic for finding and executing a direct mapping path.
- The `MappingExecutor.execute_mapping` method is updated to call this new service.
- The logic removed from `execute_mapping` should make it noticeably smaller and easier to read.
- All related integration tests must pass, demonstrating that the refactored logic behaves identically to the original.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`
- **Expected outputs:** A new service file (e.g., `biomapper/core/services/direct_mapping_service.py`) and a modified `mapping_executor.py`.
- **Code standards:** Follow existing project conventions for creating new service classes. Use asynchronous methods and dependency injection.

## 6. Error Recovery Instructions
- Pay close attention to the data contract between the `MappingExecutor` and the new service. Ensure all necessary data (identifiers, session, endpoints) is passed correctly and the return values (mapped/unmapped results) are handled properly.
- If tests fail, verify that the extracted logic in the new service is identical to the original logic and that it's being called correctly from the executor.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-direct-mapping.md`
- **Content:**
    - **Completed Subtasks:** Note the creation of the new service and the modification of `execute_mapping`.
    - **Issues Encountered:** Describe any difficulties in isolating the direct mapping logic.
    - **Next Action Recommendation:** Confirm readiness for the next `execute_mapping` decomposition task.
    - **Confidence Assessment:** High. This is a well-contained piece of logic.
