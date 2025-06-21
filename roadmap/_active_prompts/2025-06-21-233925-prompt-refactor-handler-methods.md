# Task: Refactor `MappingExecutor` by Extracting Handler Methods into a `MappingHandlerService`

## 1. Objective

Continue the deep refactoring of the oversized `MappingExecutor` class by extracting its large, private `_handle_*` methods into a new, dedicated `MappingHandlerService`. The primary goal is to achieve a significant reduction in `MappingExecutor`'s line count (targeting a ~400-line reduction) and move it closer to being a pure facade that delegates all complex logic to specialized services.

## 2. Context and Background

The previous refactoring effort successfully extracted the main `execute_*` methods into separate services (`IterativeExecutionService`, `DbStrategyExecutionService`, `YamlStrategyExecutionService`). However, this only resulted in a 12% size reduction, falling short of the 50% target. Feedback analysis revealed that the bulk of the remaining logic resides in three large handler methods used by the YAML strategy executor:

-   `_handle_convert_identifiers_local` (~130 lines)
-   `_handle_execute_mapping_path` (~126 lines)
-   `_handle_filter_identifiers_by_target_presence` (~124 lines)

This task will address this by moving these methods into their own service, which will drastically simplify `MappingExecutor` and improve code modularity.

## 3. Prerequisites

- The agent must be familiar with the ongoing service-oriented refactoring of the Biomapper project.
- The primary file to be modified is `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`.

## 4. Task Breakdown

1.  **Create `MappingHandlerService`**:
    - In the `biomapper/core/services/` directory, create a new file named `mapping_handler_service.py`.
    - Inside this file, define a new class `MappingHandlerService`.
    - The constructor (`__init__`) for this service must accept all necessary dependencies. Based on the logic within the handler methods, these will likely include:
        - `logger`
        - `client_manager`
        - `path_finder`
        - `async_metamapper_session`
        - `metadata_query_service`
        - `placeholder_resolver`

2.  **Migrate Handler Method Logic**:
    - Locate the methods `_handle_convert_identifiers_local`, `_handle_execute_mapping_path`, and `_handle_filter_identifiers_by_target_presence` in `mapping_executor.py`.
    - **Cut** the entire method bodies from `mapping_executor.py` and **paste** them into the new `MappingHandlerService` class.
    - Rename the methods to be public (e.g., `_handle_convert_identifiers_local` becomes `handle_convert_identifiers_local`).
    - Refactor the method bodies to use the dependencies injected into the service's `__init__` (e.g., `self.client_manager`) instead of assuming they exist on the `MappingExecutor` instance.
    - Adjust the method signatures to accept any parameters that were previously accessed via `self` in `MappingExecutor` but are not part of the service's dependencies. The `execution_context` dictionary is a critical parameter that will need to be passed into these methods.

3.  **Refactor `MappingExecutor`**:
    - In `MappingExecutor.__init__`, instantiate the new `MappingHandlerService`, injecting all its required dependencies.
        ```python
        self.mapping_handler_service = MappingHandlerService(
            logger=self.logger,
            client_manager=self.client_manager,
            # ... other dependencies
        )
        ```
    - Replace the original `_handle_*` method bodies in `MappingExecutor` with a single line that delegates the call to the new service. For example:
        ```python
        async def _handle_execute_mapping_path(self, step: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
            return await self.mapping_handler_service.handle_execute_mapping_path(
                step=step, execution_context=execution_context
            )
        ```

4.  **Update `__init__.py`**:
    - Add `MappingHandlerService` to the `__all__` list in `biomapper/core/services/__init__.py` to ensure it is correctly exported.

5.  **Fix Failing Tests**:
    - The previous feedback noted test failures due to a missing `_find_direct_paths` method. This is a pre-existing issue that must be resolved.
    - Investigate the test suite (e.g., `tests/unit/core/test_mapping_executor.py`) to identify which tests are failing.
    - Determine the correct replacement for the `_find_direct_paths` call. The logic may now reside in `PathFinder` or `DirectMappingService`. Update the test to use the correct service and method.

## 5. Implementation Requirements

- **Code Standards:** All new and modified code must be fully type-hinted and follow async/await patterns. Maintain the existing code style.
- **Dependencies:** Ensure all dependencies are correctly injected. Pay close attention to avoiding circular imports, which have been an issue in past refactorings.

## 6. Error Recovery Instructions

- **`AttributeError`:** If the new service methods fail because they are trying to access an attribute that wasn't passed in (e.g., `self.path_finder`), update the `MappingHandlerService` constructor and the instantiation in `MappingExecutor` to pass the required dependency.
- **Circular Imports:** If you encounter `ImportError: cannot import name ...`, use local, in-method imports as a last resort. The ideal solution is to refactor dependencies to break the cycle.

## 7. Validation and Success Criteria

- **Primary Validation:** The refactoring is successful when the entire test suite passes without errors.
- **Execution Command:** Run `poetry run pytest` from the project root (`/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`).
- **Code Metrics:** The `mapping_executor.py` file should be reduced in size by approximately 400 lines.
- **New Artifacts:** The new `mapping_handler_service.py` file should be created and contain the extracted logic.

## 8. Feedback and Reporting

- Provide the `diff` of the changes made to `mapping_executor.py`.
- Provide the full content of the new `mapping_handler_service.py` file.
- Provide the `diff` for any test files you modified.
- Confirm that you ran the validation command and that all tests passed successfully.
