# Task 4: Create `DatabaseSetupService`

## Objective
Extract the database schema initialization logic from `MappingExecutor` into a new, single-purpose `DatabaseSetupService`. This service will be responsible for creating database tables, ensuring a clean separation between application runtime and database management/setup tasks.

## Rationale
Database schema creation is a setup concern, not a runtime execution concern. Mixing it into `MappingExecutor` complicates the class and violates the Single Responsibility Principle. A dedicated service makes the setup process explicit and reusable, and it can be invoked independently of the main application logic if needed (e.g., in deployment scripts or standalone setup tools).

## New Component Location
- Create a new file: `biomapper/core/services/database_setup_service.py`
- Define the class: `DatabaseSetupService`

## Core Responsibilities of `DatabaseSetupService`
- Connect to a database using a provided engine.
- Check if the required tables already exist.
- Create all tables defined in a given SQLAlchemy `Base` metadata object if they do not exist.

## Methods to Move/Refactor from `MappingExecutor`

The following method should be moved from `MappingExecutor` to `DatabaseSetupService`:

1.  `_init_db_tables`: This method contains the entire logic for checking for and creating tables. It will become the primary method of the new service.

## `DatabaseSetupService` `__init__`
The constructor can be simple, primarily accepting a logger:
- `logger`

## Refactoring Steps
1.  **Create the File and Class:** Create `biomapper/core/services/database_setup_service.py` and define the `DatabaseSetupService` class.
2.  **Move `_init_db_tables`:**
    - Move the `_init_db_tables` method from `MappingExecutor` to `DatabaseSetupService`.
    - Rename it to something more public, like `async def initialize_tables(self, engine, base_metadata)`. Make it a public method of the service.
3.  **Update `MappingExecutor.create`:**
    - In the `MappingExecutor.create` class method, instantiate the new `DatabaseSetupService`.
    - Instead of calling `await executor._init_db_tables(...)` for both the metamapper and cache databases, you will now call:
      ```python
      db_setup_service = DatabaseSetupService(logger=executor.logger)
      await db_setup_service.initialize_tables(executor.async_metamapper_engine, MetamapperBase.metadata)
      await db_setup_service.initialize_tables(executor.async_cache_engine, CacheBase.metadata)
      ```
    - (Note: You'll need to ensure `MetamapperBase` is imported or accessible).
4.  **Remove from `MappingExecutor`:** Delete the `_init_db_tables` method from the `MappingExecutor` class.

## Acceptance Criteria
- The new `DatabaseSetupService` is created and contains the logic for initializing database schemas.
- The `_init_db_tables` method is completely removed from `MappingExecutor`.
- The `MappingExecutor.create` factory method successfully uses the new `DatabaseSetupService` to set up the databases upon instantiation.
- The application continues to start up correctly, and tests that rely on database setup still pass, confirming that the tables are being created as expected.
