Strategy Execution API
======================

Details on how strategies are executed through the REST API.

Execution Flow
--------------

1. **YAML Parsing**: Strategy file is parsed and validated
2. **Action Loading**: Required actions are loaded from registry
3. **Context Creation**: Empty context dictionary is created
4. **Sequential Execution**: Steps are executed in order
5. **Result Collection**: Final context and metadata are returned

Timing Metrics
--------------

The API automatically tracks timing information:

* Per-action execution time
* Total strategy execution time
* UniProt resolution timing (where applicable)
* Data processing timing

Error Handling
--------------

**Validation Errors**
  YAML syntax errors and parameter validation failures.

**Execution Errors**
  Runtime errors during action execution with full context.

**Timeout Handling**
  Long-running strategies with appropriate timeout settings.

**Recovery Options**
  Partial results available even if some steps fail.

Monitoring
----------

**Logging**
  Detailed execution logs available on API server.

**Progress Tracking**
  Step-by-step progress information in server logs.

**Resource Usage**
  Memory and CPU usage monitoring for large datasets.

Scalability
-----------

**Large Datasets**
  Efficient handling of datasets with 100K+ rows.

**Concurrent Execution**
  Multiple strategies can execute simultaneously.

**Memory Management**
  Automatic memory cleanup after execution.

Future Enhancements
-------------------

* Real-time progress updates via WebSocket
* Strategy execution queuing system  
* Distributed execution across multiple workers
* Enhanced monitoring and alerting