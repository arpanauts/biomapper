CHEMISTRY_VENDOR_HARMONIZATION
===============================

Harmonize clinical chemistry tests across different vendor platforms.

Purpose
-------

This action standardizes clinical chemistry data from multiple vendors by:

* Mapping vendor-specific test codes to standard nomenclature
* Harmonizing measurement units across platforms
* Aligning reference ranges to common standards
* Resolving platform-specific naming variations
* Creating unified test catalogs from multiple sources

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Context key containing vendor-specific test data.

**vendor_name** (string)
  Vendor/platform identifier (e.g., 'roche', 'abbott', 'siemens').

**output_key** (string)
  Context key for harmonized results.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**mapping_file** (string)
  Path to vendor-specific mapping configuration. Default: auto-detect

**target_standard** (string)
  Target standard: 'loinc', 'snomed', 'custom'. Default: 'loinc'

**unit_system** (string)
  Target unit system: 'SI', 'conventional', 'both'. Default: 'SI'

**preserve_original** (boolean)
  Keep original vendor values alongside harmonized. Default: true

**strict_mode** (boolean)
  Fail on unmapped tests (vs. pass through). Default: false

**reference_range_strategy** (string)
  Strategy: 'vendor', 'standard', 'population'. Default: 'standard'

Example Usage
-------------

Basic Harmonization
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: harmonize_roche_tests
      action:
        type: CHEMISTRY_VENDOR_HARMONIZATION
        params:
          input_key: "roche_data"
          vendor_name: "roche"
          output_key: "harmonized_tests"
          target_standard: "loinc"

Multi-Vendor Pipeline
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: harmonize_multi_vendor
      action:
        type: CHEMISTRY_VENDOR_HARMONIZATION
        params:
          input_key: "vendor_tests"
          vendor_name: "abbott"
          output_key: "unified_tests"
          mapping_file: "/config/abbott_mappings.yaml"
          unit_system: "both"
          preserve_original: true
          reference_range_strategy: "population"

Vendor Mapping Configuration
-----------------------------

**Mapping File Structure**

.. code-block:: yaml

    vendor: abbott
    version: "2.1"
    mappings:
      - vendor_code: "GLU_01"
        vendor_name: "Glucose"
        standard_name: "Glucose in Serum or Plasma"
        loinc_code: "2345-7"
        unit_conversion:
          from: "mg/dL"
          to_si: "mmol/L"
          factor: 0.0555
        reference_range:
          conventional: "70-100 mg/dL"
          si: "3.9-5.6 mmol/L"
      
      - vendor_code: "CHOL_T"
        vendor_name: "Total Cholesterol"
        standard_name: "Cholesterol Total"
        loinc_code: "2093-3"
        unit_conversion:
          from: "mg/dL"
          to_si: "mmol/L"
          factor: 0.0259

Input Format
------------

**Vendor-Specific Data**

.. code-block:: python

    [
        {
            "test_code": "GLU_01",
            "test_name": "Glucose",
            "result": "95",
            "units": "mg/dL",
            "ref_low": "70",
            "ref_high": "100",
            "platform": "ARCHITECT c16000"
        }
    ]

Output Format
-------------

**Harmonized Results**

.. code-block:: python

    {
        "datasets": {
            "harmonized_tests": [
                {
                    # Harmonized fields
                    "standard_name": "Glucose in Serum or Plasma",
                    "loinc_code": "2345-7",
                    "value_si": 5.27,
                    "units_si": "mmol/L",
                    "value_conventional": 95,
                    "units_conventional": "mg/dL",
                    
                    # Original vendor data
                    "vendor_code": "GLU_01",
                    "vendor_name": "Glucose",
                    "vendor_platform": "ARCHITECT c16000",
                    
                    # Harmonization metadata
                    "harmonization_version": "2.1",
                    "mapping_confidence": "high",
                    "unit_converted": true
                }
            ]
        }
    }

**Harmonization Statistics**

.. code-block:: python

    {
        "statistics": {
            "vendor_harmonization": {
                "vendor": "abbott",
                "total_tests": 250,
                "successfully_mapped": 245,
                "unmapped": 5,
                "mapping_rate": 0.98,
                "unit_conversions": 180,
                "reference_ranges_aligned": 240,
                "unmapped_codes": [
                    "CUSTOM_01",
                    "RESEARCH_42"
                ]
            }
        }
    }

Supported Vendors
-----------------

**Major Platforms**

* **Roche**: Cobas series
* **Abbott**: ARCHITECT, Alinity
* **Siemens**: ADVIA, Dimension
* **Beckman Coulter**: AU series, DxC
* **Ortho Clinical**: VITROS
* **Custom**: User-defined mappings

Unit Conversions
----------------

**Common Conversions**

.. list-table::
   :header-rows: 1
   :widths: 30 30 20 20

   * - Test
     - Conventional
     - SI
     - Factor
   * - Glucose
     - mg/dL
     - mmol/L
     - 0.0555
   * - Cholesterol
     - mg/dL
     - mmol/L
     - 0.0259
   * - Creatinine
     - mg/dL
     - μmol/L
     - 88.4
   * - Hemoglobin
     - g/dL
     - g/L
     - 10

Error Handling
--------------

**Unmapped Tests**

.. code-block:: python

    # With strict_mode: false
    {
        "test_code": "CUSTOM_01",
        "harmonization_status": "unmapped",
        "original_preserved": true
    }
    
    # With strict_mode: true
    # Raises ValidationError

Best Practices
--------------

1. **Maintain vendor mapping files** with version control
2. **Validate mappings** with clinical experts
3. **Use both unit systems** for international collaboration
4. **Document custom tests** that lack standard codes
5. **Regular updates** as vendors change test catalogs

Performance Notes
-----------------

* Caches vendor mappings for repeated use
* Batch processes unit conversions efficiently
* Supports incremental updates to mappings
* Thread-safe for concurrent processing

Integration Example
-------------------

.. code-block:: yaml

    name: multi_vendor_harmonization
    description: Unify tests from multiple laboratory platforms
    
    steps:
      - name: load_roche
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/roche_results.csv"
            identifier_column: "sample_id"
            output_key: "roche_raw"
      
      - name: harmonize_roche
        action:
          type: CHEMISTRY_VENDOR_HARMONIZATION
          params:
            input_key: "roche_raw"
            vendor_name: "roche"
            output_key: "roche_harmonized"
      
      - name: load_abbott
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/abbott_results.csv"
            identifier_column: "sample_id"
            output_key: "abbott_raw"
      
      - name: harmonize_abbott
        action:
          type: CHEMISTRY_VENDOR_HARMONIZATION
          params:
            input_key: "abbott_raw"
            vendor_name: "abbott"
            output_key: "abbott_harmonized"
      
      - name: merge_harmonized
        action:
          type: MERGE_DATASETS
          params:
            dataset_keys: ["roche_harmonized", "abbott_harmonized"]
            output_key: "unified_chemistry"
            merge_strategy: "union"

See Also
--------

* :doc:`chemistry_extract_loinc` - Extract LOINC codes
* :doc:`chemistry_fuzzy_test_match` - Fuzzy match test names
* :doc:`merge_datasets` - Combine harmonized results