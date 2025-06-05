# Task: Refactor MappingExecutor for Async Resource Management and Update Test Script

## Context:
We have a Python class `MappingExecutor` (in `biomapper/core/mapping_executor.py`) that manages database connections using SQLAlchemy's `AsyncEngine`. A test script, `scripts/test_protein_yaml_strategy.py`, uses this class but currently fails with `AttributeError` because it tries to call non-existent `executor.initialize()` and `executor.close()` methods.

The `MappingExecutor` is instantiated via an `async` class method `MappingExecutor.create(...)` which handles necessary setup, including initializing database tables. The core issue is the lack of a proper asynchronous disposal mechanism for the `AsyncEngine` instances created within `MappingExecutor`.

## Goal:
1.  Modify `MappingExecutor` to include an `async_dispose()` method that properly closes/disposes of its `AsyncEngine` instances.
2.  Update `scripts/test_protein_yaml_strategy.py` to:
    *   Use `await MappingExecutor.create(...)` for instantiation.
    *   Remove the incorrect call to `executor.initialize()`.
    *   Call the new `await executor.async_dispose()` method in the `finally` block for cleanup.

## Files to Modify:
1.  `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
2.  `/home/ubuntu/biomapper/scripts/test_protein_yaml_strategy.py`

## Detailed Instructions:

### 1. Modify `biomapper/core/mapping_executor.py` (Class: `MappingExecutor`)

*   **Add an `async_dispose()` method:**
    *   Define a new `async` instance method, for example, `async_dispose()`.
    *   Inside this method, ensure that the `dispose()` method is called on both SQLAlchemy `AsyncEngine` instances managed by the `MappingExecutor`. These are likely named `self.metamapper_engine` and `self.cache_engine` (created in `__init__`).
    *   The calls should be `await self.metamapper_engine.dispose()` and `await self.cache_engine.dispose()`.
    *   Add logging to indicate that engines are being disposed.
    *   Consider adding checks to see if the engines exist before trying to dispose of them, e.g., `if hasattr(self, 'metamapper_engine') and self.metamapper_engine:`.

    **Example structure for `async_dispose` in `MappingExecutor`:**
    ```python
    # Inside MappingExecutor class

    async def async_dispose(self):
        """Asynchronously dispose of underlying database engines."""
        self.logger.info("Disposing of MappingExecutor engines...")
        if hasattr(self, 'metamapper_engine') and self.metamapper_engine:
            await self.metamapper_engine.dispose()
            self.logger.info("Metamapper engine disposed.")
        if hasattr(self, 'cache_engine') and self.cache_engine:
            await self.cache_engine.dispose()
            self.logger.info("Cache engine disposed.")
        self.logger.info("MappingExecutor engines disposed.")
    ```

*   **Verify Engine Initialization:**
    *   Ensure that `self.metamapper_engine` and `self.cache_engine` are indeed the attributes holding the `AsyncEngine` instances created in the `__init__` method. The `__init__` method looks like this:
        ```python
        # Snippet from MappingExecutor.__init__
        # ...
        self.metamapper_db_url = metamapper_db_url or settings.metamapper_db_url
        self.mapping_cache_db_url = mapping_cache_db_url or settings.cache_db_url
        self.echo_sql = echo_sql
        # ...
        self.metamapper_engine = create_async_engine(
            self.metamapper_db_url, 
            echo=self.echo_sql, 
            json_serializer=PydanticEncoder.encode_json, # Assuming PydanticEncoder is available
            json_deserializer=json.loads
        )
        self.MetamapperSessionFactory = sessionmaker( # Corrected from CacheMetamapperSessionFactory
            self.metamapper_engine, class_=AsyncSession, expire_on_commit=False
        )
        # ...
        cache_async_url = self.mapping_cache_db_url 
        self.cache_engine = create_async_engine(
            cache_async_url, 
            echo=self.echo_sql, 
            json_serializer=PydanticEncoder.encode_json, # Assuming PydanticEncoder is available
            json_deserializer=json.loads
        )
        self.CacheSessionFactory = sessionmaker( 
            self.cache_engine, class_=AsyncSession, expire_on_commit=False
        )
        # ...
        ```
        The key is that `self.metamapper_engine` and `self.cache_engine` are the `AsyncEngine` instances.

### 2. Modify `scripts/test_protein_yaml_strategy.py`

*   **Update `test_yaml_strategy` function:**
    *   **Instantiate `MappingExecutor` correctly:**
        *   The `MappingExecutor` should be instantiated using its `async` class method `create()`.
        *   Change from direct instantiation to `await MappingExecutor.create(...)`.
        *   Ensure all necessary parameters (`metamapper_db_url`, `mapping_cache_db_url`, `enable_metrics`) are passed to `create()`. The `create()` method signature is: `MappingExecutor.create(cls, metamapper_db_url: Optional[str] = None, mapping_cache_db_url: Optional[str] = None, echo_sql: bool = False, path_cache_size: int = 100, path_cache_expiry_seconds: int = 300, max_concurrent_batches: int = 5, enable_metrics: bool = True)`.

    *   **Remove `executor.initialize()`:**
        *   Delete the line `await executor.initialize()` as the `create()` method handles initialization.

    *   **Update cleanup in `finally` block:**
        *   Change `await executor.close()` to `await executor.async_dispose()`.

    **Target structure for `test_yaml_strategy` (relevant parts):**
    ```python
    async def test_yaml_strategy():
        # ...
        executor = None # Initialize to None for finally block
        try:
            executor = await MappingExecutor.create(
                metamapper_db_url=settings.metamapper_db_url,
                mapping_cache_db_url=settings.cache_db_url,
                enable_metrics=True 
            )
            
            await check_database_state()
            
            logger.info("\n==================================================\n")
            # ... (rest of the existing logic for executing strategy)
            
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            logger.error(traceback.format_exc())
        finally:
            if executor:
                await executor.async_dispose() # Use the new dispose method
                logger.info("MappingExecutor disposed in test script.")
    ```

## Expected Outcome:
The `test_protein_yaml_strategy.py` script should run without `AttributeError`s related to `initialize` or `close` on the `MappingExecutor` instance. The `AsyncEngine` resources within `MappingExecutor` should be correctly disposed of when `async_dispose()` is called.

Please ensure all changes are asynchronous where appropriate (using `async` and `await`).
