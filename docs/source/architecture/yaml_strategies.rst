YAML Strategy System
===================

The strategy system is the core of Biomapper's configuration-driven approach.

Strategy Structure
------------------

Every strategy follows this pattern:

.. code-block:: yaml

    name: "STRATEGY_NAME"
    description: "What this strategy accomplishes"
    
    steps:
      - name: step_identifier
        action:
          type: ACTION_TYPE
          params:
            param1: value1
            param2: value2

Execution Model
---------------

**Sequential Processing**
  Steps execute in the order defined in the YAML file.

**Shared Context**
  A dictionary object is passed between all steps, allowing data sharing.

**Key-Value Storage**
  Each action stores its results using an ``output_key`` parameter.

**Metadata Tracking**
  Execution statistics and timing information is automatically collected.

Strategy Examples
-----------------

See the :doc:`../configuration` guide for complete examples and best practices.

Loading Strategies
------------------

The MinimalStrategyService loads strategies from:

1. **Direct file paths** specified in API calls
2. **YAML string content** passed directly  
3. **Config directories** for batch processing

Integration Points
------------------

**API Endpoints**
  Strategies are executed via ``/strategies/execute``

**Client Libraries**  
  Python client provides convenient strategy execution methods

**CLI Tools**
  Command-line scripts for automated strategy execution

Benefits
--------

* **Version Control**: Strategies are plain text files
* **Reproducibility**: Same YAML produces same results  
* **Collaboration**: Non-programmers can create workflows
* **Testing**: Easy to create test strategies
* **Documentation**: Self-documenting workflow definitions