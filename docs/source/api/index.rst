API Reference
=============

BioMapper provides a comprehensive REST API for biological data harmonization workflow execution. The API uses standard JSON for request/response bodies, with strategies defined in YAML format for human readability and maintainability.

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

* Interactive docs: http://localhost:8000/api/docs
* OpenAPI schema: http://localhost:8000/api/openapi.json
* Root endpoint: http://localhost:8000/

Core Endpoints
--------------

Health Check
~~~~~~~~~~~~

.. code-block:: bash

   GET /api/health
   
   # Response
   {
     "status": "healthy",
     "version": "0.2.0",
     "services": {
       "database": "connected",
       "mapper_service": "initialized",
       "resource_manager": "running"
     }
   }

Execute Strategy
~~~~~~~~~~~~~~~~

**How it works:**
- The REST API uses JSON for HTTP request/response bodies (standard for REST APIs)
- Strategies are defined in YAML format (stored as files or embedded in JSON)
- The API can either reference pre-defined YAML files or accept YAML content

.. code-block:: bash

   POST /api/strategies/v2/execute
   Content-Type: application/json
   
   # Option 1: Execute pre-defined YAML strategy by name
   {
     "strategy": "protein_harmonization",  # References a .yaml file
     "parameters": {
       "input_file": "/data/proteins.csv",
       "output_dir": "/results"
     }
   }
   
   # Option 2: Submit strategy content directly (as a dict in JSON)
   {
     "strategy": {
       "name": "custom_workflow",
       "steps": [
         {
           "action": {
             "type": "LOAD_DATASET_IDENTIFIERS",
             "params": {"file_path": "/data/input.csv"}
           }
         }
       ]
     },
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

   GET /api/jobs/{job_id}/status
   
   # Response
   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "completed",
     "progress": 100,
     "current_step": "export_results",
     "total_steps": 5,
     "started_at": "2024-08-13T10:00:00Z",
     "completed_at": "2024-08-13T10:01:00Z"
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
   
   print(f"Success: {result.success}")
   print(f"Records processed: {result.results['statistics']['total_records']}")

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

Currently, BioMapper API does not require authentication for local deployments. The API supports optional API key authentication through the ``BIOMAPPER_API_KEY`` environment variable. For production deployments, consider implementing:

* API key authentication (partially supported)
* OAuth2 with JWT tokens (future)
* Basic authentication with HTTPS (future)

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

Real-time Updates Support
-------------------------

Progress updates via Server-Sent Events (SSE) and WebSocket connections:

.. code-block:: python

   import requests
   import json
   
   # SSE endpoint for real-time progress
   response = requests.get(
       f"http://localhost:8000/api/jobs/{job_id}/events",
       stream=True
   )
   
   for line in response.iter_lines():
       if line:
           event = json.loads(line.decode('utf-8'))
           print(f"Progress: {event['progress']}%")
           print(f"Current step: {event.get('current_step', 'N/A')}")

---

Verification Sources
~~~~~~~~~~~~~~~~~~~~
*Last verified: 2025-08-16*

This documentation was verified against the following project resources:

- ``/biomapper/biomapper-api/app/main.py`` (API initialization, routers, and startup events)
- ``/biomapper/biomapper-api/app/api/routes/strategies_v2_simple.py`` (V2 strategy execution endpoint implementation)
- ``/biomapper/biomapper-api/app/api/routes/jobs.py`` (Job management and persistence endpoints)
- ``/biomapper/biomapper-api/app/api/routes/health.py`` (Health check endpoint)
- ``/biomapper/biomapper-api/pyproject.toml`` (API dependencies and version)
- ``/biomapper/biomapper_client/biomapper_client/client_v2.py`` (BiomapperClient implementation)
- ``/biomapper/CLAUDE.md`` (Project conventions, commands, and architecture)