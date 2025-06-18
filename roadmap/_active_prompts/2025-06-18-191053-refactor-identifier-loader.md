# Task: Create a Dedicated `IdentifierLoader` for Endpoint Data

## Objective
To better separate concerns, extract the logic for loading identifiers from data endpoints into a new, dedicated `IdentifierLoader` class. This will decouple the `MappingExecutor` from the specifics of data loading.

## Current Implementation
The `MappingExecutor` has a public method `load_endpoint_identifiers` that contains logic to connect to a database, query an endpoint table, and return a list of identifiers. 

## Refactoring Steps

1.  **Create the `IdentifierLoader` Class:**
    *   Create a new file: `biomapper/core/engine_components/identifier_loader.py`.
    *   Define an `IdentifierLoader` class.
    *   The `__init__` method should accept a `session_manager` instance to handle database connections.
    *   Move the `load_endpoint_identifiers` method from `MappingExecutor` into the `IdentifierLoader` class. The method signature should be similar.

2.  **Update `MappingExecutor`:**
    *   In `biomapper/core/mapping_executor.py`, remove the `load_endpoint_identifiers` method.
    *   In `MappingExecutor.__init__`, instantiate the `IdentifierLoader`:
        ```python
        # Assuming self.session_manager is already created
        self.identifier_loader = IdentifierLoader(session_manager=self.session_manager)
        ```
    *   Create a new public method `load_endpoint_identifiers` on `MappingExecutor` that simply acts as a pass-through to the `IdentifierLoader` instance:
        ```python
        def load_endpoint_identifiers(self, endpoint_name: str, identifier_column: Optional[str] = None) -> List[str]:
            return self.identifier_loader.load_endpoint_identifiers(endpoint_name, identifier_column)
        ```
    *   Add the necessary import: `from .engine_components.identifier_loader import IdentifierLoader`.

## Acceptance Criteria
*   An `IdentifierLoader` class is implemented in `biomapper/core/engine_components/identifier_loader.py`.
*   The core logic of `load_endpoint_identifiers` is moved out of `MappingExecutor`.
*   `MappingExecutor` delegates the call to its `IdentifierLoader` instance.
*   The ability to load identifiers from an endpoint remains fully functional.
