API Reference
=============

BioMapper provides a REST API for workflow execution. The API uses standard JSON for request/response bodies, but strategies themselves are defined in YAML format.

.. toctree::
   :maxdepth: 2
   :caption: API Documentation
   
   rest_endpoints
   strategy_execution
   client_reference

Quick Start
-----------

**Start the API Server:**

.. code-block:: bash

   cd biomapper-api
   poetry run uvicorn app.main:app --reload --port 8000

**Access API Documentation:**

* Interactive docs: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc
* OpenAPI schema: http://localhost:8000/openapi.json

Core Endpoints
--------------

Health Check
~~~~~~~~~~~~

.. code-block:: bash

   GET /health
   
   # Response
   {
     "status": "healthy",
     "version": "0.5.2",
     "timestamp": "2024-08-13T10:00:00Z"
   }

Execute Strategy
~~~~~~~~~~~~~~~~

**How it works:**
- The REST API uses JSON for HTTP request/response bodies (standard for REST APIs)
- Strategies are defined in YAML format (stored as files or embedded in JSON)
- The API can either reference pre-defined YAML files or accept YAML content

.. code-block:: bash

   POST /api/v2/strategies/execute
   Content-Type: application/json
   
   # Option 1: Execute pre-defined YAML strategy by name
   {
     "strategy_name": "protein_harmonization",  # References a .yaml file
     "parameters": {
       "input_file": "/data/proteins.csv",
       "output_dir": "/results"
     }
   }
   
   # Option 2: Submit YAML strategy content directly (as a string in JSON)
   {
     "strategy_yaml": "name: custom_workflow\nsteps:\n  - action:\n      type: LOAD_DATASET_IDENTIFIERS\n      params:\n        file_path: /data/input.csv",
     "parameters": {}
   }
   
   # Response
   {
     "job_id": "job_123",
     "status": "running",
     "created_at": "2024-08-13T10:00:00Z"
   }

Get Job Status
~~~~~~~~~~~~~~

.. code-block:: bash

   GET /api/v2/jobs/{job_id}
   
   # Response
   {
     "job_id": "job_123",
     "status": "completed",
     "progress": 100,
     "result": {
       "success": true,
       "datasets": {...},
       "statistics": {...}
     }
   }

Python Client Usage
-------------------

Synchronous
~~~~~~~~~~~

.. code-block:: python

   from biomapper_client import BiomapperClient
   
   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Execute strategy
   result = client.run("protein_harmonization", parameters={
       "input_file": "/data/proteins.csv",
       "output_dir": "/results"
   })
   
   print(f"Success: {result['success']}")
   print(f"Records processed: {result['statistics']['total_records']}")

Asynchronous
~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from biomapper_client import BiomapperClient
   
   async def run_strategy():
       async with BiomapperClient() as client:
           # Execute with progress tracking
           async for event in client.execute_with_progress(
               "protein_harmonization",
               parameters={"input_file": "/data/proteins.csv"}
           ):
               print(f"Progress: {event['progress']}%")
           
           return event['result']
   
   result = asyncio.run(run_strategy())

Authentication
--------------

Currently, BioMapper API does not require authentication for local deployments. For production deployments, consider implementing:

* API key authentication
* OAuth2 with JWT tokens
* Basic authentication with HTTPS

Rate Limiting
-------------

Default rate limits:

* 100 requests per minute per IP
* 10 concurrent strategy executions
* 1GB maximum file upload size

Error Handling
--------------

The API returns standard HTTP status codes:

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
     - Bad request (invalid parameters)
   * - 404
     - Resource not found
   * - 422
     - Validation error
   * - 500
     - Internal server error

Error Response Format:

.. code-block:: json

   {
     "detail": "Validation error in strategy parameters",
     "errors": [
       {
         "field": "input_file",
         "message": "File not found: /data/missing.csv"
       }
     ]
   }

WebSocket Support
-----------------

Real-time progress updates via Server-Sent Events (SSE):

.. code-block:: python

   import requests
   
   response = requests.get(
       f"http://localhost:8000/api/v2/jobs/{job_id}/stream",
       stream=True
   )
   
   for line in response.iter_lines():
       if line:
           event = json.loads(line.decode('utf-8'))
           print(f"Progress: {event['progress']}%")