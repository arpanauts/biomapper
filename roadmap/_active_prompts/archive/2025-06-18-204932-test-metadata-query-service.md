# Task: Generate Unit Tests for `MetadataQueryService`

## Objective
To ensure the `MetadataQueryService` correctly retrieves metadata entities from the metamapper database and handles various scenarios, including data presence and absence, and interacts properly with its dependencies.

## Component to Test
`biomapper.core.services.metadata_query_service.MetadataQueryService`
(Assuming this path after refactoring)

## Test File Target
`tests/core/services/test_metadata_query_service.py`

## Key Functionalities to Test
*   Retrieval of endpoint properties (`_get_endpoint_properties` equivalent).
*   Retrieval of ontology preferences (`_get_ontology_preferences` equivalent).
*   Retrieval of a single endpoint (`_get_endpoint` equivalent).
*   Retrieval of an ontology type for an endpoint property (`_get_ontology_type` equivalent).
*   Correct usage of `SessionManager` to obtain `AsyncSession` for the metamapper database.
*   Proper handling of cases where data is found or not found (e.g., returning `None` or empty lists).
*   Error handling for database query issues.

## Mocking Strategy
*   Mock `SessionManager` to control `AsyncSession` instances provided to the service.
*   Mock `AsyncSession` methods (`execute`, `scalar_one_or_none`, `scalars`, `all`).
*   Mock SQLAlchemy model instances returned by queries.
*   Use `unittest.mock.AsyncMock` for asynchronous methods and context managers.

## Test Cases

1.  **`__init__`:**
    *   Test that `MetadataQueryService` initializes correctly with a `SessionManager` instance.

2.  **`get_endpoint_properties` (or equivalent method):**
    *   Test successful retrieval of multiple `EndpointPropertyConfig` objects for a given endpoint name.
    *   Test retrieval when no properties are found (returns empty list).
    *   Test when the endpoint itself is not found (should likely also result in an empty list or handle gracefully).

3.  **`get_ontology_preferences` (or equivalent method):**
    *   Test successful retrieval of multiple `OntologyPreference` objects for an endpoint.
    *   Test retrieval when no preferences are found (returns empty list).

4.  **`get_endpoint` (or equivalent method):**
    *   Test successful retrieval of an `Endpoint` object by name.
    *   Test when the endpoint is not found (returns `None`).

5.  **`get_ontology_type` (or equivalent method):**
    *   Test successful retrieval of an ontology type string for a given endpoint and property name.
    *   Test when the property or endpoint is not found (returns `None`).
    *   Test with different combinations of valid/invalid endpoint/property names.

6.  **Database Interaction:**
    *   Verify that `SessionManager.get_session()` is called to obtain a session for metamapper DB.
    *   Verify that `session.execute()` (or `scalars`, `scalar_one_or_none`) is called with correctly formulated SQLAlchemy queries.

7.  **Error Handling:**
    *   Test behavior when `session.execute()` raises a `SQLAlchemyError` (e.g., `DatabaseQueryError` should be raised by the service or handled appropriately).

## Acceptance Criteria
*   All specified test cases pass.
*   Tests cover successful data retrieval, data not found scenarios, and error conditions.
*   Mocks are used effectively to isolate the `MetadataQueryService` from actual database interactions and other services.
*   Tests confirm correct interaction with `SessionManager` and `AsyncSession`.
