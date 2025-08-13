MERGE_DATASETS
==============

Merge multiple datasets with optional deduplication and flexible join strategies.

Purpose
-------

This action combines multiple datasets from the execution context into a single unified dataset. It provides:

* Multiple merge strategies (concatenation and join)
* Flexible deduplication options
* Support for different join types
* Comprehensive error handling and validation
* Detailed provenance tracking

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**dataset_keys** (list of strings)
  List of dataset keys to merge from the execution context.

**output_key** (string)
  Key name to store the merged dataset in the execution context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**deduplication_column** (string)
  Column name to use for deduplication. If not specified, no deduplication is performed.
  Default: None

**keep** (string)
  Which duplicate to keep when deduplicating: 'first', 'last', or 'all'.
  Default: 'first'

**merge_strategy** (string)
  How to merge datasets: 'concat' (stack rows) or 'join' (merge on common column).
  Default: 'concat'

**join_on** (string)
  Column name to join on when using 'join' strategy. Required for join operations.
  Default: None

**join_how** (string)
  Type of join to perform: 'inner', 'outer', 'left', 'right'.
  Default: 'outer'

Example Usage
-------------

Basic Dataset Concatenation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: merge_protein_datasets
      action:
        type: MERGE_DATASETS
        params:
          dataset_keys: ["ukbb_proteins", "arv_proteins", "kg2c_proteins"]
          output_key: "all_proteins"
          deduplication_column: "uniprot_id"
          keep: "first"

Join-Based Merging
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: merge_with_metadata
      action:
        type: MERGE_DATASETS
        params:
          dataset_keys: ["protein_data", "protein_annotations"]
          output_key: "annotated_proteins"
          merge_strategy: "join"
          join_on: "uniprot_id"
          join_how: "left"

Advanced Deduplication
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: combine_metabolite_results
      action:
        type: MERGE_DATASETS
        params:
          dataset_keys: ["cts_matches", "hmdb_matches", "manual_matches"]
          output_key: "unified_metabolites"
          deduplication_column: "hmdb_id"
          keep: "last"  # Keep most recent match

Output Format
-------------

The action stores the merged dataset in the context under the specified ``output_key``:

.. code-block:: python

    # Context after execution
    {
        "datasets": {
            "all_proteins": [
                {
                    "uniprot_id": "P12345",
                    "gene_name": "EXAMPLE1",
                    "source": "ukbb_proteins"
                },
                {
                    "uniprot_id": "Q67890", 
                    "gene_name": "EXAMPLE2",
                    "source": "arv_proteins"
                }
                # ... merged rows from all datasets
            ]
        }
    }

Merge Strategies
----------------

**Concatenation (concat)**
  Stacks datasets vertically, preserving all columns from all datasets. Missing columns are filled with NaN.

**Join (join)**
  Merges datasets horizontally based on a common column. Column conflicts are resolved with suffixes.

Deduplication Options
---------------------

**keep='first'**
  Keeps the first occurrence of each duplicate identifier.

**keep='last'**
  Keeps the last occurrence of each duplicate identifier.

**keep='all'**
  Keeps all rows (no deduplication performed).

Error Handling
--------------

**Missing datasets**
  .. code-block::
  
      Warning: Dataset 'missing_data' not found in context
      
  Solution: Verify dataset keys exist in context from previous actions.

**Join column missing**
  .. code-block::
  
      Error: join_on parameter required for join strategy
      
  Solution: Specify the column name to join on when using join strategy.

**Empty datasets**
  .. code-block::
  
      Warning: Dataset at index 1 is empty or invalid type
      
  Solution: Ensure datasets contain valid data before merging.

Best Practices
--------------

1. **Use descriptive output keys** like "merged_proteins" instead of "result"
2. **Choose appropriate merge strategy** - concat for combining similar datasets, join for adding metadata
3. **Consider deduplication carefully** - first occurrence often preserves original data quality
4. **Validate join columns** exist in all datasets before using join strategy
5. **Handle missing datasets gracefully** by checking dataset availability

Performance Notes
-----------------

* Large datasets (>100K rows) are processed efficiently using pandas
* Memory usage scales with combined dataset size
* Join operations may be slower than concatenation for large datasets
* Consider processing in chunks for extremely large datasets (>1M rows)

Common Use Cases
----------------

**Combining Multi-Source Data**
  Merge datasets from different platforms (UK Biobank, ArraySeq, etc.)

**Adding Annotations**
  Join experimental data with reference annotations or metadata

**Result Consolidation**
  Combine results from multiple matching algorithms with deduplication

**Quality Control**
  Merge datasets while removing duplicates to ensure data integrity

Integration
-----------

This action typically follows data loading actions and precedes analysis:

.. code-block:: yaml

    steps:
      # 1. Load datasets
      - name: load_ukbb
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/ukbb_proteins.csv"
            identifier_column: "UniProt"
            output_key: "ukbb_data"
      
      - name: load_arv
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/arv_proteins.csv"
            identifier_column: "UniProt"
            output_key: "arv_data"
      
      # 2. Merge datasets
      - name: merge_all
        action:
          type: MERGE_DATASETS
          params:
            dataset_keys: ["ukbb_data", "arv_data"]
            output_key: "combined_proteins"
            deduplication_column: "UniProt"
            keep: "first"
      
      # 3. Continue with analysis
      - name: analyze_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_key: "combined_proteins"
            identifier_column: "UniProt"