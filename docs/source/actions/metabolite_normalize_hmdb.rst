METABOLITE_NORMALIZE_HMDB
=========================

Normalize and validate HMDB identifiers to standard format.

Purpose
-------

This action standardizes Human Metabolome Database (HMDB) identifiers by:

* Converting various HMDB formats to canonical form
* Validating identifier structure and checksums
* Handling legacy and modern HMDB ID formats
* Removing duplicates and invalid entries
* Providing detailed validation statistics

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Context key containing metabolite data with HMDB identifiers.

**hmdb_column** (string)
  Column name containing HMDB identifiers to normalize.

**output_key** (string)
  Context key to store normalized results.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**strict_validation** (boolean)
  Enforce strict HMDB format validation. Default: true

**keep_invalid** (boolean)
  Retain rows with invalid HMDB IDs (marked). Default: false

**add_prefix** (boolean)
  Add 'HMDB' prefix if missing. Default: true

**output_format** (string)
  Format for normalized IDs: 'HMDB0000001' or '0000001'. Default: 'HMDB0000001'

Example Usage
-------------

Basic Normalization
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: normalize_hmdb
      action:
        type: METABOLITE_NORMALIZE_HMDB
        params:
          input_key: "metabolite_data"
          hmdb_column: "hmdb_id"
          output_key: "normalized_metabolites"
          strict_validation: true

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: normalize_with_options
      action:
        type: METABOLITE_NORMALIZE_HMDB
        params:
          input_key: "raw_metabolites"
          hmdb_column: "metabolite_id"
          output_key: "processed_metabolites"
          strict_validation: false
          keep_invalid: true
          add_prefix: true
          output_format: "HMDB0000001"

Input Format
------------

Accepts various HMDB identifier formats:

.. code-block:: text

    # Supported input formats
    HMDB0000001      # Modern 7-digit format with prefix
    HMDB00001        # Legacy 5-digit format with prefix
    HMDB0001234      # 7-digit with leading zeros
    0000001          # Without prefix
    HMDB 0000001     # With space
    hmdb0000001      # Lowercase
    HMDB0000001.1    # With version

Output Format
-------------

**Normalized Dataset**

.. code-block:: python

    {
        "datasets": {
            "normalized_metabolites": [
                {
                    "metabolite_name": "L-Alanine",
                    "hmdb_id": "HMDB0000161",  # Normalized
                    "hmdb_original": "HMDB00161",  # Original value
                    "hmdb_valid": true,
                    "normalization_status": "normalized"
                },
                # ... more rows
            ]
        }
    }

**Validation Statistics**

.. code-block:: python

    {
        "statistics": {
            "hmdb_normalization": {
                "total_processed": 500,
                "valid_ids": 485,
                "invalid_ids": 15,
                "normalized_count": 450,
                "already_normalized": 35,
                "duplicates_removed": 12,
                "format_distribution": {
                    "HMDB7": 400,  # 7-digit format
                    "HMDB5": 85,   # 5-digit legacy
                    "no_prefix": 15
                }
            }
        }
    }

Validation Rules
----------------

**Valid HMDB Formats**

1. **Modern Format**: HMDB + 7 digits (e.g., HMDB0000001)
2. **Legacy Format**: HMDB + 5 digits (e.g., HMDB00001)
3. **Version Numbers**: Optional .X suffix (e.g., HMDB0000001.1)

**Validation Checks**

* Numeric portion must be valid integer
* No special characters except period for version
* Checksum validation (if enabled)
* Duplicate detection
* Range validation (HMDB0000001 - HMDB9999999)

Error Handling
--------------

**Invalid Identifier Handling**

.. code-block:: yaml

    # With keep_invalid: true
    {
        "hmdb_id": null,
        "hmdb_original": "INVALID123",
        "hmdb_valid": false,
        "normalization_status": "invalid_format",
        "validation_error": "Does not match HMDB pattern"
    }

    # With keep_invalid: false
    # Row is excluded from output

**Common Issues**

* Mixed formats in single column
* Concatenated IDs (HMDB0000001;HMDB0000002)
* Non-standard separators
* Truncated identifiers

Best Practices
--------------

1. **Pre-process data** to handle concatenated IDs
2. **Review validation statistics** to identify data quality issues
3. **Use strict validation** for critical pipelines
4. **Keep invalid entries** during exploratory analysis
5. **Standardize early** in the pipeline for consistency

Performance Notes
-----------------

* Processes ~10,000 IDs per second
* Memory efficient for large datasets
* Parallel processing for batch normalization
* Caches validation results for repeated IDs

Integration Example
-------------------

Complete metabolite processing pipeline:

.. code-block:: yaml

    name: metabolite_standardization
    description: Standardize and validate metabolite identifiers
    
    steps:
      - name: load_metabolites
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/metabolites.csv"
            identifier_column: "compound_id"
            output_key: "raw_metabolites"
      
      - name: extract_identifiers
        action:
          type: METABOLITE_EXTRACT_IDENTIFIERS
          params:
            input_key: "raw_metabolites"
            text_column: "compound_id"
            output_key: "extracted_ids"
      
      - name: normalize_hmdb
        action:
          type: METABOLITE_NORMALIZE_HMDB
          params:
            input_key: "extracted_ids"
            hmdb_column: "hmdb_id"
            output_key: "normalized_metabolites"
            strict_validation: true
      
      - name: export_results
        action:
          type: EXPORT_DATASET
          params:
            input_key: "normalized_metabolites"
            output_file: "/results/normalized_hmdb.tsv"
            format: "tsv"

See Also
--------

* :doc:`metabolite_extract_identifiers` - Extract metabolite IDs from text
* :doc:`metabolite_cts_bridge` - Convert between identifier types
* :doc:`semantic_metabolite_match` - Match metabolites semantically