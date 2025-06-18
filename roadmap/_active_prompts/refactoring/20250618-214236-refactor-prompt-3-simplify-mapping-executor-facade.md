# Task 3: Refactor `MappingExecutor` to a Lean Facade

## Objective
With the core logic now extracted into `MappingPathExecutionService` and `StrategyExecutionService`, refactor the `MappingExecutor` class to serve as a lean, clean facade. Its primary responsibilities will be initialization of components and delegation of tasks to the appropriate services.

## Rationale
This final step in the deconstruction completes the separation of concerns. A lean `MappingExecutor` is easier to understand, as its public API clearly shows the main capabilities of the system (e.g., `map`, `execute_strategy`) without exposing the complex implementation details, which now reside in the specialized services.

## Refactoring Steps

1.  **Review `MappingExecutor.__init__`:**
    - The initializer should now be primarily responsible for instantiating all the engine components and services:
        - `SessionManager`, `ClientManager`, `CacheManager`, etc.
        - The new `MappingPathExecutionService` and `StrategyExecutionService`.
    - Pass the necessary dependencies into the constructors of the new services.
    - Remove any attributes from `self` that are no longer directly used by `MappingExecutor` itself (e.g., if a component is only used by one of the new services, it might not need to be an attribute of `MappingExecutor`).

2.  **Simplify the Public API:**
    - The main public methods of `MappingExecutor` should be high-level entry points. Review and refine:
        - `execute_mapping`: This method should now use `self.path_finder` to find a path and then delegate the execution to `self.path_execution_service`.
        - `execute_strategy`: This method should be a simple pass-through to `self.strategy_execution_service`.
        - `map`: This should be the primary, user-friendly method. It might internally decide whether to call `execute_mapping` or `execute_strategy` based on its arguments.

3.  **Remove Redundant/Pass-Through Methods:**
    - `MappingExecutor` currently has several private methods that are simple pass-through calls to `PathFinder` (e.g., `_find_mapping_paths`, `_find_best_path`) or `MetadataQueryService`.
    - These should be removed from `MappingExecutor`. Components or services that need this functionality should be given a direct dependency on `PathFinder` or `MetadataQueryService` instead of going through `MappingExecutor`.

4.  **Update `MappingExecutor.create` Factory:**
    - Ensure the asynchronous factory method `create` correctly initializes the simplified `MappingExecutor` and all its dependent services.
    - The call to `_init_db_tables` should be replaced by a call to the new `DatabaseSetupService` (from Prompt 4).

## Acceptance Criteria
- `MappingExecutor` is significantly shorter and simpler. Its `__init__` method is focused on dependency injection.
- The public API of `MappingExecutor` is clean and delegates all heavy lifting to the appropriate services (`MappingPathExecutionService`, `StrategyExecutionService`).
- Redundant private helper and pass-through methods have been removed.
- All dependent components are correctly initialized and wired together.
- High-level integration tests continue to pass, demonstrating that the facade correctly orchestrates the underlying services.
