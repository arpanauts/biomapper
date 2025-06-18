# Task: Create Unit Tests for `IdentifierLoader`

## Objective
To validate the logic for loading identifiers from various data sources, create comprehensive unit tests for the `IdentifierLoader` component.

## Location for Tests
Create a new test file: `tests/core/engine_components/test_identifier_loader.py`

## Test Strategy
- Use `pytest` and `unittest.mock` with `AsyncMock` for async methods.
- Mock the `metamapper_session_factory` to return a mock `AsyncSession`.
- The mock `AsyncSession` should return mock SQLAlchemy models (`Endpoint`, `EndpointPropertyConfig`, `PropertyExtractionConfig`) when its `execute` method is called.
- Mock filesystem interactions (`os.path.exists`) and data loading (`pandas.read_csv`).

## Test Cases

### `get_ontology_column`
1.  **Test Successful Lookup:** Mock the full chain of database objects and assert that the correct column name is returned from the mock `extraction_pattern`.
2.  **Test Endpoint Not Found:** Mock the session to return `None` for the `Endpoint` query. Assert a `ConfigurationError` is raised.
3.  **Test Property Config Not Found:** Mock the session to return `None` for the `EndpointPropertyConfig` query. Assert a `ConfigurationError` is raised.

### `load_endpoint_identifiers`
1.  **Test Successful Load (as List):** Mock a successful database and file lookup. Assert that a list of unique identifiers is returned.
2.  **Test Successful Load (as DataFrame):** Call with `return_dataframe=True` and assert that the mock DataFrame is returned.
3.  **Test File Not Found:** Mock `os.path.exists` to return `False`. Assert `FileNotFoundError` is raised.
4.  **Test Column Not Found:** Mock a DataFrame that is missing the required identifier column. Assert `KeyError` is raised.
5.  **Test Placeholder Resolution:** Verify that `resolve_placeholders` is called with the file path from the mock `Endpoint` configuration.

## Acceptance Criteria
- A new test file `tests/core/engine_components/test_identifier_loader.py` is created.
- The tests use async mocks to validate the asynchronous database logic.
- The tests cover all public methods and their primary success and failure modes.
- All tests pass successfully.
