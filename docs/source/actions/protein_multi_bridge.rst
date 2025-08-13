protein_multi_bridge
====================

The ``PROTEIN_MULTI_BRIDGE`` action implements configurable protein identifier matching using multiple bridge strategies in priority order.

Overview
--------

Based on research from the Gemini collaboration investigation, this action uses a multi-bridge approach for protein matching:

1. **UniProt exact match** (90% success rate)
2. **Gene symbol fuzzy match** (adds 8% more matches)  
3. **Ensembl ID exact match** (adds 2% more matches)

The action tries each bridge strategy in order, stopping when a high-confidence match is found.

Parameters
----------

.. code-block:: yaml

   action:
     type: PROTEIN_MULTI_BRIDGE
     params:
       source_dataset_key: "source_proteins"
       target_dataset_key: "target_proteins"
       bridge_attempts:
         - type: "uniprot"
           source_column: "uniprot_id"
           target_column: "accession"
           method: "exact"
           confidence_threshold: 0.9
           enabled: true
         - type: "gene_symbol"
           source_column: "gene_name"
           target_column: "gene_symbol"
           method: "fuzzy"
           confidence_threshold: 0.8
           fuzzy_threshold: 0.85
           enabled: true
       output_key: "protein_matches"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**source_dataset_key** : str
    Key for the source protein dataset

**target_dataset_key** : str
    Key for the target protein dataset

**bridge_attempts** : list[BridgeAttempt]
    List of bridge configurations in priority order

**output_key** : str
    Where to store the matched results

Bridge Configuration
~~~~~~~~~~~~~~~~~~~~

Each bridge attempt contains:

**type** : str
    Bridge type: "uniprot", "gene_symbol", "ensembl"

**source_column** : str
    Column name in source dataset

**target_column** : str
    Column name in target dataset

**method** : str
    Matching method: "exact" or "fuzzy"

**confidence_threshold** : float
    Minimum confidence for this bridge (0.0-1.0)

**enabled** : bool, default=True
    Whether to use this bridge

**fuzzy_threshold** : float, default=0.8
    Fuzzy matching threshold (if method="fuzzy")

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**partial_match_handling** : str, default="best_match"
    How to handle sub-threshold matches: "best_match", "reject", "warn"

**logging_verbosity** : str, default="detailed"
    Logging level: "minimal", "normal", "detailed"

**min_overall_confidence** : float, default=0.7
    Minimum confidence for any match

Bridge Strategy Details
-----------------------

UniProt Bridge
~~~~~~~~~~~~~~

- **Method**: Exact matching with normalization
- **Confidence**: 1.0 for exact matches, 0.0 otherwise
- **Normalization**: Removes prefixes (sp|, tr|), isoforms (-1, -2)
- **Best for**: High-confidence, unambiguous matches

Gene Symbol Bridge
~~~~~~~~~~~~~~~~~~

- **Method**: Advanced fuzzy matching
- **Algorithms**: Token sort, partial ratio, protein-specific similarity
- **Confidence**: Based on algorithm scores and string similarity
- **Handles**: Gene name variations, protein family naming
- **Best for**: When UniProt IDs are missing or inconsistent

Ensembl Bridge
~~~~~~~~~~~~~~

- **Method**: Exact matching
- **Confidence**: 1.0 for exact matches
- **Format**: Standard Ensembl protein/gene IDs
- **Best for**: Cross-reference datasets with Ensembl annotations

Example Usage
-------------

Standard Multi-Bridge Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: multi_bridge_matching
       action:
         type: PROTEIN_MULTI_BRIDGE
         params:
           source_dataset_key: "experimental_proteins"
           target_dataset_key: "reference_database"
           bridge_attempts:
             - type: "uniprot"
               source_column: "protein_accession"
               target_column: "uniprot_id"
               method: "exact"
               confidence_threshold: 0.95
               enabled: true
             - type: "gene_symbol"
               source_column: "gene_name"
               target_column: "gene_symbol"
               method: "fuzzy"
               confidence_threshold: 0.80
               fuzzy_threshold: 0.85
               enabled: true
             - type: "ensembl"
               source_column: "ensembl_protein_id"
               target_column: "ensembl_id"
               method: "exact"
               confidence_threshold: 0.90
               enabled: true
           partial_match_handling: "best_match"
           logging_verbosity: "detailed"
           min_overall_confidence: 0.75
           output_key: "protein_bridge_matches"

Conservative Matching
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: high_confidence_only
       action:
         type: PROTEIN_MULTI_BRIDGE
         params:
           source_dataset_key: "clinical_proteins"
           target_dataset_key: "approved_database"
           bridge_attempts:
             - type: "uniprot"
               source_column: "accession"
               target_column: "uniprot_accession"
               method: "exact"
               confidence_threshold: 0.99
               enabled: true
           partial_match_handling: "reject"  # Strict matching
           min_overall_confidence: 0.95
           output_key: "verified_matches"

Gene Symbol Focused
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: gene_centric_matching
       action:
         type: PROTEIN_MULTI_BRIDGE
         params:
           source_dataset_key: "transcriptomics_data"
           target_dataset_key: "protein_atlas"
           bridge_attempts:
             - type: "gene_symbol"
               source_column: "gene_symbol"
               target_column: "approved_symbol"
               method: "fuzzy"
               confidence_threshold: 0.85
               fuzzy_threshold: 0.90
               enabled: true
             - type: "gene_symbol"
               source_column: "gene_name"
               target_column: "gene_description"
               method: "fuzzy"
               confidence_threshold: 0.70
               fuzzy_threshold: 0.75
               enabled: true
           output_key: "gene_based_matches"

Output Format
-------------

The action returns matched pairs with detailed metadata:

.. code-block::

   source_id          | target_id       | confidence | successful_bridge | bridge_method
   PROTEIN_001        | P12345          | 1.0        | uniprot          | exact
   GENE_ABC           | Q67890          | 0.89       | gene_symbol      | fuzzy
   ENSP00000123456    | O95342          | 1.0        | ensembl          | exact

Advanced Fuzzy Matching
-----------------------

The gene symbol bridge uses sophisticated fuzzy matching:

**Token Sort Ratio**
- Handles word order differences
- Example: "NRP1" matches "Neuropilin 1"

**Partial Ratio**
- Handles partial matches
- Example: "TP53" matches "TP53_VARIANT"

**Protein-Specific Similarity**
- Removes common suffixes (_HUMAN, _MOUSE)
- Handles protein family variants
- Recognizes abbreviation patterns

**Performance Optimization**
- Fast mode for very different strings
- Full algorithm suite for similar lengths
- Caching for repeated comparisons

Statistics and Metrics
----------------------

Comprehensive statistics are tracked for each bridge:

.. code-block:: python

   {
       "total_source_proteins": 1000,
       "total_target_proteins": 5000,
       "total_matches": 890,
       "matches_by_bridge": {
           "uniprot": 800,
           "gene_symbol": 80,
           "ensembl": 10
       },
       "bridge_attempts": {
           "uniprot": {
               "attempted": 1000,
               "successful": 800,
               "avg_confidence": 0.98
           },
           "gene_symbol": {
               "attempted": 200,
               "successful": 80,
               "avg_confidence": 0.85
           }
       },
       "confidence_distribution": {
           "high": 850,    # ≥0.9
           "medium": 40,   # 0.7-0.9  
           "low": 0        # <0.7
       }
   }

Error Handling
--------------

The action gracefully handles various error conditions:

- **Missing columns**: Logs warning and skips bridge
- **Empty datasets**: Returns empty results with success
- **Invalid bridges**: Continues with remaining bridges
- **Column mismatches**: Detailed error reporting

Best Practices
--------------

1. **Order bridges by reliability**: UniProt → Gene symbols → Other IDs
2. **Set appropriate thresholds**: Higher for exact methods, lower for fuzzy
3. **Use detailed logging**: Helps optimize bridge configurations
4. **Handle partial matches wisely**: "best_match" for discovery, "reject" for clinical
5. **Monitor statistics**: Track bridge performance over time

Performance Considerations
--------------------------

**Optimization Features**
- Early stopping on exact matches (confidence ≥ 0.99)
- Rate limiting for large datasets  
- Progress reporting for long operations
- Memory-efficient processing

**Scalability**
- Batch processing support
- Configurable timeouts
- Resource usage monitoring
- Parallel bridge evaluation

Integration Examples
--------------------

With Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: multi_bridge_match
       action:
         type: PROTEIN_MULTI_BRIDGE
         # ... bridge configuration

     - name: assess_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "experimental_proteins"
           mapped_key: "protein_bridge_matches"
           confidence_column: "confidence"

With Normalization Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_source
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "raw_proteins"
           id_columns: ["protein_id"]
           output_key: "normalized_source"

     - name: normalize_target  
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "reference_proteins"
           id_columns: ["accession"]
           output_key: "normalized_target"

     - name: multi_bridge_match
       action:
         type: PROTEIN_MULTI_BRIDGE
         params:
           source_dataset_key: "normalized_source"
           target_dataset_key: "normalized_target"
           # ... bridge configuration

The multi-bridge approach significantly improves protein matching success rates while maintaining high confidence scores and detailed audit trails.