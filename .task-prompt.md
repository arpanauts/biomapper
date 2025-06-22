# Task: Create LifecycleManager

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171744-prompt-create-lifecycle-manager.md`

## 1. Task Objective
Create a new `LifecycleManager` service in `/home/ubuntu/biomapper/biomapper/core/engine_components/lifecycle_manager.py`. This service will consolidate all lifecycle-related operations from `MappingExecutor`, including resource disposal, checkpoint management, and progress reporting.

## 2. Prerequisites
- [x] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
- [x] Required permissions: Write access to `/home/ubuntu/biomapper/biomapper/core/engine_components/`.

## 3. Task Decomposition
1.  **Create the new file:** Create `/home/ubuntu/biomapper/biomapper/core/engine_components/lifecycle_manager.py`.
2.  **Define `LifecycleManager` class:** This class will be initialized with dependencies like `SessionManager` and the existing `ExecutionLifecycleService`.
3.  **Move `async_dispose`:** Move the logic from `MappingExecutor.async_dispose` to the new service.
4.  **Move Checkpointing Logic:** Move the `checkpoint_dir` property (getter and setter), `save_checkpoint`, and `load_checkpoint` methods to the new service.
5.  **Move Progress Reporting:** Move the `_report_progress` method to the new service and make it public (`report_progress`).
6.  **Add necessary imports.**

## 4. Implementation Requirements
- **Input file:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- **Expected output:** A new file `/home/ubuntu/biomapper/biomapper/core/engine_components/lifecycle_manager.py`.
- **Code standards:** Follow existing project conventions.

## 5. Error Recovery Instructions
- **Refactoring:** The existing `ExecutionLifecycleService` already handles some of this. You can choose to either enhance the existing service or have the new `LifecycleManager` delegate to it. The goal is to remove this logic from the `MappingExecutor` facade.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The file `/home/ubuntu/biomapper/biomapper/core/engine_components/lifecycle_manager.py` exists.
- [ ] The `LifecycleManager` class contains all the specified lifecycle-related methods.
- [ ] The logic is identical to the original methods in `MappingExecutor`.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-create-lifecycle-manager.md`
