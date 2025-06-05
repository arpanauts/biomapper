```markdown
# Task: Correct `metamapper_session` AttributeUsage in `MappingExecutor`

## Context:
The `biomapper.core.mapping_executor.MappingExecutor` class is encountering an `AttributeError: 'MappingExecutor' object has no attribute 'metamapper_session'`. This error arises because the code incorrectly attempts to call `self.metamapper_session()` to obtain an asynchronous SQLAlchemy session for the Metamapper database.

The `__init__` method of `MappingExecutor` defines the session factory as `self.MetamapperSessionFactory` and provides an alias for easier access: `self.async_metamapper_session = self.MetamapperSessionFactory`.

Therefore, any attempt to get a session using `self.metamapper_session()` (lowercase 'm') is incorrect and should be `self.async_metamapper_session()`.

## File to Modify:
`/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

## Instructions:

1.  **Identify Incorrect Usage:**
    *   Scan the entire `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` file for all occurrences where `self.metamapper_session()` is used to obtain an asynchronous session for the Metamapper database.
    *   Pay particular attention to the `execute_yaml_strategy` method, as an error was specifically identified there (around line 3397 in older versions of the file, within an `async with` block).

2.  **Perform Correction:**
    *   Replace each identified instance of `self.metamapper_session()` with the correct attribute call: `self.async_metamapper_session()`.
    *   Ensure the change is made contextually, i.e., it's indeed being used as a callable to start an async session (e.g., `async with self.async_metamapper_session() as session:`).

3.  **Verification (Conceptual):
    *   After the changes, the code should correctly obtain an `AsyncSession` from the `self.async_metamapper_session` factory.

## Example of Incorrect vs. Correct Usage:

**Incorrect (causes AttributeError):**
```python
async with self.metamapper_session() as session:
    # ... database operations ...
```

**Correct:**
```python
async with self.async_metamapper_session() as session:
    # ... database operations ...
```

## Expected Output:
Provide the fully modified `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` file with all necessary corrections.
```
