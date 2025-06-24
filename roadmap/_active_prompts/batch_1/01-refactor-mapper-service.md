# Task: Refactor MapperService for Live Strategy Execution

**Source Prompt Reference:** Orchestrator-generated task to replace mock API components.

## 1. Task Objective

The current `MapperService` is a mock placeholder. The objective is to refactor it into a production-ready service that loads and executes mapping strategies defined in YAML configuration files. This is the central component for the `biomapper-api`.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Modify:** `/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py`
- **Dependencies:** This service will now depend on the `MappingExecutor` from the core `biomapper` library and the `settings` from `app.core.config`.

## 3. Task Decomposition

1.  **Remove Mock Components:** Delete the `MockMetaboliteNameMapper` class and all related mock logic from `mapper_service.py`.
2.  **Implement Strategy Loading:**
    *   In the `MapperService.__init__` method, implement logic to scan the directory specified by `settings.STRATEGIES_DIR`.
    *   Load each `.yaml` file, parse it, and store it in an in-memory dictionary, keyed by the strategy `name`.
    *   Log the names of all successfully loaded strategies at startup.
3.  **Implement `execute_strategy` Method:**
    *   Create a new public method: `async def execute_strategy(self, strategy_name: str, context: dict) -> dict:`.
    *   This method should retrieve the named strategy from the in-memory registry.
    *   Instantiate the `MappingExecutor` from `biomapper.core.executor.MappingExecutor`.
    *   Execute the strategy using the executor's `execute` method, passing the strategy's steps and the initial context.
    *   Return the final context dictionary containing the results.
4.  **Refactor Existing Methods:**
    *   Remove the old `create_job`, `process_mapping_job`, and other mock-related methods. The service's responsibility is now direct strategy execution.

## 4. Implementation Requirements

- The service must raise a `ValueError` if a requested `strategy_name` is not found in the registry.
- Use asynchronous file I/O for loading strategies if possible, but synchronous is acceptable for the initial implementation.
- Ensure the `MappingExecutor` is instantiated with the application's database session if required by its constructor.
- All references to mock data or mock classes must be removed.

## 5. Error Recovery Instructions

- If a YAML file is malformed and cannot be parsed, log the error with the file's name and continue to load other valid files. Do not let one bad file prevent the service from starting.

## 6. Success Criteria and Validation

- The `mapper_service.py` file is updated and no longer contains any mock logic.
- The service successfully loads YAML files from `/home/ubuntu/biomapper/configs/` at startup.
- The `execute_strategy` method correctly finds a strategy and initiates the `MappingExecutor`.
- The code must be fully type-hinted.

## 7. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-01-refactor-mapper-service.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** A link to the modified `mapper_service.py`.
-   **Summary of Changes:** A brief description of how the mock service was replaced with the live implementation.
