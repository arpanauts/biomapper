:orphan:

CHEMISTRY_FUZZY_TEST_MATCH
===========================

Fuzzy matching for clinical chemistry test names and descriptions.

Purpose
-------

This action performs intelligent fuzzy matching for clinical chemistry tests by:

* Matching test names using multiple algorithms (Levenshtein, Jaro-Winkler, token-based)
* Handling abbreviations and synonyms in clinical test nomenclature
* Normalizing units and reference ranges
* Resolving ambiguous test mappings
* Supporting LOINC code cross-referencing

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Context key containing source chemistry test data.

**target_key** (string)
  Context key containing target reference test database.

**output_key** (string)
  Context key to store matched results.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**test_name_column** (string)
  Column containing test names in source data. Default: "test_name"

**match_threshold** (float)
  Minimum similarity score for matches (0.0-1.0). Default: 0.85

**matching_strategy** (string)
  Strategy: 'best_match', 'all_above_threshold', 'top_n'. Default: 'best_match'

**top_n** (integer)
  Number of top matches to return (if strategy='top_n'). Default: 3

**use_abbreviations** (boolean)
  Enable abbreviation expansion (e.g., 'Hgb' → 'Hemoglobin'). Default: true

**use_synonyms** (boolean)
  Enable synonym matching from clinical dictionaries. Default: true

**normalize_units** (boolean)
  Standardize measurement units before matching. Default: true

Example Usage
-------------

Basic Fuzzy Matching
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: match_chemistry_tests
      action:
        type: CHEMISTRY_FUZZY_TEST_MATCH
        params:
          input_key: "lab_tests"
          target_key: "reference_tests"
          output_key: "matched_tests"
          match_threshold: 0.85

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: comprehensive_matching
      action:
        type: CHEMISTRY_FUZZY_TEST_MATCH
        params:
          input_key: "clinical_chemistry"
          target_key: "loinc_database"
          output_key: "matched_chemistry"
          test_name_column: "assay_name"
          match_threshold: 0.80
          matching_strategy: "top_n"
          top_n: 5
          use_abbreviations: true
          use_synonyms: true
          normalize_units: true

Input Format
------------

**Source Test Data**

.. code-block:: python

    [
        {
            "test_name": "Glucose, Serum",
            "value": "95",
            "units": "mg/dL",
            "reference_range": "70-100"
        },
        {
            "test_name": "Hgb",  # Abbreviation
            "value": "14.5",
            "units": "g/dl",
            "reference_range": "13.5-17.5"
        }
    ]

**Target Reference Database**

.. code-block:: python

    [
        {
            "standard_name": "Glucose in Serum or Plasma",
            "loinc_code": "2345-7",
            "units": "mg/dL",
            "synonyms": ["Blood Glucose", "Serum Glucose"]
        },
        {
            "standard_name": "Hemoglobin",
            "loinc_code": "718-7",
            "units": "g/dL",
            "abbreviations": ["Hgb", "Hb"]
        }
    ]

Output Format
-------------

**Matched Results**

.. code-block:: python

    {
        "datasets": {
            "matched_tests": [
                {
                    # Original fields
                    "test_name": "Glucose, Serum",
                    "value": "95",
                    "units": "mg/dL",
                    
                    # Match metadata
                    "matched_name": "Glucose in Serum or Plasma",
                    "loinc_code": "2345-7",
                    "match_score": 0.92,
                    "match_method": "fuzzy_token",
                    "match_confidence": "high",
                    
                    # Normalized values
                    "normalized_units": "mg/dL",
                    "standardized_value": 95.0
                }
            ]
        }
    }

**Matching Statistics**

.. code-block:: python

    {
        "statistics": {
            "fuzzy_matching": {
                "total_tests": 150,
                "matched": 142,
                "unmatched": 8,
                "match_rate": 0.947,
                "confidence_distribution": {
                    "high": 120,
                    "medium": 22,
                    "low": 0
                },
                "method_usage": {
                    "exact": 45,
                    "abbreviation": 28,
                    "synonym": 15,
                    "fuzzy_token": 54
                }
            }
        }
    }

Matching Algorithms
-------------------

**Matching Methods (in order)**

1. **Exact Match**: Direct string comparison
2. **Abbreviation Expansion**: Hgb → Hemoglobin
3. **Synonym Matching**: Uses clinical dictionaries
4. **Token-Based Fuzzy**: Compares word tokens
5. **Levenshtein Distance**: Character-level similarity
6. **Jaro-Winkler**: Optimized for short strings

**Confidence Scoring**

* **High** (>0.90): Exact or near-exact matches
* **Medium** (0.80-0.90): Good fuzzy matches
* **Low** (<0.80): Weak matches (if above threshold)

Best Practices
--------------

1. **Start with higher thresholds** (0.85+) and adjust based on results
2. **Review unmatched tests** to identify missing synonyms
3. **Use top_n strategy** for manual validation workflows
4. **Enable all normalization options** for heterogeneous data
5. **Validate LOINC codes** when available

Performance Notes
-----------------

* Optimized for datasets with <10,000 tests
* Uses indexed search for large reference databases
* Caches abbreviation and synonym lookups
* Parallel processing for batch matching

Integration Example
-------------------

.. code-block:: yaml

    name: clinical_chemistry_pipeline
    description: Map clinical chemistry tests to standards
    
    steps:
      - name: load_lab_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/lab_results.csv"
            identifier_column: "patient_id"
            output_key: "lab_data"
      
      - name: extract_loinc
        action:
          type: CHEMISTRY_EXTRACT_LOINC
          params:
            input_key: "lab_data"
            output_key: "loinc_extracted"
      
      - name: fuzzy_match
        action:
          type: CHEMISTRY_FUZZY_TEST_MATCH
          params:
            input_key: "loinc_extracted"
            target_key: "loinc_reference"
            output_key: "matched_tests"
            match_threshold: 0.85
      
      - name: export_results
        action:
          type: EXPORT_DATASET
          params:
            input_key: "matched_tests"
            output_file: "/results/matched_chemistry.xlsx"
            format: "excel"

See Also
--------

* :doc:`chemistry_extract_loinc` - Extract LOINC codes
* :doc:`chemistry_vendor_harmonization` - Harmonize vendor-specific tests
* :doc:`calculate_mapping_quality` - Assess match quality