NIGHTINGALE_NMR_MATCH
====================

Match Nightingale NMR biomarkers to standard identifiers (HMDB/LOINC) with specialized platform knowledge.

Purpose
-------

This action provides specialized matching for UK Biobank NMR metabolomics data from the Nightingale Health platform. It offers:

* Exact matching for known Nightingale biomarkers
* Fuzzy matching for naming variations
* Lipoprotein particle pattern recognition
* Abbreviation expansion and standardization
* Category classification (lipids, amino acids, etc.)
* Unit standardization
* Integration with external reference files

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Dataset key from context containing Nightingale biomarker data.

**output_key** (string)
  Key where matched results will be stored in context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**biomarker_column** (string)
  Column containing Nightingale biomarker names.
  Default: "biomarker"

**unit_column** (string)
  Column containing measurement units (optional).
  Default: None

**reference_file** (string)
  Path to Nightingale reference mapping file.
  Default: "/procedure/data/local_data/references/nightingale_nmr_reference.csv"

**use_cached_reference** (boolean)
  Cache reference file in memory for performance.
  Default: true

**target_format** (string)
  Target identifier format: 'hmdb', 'loinc', or 'both'.
  Default: "hmdb"

**match_threshold** (float)
  Fuzzy match threshold for biomarker names (0.0-1.0).
  Default: 0.85

**use_abbreviations** (boolean)
  Expand and match common abbreviations.
  Default: true

**case_sensitive** (boolean)
  Case-sensitive matching.
  Default: false

**add_metadata** (boolean)
  Add Nightingale metadata columns to output.
  Default: true

**include_units** (boolean)
  Include standardized units in output.
  Default: true

**include_categories** (boolean)
  Include biomarker categories in output.
  Default: true

Built-in Biomarker Patterns
---------------------------

The action includes built-in patterns for common Nightingale biomarkers:

**Lipids and Lipoproteins**
* Total_C (Total cholesterol) → HMDB0000067, LOINC 2093-3
* LDL_C (LDL cholesterol) → HMDB0000067, LOINC 13457-7
* HDL_C (HDL cholesterol) → HMDB0000067, LOINC 2085-9
* Triglycerides → HMDB0000827, LOINC 2571-8

**Apolipoproteins**
* ApoA1 (Apolipoprotein A1) → LOINC 1869-7
* ApoB (Apolipoprotein B) → LOINC 1884-6

**Amino Acids**
* Ala (Alanine) → HMDB0000161, LOINC 1916-6
* Gln (Glutamine) → HMDB0000641, LOINC 14681-2

**Metabolic Markers**
* Glucose → HMDB0000122, LOINC 2345-7
* Lactate → HMDB0000190, LOINC 2524-7
* bOHbutyrate (Beta-hydroxybutyrate) → HMDB0000357, LOINC 53060-9

**Inflammation**
* GlycA (Glycoprotein acetyls) → No standard IDs (Nightingale-specific)

Lipoprotein Particle Patterns
------------------------------

The action recognizes complex lipoprotein particle naming patterns:

* **VLDL particles**: XXL_VLDL_*, XL_VLDL_*, L_VLDL_*, etc.
* **LDL particles**: L_LDL_*, M_LDL_*, S_LDL_*
* **HDL particles**: XL_HDL_*, L_HDL_*, M_HDL_*, S_HDL_*

Each pattern includes appropriate units (nmol/L for particles, mmol/L for concentrations).

Example Usage
-------------

Basic HMDB Matching
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: match_nmr_biomarkers
      action:
        type: NIGHTINGALE_NMR_MATCH
        params:
          input_key: "ukbb_nmr_data"
          output_key: "matched_biomarkers"
          biomarker_column: "biomarker_name"
          target_format: "hmdb"
          match_threshold: 0.85

LOINC Code Mapping
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: map_to_loinc
      action:
        type: NIGHTINGALE_NMR_MATCH
        params:
          input_key: "clinical_metabolites"
          output_key: "loinc_mapped"
          biomarker_column: "test_name"
          target_format: "loinc"
          include_units: true
          include_categories: true

Both HMDB and LOINC
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: comprehensive_mapping
      action:
        type: NIGHTINGALE_NMR_MATCH
        params:
          input_key: "nmr_metabolomics"
          output_key: "fully_mapped"
          target_format: "both"
          add_metadata: true
          use_abbreviations: true

Custom Reference File
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: custom_nightingale_match
      action:
        type: NIGHTINGALE_NMR_MATCH
        params:
          input_key: "biomarker_data"
          output_key: "custom_matched"
          reference_file: "/data/custom_nightingale_reference.csv"
          use_cached_reference: false
          match_threshold: 0.90

Strict Matching
~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: exact_matches_only
      action:
        type: NIGHTINGALE_NMR_MATCH
        params:
          input_key: "quality_controlled_data"
          output_key: "exact_matches"
          match_threshold: 1.0  # Only exact matches
          use_abbreviations: false
          case_sensitive: true

Input Data Format
-----------------

**Expected biomarker data structure:**
.. code-block:: python

    [
        {
            "biomarker": "Total_C",
            "value": 5.2,
            "unit": "mmol/L",
            "sample_id": "UKB_001"
        },
        {
            "biomarker": "Ala",
            "value": 0.45,
            "unit": "mmol/L", 
            "sample_id": "UKB_002"
        },
        {
            "biomarker": "XXL_VLDL_P",
            "value": 1.8,
            "unit": "nmol/L",
            "sample_id": "UKB_003"
        }
    ]

Output Format
-------------

**HMDB format output:**
.. code-block:: python

    [
        {
            "original_biomarker": "Total_C",
            "matched_name": "Total_C",
            "hmdb_id": "HMDB0000067",
            "description": "Total cholesterol",
            "category": "lipids",
            "unit": "mmol/L",
            "confidence": 1.0,
            "value": 5.2,
            "sample_id": "UKB_001"
        },
        {
            "original_biomarker": "Ala",
            "matched_name": "Ala", 
            "hmdb_id": "HMDB0000161",
            "description": "Alanine",
            "category": "amino_acids",
            "unit": "mmol/L",
            "confidence": 1.0,
            "value": 0.45,
            "sample_id": "UKB_002"
        }
    ]

**Both HMDB and LOINC format:**
.. code-block:: python

    [
        {
            "original_biomarker": "Total_C",
            "matched_name": "Total_C",
            "hmdb_id": "HMDB0000067",
            "loinc_code": "2093-3",
            "description": "Total cholesterol",
            "category": "lipids",
            "unit": "mmol/L",
            "confidence": 1.0,
            "value": 5.2,
            "sample_id": "UKB_001"
        }
    ]

Reference File Format
---------------------

If using a custom reference file, it should follow this CSV structure:

.. code-block:: csv

    nightingale_name,hmdb_id,loinc_code,description,category,unit
    Total_C,HMDB0000067,2093-3,Total cholesterol,lipids,mmol/L
    LDL_C,HMDB0000067,13457-7,LDL cholesterol,lipids,mmol/L
    Ala,HMDB0000161,1916-6,Alanine,amino_acids,mmol/L
    GlycA,,,"Glycoprotein acetyls",inflammation,mmol/L

Matching Algorithm
------------------

The action uses a multi-step matching approach:

1. **Exact match** against reference file or built-in patterns
2. **Lipoprotein pattern matching** for particle measurements
3. **Fuzzy matching** with abbreviation expansion
4. **Confidence scoring** based on match quality

Abbreviation Expansion
----------------------

Common abbreviations are automatically expanded:

* C → cholesterol
* TG → triglycerides  
* PL → phospholipids
* P → particles
* XXL/XL/L/M/S → size descriptors

Statistics and Metadata
------------------------

The action provides comprehensive matching statistics:

.. code-block:: python

    {
        "statistics": {
            "nightingale_nmr_match": {
                "total_biomarkers": 150,
                "matched_biomarkers": 142,
                "match_rate": 0.947,
                "category_breakdown": {
                    "lipids": 65,
                    "amino_acids": 22,
                    "glycolysis": 18,
                    "lipoproteins": 25,
                    "inflammation": 8,
                    "unknown": 4
                }
            }
        }
    }

Error Handling
--------------

**Dataset not found**
  .. code-block::
  
      Error: Dataset 'missing_data' not found in context
      
  Solution: Verify input_key exists in context datasets.

**Missing biomarker column**
  .. code-block::
  
      Error: Column 'biomarker' not found in dataset
      
  Solution: Check biomarker_column parameter matches dataset structure.

**Reference file issues**
  .. code-block::
  
      Warning: Reference file not found, using built-in patterns only
      
  Solution: Verify reference file path or rely on built-in patterns.

Best Practices
--------------

1. **Use appropriate target format** - HMDB for metabolomics, LOINC for clinical
2. **Adjust match threshold** based on data quality - higher for clean data
3. **Enable abbreviation expansion** for varied naming conventions
4. **Include metadata** for comprehensive biomarker annotation
5. **Cache reference files** for repeated strategy executions
6. **Validate match rates** - low rates may indicate data format issues

Performance Notes
-----------------

* Built-in patterns provide fast exact matching
* Fuzzy matching adds computational overhead but improves coverage
* Reference file caching significantly improves repeated execution
* Memory usage scales with dataset size and reference complexity

Common Use Cases
----------------

**UK Biobank NMR Processing**
  Map Nightingale biomarker names to standard metabolomics identifiers

**Clinical Data Integration**
  Convert platform-specific names to standardized clinical codes

**Multi-Platform Studies**
  Harmonize biomarker names across different NMR platforms

**Metabolomics Database Mapping**
  Prepare data for integration with metabolomics databases

Integration
-----------

This action typically follows data loading and precedes metabolomics analysis:

.. code-block:: yaml

    steps:
      # 1. Load Nightingale NMR data
      - name: load_nmr_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/ukbb_nmr_biomarkers.csv"
            identifier_column: "biomarker"
            output_key: "raw_nmr"
      
      # 2. Match to standard identifiers
      - name: standardize_biomarkers
        action:
          type: NIGHTINGALE_NMR_MATCH
          params:
            input_key: "raw_nmr"
            output_key: "standardized_nmr"
            target_format: "both"
            match_threshold: 0.85
      
      # 3. Continue with metabolomics analysis
      - name: analyze_metabolites
        action:
          type: SEMANTIC_METABOLITE_MATCH
          params:
            input_key: "standardized_nmr"
            target_database: "hmdb"