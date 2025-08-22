Metabolite Fuzzy String Match
============================

.. automodule:: src.actions.entities.metabolites.matching.fuzzy_string_match

Overview
--------

The ``METABOLITE_FUZZY_STRING_MATCH`` action performs fuzzy string matching to map metabolite identifiers using Levenshtein distance and advanced string similarity algorithms. This action is typically used in Stage 2 of the progressive metabolomics pipeline to capture identifiers that are close matches but not exact.

This action is essential for handling real-world metabolomics data where identifiers may have slight variations in spelling, formatting, or punctuation.

Key Features
------------

- **Multiple Algorithms**: Levenshtein distance, Jaro-Winkler, and custom biological distance
- **Configurable Thresholds**: Adjustable similarity thresholds for precision/recall balance
- **Performance Optimized**: Uses efficient string matching algorithms for large datasets
- **Biological Awareness**: Understands metabolite naming conventions and common variations

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
     - Minimum similarity threshold (default: 0.8)
   * - ``max_distance``
     - integer
     - No
     - Maximum Levenshtein distance allowed (default: 2)
   * - ``algorithm``
     - string
     - No
     - Matching algorithm: 'levenshtein', 'jaro_winkler', 'biological' (default: 'levenshtein')
   * - ``case_sensitive``
     - boolean
     - No
     - Enable case-sensitive matching (default: false)

Performance Metrics
-------------------

Expected performance for Stage 2 in progressive pipeline:

- **Coverage Addition**: +15-20% over direct matching
- **Processing Speed**: 5-10 seconds for 1,000 metabolites
- **Precision**: 85-95% (varies by threshold)
- **Recall**: 70-85% (varies by threshold)

Typical stage-by-stage improvement:
- **After Stage 1**: 500 matched (50%)
- **After Stage 2**: 650 matched (65%) - **+150 via fuzzy matching**

Example Usage
-------------

YAML Strategy
~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: stage2_fuzzy_matching
       action:
         type: METABOLITE_FUZZY_STRING_MATCH
         params:
           input_key: stage1_unmatched
           output_key: stage2_matched
           identifier_column: metabolite_name
           threshold: 0.8
           max_distance: 2
           algorithm: levenshtein

Python Client
~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Fuzzy match unmatched metabolites from previous stage
   context = {"datasets": {"unmatched_metabolites": unmatched_df}}
   
   result = await client.run_action(
       action_type="METABOLITE_FUZZY_STRING_MATCH",
       params={
           "input_key": "unmatched_metabolites",
           "output_key": "fuzzy_matched",
           "identifier_column": "compound_name",
           "threshold": 0.85,
           "algorithm": "biological"
       },
       context=context
   )

Output Format
-------------

The action returns matched metabolites with similarity scores:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Column
     - Description
   * - ``original_id``
     - Original metabolite identifier from input
   * - ``matched_id``
     - Matched identifier from reference database
   * - ``matched_name``
     - Name of the matched metabolite
   * - ``similarity_score``
     - Similarity score (0.0-1.0)
   * - ``edit_distance``
     - Levenshtein distance between strings
   * - ``match_algorithm``
     - Algorithm used for this match

Matching Algorithms
-------------------

Levenshtein Distance
~~~~~~~~~~~~~~~~~~~~

Classic edit distance algorithm optimized for metabolite names:

- **Best for**: Minor spelling variations
- **Example**: "glucose" → "glucos" (distance: 1)
- **Performance**: Fast, O(n*m) complexity
- **Threshold**: Typically 0.8-0.9

Jaro-Winkler
~~~~~~~~~~~~

Considers character transpositions and common prefixes:

- **Best for**: Rearranged or transposed names
- **Example**: "citric acid" → "citric acdi"
- **Performance**: Moderate, better for longer strings
- **Threshold**: Typically 0.7-0.85

Biological Distance (Custom)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Understands metabolite naming conventions:

- **Best for**: Chemical synonym variations
- **Features**: Ignores common prefixes (D-, L-, (R)-, (S)-)
- **Example**: "D-glucose" → "glucose" (perfect match)
- **Performance**: Slower but more accurate for biological data

Example Input/Output
--------------------

Input Dataset
~~~~~~~~~~~~~

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - metabolite_name
     - original_source
   * - glucos
     - stage1_unmatched
   * - citric acdi
     - stage1_unmatched
   * - D-galactose
     - stage1_unmatched

Output Dataset
~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 20 20 20 20
   :header-rows: 1

   * - original_id
     - matched_id
     - matched_name
     - similarity_score
     - edit_distance
   * - glucos
     - HMDB0000122
     - glucose
     - 0.857
     - 1
   * - citric acdi
     - HMDB0000094
     - citric acid
     - 0.818
     - 2
   * - D-galactose
     - HMDB0000143
     - galactose
     - 1.000
     - 0

Advanced Configuration
----------------------

Threshold Optimization
~~~~~~~~~~~~~~~~~~~~~~

Balance precision and recall based on your needs:

.. code-block:: yaml

   # Conservative (high precision)
   threshold: 0.9
   max_distance: 1
   
   # Aggressive (high recall)  
   threshold: 0.7
   max_distance: 3
   
   # Balanced (recommended)
   threshold: 0.8
   max_distance: 2

Performance Tuning
~~~~~~~~~~~~~~~~~~

For large datasets (>10K metabolites):

.. code-block:: yaml

   # Enable optimizations
   chunk_processing: true
   chunk_size: 1000
   parallel_processing: true
   
   # Use faster algorithm for initial filtering
   pre_filter_algorithm: "levenshtein"
   pre_filter_threshold: 0.6

Quality Control
~~~~~~~~~~~~~~~

Add validation and filtering:

.. code-block:: yaml

   # Minimum match confidence
   min_confidence: 0.8
   
   # Manual review for low-confidence matches
   flag_for_review_threshold: 0.75
   
   # Export ambiguous matches
   export_ambiguous: true
   ambiguous_file_path: "/tmp/ambiguous_matches.csv"

Common Use Cases
----------------

Stage 2 Progressive Matching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most common use case in metabolomics pipelines:

.. code-block:: yaml

   # After Stage 1 direct matching
   - name: stage2_fuzzy_match
     action:
       type: METABOLITE_FUZZY_STRING_MATCH
       params:
         input_key: stage1_unmatched
         output_key: stage2_matched
         identifier_column: metabolite_name
         threshold: 0.8

Data Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~

Identify data quality issues:

.. code-block:: yaml

   # Find all near-matches to assess data quality
   - name: quality_assessment
     action:
       type: METABOLITE_FUZZY_STRING_MATCH
       params:
         input_key: raw_metabolites
         output_key: quality_matches
         threshold: 0.6  # Lower threshold
         export_all_candidates: true

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Issue
     - Solution
   * - Low match rate despite similar strings
     - Lower threshold or increase max_distance
   * - Too many false positives
     - Increase threshold or use 'biological' algorithm
   * - Performance issues with large datasets
     - Enable chunk processing or parallel execution
   * - Inconsistent results
     - Ensure consistent preprocessing and normalization

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Pre-filtering**: Use simple string operations to reduce candidate set
2. **Chunking**: Process large datasets in manageable chunks
3. **Algorithm Selection**: Use Levenshtein for speed, Jaro-Winkler for accuracy
4. **Threshold Tuning**: Higher thresholds reduce computation time

Integration with Pipeline
-------------------------

The fuzzy matching typically follows this pattern:

.. code-block:: yaml

   steps:
     # Stage 1: Direct matching
     - name: stage1_direct_match
       action:
         type: NIGHTINGALE_NMR_MATCH
         
     # Stage 2: Fuzzy matching on unmatched
     - name: stage2_fuzzy_match
       action:
         type: METABOLITE_FUZZY_STRING_MATCH
         params:
           input_key: stage1_unmatched
           output_key: stage2_matched
           
     # Combine results
     - name: combine_stages_1_2
       action:
         type: MERGE_DATASETS
         params:
           input_keys: [stage1_matched, stage2_matched]
           output_key: stages_1_2_combined

Best Practices
--------------

1. **Threshold Selection**: Start with 0.8 and adjust based on results
2. **Algorithm Choice**: Use 'biological' for metabolite data
3. **Validation**: Always manually review a sample of matches
4. **Documentation**: Record threshold choices and their rationale
5. **Progressive Use**: Use as Stage 2 after exact matching

See Also
--------

- :doc:`nightingale_nmr_match` - Stage 1 direct matching
- :doc:`hmdb_vector_match` - Stage 4 vector similarity matching
- :doc:`metabolite_rampdb_bridge` - Stage 3 API-based matching
- :doc:`../workflows/metabolomics_pipeline` - Complete pipeline integration
- :doc:`../examples/metabolomics_optimization` - Threshold optimization examples