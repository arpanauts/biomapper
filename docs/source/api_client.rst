Python Client Reference
=======================

The ``biomapper_client`` package provides a convenient Python interface to the BioMapper REST API.

Installation
------------

The client is included with the main BioMapper installation:

.. code-block:: bash

    poetry install --with api

Basic Usage
-----------

.. code-block:: python

    from biomapper_client import BiomapperClient
    
    # Simple synchronous usage (recommended)
    client = BiomapperClient("http://localhost:8000")
    result = client.run("protein_harmonization", parameters={
        "input_file": "/data/proteins.csv",
        "output_dir": "/results"
    })
    print(f"Success: {result['success']}")
    
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
            result = await client.execute_strategy("protein_harmonization", context)
            print(result)
    
    asyncio.run(main())

Client Configuration
--------------------

The client automatically configures itself with sensible defaults:

.. code-block:: python

    client = BiomapperClient(
        base_url="http://localhost:8000",  # API server URL (default)
        # timeout is automatically set to 3 hours for large datasets
    )
    
    # The client handles both sync and async usage
    # Sync: client.run("strategy_name") 
    # Async: await client.execute_strategy("strategy_name", context)

Core Methods
------------

run(strategy_name, parameters=None, wait=True)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Synchronous method** for simple strategy execution. This is the recommended method for most users.

**Parameters:**
* ``strategy_name`` (str): Name of the strategy to execute
* ``parameters`` (dict): Optional parameter overrides for the strategy
* ``wait`` (bool): If True, wait for completion (default)

**Returns:**
* ``dict``: Strategy execution results

.. code-block:: python

    # Simple execution
    result = client.run("protein_harmonization")
    
    # With parameters
    result = client.run("protein_harmonization", parameters={
        "input_file": "/data/proteins.csv",
        "threshold": 0.9
    })

execute_strategy(strategy_name, context)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Asynchronous method** for advanced users who need full control.

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

    from biomapper_client import BiomapperClient, ApiError, NetworkError
    
    # Synchronous error handling
    try:
        result = client.run("protein_harmonization")
    except ApiError as e:
        print(f"API error (status {e.status_code}): {e}")
    except NetworkError as e:
        print(f"Network error: {e}")
    
    # Asynchronous error handling
    async def robust_execution():
        try:
            async with BiomapperClient() as client:
                context = {"datasets": {}, "statistics": {}, "output_files": []}
                result = await client.execute_strategy("protein_harmonization", context)
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
        "protein_harmonization",
        "metabolomics_baseline", 
        "chemistry_normalization"
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
    result = client.run("metabolomics_harmonization", 
                       parameters={"threshold": 0.95})
    
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
           tasks = [client.execute_strategy(name, context) for name in strategies]
           results = await asyncio.gather(*tasks)

3. **Check execution status before processing results**:
   
   .. code-block:: python
   
       result = client.run("protein_harmonization")
       if result["status"] == "success":
           datasets = result["results"]["datasets"]
           # Process datasets
       else:
           print(f"Strategy failed: {result.get('detail')}")

4. **Use parameters to override strategy defaults**:
   
   .. code-block:: python
   
       # Override default parameters defined in YAML
       result = client.run("metabolomics_baseline", parameters={
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
  The client automatically sets a 3-hour timeout for large datasets. For extremely large datasets (>100K rows), consider breaking into smaller batches.

**Strategy not found**
  Check that the strategy exists in ``configs/strategies/`` or verify the strategy name:
  
  .. code-block:: bash
  
      ls configs/strategies/*.yaml

**API errors (400/422)**
  These indicate validation errors. Check the error detail for specific parameter issues:
  
  .. code-block:: python
  
      try:
          result = client.run("strategy_name")
      except ApiError as e:
          print(f"Validation error: {e.response_body}")

**Network errors**
  Check your network connection and ensure the API server URL is correct.