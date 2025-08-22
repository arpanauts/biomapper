RampDB Integration
==================

Overview
--------

RampDB (Relational Database of Metabolic Pathways) is a comprehensive metabolite database that provides cross-references between multiple metabolomics databases including HMDB, KEGG, ChEBI, PubChem, and others. Biomapper integrates with RampDB through its REST API to enhance metabolite identifier resolution.

The RampDB integration is primarily used in Stage 3 of the progressive metabolomics pipeline via the ``METABOLITE_RAMPDB_BRIDGE`` action, which is implemented as ``RAMPDB_BRIDGE`` in the current codebase.

Key Features
------------

- **Cross-Database Mapping**: Maps identifiers across 15+ metabolite databases
- **Real-Time API Access**: Query RampDB service in real-time
- **Batch Processing**: Optimized batch queries for better performance
- **Comprehensive Coverage**: Access to pathway and reaction information
- **Standardized Outputs**: Consistent identifier formats across databases

Supported Databases
--------------------

Primary Metabolite Databases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Database
     - Description
   * - HMDB
     - Human Metabolome Database - comprehensive human metabolite data
   * - KEGG
     - Kyoto Encyclopedia of Genes and Genomes - metabolic pathways
   * - ChEBI
     - Chemical Entities of Biological Interest - chemical compounds
   * - PubChem
     - PubChem Compound Database - chemical information
   * - BioCyc
     - Metabolic pathway database collection
   * - LIPID MAPS
     - Lipidomics database and tools

Secondary Databases
~~~~~~~~~~~~~~~~~~~

- MetaCyc - Metabolic pathway database
- Reactome - Pathway database
- WikiPathways - Community pathway database
- CAS Registry - Chemical abstracts service
- InChI/InChIKey - International chemical identifier

Setup and Configuration
-----------------------

API Access Setup
~~~~~~~~~~~~~~~~~

1. **API Access Configuration**

   The RampDB client uses the modern RaMP database API for metabolite matching:
   
   .. code-block:: bash
   
      # RampDB integration is available without API key registration
      # The client uses async HTTP requests with rate limiting
      # No manual API key setup required

2. **Configure Rate Limiting (Optional)**

   Set up environment variables for performance tuning:
   
   .. code-block:: bash
   
      # Optional: Configure rate limiting (defaults are built-in)
      export RAMPDB_RATE_LIMIT="5"   # requests per second (default)
      export RAMPDB_TIMEOUT="30"     # seconds (default)
      export RAMPDB_BATCH_SIZE="50" # batch processing size

3. **Install Required Dependencies**

   .. code-block:: bash
   
      # Install all dependencies (includes aiohttp for RampDB client)
      poetry install --with dev,docs,api
      
      # No separate RampDB verification script needed
      # Integration testing handled through biomapper test suite

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a configuration file for RampDB settings:

.. code-block:: yaml

   # config/rampdb_config.yaml
   rampdb:
     api:
       base_url: "https://rampdb.nih.gov/api/v1/"
       timeout: 30
       max_retries: 3
       rate_limit: 60  # requests per minute
       
     databases:
       primary: ["hmdb", "kegg", "chebi", "pubchem"]
       secondary: ["biocyc", "lipidmaps", "metacyc"]
       
     batch_processing:
       default_batch_size: 50
       max_batch_size: 100
       batch_delay: 1.0  # seconds between batches

API Usage Patterns
------------------

Basic Query
~~~~~~~~~~~

.. code-block:: python

   from actions.entities.metabolites.external.ramp_client_modern import RaMPClientModern, create_ramp_client
   
   # Initialize client with default configuration
   client = create_ramp_client()
   
   # Single metabolite query
   result = await client.search_metabolite_by_name("glucose")
   print(f"Found {len(result)} matches")
   
   # Access cross-references
   for match in result:
       print(f"Common Name: {match.common_name}")
       print(f"Source ID: {match.source_id}")
       print(f"Database: {match.id_type}")

Batch Query
~~~~~~~~~~~

.. code-block:: python

   # Batch query for multiple metabolites
   metabolite_names = ["glucose", "fructose", "galactose"]
   
   batch_results = await client.batch_metabolite_search(
       metabolite_names=metabolite_names,
       batch_size=25
   )
   
   # Process batch results
   for metabolite, matches in batch_results.items():
       print(f"{metabolite}: {len(matches)} matches found")

Advanced Queries
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Query with specific database targets
   # Search with specific options
   result = await client.search_metabolite_by_name(
       name="citric acid",
       analyte_type="metabolite"
   )
   
   # Get pathway information (if available)
   pathway_info = await client.get_pathways_from_analytes(
       analytes=["HMDB0000094"]
   )

Integration with Biomapper Actions
----------------------------------

YAML Strategy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: rampdb_metabolite_mapping
       action:
         type: RAMPDB_BRIDGE
         params:
           unmapped_key: unmatched_metabolites
           output_key: rampdb_matches
           final_unmapped_key: rampdb_unmapped
           identifier_column: metabolite_name
           batch_size: 40
           timeout: 45
           max_retries: 3

Python Client Usage
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient
   
   client = BiomapperClient(base_url="http://localhost:8000")
   
   result = await client.run_action(
       action_type="RAMPDB_BRIDGE",
       params={
           "unmapped_key": "metabolites",
           "output_key": "rampdb_results",
           "final_unmapped_key": "still_unmapped",
           "identifier_column": "compound_name",
           "batch_size": 30
       },
       context={"datasets": {"metabolites": metabolite_df}}
   )

Performance Optimization
------------------------

Batch Size Optimization
~~~~~~~~~~~~~~~~~~~~~~~

Optimize batch sizes based on your use case:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Dataset Size
     - Recommended Batch Size
     - Expected Time
     - Memory Usage
   * - < 100 metabolites
     - 25
     - < 30 seconds
     - Low
   * - 100-1,000 metabolites
     - 50
     - 1-5 minutes
     - Medium
   * - 1,000-10,000 metabolites
     - 75
     - 10-30 minutes
     - High
   * - > 10,000 metabolites
     - 100
     - 30+ minutes
     - Very High

Rate Limiting Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Conservative rate limiting (high reliability)
   rate_limiting:
     requests_per_minute: 30
     batch_delay: 2.0
     exponential_backoff: true
     
   # Aggressive rate limiting (faster processing)
   rate_limiting:
     requests_per_minute: 100
     batch_delay: 0.5
     exponential_backoff: false
     
   # Balanced rate limiting (recommended)
   rate_limiting:
     requests_per_minute: 60
     batch_delay: 1.0
     exponential_backoff: true

Caching Strategy
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Enable caching for repeated queries
   client_config = {
       "cache_enabled": True,
       "cache_ttl": 3600,  # 1 hour
       "cache_backend": "redis",  # or "memory"
       "cache_key_prefix": "rampdb_"
   }
   
   client = RampDBClient(config=client_config)

Error Handling and Monitoring
------------------------------

Common API Errors
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Error Type
     - Handling Strategy
   * - ``401 Unauthorized``
     - Check API key configuration and registration status
   * - ``429 Rate Limited``
     - Implement exponential backoff and reduce request rate
   * - ``500 Server Error``
     - Retry with exponential backoff, consider service status
   * - ``503 Service Unavailable``
     - Wait and retry, check RampDB service status
   * - ``Timeout``
     - Increase timeout values or reduce batch sizes

Monitoring Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import logging
   from src.integrations.rampdb_monitor import RampDBMonitor
   
   # Setup monitoring
   monitor = RampDBMonitor()
   
   # Track API metrics
   @monitor.track_api_call
   async def query_rampdb(query):
       result = await client.search_metabolite(query)
       
       # Log metrics
       monitor.log_success_rate(result.success)
       monitor.log_response_time(result.response_time)
       monitor.log_quota_usage(result.quota_used)
       
       return result

Error Recovery Patterns
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10)
   )
   async def robust_rampdb_query(identifiers):
       try:
           return await client.batch_search(identifiers)
       except RampDBAPIError as e:
           if e.status_code == 429:  # Rate limited
               await asyncio.sleep(e.retry_after or 60)
               raise
           elif e.status_code >= 500:  # Server error
               raise
           else:  # Client error - don't retry
               return None

Data Quality and Validation
---------------------------

Result Validation
~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_rampdb_results(results):
       """Validate RampDB API results for quality"""
       validation_report = {
           "total_queries": len(results),
           "successful_matches": 0,
           "failed_queries": 0,
           "quality_issues": []
       }
       
       for query, result in results.items():
           if result.success:
               validation_report["successful_matches"] += 1
               
               # Check for quality issues
               if not result.hmdb_id and not result.kegg_id:
                   validation_report["quality_issues"].append(
                       f"No primary database IDs for {query}"
                   )
           else:
               validation_report["failed_queries"] += 1
       
       return validation_report

Cross-Reference Consistency
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def check_cross_reference_consistency(rampdb_result):
       """Verify cross-references are consistent"""
       issues = []
       
       # Check if HMDB and KEGG refer to same compound
       if rampdb_result.hmdb_id and rampdb_result.kegg_id:
           hmdb_name = get_compound_name_from_hmdb(rampdb_result.hmdb_id)
           kegg_name = get_compound_name_from_kegg(rampdb_result.kegg_id) 
           
           if not compounds_are_equivalent(hmdb_name, kegg_name):
               issues.append("HMDB and KEGG cross-references inconsistent")
       
       return issues

Best Practices
--------------

1. **API Key Management**
   
   - Store API keys securely in environment variables
   - Use different keys for development and production
   - Monitor API key usage and quotas
   - Rotate keys regularly for security

2. **Rate Limiting**
   
   - Respect RampDB rate limits to maintain service availability
   - Implement exponential backoff for rate limit errors
   - Monitor quota usage to avoid service interruption
   - Use batch queries to maximize efficiency

3. **Error Handling**
   
   - Implement comprehensive error handling for all API calls
   - Log errors with sufficient context for debugging
   - Use retry logic with exponential backoff
   - Have fallback strategies for service unavailability

4. **Data Quality**
   
   - Validate API responses before using results
   - Check for cross-reference consistency
   - Monitor match rates and quality metrics
   - Flag low-confidence matches for manual review

5. **Performance**
   
   - Use appropriate batch sizes for your dataset
   - Cache results to avoid repeated API calls
   - Process in parallel where possible
   - Monitor response times and optimize accordingly

Troubleshooting Guide
---------------------

Connection Issues
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test basic connectivity
   curl -X GET "https://rampdb.nih.gov/api/v1/status" \
        -H "Authorization: Bearer YOUR_API_KEY"
   
   # Check DNS resolution
   nslookup rampdb.nih.gov
   
   # Test from Python
   python -c "
   import requests
   response = requests.get('https://rampdb.nih.gov/api/v1/status')
   print(f'Status: {response.status_code}')
   "

Authentication Issues
~~~~~~~~~~~~~~~~~~~~~

1. Verify API key is correctly set in environment
2. Check API key has not expired
3. Confirm registration is active and approved
4. Test with simple API call to verify credentials

Performance Issues
~~~~~~~~~~~~~~~~~~

1. **Slow API Responses**
   
   - Reduce batch sizes
   - Increase timeout values
   - Check network connectivity
   - Monitor RampDB service status

2. **Rate Limiting**
   
   - Implement longer delays between requests
   - Use exponential backoff
   - Reduce concurrent requests
   - Monitor quota usage patterns

Data Quality Issues
~~~~~~~~~~~~~~~~~~~

1. **Low Match Rates**
   
   - Verify input data quality and formatting
   - Check metabolite name normalization
   - Try different database targets
   - Review confidence thresholds

2. **Inconsistent Results**
   
   - Check RampDB service version and updates
   - Validate cross-references manually
   - Compare with alternative data sources
   - Report data quality issues to RampDB team

See Also
--------

- :doc:`../actions/metabolite_rampdb_bridge` - RampDB action documentation
- :doc:`../workflows/metabolomics_pipeline` - Pipeline integration examples
- :doc:`../examples/api_error_handling` - Error handling patterns
- :doc:`../performance/api_optimization` - API performance optimization
- `RampDB Official Documentation <https://rampdb.nih.gov/docs>`_
- `RampDB API Reference <https://rampdb.nih.gov/api/docs>`_

---

## Verification Sources
*Last verified: August 22, 2025*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/entities/metabolites/matching/rampdb_bridge.py` (RampDB bridge action implementation for Stage 3 progressive metabolite mapping)
- `/biomapper/src/actions/entities/metabolites/external/ramp_client_modern.py` (Modern RaMP-DB API client with async support, rate limiting, and comprehensive error handling)
- `/biomapper/src/actions/registry.py` (Action registration system showing RAMPDB_BRIDGE action registration)
- `/biomapper/pyproject.toml` (Project dependencies including aiohttp for async HTTP requests)
- `/biomapper/src/core/standards/base_models.py` (Standardized parameter models and validation)
- `/biomapper/src/client/client_v2.py` (Main BiomapperClient for action execution)
- `/biomapper/CLAUDE.md` (Development standards and parameter naming conventions)