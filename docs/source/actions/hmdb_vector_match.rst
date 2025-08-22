HMDB Vector Match
=================

.. automodule:: src.actions.entities.metabolites.matching.hmdb_vector_match

Overview
--------

The ``HMDB_VECTOR_MATCH`` action performs semantic similarity matching using vector embeddings to map metabolite identifiers against the Human Metabolome Database (HMDB). This action uses the Qdrant vector database for high-performance similarity search and FastEmbed for efficient embedding generation.

This is particularly useful for Stage 4 progressive matching when direct matching, fuzzy matching, and other approaches have been exhausted.

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
     - Key for the output dataset with matched identifiers
   * - ``identifier_column``
     - string
     - Yes
     - Column name containing metabolite identifiers to match
   * - ``threshold``
     - float
     - No
     - Minimum similarity threshold (default: 0.7)
   * - ``max_results``
     - integer
     - No
     - Maximum number of matches per metabolite (default: 5)
   * - ``use_llm_validation``
     - boolean
     - No
     - Enable LLM validation for high-confidence matches (default: false)

Performance
-----------

- **Vector Search Speed**: ~1-5ms per query
- **Batch Processing**: Processes multiple metabolites efficiently
- **Memory Usage**: Optimized embedding generation
- **Coverage Improvement**: Typically adds 5-10% to total pipeline coverage

Expected coverage improvement over previous stages:
- After direct matching: +15-25%
- After fuzzy matching: +8-15%  
- After RampDB bridge: +5-10%

Example Usage
-------------

YAML Strategy
~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: stage4_vector_matching
       action:
         type: HMDB_VECTOR_MATCH
         params:
           input_key: stage3_unmatched
           output_key: stage4_matched
           identifier_column: metabolite_name
           threshold: 0.75
           max_results: 3
           use_llm_validation: true

Python Client
~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Load your metabolite data first
   context = {"datasets": {"unmatched_metabolites": metabolite_df}}
   
   result = await client.run_action(
       action_type="HMDB_VECTOR_MATCH",
       params={
           "input_key": "unmatched_metabolites",
           "output_key": "vector_matched",
           "identifier_column": "compound_name",
           "threshold": 0.8
       },
       context=context
   )

Output Format
-------------

The action returns a dataset with the following structure:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Column
     - Description
   * - ``original_id``
     - Original metabolite identifier from input
   * - ``matched_hmdb_id`` 
     - HMDB identifier of the best match
   * - ``matched_name``
     - Name of the matched HMDB compound
   * - ``similarity_score``
     - Cosine similarity score (0.0-1.0)
   * - ``match_confidence``
     - Confidence level: high/medium/low
   * - ``llm_validation``
     - LLM validation result (if enabled)

Technical Details
-----------------

Vector Database
~~~~~~~~~~~~~~~

Uses Qdrant vector database with pre-computed HMDB embeddings:

- **Collection**: ``hmdb_metabolites``
- **Vector Size**: 384 dimensions (all-MiniLM-L6-v2)
- **Distance Metric**: Cosine similarity
- **Index Type**: HNSW for fast approximate search

Embedding Generation
~~~~~~~~~~~~~~~~~~~~

- **Model**: ``sentence-transformers/all-MiniLM-L6-v2``
- **Library**: FastEmbed for optimized performance
- **Preprocessing**: Text normalization and cleaning
- **Batch Size**: Configurable for memory optimization

LLM Validation (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~

When ``use_llm_validation`` is enabled:

- Uses lightweight language model for validation
- Compares original and matched compound names
- Provides confidence assessment
- Filters out obvious false positives

Best Practices
--------------

1. **Threshold Selection**: Start with 0.7-0.8 for balanced precision/recall
2. **Progressive Use**: Use as final stage after direct/fuzzy matching
3. **Validation**: Enable LLM validation for critical applications
4. **Batch Processing**: Process large datasets in chunks for optimal performance

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

- **Qdrant Connection Error**: Ensure vector database is running
- **Low Match Quality**: Adjust threshold or enable LLM validation  
- **Performance Issues**: Reduce batch size or max_results
- **Missing Embeddings**: Verify HMDB collection exists and is populated

Performance Tuning
~~~~~~~~~~~~~~~~~~~

- **Reduce threshold**: Increases recall but may reduce precision
- **Increase max_results**: More candidates but slower processing
- **Enable batching**: Process multiple queries together
- **Optimize embedding model**: Use smaller model for speed

See Also
--------

- :doc:`metabolite_fuzzy_string_match` - String-based fuzzy matching
- :doc:`metabolite_rampdb_bridge` - RampDB integration  
- :doc:`progressive_semantic_match` - Multi-stage semantic matching
- :doc:`../workflows/metabolomics_pipeline` - Complete workflow implementation