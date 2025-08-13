metabolite_cts_bridge
====================

The ``METABOLITE_CTS_BRIDGE`` action integrates with the Chemical Translation Service (CTS) API to bridge between different metabolite identifier types.

Overview
--------

This action uses the CTS (Chemical Translation Service) API from UC Davis to translate between metabolite identifier systems:

- **HMDB** ↔ **InChIKey** ↔ **CHEBI** ↔ **KEGG** ↔ **PubChem** ↔ **CAS** ↔ **SMILES**

The action includes intelligent caching, rate limiting, fallback services, and batch processing for efficient translation of large datasets.

Parameters
----------

.. code-block:: yaml

   action:
     type: METABOLITE_CTS_BRIDGE
     params:
       source_key: "source_metabolites"
       target_key: "target_metabolites"
       source_id_column: "hmdb_id"
       source_id_type: "hmdb"
       target_id_column: "inchikey"
       target_id_type: "inchikey"
       batch_size: 100
       confidence_threshold: 0.8
       output_key: "cts_matches"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**source_key** : str
    Source dataset key containing metabolite identifiers

**target_key** : str
    Target dataset key to match against

**source_id_column** : str
    Column containing source identifiers

**source_id_type** : str
    Type of source identifier: "hmdb", "inchikey", "chebi", "kegg", "pubchem", "cas", "smiles"

**target_id_column** : str
    Column containing target identifiers

**target_id_type** : str
    Type of target identifier: "hmdb", "inchikey", "chebi", "kegg", "pubchem", "cas", "smiles"

**output_key** : str
    Where to store translation matches

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**batch_size** : int, default=100
    Number of identifiers to translate per API batch

**max_retries** : int, default=3
    Maximum retries for failed requests

**timeout_seconds** : int, default=30
    Timeout per CTS API request

**cache_results** : bool, default=True
    Cache successful translations to disk

**cache_file** : str, default=None
    Custom path for cache file

**use_fallback_services** : bool, default=True
    Use alternative services if CTS fails

**fallback_services** : list[str], default=["pubchem", "chemspider"]
    Alternative translation services

**confidence_threshold** : float, default=0.8
    Minimum confidence for accepting matches

**handle_multiple_translations** : str, default="best"
    How to handle multiple results: "first", "best", "all"

**skip_on_error** : bool, default=True
    Continue processing if individual translations fail

Supported Identifier Types
--------------------------

HMDB (Human Metabolome Database)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Format: HMDB0001234 (7 digits)
- Example: HMDB0000122 (glucose)
- Validation: HMDB followed by 7 digits

InChIKey
~~~~~~~~
- Format: XXXXXXXXXXXXXX-YYYYYYYYYY-Z
- Example: WQZGKKKJIJFFOK-GASJEMHNSA-N
- Validation: 14-10-1 character pattern

CHEBI (Chemical Entities of Biological Interest)  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Format: CHEBI:12345
- Example: CHEBI:17234 (glucose)
- Validation: CHEBI: followed by digits

KEGG Compound
~~~~~~~~~~~~~
- Format: C12345
- Example: C00031 (glucose)
- Validation: C followed by 5 digits

PubChem CID
~~~~~~~~~~~
- Format: 12345 (numeric)
- Example: 5793 (glucose)
- Validation: Numeric string

CAS Registry Number
~~~~~~~~~~~~~~~~~~
- Format: 123-45-6
- Example: 50-99-7 (glucose)
- Validation: XXX-XX-X pattern

SMILES
~~~~~~
- Format: Chemical structure notation
- Example: C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O)O)O)O)O
- Validation: Valid SMILES syntax

Example Usage
-------------

Basic HMDB to InChIKey Translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: translate_hmdb_to_inchikey
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "hmdb_metabolites"
           target_key: "inchikey_database"
           source_id_column: "hmdb_id"
           source_id_type: "hmdb"
           target_id_column: "inchikey"
           target_id_type: "inchikey"
           batch_size: 50
           confidence_threshold: 0.85
           output_key: "hmdb_inchikey_matches"

Multi-Direction Translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: kegg_to_hmdb
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "kegg_compounds"
           target_key: "hmdb_reference"
           source_id_column: "compound_id"
           source_id_type: "kegg"
           target_id_column: "hmdb_accession"
           target_id_type: "hmdb"
           output_key: "kegg_hmdb_bridge"

     - name: hmdb_to_chebi
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "kegg_hmdb_bridge"
           target_key: "chebi_ontology"
           source_id_column: "hmdb_accession"
           source_id_type: "hmdb"
           target_id_column: "chebi_id"
           target_id_type: "chebi"
           output_key: "multi_bridge_results"

High-Throughput Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: batch_translate
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "large_metabolite_dataset"
           target_key: "pubchem_reference"
           source_id_column: "identifier"
           source_id_type: "hmdb"
           target_id_column: "pubchem_cid"
           target_id_type: "pubchem"
           batch_size: 200        # Larger batches
           max_retries: 5         # More retries
           timeout_seconds: 60    # Longer timeout
           cache_results: true    # Enable caching
           cache_file: "/tmp/metabolite_cache.pkl"
           use_fallback_services: true
           skip_on_error: true
           output_key: "batch_translations"

CTS API Integration
-------------------

Rate Limiting
~~~~~~~~~~~~~
- Automatic rate limiting to prevent API overload
- Configurable requests per second
- Exponential backoff on failures

Caching System
~~~~~~~~~~~~~~
- Disk-based persistent cache
- TTL (time-to-live) for cache entries
- Memory cache for session optimization

Error Handling
~~~~~~~~~~~~~~
- Graceful handling of API failures
- Retry logic with exponential backoff
- Fallback to alternative services

Batch Processing
~~~~~~~~~~~~~~~~
- Efficient batching to minimize API calls
- Progress tracking for large datasets
- Parallel processing where possible

Output Format
-------------

The action outputs matched pairs with confidence scores:

.. code-block::

   source_id        | target_id                      | confidence | match_type
   HMDB0000122      | WQZGKKKJIJFFOK-GASJEMHNSA-N   | 0.95       | cts_bridge
   HMDB0000168      | HMJBTJJHQPSFPW-UHFFFAOYSA-N   | 0.90       | cts_bridge
   C00031           | WQZGKKKJIJFFOK-GASJEMHNSA-N   | 0.92       | cts_bridge

Fallback Services
-----------------

PubChem REST API
~~~~~~~~~~~~~~~~
- Used when CTS fails for InChIKey/PubChem translations
- Provides additional coverage for common compounds
- Integrated with confidence scoring

ChemSpider API
~~~~~~~~~~~~~~
- Alternative chemical database service
- Requires API key configuration
- Used for specialized compound lookups

Local Database Fallback
~~~~~~~~~~~~~~~~~~~~~~~
- Pre-downloaded mapping tables
- Instant lookups for common compounds
- No network dependency

Statistics and Monitoring
-------------------------

The action provides comprehensive statistics:

.. code-block:: python

   {
       "total_source": 1000,
       "total_target": 5000,
       "successful_translations": 850,
       "failed_translations": 150,
       "matches_found": 780,
       "cache_hits": 200,
       "cache_misses": 800,
       "api_calls": 800,
       "fallback_successes": 30,
       "confidence_scores": {
           "high": 600,    # >0.9
           "medium": 180,  # 0.8-0.9
           "low": 0        # <0.8
       }
   }

Performance Optimization
------------------------

Caching Strategy
~~~~~~~~~~~~~~~~
- MD5 hashing for cache keys
- JSON serialization for disk storage
- LRU eviction for memory management

API Efficiency
~~~~~~~~~~~~~~
- Request deduplication
- Batch size optimization
- Connection pooling

Memory Management
~~~~~~~~~~~~~~~~~
- Streaming processing for large datasets
- Garbage collection optimization
- Memory usage monitoring

Error Recovery
--------------

Network Issues
~~~~~~~~~~~~~~
- Automatic retry with exponential backoff
- Timeout handling with graceful degradation
- Connection pooling for reliability

API Rate Limits
~~~~~~~~~~~~~~~
- Intelligent rate limiting
- Queue management for burst requests
- Adaptive throttling based on response times

Data Quality Issues
~~~~~~~~~~~~~~~~~~
- Identifier format validation
- Invalid response handling
- Confidence scoring for uncertain matches

Best Practices
--------------

1. **Enable caching**: Significantly reduces API calls for repeated analyses
2. **Use appropriate batch sizes**: Balance API efficiency with memory usage
3. **Set conservative timeouts**: Account for CTS API variability
4. **Monitor API usage**: Track calls to avoid exceeding limits
5. **Validate inputs**: Ensure identifier formats are correct before translation
6. **Handle failures gracefully**: Use fallback services and error skipping

Integration Examples
--------------------

With Metabolite Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_hmdb
       action:
         type: METABOLITE_NORMALIZE_HMDB
         params:
           input_key: "raw_metabolites"
           hmdb_columns: ["metabolite_id"]
           output_key: "normalized_hmdb"

     - name: translate_to_inchikey
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "normalized_hmdb"
           target_key: "inchikey_reference"
           source_id_column: "metabolite_id"
           source_id_type: "hmdb"
           target_id_column: "inchikey"
           target_id_type: "inchikey"
           output_key: "translated_metabolites"

With Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: cts_translation
       action:
         type: METABOLITE_CTS_BRIDGE
         # ... translation parameters

     - name: assess_translation_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "source_metabolites"
           mapped_key: "translated_metabolites"
           confidence_column: "confidence"
           confidence_threshold: 0.8
           output_key: "translation_quality"

The CTS bridge provides reliable, high-throughput translation between metabolite identifier systems with comprehensive error handling and performance optimization.