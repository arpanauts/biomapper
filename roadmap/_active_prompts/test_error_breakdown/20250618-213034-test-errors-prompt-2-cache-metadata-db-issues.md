# Task: Resolve Cache & Metadata Database Issues (SQLite & SQLAlchemy 2.0)

## Objective
Fix SQLite operational errors related to missing tables (specifically `entity_mappings`) and address SQLAlchemy 2.0 compatibility issues for raw SQL queries in tests related to caching and metadata.

## Affected Files/Modules
- `tests/cache/test_cached_mapper.py`
- `tests/cache/test_manager.py`
- `tests/core/test_metadata_fields.py`
- `tests/core/test_metadata_impl.py`

## Common Error(s)
- `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: entity_mappings`
- `sqlalchemy.exc.ArgumentError: Textual SQL expression 'DELETE FROM entity_mappin...' should be explicitly declared as text('DELETE FROM e...')`

## Background/Context
The `entity_mappings` table, crucial for caching, appears to be missing or inaccessible during certain test executions. This could be due to issues with test database setup, schema creation, or session management within the tests.

Additionally, SQLAlchemy 2.0 has enforced stricter handling of raw SQL strings. Queries executed directly (not through the ORM's expression language) must now be explicitly wrapped with `text()` to be recognized as SQL statements.

## Debugging Guidance/Hypotheses

**For `no such table: entity_mappings`:**
- **Test Database Setup:** Verify how the test database is initialized. Is it an in-memory SQLite database (`sqlite:///:memory:`) or a file-based one? Ensure consistency.
- **Schema Creation:** Confirm that `Base.metadata.create_all(engine)` (or its async equivalent) is called correctly before tests that interact with the database are run. This is essential for creating all defined tables.
- **Session Scope:** Check if test sessions are correctly scoped and if schema creation happens within the right context for the test's session to see the tables.
- **Fixtures:** Review pytest fixtures responsible for database setup (e.g., `engine`, `session` fixtures) to ensure they correctly set up and tear down the database environment, including table creation.

**For `ArgumentError: Textual SQL expression ... should be explicitly declared as text(...)`:**
- **Import `text`:** Ensure `from sqlalchemy import text` is present in the relevant files.
- **Wrap SQL Strings:** Locate all raw SQL strings used in functions like `session.execute()` and wrap them with the `text()` construct. For example, `session.execute("DELETE FROM entity_mappings")` should become `session.execute(text("DELETE FROM entity_mappings"))`.

## Specific Error Examples
1.  `FAILED tests/cache/test_cached_mapper.py::CachedMapperTest::test_batch_map_mixed_hits - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: entity_mappings`
2.  `FAILED tests/cache/test_manager.py::CacheManagerTest::test_add_mapping - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: entity_mappings`
3.  `FAILED tests/core/test_metadata_fields.py::test_cache_results_populates_metadata_fields - sqlalchemy.exc.ArgumentError: Textual SQL expression 'DELETE FROM entity_mappin...' should be explicitly declared as text('DELETE FROM e...')`

## Acceptance Criteria
- All tests in the listed 'Affected Files/Modules' that previously failed with `OperationalError: no such table: entity_mappings` now pass, indicating the `entity_mappings` table is correctly created and accessible.
- All tests that previously failed with `ArgumentError: Textual SQL expression ... should be explicitly declared as text(...)` now pass, with raw SQL queries correctly adapted for SQLAlchemy 2.0.
- Database interactions within these tests are robust and schema is correctly managed.
