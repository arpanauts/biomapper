API Reference
=============

BioMapper provides a comprehensive REST API for strategy execution and job management.

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

.. code-block:: bash

   POST /api/v2/strategies/execute
   
   # Request Body
   {
     "strategy_name": "protein_harmonization",
     "parameters": {
       "input_file": "/data/proteins.csv",
       "output_dir": "/results"
     }
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