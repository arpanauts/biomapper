Strategy Execution API
======================

Detailed guide for executing YAML strategies through the BioMapper API.

Overview
--------

BioMapper strategies are YAML-defined workflows that execute as background jobs. The API provides comprehensive job management including execution, monitoring, pausing, and checkpointing. Strategies are executed using the MinimalStrategyService with a shared execution context that flows through all actions.

Strategy Definition
-------------------

Strategies can be executed in two ways:

1. **Pre-defined Strategies**: YAML files stored in ``configs/strategies/``
2. **Inline Strategies**: YAML content submitted directly in the API request

Strategy Structure
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   name: example_strategy
   description: Example workflow for data processing
   
   parameters:
     input_file: "${DATA_DIR}/input.csv"
     output_dir: "${OUTPUT_DIR}"
     threshold: 0.8
   
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "${parameters.input_file}"
           identifier_column: "id"
           output_key: "raw_data"
     
     - name: process_data
       action:
         type: FILTER_DATASET
         params:
           input_key: "raw_data"
           threshold: "${parameters.threshold}"
           output_key: "filtered_data"
     
     - name: export_results
       action:
         type: EXPORT_DATASET_V2
         params:
           input_key: "filtered_data"
           output_file: "${parameters.output_dir}/results.csv"

Execution Workflow
------------------

1. **Submit Strategy**
   
   .. code-block:: python
   
      response = client.post("/api/strategies/v2/execute", json={
          "strategy": "example_strategy",
          "parameters": {
              "input_file": "/data/mydata.csv",
              "threshold": 0.9
          },
          "options": {
              "checkpoint_enabled": false,
              "timeout_seconds": 3600
          }
      })
      job_id = response.json()["job_id"]

2. **Job Creation**
   
   - Unique job ID generated (UUID)
   - Job record created in SQLite database
   - Background task initiated
   - Immediate response with job ID

3. **Strategy Loading**
   
   - YAML file loaded from ``configs/strategies/`` directory and subdirectories
   - Parameters substituted using ParameterResolver (``${parameters.key}``)
   - Environment variables resolved (``${env.VAR}`` or ``${VAR}``)
   - Default values supported (``${parameters.key:-default}``)
   - Strategy validated for required fields (name, steps)

4. **Action Execution**
   
   - Actions executed sequentially by MinimalStrategyService
   - Each action receives shared execution context
   - Context contains: ``datasets``, ``statistics``, ``output_files``, ``current_identifiers``
   - Actions self-register via ``@register_action`` decorator
   - Actions modify context in-place

5. **Progress Tracking**
   
   .. code-block:: python
   
      # Poll for status
      status = client.get(f"/api/jobs/{job_id}/status")
      print(f"Progress: {status.json()['progress']}%")
      
      # Or use SSE for real-time updates
      for event in client.stream(f"/api/jobs/{job_id}/events"):
          print(f"Step: {event['current_step']}")
          print(f"Progress: {event['progress']}%")

6. **Result Retrieval**
   
   .. code-block:: python
   
      results = client.get(f"/api/jobs/{job_id}/results")
      data = results.json()
      
      # Access outputs
      datasets = data["results"]["datasets"]
      statistics = data["results"]["statistics"]
      files = data["results"]["output_files"]

Execution Context
-----------------

The execution context is a shared dictionary passed between actions:

.. code-block:: python

   context = {
       "datasets": {
           "raw_data": [...],        # Named datasets
           "processed": [...],
           "normalized": [...]
       },
       "current_identifiers": [...],  # Active identifier set
       "statistics": {
           "total_records": 1000,
           "processing_time": 45.2,
           "action_metrics": {...}
       },
       "output_files": [
           "/results/output.csv",
           "/results/report.html"
       ],
       "metadata": {
           "strategy_name": "example_strategy",
           "start_time": "2024-08-13T10:00:00Z",
           "parameters": {...}
       }
   }

Parameter Substitution
----------------------

Parameters can be substituted in YAML strategies:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Pattern
     - Description
   * - ``${parameters.key}``
     - Strategy parameters passed at execution
   * - ``${env.VAR_NAME}``
     - Environment variables
   * - ``${VAR_NAME}``
     - Shorthand for environment variables
   * - ``${metadata.field}``
     - Metadata fields (less common)

Example:

.. code-block:: yaml

   params:
     file_path: "${parameters.input_file}"
     output_dir: "${env.OUTPUT_DIR}"
     threshold: "${parameters.threshold:-0.8}"  # Default value

Job Management
--------------

Job States
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - State
     - Description
   * - ``pending``
     - Job created but not started
   * - ``running``
     - Currently executing
   * - ``paused``
     - Execution paused by user
   * - ``completed``
     - Successfully finished
   * - ``failed``
     - Execution failed with error
   * - ``cancelled``
     - Cancelled by user

Job Control
~~~~~~~~~~~

**Pause Execution:**

.. code-block:: python

   client.post(f"/api/jobs/{job_id}/pause")

**Resume Execution:**

.. code-block:: python

   client.post(f"/api/jobs/{job_id}/resume")

**Cancel Job:**

.. code-block:: python

   client.post(f"/api/jobs/{job_id}/cancel")

Checkpointing
-------------

BioMapper supports checkpointing for long-running strategies:

**Enable Checkpointing:**

.. code-block:: python

   response = client.post("/api/strategies/v2/execute", json={
       "strategy": "long_running_strategy",
       "options": {
           "checkpoint_enabled": True,
           "checkpoint_frequency": 5  # Every 5 actions
       }
   })

**List Checkpoints:**

.. code-block:: python

   checkpoints = client.get(f"/api/jobs/{job_id}/checkpoints")

**Restore from Checkpoint:**

.. code-block:: python

   client.post(f"/api/jobs/{job_id}/restore/{checkpoint_id}")

Error Handling
--------------

Strategy Validation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "detail": "Strategy validation failed",
     "errors": [
       {
         "field": "steps[0].action.type",
         "message": "Unknown action type: INVALID_ACTION"
       }
     ]
   }

Execution Errors
~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "job_id": "550e8400-e29b-41d4-a716-446655440000",
     "status": "failed",
     "error": {
       "step": "load_data",
       "action": "LOAD_DATASET_IDENTIFIERS",
       "message": "File not found: /data/missing.csv",
       "traceback": "..."
     }
   }

Recovery Options
~~~~~~~~~~~~~~~~

- Partial results available even if later steps fail
- Checkpoints allow resuming from last successful step
- Failed jobs can be cloned with modified parameters

Performance Considerations
--------------------------

Memory Management
~~~~~~~~~~~~~~~~~

- Large datasets processed in chunks (10,000 rows default)
- Automatic garbage collection between actions
- Context size monitoring to prevent memory overflow

Concurrency
~~~~~~~~~~~

- Multiple strategies can execute simultaneously
- Default limit: 10 concurrent executions
- Job queue for excess requests

Timeouts
~~~~~~~~

.. code-block:: python

   response = client.post("/api/strategies/v2/execute", json={
       "strategy": "example_strategy",
       "options": {
           "timeout_seconds": 3600,  # 1 hour
           "action_timeout": 300      # 5 min per action
       }
   })

Monitoring and Logging
----------------------

Execution Logs
~~~~~~~~~~~~~~

.. code-block:: python

   logs = client.get(f"/api/jobs/{job_id}/logs")
   for entry in logs.json()["logs"]:
       print(f"[{entry['level']}] {entry['message']}")

Metrics
~~~~~~~

.. code-block:: python

   metrics = client.get(f"/api/jobs/{job_id}/metrics")
   print(f"CPU Usage: {metrics.json()['cpu_percent']}%")
   print(f"Memory: {metrics.json()['memory_mb']} MB")
   print(f"Execution Time: {metrics.json()['elapsed_seconds']}s")

Progress Events
~~~~~~~~~~~~~~~

Real-time progress via Server-Sent Events:

.. code-block:: python

   import json
   import requests
   
   # SSE endpoint for streaming updates
   response = requests.get(
       f"http://localhost:8000/api/jobs/{job_id}/events",
       stream=True
   )
   
   for line in response.iter_lines():
       if line:
           event = json.loads(line)
           if event["type"] == "progress":
               print(f"Progress: {event['percentage']}%")
           elif event["type"] == "step_complete":
               print(f"Completed: {event['step_name']}")
   
   # WebSocket endpoint also available:
   # ws://localhost:8000/api/jobs/{job_id}/ws

Best Practices
--------------

1. **Use Checkpointing** for long-running strategies
2. **Set Appropriate Timeouts** to prevent hanging jobs
3. **Monitor Memory Usage** for large datasets
4. **Handle Errors Gracefully** with try-catch in client code
5. **Use Parameter Defaults** in YAML for flexibility
6. **Stream Progress** for better user experience
7. **Clean Up Old Jobs** periodically to save disk space

Example: Complete Workflow
--------------------------

.. code-block:: python

   from biomapper_client import BiomapperClient
   import asyncio
   
   async def run_workflow():
       async with BiomapperClient() as client:
           # Submit strategy
           job = await client.execute_strategy(
               "protein_harmonization",
               parameters={
                   "input_file": "/data/proteins.csv",
                   "output_dir": "/results"
               },
               options={
                   "checkpoint_enabled": True,
                   "timeout_seconds": 3600
               }
           )
           
           # Monitor progress
           async for event in client.stream_progress(job.id):
               print(f"Progress: {event.percentage}%")
               if event.type == "error":
                   print(f"Error: {event.message}")
                   break
           
           # Get results
           result = await client.get_job_results(job.id)
           if result.success:
               print(f"Processed {len(result.datasets['output'])} records")
               print(f"Files created: {result.output_files}")
           
           return result
   
   # Run the workflow
   result = asyncio.run(run_workflow())

---

Verification Sources
~~~~~~~~~~~~~~~~~~~~
*Last verified: 2025-08-16*

This documentation was verified against the following project resources:

- ``/biomapper/biomapper-api/app/api/routes/strategies_v2_simple.py`` (V2 strategy execution endpoints and job handling)
- ``/biomapper/biomapper-api/app/api/routes/jobs.py`` (Job management with persistence and checkpointing)
- ``/biomapper/biomapper-api/app/services/persistent_execution_engine.py`` (Execution engine with checkpoint support)
- ``/biomapper/biomapper/core/minimal_strategy_service.py`` (MinimalStrategyService implementation and YAML loading)
- ``/biomapper/biomapper/core/strategy_actions/registry.py`` (Self-registering action system)
- ``/biomapper/biomapper/core/infrastructure/parameter_resolver.py`` (Parameter substitution logic)
- ``/biomapper/biomapper_client/biomapper_client/client_v2.py`` (Client-side progress tracking and SSE)
- ``/biomapper/CLAUDE.md`` (Strategy execution patterns and architecture)