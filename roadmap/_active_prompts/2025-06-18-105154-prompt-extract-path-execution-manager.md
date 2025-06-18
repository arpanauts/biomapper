# Task: Refactor MappingExecutor - Extract PathExecutionManager

**Project:** Biomapper
**Target Worktree Root:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper-feature-path-manager/`
**Target Branch:** `feature/extract-path-manager`
**Parent Supervisor:** Cascade (Main Project Instance)

## 1. Objective
Refactor the `biomapper.core.mapping_executor.MappingExecutor` class by extracting the logic responsible for the detailed execution of a single mapping path into a new, dedicated component: `biomapper.core.engine_components.PathExecutionManager`.

This will improve modularity, testability, and maintainability of the `MappingExecutor`.

## 2. Background & Context
The `MappingExecutor._execute_path` method is currently very large and handles complex logic including:
- Batching of input identifiers.
- Concurrency management using `asyncio.Semaphore`.
- Iterating through `MappingPathStep` objects.
- Invoking appropriate client methods for each step (`_execute_step_with_client`).
- Handling results, errors, and filtering for each identifier within a batch.
- Aggregating results from all batches.
- Interacting with the `CacheManager` to store results.

Extracting this into a `PathExecutionManager` will isolate this core execution logic.

## 3. Scope of Work

**3.1. Create `PathExecutionManager` Class:**
   - Create a new file: `biomapper/core/engine_components/path_execution_manager.py`.
   - Define a class `PathExecutionManager`.
   - The constructor `__init__` should accept necessary dependencies, which will likely include:
     - `metamapper_session_factory` (for fetching path/client details if not passed directly)
     - `cache_manager` (instance of `CacheManager`)
     - `logger`
     - `semaphore` (for concurrency control, or it could be managed internally)
     - `max_retries`, `retry_delay` (for client calls)
     - `batch_size`

**3.2. Migrate Core Path Execution Logic:**
   - The primary public method of `PathExecutionManager` should be something like `async execute_path(...)`.
   - This method will take parameters similar to the current `MappingExecutor._execute_path`:
     - `path: Union[MappingPath, ReversiblePath]`
     - `input_identifiers: List[str]`
     - `source_ontology: str`
     - `target_ontology: str`
     - `mapping_session_id: Optional[int]`
     - `execution_context: Dict[str, Any]` (for logging and context)
     - `resource_clients: Dict[str, Any]` (pre-initialized clients)
   - Move the core logic from `MappingExecutor._execute_path` into this new method.
   - Identify and move relevant helper methods currently in `MappingExecutor` that are *exclusively* used by `_execute_path`. Examples might include:
     - `_execute_step_with_client`
     - `_process_batch_for_path` (or its equivalent logic)
     - `_handle_client_execution` (if primarily used by path execution)
     - Any other private methods solely supporting `_execute_path`.
   - Adapt these methods to work within the `PathExecutionManager` class context.

**3.3. Update `MappingExecutor`:**
   - In `biomapper.core.mapping_executor.MappingExecutor`:
     - Instantiate `PathExecutionManager` in the `__init__` method, passing necessary dependencies.
     - Modify the existing `_execute_path` method to become a thin wrapper that primarily delegates its call to `self.path_execution_manager.execute_path(...)`.
     - Remove the helper methods that were moved to `PathExecutionManager` from `MappingExecutor`.

**3.4. Handle Dependencies and Imports:**
   - Ensure all necessary imports are added to `path_execution_manager.py`.
   - Update imports in `mapping_executor.py` as needed.
   - Add `PathExecutionManager` to `biomapper/core/engine_components/__init__.py`.

## 4. Key Considerations

- **Interface Definition:** Carefully define the interface between `MappingExecutor` and `PathExecutionManager`. The goal is for `MappingExecutor` to pass all necessary data and configurations to `PathExecutionManager` so it can operate mostly independently for the duration of a path execution.
- **Client Management:** `MappingExecutor` currently initializes clients (`_get_resource_client`). Decide if `PathExecutionManager` should receive pre-initialized clients or if it should be responsible for fetching/initializing them (the former is likely cleaner for this refactor).
- **Error Handling:** Ensure error handling and logging remain robust and are correctly attributed.
- **Cache Interaction:** The `PathExecutionManager` will need to interact with the `CacheManager` to store results. Ensure this is done correctly using the passed `cache_manager` instance.
- **Testing (Future):** While full unit tests are for a subsequent step, keep testability in mind. The `PathExecutionManager` should be easier to unit test in isolation.

## 5. Implementation Requirements
- **Input files/data:** Primarily `biomapper/core/mapping_executor.py`.
- **Expected outputs:** 
    - New file: `biomapper/core/engine_components/path_execution_manager.py`
    - Modified: `biomapper/core/mapping_executor.py`
    - Modified: `biomapper/core/engine_components/__init__.py`
- **Code standards:** Adhere to existing project formatting, type hinting, and async/await patterns.
- **Validation requirements:** The application should remain functional. A good first check is to ensure existing tests (if any that cover path execution) still pass or can be adapted. Manual testing of a simple mapping path execution might be necessary if automated tests are sparse.

## 6. Error Recovery Instructions
- If you encounter errors related to dependencies or imports, resolve them by ensuring correct paths and availability.
- If refactoring introduces logical errors, carefully trace the data flow and responsibilities between `MappingExecutor` and the new `PathExecutionManager`.
- Commit frequently within your worktree branch (`feature/extract-path-manager`).

## 7. Feedback to Parent Supervisor (Cascade)
Upon completion or if significant blockers arise, provide feedback including:
- **Status:** (e.g., Completed, Blocked, In Progress)
- **Summary of Changes:** Brief description of files created/modified.
- **Key Decisions Made:** Any significant design choices during implementation.
- **Challenges Encountered:** Any difficulties or complex areas.
- **Testing Done:** What manual or automated checks were performed.
- **Next Steps/Concerns:** Any follow-up actions needed or potential issues.
- **Completed Subtasks:** Checklist of what was accomplished from section 3.
- **Issues Encountered:** Detailed error descriptions with context if blocked.
- **Confidence Assessment:** Quality, testing coverage, risk level.
- **Environment Changes:** Any files created, permissions changed, etc.
- **Lessons Learned:** Patterns that worked or should be avoided.

Remember to operate within the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper-feature-path-manager/` worktree and commit changes to the `feature/extract-path-manager` branch.
