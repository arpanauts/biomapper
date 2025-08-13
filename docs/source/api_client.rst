Python Client Reference
=======================

The ``biomapper_client`` package provides a convenient Python interface to the BioMapper REST API.

Installation
------------

The client can be installed as a standalone package or with the main BioMapper installation:

.. code-block:: bash

    # Standalone client installation
    cd biomapper_client
    poetry install
    
    # Or as part of main BioMapper with API
    poetry install --with api,dev

Basic Usage
-----------

.. code-block:: python

    from biomapper_client import BiomapperClient
    
    # Simple synchronous usage (recommended)
    client = BiomapperClient("http://localhost:8000")
    result = client.run("protein_mapping_template", parameters={
        "input_file": "/data/proteins.csv",
        "output_dir": "/results"
    })
    print(f"Status: {result['status']}")
    
    # Async usage for advanced scenarios
    import asyncio
    
    async def main():
        async with BiomapperClient() as client:
            context = {
                "current_identifiers": [],
                "datasets": {},
                "statistics": {},
                "output_files": []
            }
            result = await client.execute_strategy_async("protein_mapping_template", context)
            print(result)
    
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
* ``dict``: Strategy execution results

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

execute_strategy_async(strategy, context=None, parameters=None)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Asynchronous method** for advanced users who need full control or concurrent execution.

**Parameters:**
* ``strategy_name`` (str): Name of the strategy to execute
* ``context`` (dict): Execution context with datasets, identifiers, etc.

**Returns:**
* ``dict``: Strategy execution results

.. code-block:: python

    async with BiomapperClient() as client:
        context = {
            "current_identifiers": [],
            "datasets": {"input_data": [...]},
            "statistics": {},
            "output_files": [],
            "metadata": {"source": "experiment_001"}
        }
        result = await client.execute_strategy("protein_harmonization", context)

Error Handling
--------------

The client provides custom exceptions for different error scenarios:

.. code-block:: python

    from biomapper_client import BiomapperClient
    from biomapper_client.exceptions import ApiError, NetworkError, ValidationError
    
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
                result = await client.execute_strategy_async("protein_mapping_template", context)
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
        print(f"Completed with status: {results[strategy_name]['status']}")
    
    # Process results
    for name, result in results.items():
        if result['status'] == 'success':
            print(f"{name}: Processed {len(result['results']['datasets'])} datasets")

Using with Jupyter Notebooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # In Jupyter notebooks, use the synchronous interface
    from biomapper_client import BiomapperClient
    
    client = BiomapperClient()
    
    # Run with progress display (great for notebooks)
    result = client.run("metabolite_mapping_template", 
                       parameters={"threshold": 0.95},
                       watch=True)
    
    # Access results
    if result['status'] == 'success':
        datasets = result['results']['datasets']
        stats = result['results'].get('statistics', {})
        print(f"Processed {stats.get('total_records', 0)} records")

Response Format
---------------

The ``run()`` method returns a dictionary with execution results:

.. code-block:: python

    {
        "status": "success",           # "success" or "error"
        "results": {                   # Strategy execution results
            "datasets": {              # Named datasets from the workflow
                "proteins": [...],
                "normalized": [...],
                "harmonized": [...] 
            },
            "statistics": {            # Accumulated statistics
                "total_records": 1000,
                "processing_time": 45.2,
                "success_rate": 0.98
            },
            "output_files": [          # Generated files
                "/results/harmonized.csv",
                "/results/report.html"
            ]
        },
        "execution_time": 45.2         # Total execution time in seconds
    }

For error responses:

.. code-block:: python

    {
        "status": "error",
        "detail": "Strategy 'unknown_strategy' not found",
        "error_type": "StrategyNotFoundError",
        "traceback": "..."            # Stack trace for debugging
    }

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
       if result["status"] == "success":
           datasets = result["results"]["datasets"]
           # Process datasets
       else:
           print(f"Strategy failed: {result.get('detail')}")

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
  Check that the strategy exists in ``configs/strategies/`` or its subdirectories:
  
  .. code-block:: bash
  
      find configs/strategies -name "*.yaml" -type f

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
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper_client/biomapper_client/client_v2.py`` (BiomapperClient implementation)
- ``biomapper_client/biomapper_client/exceptions.py`` (Exception definitions)
- ``biomapper_client/biomapper_client/models.py`` (Data models)
- ``biomapper-api/app/main.py`` (API server endpoints)
- ``configs/strategies/templates/*.yaml`` (Strategy templates)
- ``README.md`` (Installation instructions)
- ``pyproject.toml`` (Package dependencies)