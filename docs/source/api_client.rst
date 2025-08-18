Python Client Reference
=======================

The ``client`` module provides a convenient Python interface to the BioMapper REST API.

Installation
------------

The client can be installed as a standalone package or with the main BioMapper installation:

.. code-block:: bash

    # Install as part of main BioMapper package
    poetry install --with dev,docs,api
    poetry shell

Basic Usage
-----------

.. code-block:: python

    from client.client_v2 import BiomapperClient
    
    # Simple synchronous usage (recommended)
    client = BiomapperClient("http://localhost:8000")
    result = client.run("protein_mapping_template", parameters={
        "input_file": "/data/proteins.csv",
        "output_dir": "/results"
    })
    print(f"Success: {result.success}")  # StrategyResult object
    
    # Async usage for advanced scenarios
    import asyncio
    
    async def main():
        async with BiomapperClient() as client:
            result = await client.execute_strategy(
                "protein_mapping_template", 
                parameters={"input_file": "/data/proteins.csv"}
            )
            print(f"Success: {result.success}")
    
    asyncio.run(main())

Client Configuration
--------------------

The client automatically configures itself with sensible defaults:

.. code-block:: python

    client = BiomapperClient(
        base_url="http://localhost:8000",  # API server URL (default)
        timeout=300,                       # Default timeout in seconds (5 minutes)
        auto_retry=True,                   # Automatic retry on failures
        max_retries=3                      # Maximum retry attempts
    )
    
    # The client handles both sync and async usage
    # Sync: client.run("strategy_name") 
    # Async: await client.execute_strategy("strategy_name", context)

Core Methods
------------

run(strategy, parameters=None, context=None, wait=True, watch=False)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Synchronous method** for simple strategy execution. This is the recommended method for most users.

**Parameters:**
* ``strategy`` (str|Path|dict): Strategy name, path to YAML file, or dict configuration
* ``parameters`` (dict): Optional parameter overrides for the strategy
* ``context`` (dict): Optional execution context
* ``wait`` (bool): If True, wait for completion (default)
* ``watch`` (bool): If True, print progress to stdout

**Returns:**
* ``StrategyResult``: Strategy execution results object with success, data, error attributes

.. code-block:: python

    # Simple execution with strategy name
    result = client.run("protein_mapping_template")
    
    # With parameters
    result = client.run("metabolite_mapping_template", parameters={
        "input_file": "/data/metabolites.csv",
        "threshold": 0.9
    })
    
    # With path to custom YAML
    result = client.run("/path/to/custom_strategy.yaml")
    
    # With progress display
    result = client.run("chemistry_mapping_template", watch=True)

execute_strategy(strategy, parameters=None, context=None, options=None)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Asynchronous method** for advanced users who need full control or concurrent execution.

**Parameters:**
* ``strategy`` (str|Path|dict): Strategy name, path to YAML file, or dict configuration
* ``parameters`` (dict): Optional parameter overrides
* ``context`` (dict): Optional execution context
* ``options`` (ExecutionOptions): Optional execution options

**Returns:**
* ``Job``: Job object for tracking execution

.. code-block:: python

    async with BiomapperClient() as client:
        job = await client.execute_strategy(
            "protein_harmonization",
            parameters={"input_file": "/data/proteins.csv"}
        )
        result = await client.wait_for_job(job.id)

Error Handling
--------------

The client provides custom exceptions for different error scenarios:

.. code-block:: python

    from client.client_v2 import BiomapperClient
    from client.exceptions import ApiError, NetworkError, ValidationError
    
    # Synchronous error handling
    try:
        result = client.run("protein_mapping_template")
    except ApiError as e:
        print(f"API error (status {e.status_code}): {e}")
    except NetworkError as e:
        print(f"Network error: {e}")
    
    # Asynchronous error handling
    async def robust_execution():
        try:
            async with BiomapperClient() as client:
                context = {"datasets": {}, "statistics": {}, "output_files": []}
                job = await client.execute_strategy("protein_mapping_template")
                result = await client.wait_for_job(job.id)
                return result
        except ApiError as e:
            if e.status_code == 404:
                print("Strategy not found")
            elif e.status_code == 422:
                print("Validation error:", e.response_body)
            else:
                print(f"API error: {e}")
        except NetworkError as e:
            print(f"Network or timeout error: {e}")

Advanced Usage
--------------

Running Multiple Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Synchronous execution of multiple strategies
    strategies = [
        "protein_mapping_template",
        "metabolite_mapping_template", 
        "chemistry_mapping_template"
    ]
    
    client = BiomapperClient()
    results = {}
    
    for strategy_name in strategies:
        print(f"Running {strategy_name}...")
        results[strategy_name] = client.run(strategy_name)
        print(f"Completed with success: {results[strategy_name].success}")
    
    # Process results
    for name, result in results.items():
        if result.success:
            print(f"{name}: Strategy executed successfully")

Using with Jupyter Notebooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # In Jupyter notebooks, use the synchronous interface
    from client.client_v2 import BiomapperClient
    
    client = BiomapperClient()
    
    # Run with progress display (great for notebooks)
    result = client.run_with_progress("metabolite_mapping_template", 
                                     parameters={"threshold": 0.95})
    
    # Access results
    if result.success:
        print(f"Strategy completed successfully in {result.execution_time_seconds:.1f}s")
        print(f"Job ID: {result.job_id}")
    else:
        print(f"Strategy failed: {result.error}")

Response Format
---------------

The ``run()`` method returns a ``StrategyResult`` object with the following structure:

.. code-block:: python

    # Successful execution
    result = client.run("strategy_name")
    print(result.success)                    # True/False
    print(result.job_id)                     # Job tracking ID
    print(result.execution_time_seconds)     # Execution time
    print(result.result_data)                # Dictionary with execution results
    print(result.error)                      # None for successful runs

For failed executions:

.. code-block:: python

    # Failed execution
    result = client.run("invalid_strategy")
    print(result.success)                    # False
    print(result.error)                      # Error message
    print(result.job_id)                     # Job ID (if created)

Best Practices
--------------

1. **Use the synchronous interface for simplicity**:
   
   .. code-block:: python
   
       # Recommended for most users
       client = BiomapperClient()
       result = client.run("strategy_name")

2. **Only use async when you need concurrency**:
   
   .. code-block:: python
   
       # For advanced users running multiple strategies in parallel
       async with BiomapperClient() as client:
           tasks = [client.execute_strategy_async(name) for name in strategies]
           results = await asyncio.gather(*tasks)

3. **Check execution status before processing results**:
   
   .. code-block:: python
   
       result = client.run("protein_mapping_template")
       if result.success:
           data = result.result_data
           # Process results data
       else:
           print(f"Strategy failed: {result.error}")

4. **Use parameters to override strategy defaults**:
   
   .. code-block:: python
   
       # Override default parameters defined in YAML
       result = client.run("metabolite_mapping_template", parameters={
           "input_file": "/custom/path/data.csv",
           "threshold": 0.95,
           "output_dir": "/custom/output"
       })

Troubleshooting
---------------

**Connection refused**
  Ensure the API server is running:
  
  .. code-block:: bash
  
      cd biomapper-api
      poetry run uvicorn app.main:app --reload --port 8000

**Timeout errors**
  The client has a default timeout of 300 seconds (5 minutes). For large datasets, you can increase it:
  
  .. code-block:: python
  
      client = BiomapperClient(timeout=3600)  # 1 hour timeout

**Strategy not found**
  Check that the strategy exists in ``src/configs/strategies/`` or its subdirectories:
  
  .. code-block:: bash
  
      find src/configs/strategies -name "*.yaml" -type f

**API errors (400/422)**
  These indicate validation errors. Check the error detail for specific parameter issues:
  
  .. code-block:: python
  
      try:
          result = client.run("strategy_name")
      except ApiError as e:
          print(f"Validation error: {e.response_body}")

**Network errors**
  Check your network connection and ensure the API server URL is correct.

---

Verification Sources
--------------------
*Last verified: 2025-08-18*

This documentation was verified against the following project resources:

- ``/biomapper/src/client/client_v2.py`` (BiomapperClient implementation with run() and execute_strategy() methods)
- ``/biomapper/src/client/models.py`` (StrategyResult, Job, and other client data models)
- ``/biomapper/src/client/exceptions.py`` (Custom exception classes for error handling)
- ``/biomapper/pyproject.toml`` (Package dependencies and CLI script configuration)
- ``/biomapper/CLAUDE.md`` (Installation commands and usage patterns)