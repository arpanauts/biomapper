# Task 1: Extract `MappingPathExecutionService`

## Objective
Deconstruct `MappingExecutor` by extracting the logic responsible for executing a single, complete mapping path into a new, focused service class named `MappingPathExecutionService`. This service will handle the mechanics of running a path, from step execution to result processing and provenance tracking.

## Rationale
`MappingExecutor` currently intertwines the orchestration of high-level strategies with the low-level mechanics of executing a single path. Separating this logic will improve modularity, simplify `MappingExecutor`, and make the path execution process easier to test and maintain in isolation.

## New Component Location
- Create a new file: `biomapper/core/services/mapping_path_execution_service.py`
- Define the class: `MappingPathExecutionService`

## Core Responsibilities of `MappingPathExecutionService`
- Execute a given mapping path for a batch of identifiers.
- Interact with the `ClientManager` to get client instances for each step.
- Process the results from each step.
- Handle bidirectional validation if requested.
- Calculate confidence scores for mappings.
- Assemble the final `MappingResultBundle` with detailed provenance.

## Methods to Move/Refactor from `MappingExecutor`

The following methods (or their logic) should be moved from `MappingExecutor` to `MappingPathExecutionService`. The method signatures may need to be adapted to accept necessary dependencies (like `session`, `client_manager`, etc.) via the constructor or method arguments.

1.  `_execute_mapping_step`: This is a core method for executing a single client call. It will be a private helper within the new service.
2.  `_process_path_results`: This method processes the raw output of a path execution into a structured format.
3.  `_calculate_confidence_score`: Logic for determining the confidence of a mapping.
4.  `_create_mapping_path_details`: Helper for building provenance information.
5.  `_determine_mapping_source`: Helper for identifying the source of a mapping.
6.  The core loop/logic from `execute_mapping_path` (or a similar name): This will become the main public method of the new service (e.g., `async def execute(...)`). It will orchestrate the execution of all steps in a path.

## `MappingPathExecutionService` `__init__`
The constructor should accept the components it depends on, which will be injected by `MappingExecutor`:
- `logger`
- `client_manager: ClientManager`
- `cache_manager: CacheManager`

## Refactoring Steps
1.  **Create the File and Class:** Create `biomapper/core/services/mapping_path_execution_service.py` and define the `MappingPathExecutionService` class.
2.  **Define `__init__`:** Implement the constructor to accept its dependencies.
3.  **Move and Adapt Methods:**
    - Copy the logic from the methods listed above (`_execute_mapping_step`, `_process_path_results`, etc.) into the new service class.
    - Refactor them to work within the context of the new service. Replace `self.` references (that point to `MappingExecutor`) with direct access to its dependencies (e.g., `self.client_manager`).
4.  **Create Public `execute` Method:** Design the main public method for the service (e.g., `async def execute_path(...)`) that takes a `path`, `identifiers`, and other relevant options, and orchestrates the execution using the private helper methods.
5.  **Update `MappingExecutor`:**
    - In `MappingExecutor`, remove the private methods that were moved (`_execute_mapping_step`, `_process_path_results`, etc.).
    - Instantiate `MappingPathExecutionService` in `MappingExecutor.__init__` and store it as `self.path_execution_service`.
    - Update the existing `execute_mapping_path` method in `MappingExecutor` to be a simple pass-through call to `self.path_execution_service.execute_path(...)`.

## Acceptance Criteria
- The new `MappingPathExecutionService` is created and contains all the logic for executing a single mapping path.
- The original `MappingExecutor` is simplified, with the moved methods removed and its `execute_mapping_path` method now delegating to the new service.
- All existing tests related to single path execution must be refactored to test the new service and continue to pass. New unit tests for `MappingPathExecutionService` should be created.
