REST API Reference
==================

Biomapper provides a FastAPI-based REST API for executing strategies remotely.

Base URL
--------

When running locally: ``http://localhost:8000``

Authentication
--------------

Currently no authentication is required for local development.

Endpoints
---------

Execute Strategy
~~~~~~~~~~~~~~~~

Execute a YAML strategy file.

**POST** ``/strategies/execute``

Request Body:
  * ``strategy`` (string): YAML strategy content

Response:
  * ``status`` (string): "success" or "error"  
  * ``results`` (object): Strategy execution results
  * ``execution_time`` (float): Total execution time in seconds

Example:

.. code-block:: http

    POST /strategies/execute
    Content-Type: application/json
    
    {
        "strategy": "name: TEST\ndescription: Test strategy\nsteps: []"
    }

.. code-block:: json

    {
        "status": "success",
        "results": {
            "datasets": {},
            "metadata": {}
        },
        "execution_time": 0.1
    }

Health Check
~~~~~~~~~~~~

Check API server status.

**GET** ``/health``

Response:
  * ``status`` (string): "healthy"
  * ``timestamp`` (string): Current server time

.. code-block:: http

    GET /health

.. code-block:: json

    {
        "status": "healthy", 
        "timestamp": "2025-07-22T10:30:00Z"
    }

Python Client
-------------

Use the ``biomapper_client`` package for convenient API access:

.. code-block:: python

    from biomapper_client import BiomapperClient
    
    async with BiomapperClient("http://localhost:8000") as client:
        result = await client.execute_strategy_file("strategy.yaml")

Error Handling
--------------

The API returns standard HTTP status codes:

* **200**: Success
* **400**: Bad Request (invalid strategy YAML)
* **500**: Internal Server Error

Error responses include:

.. code-block:: json

    {
        "status": "error",
        "message": "Detailed error description",
        "error_type": "ValidationError"
    }

Interactive Documentation
-------------------------

FastAPI provides interactive API documentation at:

* Swagger UI: ``http://localhost:8000/docs``
* ReDoc: ``http://localhost:8000/redoc``