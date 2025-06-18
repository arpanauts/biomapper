# Task: Extract `MetadataQueryService` from `MappingExecutor`

## Objective
To improve separation of concerns and centralize database interactions for metadata, extract logic for querying metamapper database entities (Endpoints, Properties, Ontologies, etc.) from `MappingExecutor` into a dedicated `MetadataQueryService`.

## Current Implementation
`MappingExecutor` currently contains several private methods (e.g., `_get_endpoint_properties`, `_get_ontology_preferences`, `_get_endpoint`, `_get_ontology_type`) that directly execute SQLAlchemy queries against the metamapper database to fetch configuration and metadata.

## Refactoring Steps

1.  **Create the `MetadataQueryService` Class:**
    *   Create a new file: `biomapper/core/services/metadata_query_service.py` (or `biomapper/core/engine_components/metadata_query_service.py`).
    *   Define a `MetadataQueryService` class.
    *   Its `__init__` method should accept a `SessionManager` instance to obtain database sessions for the metamapper database.

2.  **Move Query Logic:**
    *   Identify all methods in `MappingExecutor` that perform read-only queries for metadata from the metamapper DB (e.g., `Endpoint`, `EndpointPropertyConfig`, `OntologyPreference` tables).
    *   Examples: `_get_endpoint_properties`, `_get_ontology_preferences`, `_get_endpoint`, `_get_ontology_type`.
    *   Move the core query logic of these methods into corresponding public methods in `MetadataQueryService`. These methods should accept an `AsyncSession` (obtained via `SessionManager`) and necessary parameters.
    *   Ensure these methods return data in a consistent format (e.g., Pydantic models, SQLAlchemy model instances, or basic data structures).

3.  **Update `MappingExecutor`:**
    *   In `MappingExecutor.__init__`, instantiate `MetadataQueryService`, passing its `SessionManager`.
    *   Replace the internal logic of the original private methods in `MappingExecutor` with calls to the new `MetadataQueryService` methods.
    *   Alternatively, if these private methods are only used by logic being moved to other new components (like `RobustExecutionCoordinator`), then `MappingExecutor` might not need to call this service directly, but the new components will.
    *   Update imports as necessary.

## Acceptance Criteria
*   `MetadataQueryService` class is implemented and handles queries for metamapper metadata.
*   Relevant query logic is removed from `MappingExecutor` and delegated to `MetadataQueryService`.
*   `MappingExecutor` (or other components) use `MetadataQueryService` to fetch metadata.
*   The application's ability to retrieve and use metadata from the metamapper database remains unchanged.
