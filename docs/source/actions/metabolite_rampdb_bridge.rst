Metabolite RampDB Bridge
=======================

.. automodule:: src.actions.entities.metabolites.matching.rampdb_bridge

Overview
--------

The ``METABOLITE_RAMPDB_BRIDGE`` action integrates with the RampDB API to perform external database lookups for metabolite identifiers. This action is typically used in Stage 3 of the progressive metabolomics pipeline to leverage RampDB's comprehensive metabolite mapping capabilities.

RampDB provides cross-references between multiple metabolite databases including HMDB, KEGG, ChEBI, PubChem, and others, making it valuable for resolving identifiers that couldn't be matched through direct or fuzzy approaches.

Key Features
------------

- **External API Integration**: Real-time queries to RampDB service
- **Cross-Database Mapping**: Maps across HMDB, KEGG, ChEBI, PubChem, and more
- **Batch Processing**: Optimized batch API calls for better performance
- **Retry Logic**: Robust error handling with exponential backoff
- **Rate Limiting**: Respects API rate limits to avoid service disruption

Parameters
----------

.. list-table::
   :widths: 25 15 10 50
   :header-rows: 1

   * - Parameter
     - Type
     - Required
     - Description
   * - ``input_key``
     - string
     - Yes
     - Key for the input dataset containing metabolite identifiers
   * - ``output_key``
     - string
     - Yes
     - Key for the output dataset with RampDB matches
   * - ``identifier_column``
     - string
     - Yes
     - Column containing metabolite identifiers to query
   * - ``batch_size``
     - integer
     - No
     - Number of identifiers per API call (default: 50)
   * - ``timeout``
     - integer
     - No
     - API request timeout in seconds (default: 30)
   * - ``max_retries``
     - integer
     - No
     - Maximum retry attempts for failed requests (default: 3)
   * - ``target_databases``
     - list
     - No
     - Specific databases to query (default: ["hmdb", "kegg", "chebi"])

Performance Metrics
-------------------

Expected performance for Stage 3 in progressive pipeline:

- **Coverage Addition**: +8-12% over previous stages
- **Processing Speed**: 30-60 seconds for 1,000 metabolites (API dependent)
- **Success Rate**: 90-95% API call success rate
- **Database Coverage**: Access to 15+ metabolite databases

API Rate Limits:
- **Requests per minute**: 60 (varies by RampDB service level)
- **Concurrent requests**: 5 maximum recommended
- **Daily quota**: 10,000 requests (free tier)

Example Usage
-------------

YAML Strategy
~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: stage3_rampdb_bridge
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params:
           input_key: stage2_unmatched
           output_key: stage3_matched
           identifier_column: metabolite_name
           batch_size: 25
           timeout: 45
           target_databases: ["hmdb", "kegg", "chebi", "pubchem"]

Python Client
~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Query RampDB for unmatched metabolites
   context = {"datasets": {"stage2_unmatched": unmatched_df}}
   
   result = await client.run_action(
       action_type="METABOLITE_RAMPDB_BRIDGE",
       params={
           "input_key": "stage2_unmatched",
           "output_key": "rampdb_matches",
           "identifier_column": "compound_name",
           "batch_size": 30,
           "timeout": 60,
           "target_databases": ["hmdb", "kegg"]
       },
       context=context
   )

Output Format
-------------

The action returns matches from RampDB with cross-references:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Column
     - Description
   * - ``original_id``
     - Original metabolite identifier from input
   * - ``rampdb_id``
     - RampDB internal identifier
   * - ``matched_name``
     - Standardized metabolite name from RampDB
   * - ``hmdb_id``
     - HMDB identifier (if available)
   * - ``kegg_id``
     - KEGG identifier (if available)
   * - ``chebi_id``
     - ChEBI identifier (if available)
   * - ``pubchem_cid``
     - PubChem CID (if available)
   * - ``confidence_score``
     - RampDB confidence score (0.0-1.0)
   * - ``api_response_time``
     - Time taken for API call (ms)

Technical Implementation
------------------------

API Integration
~~~~~~~~~~~~~~~

RampDB API endpoint structure:

.. code-block:: python

   # Base API configuration
   RAMPDB_BASE_URL = "https://rampdb.nih.gov/api/v1/"
   ENDPOINTS = {
       "search": "metabolites/search",
       "batch": "metabolites/batch_search",
       "crossref": "metabolites/crossref"
   }

Batch Processing Logic
~~~~~~~~~~~~~~~~~~~~~~

Optimized batch processing to minimize API calls:

1. **Batch Grouping**: Groups identifiers into optimal batch sizes
2. **Rate Limiting**: Implements delays between API calls
3. **Error Handling**: Retries failed batches with exponential backoff
4. **Result Aggregation**: Combines batch results into unified dataset

Retry Strategy
~~~~~~~~~~~~~~

Robust error handling for API reliability:

.. code-block:: yaml

   retry_configuration:
     max_retries: 3
     base_delay: 1.0        # seconds
     backoff_multiplier: 2.0
     max_delay: 30.0        # seconds
     
   timeout_handling:
     connect_timeout: 10    # seconds
     read_timeout: 30       # seconds

Database Cross-References
-------------------------

RampDB provides cross-references to multiple databases:

Primary Databases
~~~~~~~~~~~~~~~~~

- **HMDB**: Human Metabolome Database
- **KEGG**: Kyoto Encyclopedia of Genes and Genomes  
- **ChEBI**: Chemical Entities of Biological Interest
- **PubChem**: PubChem Compound Database

Secondary Databases
~~~~~~~~~~~~~~~~~~~

- **BioCyc**: Metabolic pathway database
- **LIPID MAPS**: Lipidomics database
- **MetaCyc**: Metabolic pathway database
- **Reactome**: Pathway database
- **WikiPathways**: Community pathway database

Example Workflow Integration
----------------------------

Stage 3 in Progressive Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Complete Stage 3 implementation
   steps:
     # Previous stages completed
     - name: load_unmatched_from_stage2
       action:
         type: FILTER_DATASET
         params:
           input_key: stage2_results
           output_key: stage2_unmatched
           filter_expression: "matched_status == 'unmatched'"
           
     - name: stage3_rampdb_query
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params:
           input_key: stage2_unmatched
           output_key: stage3_matched
           identifier_column: metabolite_name
           batch_size: 40
           timeout: 45
           
     - name: combine_stage3_results
       action:
         type: MERGE_DATASETS
         params:
           input_keys: [stage2_matched, stage3_matched]
           output_key: stages_1_3_combined

Error Handling and Monitoring
------------------------------

Common API Issues
~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Error Type
     - Handling Strategy
   * - ``Rate Limit Exceeded``
     - Automatic retry with exponential backoff
   * - ``Network Timeout``
     - Retry with increased timeout values
   * - ``API Service Down``
     - Skip batch and continue with remaining data
   * - ``Invalid Response Format``
     - Log error and mark identifiers as unprocessable
   * - ``Authentication Error``
     - Check API key configuration

Monitoring Metrics
~~~~~~~~~~~~~~~~~~

Track these metrics for API health:

- **Success Rate**: Percentage of successful API calls
- **Average Response Time**: Monitor API performance
- **Error Distribution**: Track types of failures
- **Coverage Rate**: Percentage of identifiers successfully mapped
- **Quota Usage**: Monitor daily API quota consumption

Configuration Examples
----------------------

High-Throughput Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For large datasets with relaxed accuracy requirements:

.. code-block:: yaml

   params:
     batch_size: 100        # Larger batches
     timeout: 60            # Longer timeout
     max_retries: 2         # Fewer retries
     target_databases: ["hmdb", "kegg"]  # Focus on key databases

High-Accuracy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For critical datasets requiring comprehensive mapping:

.. code-block:: yaml

   params:
     batch_size: 20         # Smaller batches for reliability
     timeout: 90            # Extended timeout
     max_retries: 5         # More retries
     target_databases: ["hmdb", "kegg", "chebi", "pubchem", "lipidmaps"]

Development Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

For testing and development:

.. code-block:: yaml

   params:
     batch_size: 5          # Very small batches
     timeout: 30
     max_retries: 1
     debug_mode: true       # Enhanced logging
     dry_run: false         # Set to true to skip actual API calls

Best Practices
--------------

1. **API Key Management**: Store API keys securely in environment variables
2. **Batch Size Optimization**: Start with 25-50, adjust based on performance
3. **Timeout Configuration**: Set timeouts 2-3x longer than average response time
4. **Error Logging**: Log all API errors for debugging and monitoring
5. **Quota Monitoring**: Track daily API usage to avoid quota exhaustion

Integration Patterns
--------------------

Sequential Processing
~~~~~~~~~~~~~~~~~~~~~

Process in stages with error recovery:

.. code-block:: yaml

   steps:
     - name: stage3_batch1
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params:
           input_key: unmatched_batch1
           batch_size: 50
           
     - name: stage3_batch2  
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params:
           input_key: unmatched_batch2
           batch_size: 50

Parallel Processing
~~~~~~~~~~~~~~~~~~~

For independent batches (advanced):

.. code-block:: yaml

   # Note: Requires workflow orchestration support
   parallel_steps:
     - name: rampdb_batch_1
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params: {batch_size: 25, timeout: 30}
     - name: rampdb_batch_2  
       action:
         type: METABOLITE_RAMPDB_BRIDGE
         params: {batch_size: 25, timeout: 30}

Troubleshooting
---------------

Performance Issues
~~~~~~~~~~~~~~~~~~

1. **Slow API responses**: Reduce batch size, increase timeout
2. **Rate limiting**: Decrease request frequency, implement delays
3. **Memory usage**: Process in smaller chunks
4. **Network instability**: Increase retry attempts with longer delays

Data Quality Issues
~~~~~~~~~~~~~~~~~~~

1. **Low match rates**: Verify input data quality and identifier formats
2. **Inconsistent results**: Check RampDB service status and version
3. **Missing cross-references**: Query additional target databases
4. **Duplicate matches**: Implement deduplication logic

API Configuration Issues
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Authentication failures**: Verify API key configuration
2. **Quota exceeded**: Monitor and manage daily usage
3. **Service unavailable**: Implement fallback strategies
4. **Version compatibility**: Check RampDB API version requirements

See Also
--------

- :doc:`metabolite_fuzzy_string_match` - Stage 2 fuzzy matching
- :doc:`hmdb_vector_match` - Stage 4 vector similarity matching  
- :doc:`progressive_semantic_match` - Multi-stage orchestration
- :doc:`../workflows/metabolomics_pipeline` - Complete pipeline implementation
- :doc:`../integrations/rampdb_integration` - RampDB setup and configuration
- :doc:`../examples/api_error_handling` - Error handling patterns