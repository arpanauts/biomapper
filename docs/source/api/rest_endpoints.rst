REST API Reference
==================

BioMapper provides a FastAPI-based REST API for strategy execution and job management.

Base URL
--------

Default: ``http://localhost:8000``

When running the API server:

.. code-block:: bash

   cd biomapper-api
   poetry run uvicorn app.main:app --reload --port 8000

Interactive Documentation
-------------------------

FastAPI automatically generates interactive API documentation:

* **Swagger UI**: http://localhost:8000/docs (recommended)
* **ReDoc**: http://localhost:8000/redoc
* **OpenAPI Schema**: http://localhost:8000/openapi.json

Authentication
--------------

Currently no authentication is required for local development. Production deployments should implement authentication.

Core Endpoints
--------------

Health Check
~~~~~~~~~~~~

Check if the API server is running.

.. code-block:: http

   GET /
   
   Response:
   {
     "message": "BioMapper API is running",
     "version": "0.5.2"
   }

Strategy Execution (v2)
~~~~~~~~~~~~~~~~~~~~~~~

Execute a strategy by name or with inline YAML.

.. code-block:: http

   POST /api/strategies/v2/execute
   Content-Type: application/json
   
   # Option 1: Execute by strategy name
   {
     "strategy": "protein_harmonization",
     "parameters": {
       "input_file": "/data/proteins.csv",
       "output_dir": "/results"
     },
     "options": {
       "checkpoint_enabled": false,
       "timeout_seconds": 3600
     }
   }
   
   # Option 2: Execute inline strategy (as dict)
   {
     "strategy": {
       "name": "custom_workflow",
       "steps": [
         {
           "name": "load_data",
           "action": {
             "type": "LOAD_DATASET_IDENTIFIERS",
             "params": {
               "file_path": "/data/input.csv",
               "output_key": "data"
             }
           }
         }
       ]
     },
     "parameters": {}
   }
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "running",
     "message": "Strategy execution started"
   }

Job Management Endpoints
------------------------

Get Job Status
~~~~~~~~~~~~~~

.. code-block:: http

   GET /api/jobs/{job_id}/status
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "running",
     "progress": 45,
     "current_step": "normalizing_proteins",
     "total_steps": 5,
     "started_at": "2024-08-13T10:00:00Z"
   }

Get Job Results
~~~~~~~~~~~~~~~

.. code-block:: http

   GET /api/jobs/{job_id}/results
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "completed",
     "success": true,
     "results": {
       "datasets": {
         "proteins": [...],
         "normalized": [...]
       },
       "statistics": {
         "total_processed": 1000,
         "execution_time": 45.2
       },
       "output_files": [
         "/results/harmonized.csv"
       ]
     },
     "completed_at": "2024-08-13T10:01:00Z"
   }

List All Jobs
~~~~~~~~~~~~~

.. code-block:: http

   GET /api/jobs/
   
   Response:
   [
     {
       "job_id": "550e8400-e29b-41d4-a716-446655440000",
       "status": "completed",
       "strategy_name": "protein_harmonization",
       "created_at": "2024-08-13T10:00:00Z"
     },
     ...
   ]

Get Job Logs
~~~~~~~~~~~~

.. code-block:: http

   GET /api/jobs/{job_id}/logs
   
   Response:
   {
     "logs": [
       {
         "timestamp": "2024-08-13T10:00:00Z",
         "level": "INFO",
         "message": "Starting strategy execution"
       },
       {
         "timestamp": "2024-08-13T10:00:01Z",
         "level": "INFO",
         "message": "Loading dataset from /data/proteins.csv"
       }
     ]
   }

Cancel Job
~~~~~~~~~~

.. code-block:: http

   POST /api/jobs/{job_id}/cancel
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "cancelled",
     "message": "Job cancelled successfully"
   }

Pause Job
~~~~~~~~~

.. code-block:: http

   POST /api/jobs/{job_id}/pause
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "paused",
     "message": "Job paused successfully"
   }

Resume Job
~~~~~~~~~~

.. code-block:: http

   POST /api/jobs/{job_id}/resume
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "running",
     "message": "Job resumed successfully"
   }

Checkpoint Management
---------------------

List Checkpoints
~~~~~~~~~~~~~~~~

.. code-block:: http

   GET /api/jobs/{job_id}/checkpoints
   
   Response:
   [
     {
       "checkpoint_id": "checkpoint_1",
       "created_at": "2024-08-13T10:00:30Z",
       "step_name": "after_normalization",
       "context_size": 1048576
     }
   ]

Restore from Checkpoint
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: http

   POST /api/jobs/{job_id}/restore/{checkpoint_id}
   
   Response:
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "running",
     "message": "Restored from checkpoint and resumed execution"
   }

Resource Management
-------------------

Get Resource Status
~~~~~~~~~~~~~~~~~~~

.. code-block:: http

   GET /resources/status
   
   Response:
   {
     "qdrant": {
       "status": "running",
       "version": "1.9.0",
       "collections": ["metabolites", "proteins"]
     },
     "cache": {
       "status": "running",
       "entries": 1234,
       "size_mb": 45.6
     }
   }

Error Responses
---------------

The API returns standard HTTP status codes with detailed error messages:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status Code
     - Description
   * - 200
     - Success
   * - 201
     - Created (job submitted)
   * - 400
     - Bad Request (invalid parameters)
   * - 404
     - Not Found (job or strategy not found)
   * - 422
     - Validation Error (invalid strategy format)
   * - 500
     - Internal Server Error

Error Response Format:

.. code-block:: json

   {
     "detail": "Strategy 'unknown_strategy' not found",
     "error_type": "StrategyNotFoundError",
     "status_code": 404,
     "timestamp": "2024-08-13T10:00:00Z"
   }

Validation Error Format:

.. code-block:: json

   {
     "detail": [
       {
         "loc": ["body", "parameters", "input_file"],
         "msg": "field required",
         "type": "value_error.missing"
       }
     ]
   }

Rate Limiting
-------------

Default limits (configurable):

* 100 requests per minute per IP
* 10 concurrent strategy executions
* 1GB maximum request body size

WebSocket/SSE Support
---------------------

For real-time progress updates, the API supports Server-Sent Events:

.. code-block:: python

   import requests
   
   # Stream job progress
   response = requests.get(
       f"http://localhost:8000/api/jobs/{job_id}/stream",
       stream=True
   )
   
   for line in response.iter_lines():
       if line:
           event = json.loads(line)
           print(f"Progress: {event['progress']}%")

Python Client Usage
-------------------

The ``biomapper_client`` package provides a convenient Python interface:

.. code-block:: python

   from biomapper_client import BiomapperClient
   
   # Synchronous usage
   client = BiomapperClient(base_url="http://localhost:8000")
   result = client.run("protein_harmonization", parameters={
       "input_file": "/data/proteins.csv"
   })
   
   # Async usage
   async with BiomapperClient() as client:
       job = await client.execute_strategy("protein_harmonization")
       result = await client.wait_for_job(job.id)

See :doc:`../api_client` for detailed client documentation.