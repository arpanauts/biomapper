MERGE_WITH_UNIPROT_RESOLUTION
=============================

Merge two datasets with historical UniProt identifier resolution to handle outdated or alternative protein identifiers.

Purpose
-------

This action performs intelligent merging of protein datasets by:

* Resolving historical and obsolete UniProt identifiers
* Handling composite identifiers (e.g., "Q14213_Q8NEV9")  
* Merging datasets based on resolved identifiers
* Preserving data from both source and target datasets

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**source_dataset_key** (string)
  Context key of the source dataset to merge from.

**target_dataset_key** (string)
  Context key of the target dataset to merge into.

**source_id_column** (string)
  Column name containing identifiers in the source dataset.

**target_id_column** (string)
  Column name containing identifiers in the target dataset.

**output_key** (string)
  Key name to store the merged results in the execution context.

Example Usage
-------------

.. code-block:: yaml

    - name: merge_ukbb_hpa
      action:
        type: MERGE_WITH_UNIPROT_RESOLUTION
        params:
          source_dataset_key: "ukbb_proteins"
          target_dataset_key: "hpa_proteins"
          source_id_column: "UniProt"
          target_id_column: "uniprot"
          output_key: "ukbb_hpa_merged"

Resolution Process
------------------

The action performs these steps:

1. **Extract identifiers** from both datasets
2. **Resolve historical IDs** using UniProt API
3. **Handle composite IDs** by splitting and resolving each part
4. **Create mapping** between resolved identifiers
5. **Merge data** based on successful mappings
6. **Track statistics** on resolution success rates

Output Format
-------------

The merged dataset contains combined data from both sources:

.. code-block:: python

    {
        "datasets": {
            "ukbb_hpa_merged": [
                {
                    # Source data fields
                    "protein_name": "AARSD1",
                    "UniProt": "Q9BTE6",
                    # Target data fields  
                    "uniprot": "Q9BTE6",
                    "gene_name": "AARSD1",
                    # Resolution metadata
                    "_merge_status": "exact_match"
                },
                # ... more merged records
            ]
        },
        "metadata": {
            "ukbb_hpa_merged": {
                "total_source_records": 1463,
                "total_target_records": 1825,
                "successful_merges": 1401,
                "merge_rate": 0.958,
                "processing_time_seconds": 45.2,
                "resolution_stats": {
                    "exact_matches": 1389,
                    "historical_resolved": 12,
                    "composite_resolved": 0,
                    "unresolved": 62
                }
            }
        }
    }

Best Practices
--------------

1. **Load datasets first** using LOAD_DATASET_IDENTIFIERS
2. **Use consistent column naming** across strategies
3. **Check merge rates** in results to assess data quality
4. **Handle large datasets** - resolution may take time
5. **Review unresolved identifiers** for data quality improvements

See Also
--------

* :doc:`load_dataset_identifiers` - Load datasets for merging
* :doc:`calculate_set_overlap` - Analyze merged results