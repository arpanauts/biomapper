# Task: Refactor Execution Lifecycle Management

## 1. Task Objective
To decouple the `MappingExecutor` from the direct management of execution lifecycle concerns like checkpointing, progress reporting, and metrics. This will be achieved by creating a new, high-level service that coordinates these aspects, further simplifying the executor.

## 2. Context and Background
The `MappingExecutor` currently has several delegate methods for saving/loading checkpoints (`save_checkpoint`, `load_checkpoint`) and reporting progress (`_report_progress`). While these delegate to other managers, they still clutter the executor's interface. Consolidating these into a single `ExecutionLifecycleService` would provide a cleaner separation of concerns.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Component Managers:** `CheckpointManager`, `ProgressReporter`.
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- A new `ExecutionLifecycleService` is created in `biomapper/core/services/`.
- This service is initialized with the `CheckpointManager`, `ProgressReporter`, and potentially a new `MetricsManager`.
- The delegate methods for checkpointing and progress reporting are removed from `MappingExecutor`.
- The `MappingExecutor` calls the new `ExecutionLifecycleService` at appropriate points (e.g., `lifecycle_service.report_progress(...)`).
- The `MappingExecutor`'s public API is cleaner and more focused on mapping orchestration.
- All tests related to checkpointing and progress reporting must pass.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`, and the paths to the component manager classes.
- **Expected outputs:** A new service file (e.g., `biomapper/core/services/execution_lifecycle_service.py`) and a modified `mapping_executor.py`.
- **Code standards:** The new service should be injected into the `MappingExecutor` during initialization.

## 6. Error Recovery Instructions
- If tests fail, it's likely because a call to a lifecycle method (like reporting progress) was missed during the refactoring. Review the original `execute_mapping` and `execute_strategy` methods to ensure all original calls are now being made via the new service.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-lifecycle-management.md`
- **Content:**
    - **Completed Subtasks:** Describe the creation of the new service and the removal of delegate methods from the executor.
    - **Issues Encountered:** Note any difficulties in deciding the boundaries of the new service.
    - **Next Action Recommendation:** Confirm that the executor is now sufficiently decoupled from lifecycle concerns.
    - **Confidence Assessment:** High. This refactoring helps to enforce better separation of concerns.
