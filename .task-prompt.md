# Task: Create InitializationService to Encapsulate Component Setup

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171741-prompt-create-initialization-service.md`

## 1. Task Objective
Create a new, self-contained `InitializationService` in a new file at `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`. This service will be responsible for all the logic currently found in `MappingExecutor.__init__`, effectively separating the complex setup of services and components from the `MappingExecutor` facade itself.

## 2. Prerequisites
- [x] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- [x] Required permissions: Write access to `/home/ubuntu/biomapper/biomapper/core/engine_components/`

## 3. Task Decomposition
1.  **Create the new file:** Create `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`.
2.  **Define `InitializationService` class:** Inside the new file, create a class named `InitializationService`.
3.  **Create an `initialize_components` method:** This method will take the same configuration parameters as the current `MappingExecutor.__init__` (e.g., `metamapper_db_url`, `mapping_cache_db_url`, `echo_sql`, etc.).
4.  **Move initialization logic:** Transfer the entire logic from `MappingExecutor.__init__` into the `initialize_components` method. This includes:
    *   Distinguishing between legacy (config-based) and component-based initialization.
    *   Instantiating all services (`SessionManager`, `ClientManager`, `StrategyOrchestrator`, etc.).
    *   The existing `MappingExecutorInitializer` class can be refactored or its logic directly absorbed into this new service.
5.  **Return a components dictionary:** The `initialize_components` method should return a dictionary containing all the initialized service instances (e.g., `{'session_manager': sm_instance, 'client_manager': cm_instance, ...}`).
6.  **Add necessary imports:** Copy all necessary imports from `mapping_executor.py` to the new file.

## 4. Implementation Requirements
- **Input file:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- **Expected output:** A new file `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py` containing the `InitializationService` class.
- **Code standards:** Follow existing project conventions for styling, typing, and documentation.

## 5. Error Recovery Instructions
- **Import Errors:** If you encounter import errors, ensure all required modules from `mapping_executor.py` are correctly imported in the new file. Add `__init__.py` files to directories if they are missing.
- **Logic/Implementation Errors:** The goal is to lift and shift the logic. Do not refactor the logic itself in this step, only move it. This will minimize the risk of new bugs.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The file `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py` exists.
- [ ] The file contains a class `InitializationService` with an `initialize_components` method.
- [ ] The `initialize_components` method contains the logic from `MappingExecutor.__init__` and returns a dictionary of initialized components.
- [ ] The new file is free of syntax errors.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-create-initialization-service.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
