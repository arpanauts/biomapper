# Task: Refactor MappingExecutor - Extract StrategyOrchestrator

**Project:** Biomapper
**Target Worktree Root:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper-feature-strategy-orchestrator/`
**Target Branch:** `feature/extract-strategy-orchestrator`
**Parent Supervisor:** Cascade (Main Project Instance)

## 1. Objective
Refactor the `biomapper.core.mapping_executor.MappingExecutor` class by extracting the logic responsible for orchestrating the execution of mapping strategies (defined in YAML) into a new, dedicated component: `biomapper.core.engine_components.StrategyOrchestrator`.

This will improve modularity, testability, and maintainability of the `MappingExecutor`, separating strategy execution flow from other concerns like path execution details or client initialization.

## 2. Background & Context
The `MappingExecutor` currently handles the entire lifecycle of executing a YAML-defined strategy. This includes:
- Loading and validating the strategy definition (delegated to `StrategyHandler`).
- Iterating through strategy steps (`_execute_strategy_step`).
- Managing the `execution_context` as it flows between steps.
- Deciding whether a step involves executing a mapping path (`_handle_execute_mapping_path`) or a custom action (`_handle_action_step`).
- Initializing and invoking `StrategyAction` instances.
- Collecting results and metrics for the overall strategy execution.

This refactoring aims to move the core strategy execution loop and step-type handling into `StrategyOrchestrator`.

## 3. Scope of Work

**3.1. Create `StrategyOrchestrator` Class:**
   - Create a new file: `biomapper/core/engine_components/strategy_orchestrator.py`.
   - Define a class `StrategyOrchestrator`.
   - The constructor `__init__` should accept necessary dependencies. These will likely include:
     - `metamapper_session_factory` (for fetching strategy/path/client details)
     - `cache_manager` (instance of `CacheManager`, to be passed down to path execution)
     - `logger`
     - `strategy_handler` (instance of `StrategyHandler` for loading/validating strategies)
     - `path_execution_manager` (This component will be developed in parallel. For now, assume an interface or that `MappingExecutor` will pass its own `_execute_path` method or a similar callable. The final integration will use the `PathExecutionManager` instance from `MappingExecutor`.)
     - `resource_clients_provider` (a way to get initialized resource clients, perhaps a method from `MappingExecutor` or `MappingExecutor` itself to call `_get_resource_client`)

**3.2. Migrate Strategy Execution Logic:**
   - The primary public method of `StrategyOrchestrator` should be `async execute_strategy(...)`.
   - This method will take parameters similar to `MappingExecutor.execute_yaml_strategy`:
     - `strategy_name: str`
     - `input_identifiers: List[str]`
     - `initial_context: Optional[Dict[str, Any]] = None`
     - `source_endpoint_name: Optional[str] = None` (and similar for target)
     - `mapping_session_id: Optional[int]`
   - Move the core logic from `MappingExecutor.execute_yaml_strategy` (and its main loop) into this new method.
   - Move helper methods primarily supporting strategy execution into `StrategyOrchestrator`. Examples:
     - `_execute_strategy_step`
     - `_handle_execute_mapping_path` (this will call the `path_execution_manager`)
     - `_handle_action_step`
     - `_load_and_validate_strategy` (or use `strategy_handler` directly)
     - `_initialize_strategy_actions`
   - Adapt these methods to work within the `StrategyOrchestrator` class context.

**3.3. Update `MappingExecutor`:**
   - In `biomapper.core.mapping_executor.MappingExecutor`:
     - Instantiate `StrategyOrchestrator` in the `__init__` method, passing necessary dependencies (including `self` if some `MappingExecutor` methods are needed as callbacks initially, e.g., for client or path execution if `PathExecutionManager` is not yet integrated).
     - Modify `MappingExecutor.execute_yaml_strategy` to become a thin wrapper that primarily delegates its call to `self.strategy_orchestrator.execute_strategy(...)`.
     - Remove the helper methods that were moved to `StrategyOrchestrator` from `MappingExecutor`.

**3.4. Handle Dependencies and Imports:**
   - Ensure all necessary imports are added to `strategy_orchestrator.py`.
   - Update imports in `mapping_executor.py` as needed.
   - Add `StrategyOrchestrator` to `biomapper/core/engine_components/__init__.py`.

## 4. Key Considerations

- **Interface with `PathExecutionManager`:** The `StrategyOrchestrator` will need to invoke path executions. Since `PathExecutionManager` is being developed in parallel, initially, `_handle_execute_mapping_path` within `StrategyOrchestrator` might need to call back to a method on `MappingExecutor` that wraps the original `_execute_path`. The final goal is for it to call an instance of `PathExecutionManager` passed to `StrategyOrchestrator`.
- **Client Instantiation:** `StrategyAction` instances often need resource clients. `MappingExecutor._get_resource_client` handles this. `StrategyOrchestrator` will need access to this functionality, either by receiving `MappingExecutor` itself, or a dedicated callable/provider for clients.
- **Context Management:** The `execution_context` is critical. Ensure its flow and updates are correctly managed by `StrategyOrchestrator`.
- **StrategyHandler Usage:** `StrategyOrchestrator` should leverage the existing `StrategyHandler` for loading, validating, and accessing strategy definitions.
- **Logging and Metrics:** Ensure that logging and any high-level strategy metrics collection are preserved or adapted.

## 5. Implementation Requirements
- **Input files/data:** Primarily `biomapper/core/mapping_executor.py`.
- **Expected outputs:** 
    - New file: `biomapper/core/engine_components/strategy_orchestrator.py`
    - Modified: `biomapper/core/mapping_executor.py`
    - Modified: `biomapper/core/engine_components/__init__.py`
- **Code standards:** Adhere to existing project formatting, type hinting, and async/await patterns.
- **Validation requirements:** The application should remain functional. Testing execution of a simple YAML strategy is crucial. Existing tests for strategy execution (if any) should be adapted or new ones considered for the future.

## 6. Error Recovery Instructions
- If you encounter errors related to dependencies or imports, resolve them by ensuring correct paths and availability.
- If refactoring introduces logical errors, carefully trace the data flow, context management, and responsibilities between `MappingExecutor` and the new `StrategyOrchestrator`.
- Commit frequently within your worktree branch (`feature/extract-strategy-orchestrator`).

## 7. Feedback to Parent Supervisor (Cascade)
Upon completion or if significant blockers arise, provide feedback including:
- **Status:** (e.g., Completed, Blocked, In Progress)
- **Summary of Changes:** Brief description of files created/modified.
- **Key Decisions Made:** Any significant design choices during implementation (especially regarding interaction with `PathExecutionManager` and client provision).
- **Challenges Encountered:** Any difficulties or complex areas.
- **Testing Done:** What manual or automated checks were performed.
- **Next Steps/Concerns:** Any follow-up actions needed or potential issues.
- **Completed Subtasks:** Checklist of what was accomplished from section 3.
- **Issues Encountered:** Detailed error descriptions with context if blocked.
- **Confidence Assessment:** Quality, testing coverage, risk level.
- **Environment Changes:** Any files created, permissions changed, etc.
- **Lessons Learned:** Patterns that worked or should be avoided.

Remember to operate within the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper-feature-strategy-orchestrator/` worktree and commit changes to the `feature/extract-strategy-orchestrator` branch.
