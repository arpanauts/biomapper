# Task: Create MappingCoordinatorService

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171743-prompt-create-mapping-coordinator-service.md`

## 1. Task Objective
Create a new `MappingCoordinatorService` in `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_coordinator_service.py`. This service will consolidate the high-level mapping orchestration logic from `MappingExecutor`, specifically the `execute_mapping` and `_execute_path` methods.

## 2. Prerequisites
- [x] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
- [x] Required permissions: Write access to `/home/ubuntu/biomapper/biomapper/core/engine_components/`.

## 3. Task Decomposition
1.  **Create the new file:** Create `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_coordinator_service.py`.
2.  **Define `MappingCoordinatorService` class:** This class will be initialized with dependencies like `IterativeExecutionService` and `MappingPathExecutionService`.
3.  **Move `execute_mapping`:** Move the `MappingExecutor.execute_mapping` method and its logic to the new service.
4.  **Move `_execute_path`:** Move the `MappingExecutor._execute_path` method and its logic to the new service. Rename it to `execute_path` to make it a public method of the service.
5.  **Add necessary imports:** Copy all required imports to the new file.

## 4. Implementation Requirements
- **Input file:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- **Expected output:** A new file `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_coordinator_service.py`.
- **Code standards:** Follow existing project conventions.

## 5. Error Recovery Instructions
- **Dependency Errors:** Ensure the service's `__init__` correctly accepts its dependencies.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The file `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_coordinator_service.py` exists.
- [ ] The `MappingCoordinatorService` class contains the `execute_mapping` and `execute_path` methods.
- [ ] The logic is identical to the original methods in `MappingExecutor`.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-create-mapping-coordinator-service.md`
