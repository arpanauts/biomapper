BiomapperClient API Reference
==============================

The ``BiomapperClient`` class provides the main interface for interacting with the BioMapper API. It supports both synchronous and asynchronous operation modes.

.. class:: BiomapperClient(base_url="http://localhost:8000", api_key=None, timeout=300, auto_retry=True, max_retries=3)

   Enhanced Biomapper API client for strategy execution.
   
   :param base_url: Base URL of the BioMapper API server
   :type base_url: str
   :param api_key: Optional API key for authentication
   :type api_key: str
   :param timeout: Request timeout in seconds (default: 300)
   :type timeout: int
   :param auto_retry: Whether to automatically retry failed requests
   :type auto_retry: bool
   :param max_retries: Maximum number of retries
   :type max_retries: int

   **Example:**
   
   .. code-block:: python
   
       from biomapper_client import BiomapperClient
       
       # Create client instance
       client = BiomapperClient("http://localhost:8000")
       
       # Execute a strategy
       result = client.run("protein_harmonization")

Synchronous Methods
-------------------

.. method:: run(strategy_name, parameters=None, options=None, watch=False)

   Execute a strategy synchronously (recommended for most users).
   
   :param strategy_name: Name of the strategy to execute
   :type strategy_name: str
   :param parameters: Optional parameter overrides
   :type parameters: dict
   :param options: Execution options (checkpoint_enabled, timeout_seconds, etc.)
   :type options: dict
   :param watch: Display real-time progress (default: False)
   :type watch: bool
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

.. method:: async execute_strategy(strategy_name, parameters=None, options=None)

   Execute a strategy asynchronously.
   
   :param strategy_name: Name of the strategy to execute or inline strategy dict
   :type strategy_name: Union[str, dict]
   :param parameters: Optional parameter overrides
   :type parameters: dict
   :param options: Execution options
   :type options: ExecutionOptions
   :returns: Job object with execution details
   :rtype: Job

.. method:: async wait_for_job(job_id, poll_interval=1.0)

   Wait for a job to complete.
   
   :param job_id: Job identifier
   :type job_id: str
   :param poll_interval: Seconds between status checks
   :type poll_interval: float
   :returns: Final job result
   :rtype: StrategyResult
   
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

.. class:: ApiError

   Raised when the API returns a non-success status code.

.. class:: NetworkError

   Raised for network-related issues (connection, timeout).

.. class:: ValidationError

   Raised when request validation fails.

.. class:: StrategyNotFoundError

   Raised when a requested strategy doesn't exist.

.. class:: JobNotFoundError

   Raised when a job ID is not found.

.. class:: TimeoutError

   Raised when operation exceeds timeout.

.. class:: FileUploadError

   Raised when file upload fails.

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
     - API key for authentication
   * - ``BIOMAPPER_TIMEOUT``
     - Request timeout in seconds
   * - ``BIOMAPPER_MAX_RETRIES``
     - Maximum retry attempts
   * - ``BIOMAPPER_AUTO_RETRY``
     - Enable/disable auto-retry (true/false)

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
- Dependencies: httpx, pydantic 2.11+

See Also
--------

- :doc:`rest_endpoints` - REST API endpoint reference
- :doc:`strategy_execution` - Strategy execution details
- :doc:`index` - API overview and quick start

---

Verification Sources
~~~~~~~~~~~~~~~~~~~~
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper_client/biomapper_client/client_v2.py`` (BiomapperClient implementation)
- ``biomapper_client/biomapper_client/models.py`` (Client data models)
- ``biomapper_client/biomapper_client/exceptions.py`` (Exception classes)
- ``biomapper_client/biomapper_client/progress.py`` (Progress tracking)
- ``biomapper_client/pyproject.toml`` (Client dependencies and version)
- ``biomapper-api/app/models/strategy_execution.py`` (API response models)
- ``CLAUDE.md`` (Client usage patterns)