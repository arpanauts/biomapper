BiomapperClient API Reference
==============================

The ``BiomapperClient`` class provides the main interface for interacting with the BioMapper API.

.. class:: BiomapperClient(base_url="http://localhost:8000")

   Main client for BioMapper API interaction.
   
   :param base_url: Base URL of the BioMapper API server
   :type base_url: str

   **Example:**
   
   .. code-block:: python
   
       from biomapper_client import BiomapperClient
       
       # Create client instance
       client = BiomapperClient("http://localhost:8000")
       
       # Execute a strategy
       result = client.run("protein_harmonization")

Synchronous Methods
-------------------

.. method:: run(strategy_name, parameters=None, wait=True)

   Execute a strategy synchronously (recommended for most users).
   
   :param strategy_name: Name of the strategy to execute
   :type strategy_name: str
   :param parameters: Optional parameter overrides
   :type parameters: dict
   :param wait: Wait for completion (default: True)
   :type wait: bool
   :returns: Strategy execution results
   :rtype: dict
   
   **Example:**
   
   .. code-block:: python
   
       result = client.run("metabolomics_baseline", parameters={
           "input_file": "/data/metabolites.csv",
           "threshold": 0.95
       })

Asynchronous Methods
--------------------

.. method:: async execute_strategy(strategy_name, context)

   Execute a strategy asynchronously with full context control.
   
   :param strategy_name: Name of the strategy to execute
   :type strategy_name: str
   :param context: Execution context dictionary
   :type context: dict
   :returns: Strategy execution results
   :rtype: dict
   
   **Required context structure:**
   
   .. code-block:: python
   
       context = {
           "current_identifiers": [],     # List of active identifiers
           "datasets": {},                 # Named datasets
           "statistics": {},               # Accumulated statistics
           "output_files": [],            # Generated file paths
           "metadata": {}                 # Optional metadata
       }
   
   **Example:**
   
   .. code-block:: python
   
       import asyncio
       
       async def run_strategy():
           async with BiomapperClient() as client:
               context = {
                   "current_identifiers": [],
                   "datasets": {"input": [...]},
                   "statistics": {},
                   "output_files": []
               }
               result = await client.execute_strategy("protein_harmonization", context)
               return result
       
       result = asyncio.run(run_strategy())

Context Manager Support
-----------------------

The client supports both synchronous and asynchronous context managers:

**Asynchronous Context Manager:**

.. code-block:: python

   async with BiomapperClient() as client:
       result = await client.execute_strategy("strategy_name", context)

**Synchronous Usage (no context manager needed):**

.. code-block:: python

   client = BiomapperClient()
   result = client.run("strategy_name")

Exception Classes
-----------------

.. class:: ApiError(status_code, message, response_body=None)

   Raised when the API returns a non-200 status code.
   
   :param status_code: HTTP status code
   :type status_code: int
   :param message: Error message
   :type message: str
   :param response_body: Optional response body
   :type response_body: Any

.. class:: NetworkError(message)

   Raised for network-related issues (connection, timeout).
   
   :param message: Error description
   :type message: str

.. class:: BiomapperClientError(message)

   Base exception for all client errors.
   
   :param message: Error description
   :type message: str

Utility Functions
-----------------

The ``biomapper_client`` package also provides utility functions for CLI usage:

.. function:: run_strategy(strategy_path, output_dir=None, verbose=False)

   Execute a strategy from the command line.
   
   :param strategy_path: Path to strategy YAML file
   :type strategy_path: str
   :param output_dir: Optional output directory
   :type output_dir: str
   :param verbose: Enable verbose output
   :type verbose: bool
   :returns: Execution results
   :rtype: dict

.. function:: parse_parameters(param_strings)

   Parse command-line parameter strings into a dictionary.
   
   :param param_strings: List of "key=value" strings
   :type param_strings: list
   :returns: Parameter dictionary
   :rtype: dict
   
   **Example:**
   
   .. code-block:: python
   
       params = parse_parameters([
           "input_file=/data/proteins.csv",
           "threshold=0.95",
           "output_dir=/results"
       ])
       # Returns: {"input_file": "/data/proteins.csv", "threshold": 0.95, "output_dir": "/results"}

Response Schemas
----------------

**Successful Response:**

.. code-block:: python

   {
       "status": "success",
       "results": {
           "datasets": {
               "dataset_name": [...]  # Named datasets from workflow
           },
           "statistics": {
               "total_records": int,
               "processing_time": float,
               # Additional action-specific statistics
           },
           "output_files": [
               # List of generated file paths
           ],
           "metadata": {
               # Strategy metadata and parameters
           }
       },
       "execution_time": float  # Total execution time in seconds
   }

**Error Response:**

.. code-block:: python

   {
       "status": "error",
       "detail": "Error message",
       "error_type": "ErrorClassName",
       "traceback": "..."  # Optional stack trace
   }

Configuration
-------------

The client can be configured through environment variables:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Environment Variable
     - Description
   * - ``BIOMAPPER_API_URL``
     - Override default API URL
   * - ``BIOMAPPER_API_KEY``
     - API key for authentication (future)
   * - ``BIOMAPPER_TIMEOUT``
     - Request timeout in seconds

Thread Safety
-------------

- The synchronous ``run()`` method is thread-safe
- The async client should use separate instances per thread
- Context managers handle resource cleanup automatically

Performance Considerations
--------------------------

- Default timeout: 3 hours (for large datasets)
- Automatic retry on network errors (configurable)
- Connection pooling for multiple requests
- Chunked uploads for large files (>10MB)

Version Compatibility
---------------------

- Client version: 0.1.0
- Compatible API versions: 0.5.0+
- Python: 3.9+

See Also
--------

- :doc:`../api_client` - User guide for the Python client
- :doc:`rest_endpoints` - REST API endpoint reference
- :doc:`strategy_execution` - Strategy execution details