Python Client Reference
=======================

The ``biomapper_client`` package provides a convenient Python interface to the Biomapper REST API.

Installation
------------

The client is included with the main biomapper installation:

.. code-block:: bash

    poetry install --with api

Basic Usage
-----------

.. code-block:: python

    import asyncio
    from biomapper_client import BiomapperClient
    
    async def main():
        # Connect to local server
        async with BiomapperClient("http://localhost:8000") as client:
            result = await client.execute_strategy_file("strategy.yaml")
            print(result)
    
    asyncio.run(main())

Client Configuration
--------------------

The client accepts several configuration options:

.. code-block:: python

    client = BiomapperClient(
        base_url="http://localhost:8000",  # API server URL
        timeout=10800.0,                   # 3 hour timeout (for large datasets)
    )

Methods
-------

execute_strategy_file(file_path)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute a strategy from a YAML file.

**Parameters:**
* ``file_path`` (str): Path to YAML strategy file

**Returns:**
* ``dict``: Strategy execution results

.. code-block:: python

    result = await client.execute_strategy_file("my_strategy.yaml")

execute_strategy_yaml(yaml_content)  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute a strategy from YAML string content.

**Parameters:**
* ``yaml_content`` (str): YAML strategy as string

**Returns:**
* ``dict``: Strategy execution results

.. code-block:: python

    strategy_yaml = '''
    name: "INLINE_STRATEGY"
    description: "Strategy defined inline"
    steps: []
    '''
    
    result = await client.execute_strategy_yaml(strategy_yaml)

Error Handling
--------------

The client raises exceptions for various error conditions:

.. code-block:: python

    from biomapper_client import BiomapperClient
    import httpx
    
    async def robust_execution():
        try:
            async with BiomapperClient() as client:
                result = await client.execute_strategy_file("strategy.yaml")
                return result
                
        except httpx.TimeoutException:
            print("Strategy execution timed out")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code}")
        except FileNotFoundError:
            print("Strategy file not found")
        except Exception as e:
            print(f"Unexpected error: {e}")

Advanced Usage
--------------

Custom Headers
~~~~~~~~~~~~~~

.. code-block:: python

    # Future feature - authentication headers
    headers = {"Authorization": "Bearer token123"}
    async with BiomapperClient(headers=headers) as client:
        result = await client.execute_strategy_file("strategy.yaml")

Multiple Strategies
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    strategies = [
        "ukbb_hpa_mapping.yaml",
        "arivale_qin_mapping.yaml", 
        "kg2c_spoke_mapping.yaml"
    ]
    
    results = []
    async with BiomapperClient() as client:
        for strategy in strategies:
            result = await client.execute_strategy_file(strategy)
            results.append(result)
            
    # Analyze all results
    for i, result in enumerate(results):
        print(f"Strategy {strategies[i]}: {result['status']}")

Response Format
---------------

All client methods return a dictionary with this structure:

.. code-block:: python

    {
        "status": "success",           # "success" or "error"
        "results": {                   # Strategy execution results
            "datasets": {              # Loaded datasets
                "dataset_name": [...] 
            },
            "metadata": {              # Dataset metadata
                "dataset_name": {...}
            }
        },
        "execution_time": 1.23        # Execution time in seconds
    }

For error responses:

.. code-block:: python

    {
        "status": "error",
        "message": "Detailed error description",
        "error_type": "ValidationError"
    }

Best Practices
--------------

1. **Always use async context manager**:
   
   .. code-block:: python
   
       async with BiomapperClient() as client:
           # Use client here
           pass

2. **Handle timeouts for large datasets**:
   
   .. code-block:: python
   
       client = BiomapperClient(timeout=21600)  # 6 hours

3. **Check execution status**:
   
   .. code-block:: python
   
       result = await client.execute_strategy_file("strategy.yaml")
       if result["status"] != "success":
           print(f"Strategy failed: {result.get('message')}")

4. **Log execution times**:
   
   .. code-block:: python
   
       result = await client.execute_strategy_file("strategy.yaml")
       print(f"Strategy completed in {result['execution_time']:.2f} seconds")

Troubleshooting
---------------

**Connection refused**
  Ensure the API server is running on the specified URL.

**Timeout errors**
  Increase the timeout for large datasets or complex strategies.

**File not found**
  Check that strategy file paths are correct and files exist.

**YAML parsing errors**
  Validate YAML syntax before execution.