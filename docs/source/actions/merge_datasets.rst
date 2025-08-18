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
  List of dataset keys to merge from the execution context. For backward compatibility, also supports `input_key` and `dataset2_key` for two-dataset merges.

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
  Column name to join on when using 'join' strategy with uniform columns. Alternative to `join_columns`.
  Default: None

**join_columns** (dict)
  Map of dataset_key to column name for joins when datasets have different column names.
  Example: {"dataset1": "id", "dataset2": "identifier"}
  Default: None

**join_how** (string)
  Type of join to perform: 'inner', 'outer', 'left', 'right'.
  Default: 'outer'

**handle_one_to_many** (string)
  How to handle one-to-many relationships: 'keep_all', 'first', 'aggregate'.
  Default: 'keep_all'

**aggregate_func** (string)
  Aggregation function when handle_one_to_many='aggregate' (e.g., 'mean', 'sum', 'first').
  Default: None

**add_provenance** (boolean)
  Whether to add a provenance column tracking the source dataset for each row.
  Default: false

**provenance_value** (string)
  Custom value for the provenance column when add_provenance=true.
  Default: None (uses dataset key as value)

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
          merge_strategy: "concat"
          deduplication_column: "uniprot_id"
          keep: "first"
          add_provenance: true

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
          join_columns: {
            "protein_data": "uniprot_id",
            "protein_annotations": "protein_id"
          }
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
  Stacks datasets vertically, preserving all columns from all datasets. Missing columns are filled with NaN. Supports provenance tracking to identify source dataset for each row.

**Join (join)**
  Merges datasets horizontally based on common columns. Supports different column names per dataset via `join_columns`. Column conflicts are resolved with suffixes (_x, _y).

Deduplication Options
---------------------

**keep='first'**
  Keeps the first occurrence of each duplicate identifier.

**keep='last'**
  Keeps the last occurrence of each duplicate identifier.

**keep='all'**
  Keeps all rows (no deduplication performed).

One-to-Many Handling
--------------------

**handle_one_to_many='keep_all'**
  Preserves all matching rows in one-to-many relationships.

**handle_one_to_many='first'**
  Keeps only the first match in one-to-many relationships.

**handle_one_to_many='aggregate'**
  Aggregates multiple matches using specified aggregation function.

Error Handling
--------------

**Missing datasets**
  .. code-block::
  
      Warning: Dataset 'missing_data' not found in context
      
  Solution: Verify dataset keys exist in context from previous actions.

**Join column missing**
  .. code-block::
  
      Error: join_columns or join_on required when merge_strategy='join'
      
  Solution: Specify either `join_on` for uniform columns or `join_columns` for different column names per dataset.

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
* Uses UniversalContext for robust context handling across different execution environments
* Supports both legacy parameter formats and new standardized formats for backward compatibility

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
            input_key: "combined_proteins"
            source_name: "UKBB"
            target_name: "ARV"
            mapping_combo_id: "UKBB_ARV"
            output_key: "overlap_stats"

Backward Compatibility
----------------------

The action supports legacy parameter formats for seamless migration:

**Legacy Two-Dataset Format**
  .. code-block:: yaml
  
      params:
        input_key: "dataset1"         # Mapped to dataset_keys[0]
        dataset2_key: "dataset2"      # Mapped to dataset_keys[1]
        join_column1: "id"            # Mapped to join_columns
        join_column2: "identifier"
        join_type: "outer"            # Mapped to join_how
        
      # Alternative legacy format:
      params:
        dataset1_key: "dataset1"      # Alias for input_key
        dataset2_key: "dataset2"

**Modern Multi-Dataset Format**
  .. code-block:: yaml
  
      params:
        dataset_keys: ["dataset1", "dataset2", "dataset3"]
        join_columns: {
          "dataset1": "id",
          "dataset2": "identifier",
          "dataset3": "uid"
        }
        join_how: "outer"

---

## Verification Sources
*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/merge_datasets.py` (implementation with backward compatibility and parameter validation)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class and StandardActionResult)
- `/biomapper/src/actions/registry.py` (action registration via decorator)
- `/biomapper/src/core/standards/context_handler.py` (UniversalContext for robust context handling)
- `/biomapper/tests/unit/core/strategy_actions/test_merge_datasets_fix.py` (test coverage and validation)
- `/biomapper/CLAUDE.md` (standardized parameter naming and context handling patterns)