# Task: Decompose MappingExecutor's Execution Logic into Focused Services

## 1. Objective

Further refactor the oversized `MappingExecutor` class by extracting its main execution methods (`execute_mapping`, `execute_strategy`, and `execute_yaml_strategy`) into new, separate, and focused service classes. The goal is to dramatically reduce the size and complexity of `MappingExecutor`, enforcing the Single Responsibility Principle and turning it into a pure facade.

## 2. Context and Background

While previous refactoring has successfully delegated much of the internal logic of `MappingExecutor` to various services, the class itself remains over 2,000 lines long. This is because it still contains the high-level orchestration logic for three distinct mapping execution paradigms. This violates software design best practices and makes the class difficult to maintain and understand.

This task continues our modularization effort by isolating each execution workflow into its own service, leaving `MappingExecutor` with the sole responsibility of delegating incoming requests to the correct service.

## 3. Prerequisites

- The agent must be familiar with the ongoing service-oriented refactoring of the Biomapper project.
- All necessary services that these new execution services will depend on (e.g., `PathFinder`, `ClientManager`, `ResultAggregationService`) already exist and are injected into `MappingExecutor`.

## 4. Task Breakdown

1.  **Create New Service Classes:**
    - In the `biomapper/core/services/` directory, create a new file named `execution_services.py`.
    - Inside this new file, define three new service classes:
        - `IterativeExecutionService`: This class will contain the logic currently in `MappingExecutor.execute_mapping`.
        - `DbStrategyExecutionService`: This class will contain the logic from `MappingExecutor.execute_strategy`.
        - `YamlStrategyExecutionService`: This class will contain the logic from `MappingExecutor.execute_yaml_strategy`.

2.  **Implement Service Constructors:**
    - Each new service will require access to other existing services (e.g., `PathFinder`, `ClientManager`, `LifecycleService`, etc.).
    - The constructor for each new service (`__init__`) should accept these required services as arguments.

3.  **Move Logic to New Services:**
    - Cut the entire method body from `MappingExecutor.execute_mapping` and paste it into a new `execute` method within `IterativeExecutionService`.
    - Repeat this process for `MappingExecutor.execute_strategy` -> `DbStrategyExecutionService.execute`.
    - Repeat for `MappingExecutor.execute_yaml_strategy` -> `YamlStrategyExecutionService.execute`.
    - Carefully refactor the moved code to use the services passed into the constructor (e.g., `self.path_finder` instead of `executor.path_finder`).

4.  **Refactor `MappingExecutor`:**
    - In `MappingExecutor.__init__`, instantiate the three new execution services, passing the necessary dependencies (`self.path_finder`, `self.client_manager`, etc.).
    - Replace the original, large `execute_mapping`, `execute_strategy`, and `execute_yaml_strategy` methods with new, lightweight versions that do nothing but delegate the call to the appropriate new service. For example:
      ```python
      async def execute_mapping(self, *args, **kwargs):
          return await self.iterative_execution_service.execute(*args, **kwargs)
      ```

5.  **Update `__init__.py`:**
    - Add the new service classes to `biomapper/core/services/__init__.py` to ensure they are correctly exported.

## 5. Implementation Requirements

- **Input Files:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Expected Outputs:**
    - A new file: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/services/execution_services.py`
    - A significantly smaller and simplified `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`.
    - An updated `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/services/__init__.py`.
- **Code Standards:** All new code must be fully type-hinted and follow async/await patterns. Maintain existing code style.

## 6. Error Recovery Instructions

- **Dependency Errors:** You may encounter `AttributeError` if a service method tries to access a component that wasn't passed into its constructor. Carefully trace the dependencies and ensure all required services are injected correctly.
- **Import Errors:** Ensure all new classes are correctly imported in `MappingExecutor` and correctly exported from the services package `__init__.py`.

## 7. Validation and Success Criteria

- The primary success criterion is that all existing tests must pass after the refactoring.
- Run the full test suite using `poetry run pytest` from the project root.
- The `MappingExecutor` file should be reduced in size by at least 50%.
- The new `execution_services.py` file should be created and contain the extracted logic.

## 8. Feedback and Reporting

- Provide the `diff` of the changes made to `mapping_executor.py`.
- Provide the full content of the new `execution_services.py` file.
- Confirm that all tests passed successfully.
