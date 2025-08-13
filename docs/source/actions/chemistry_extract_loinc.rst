chemistry_extract_loinc
=======================

The ``CHEMISTRY_EXTRACT_LOINC`` action extracts and validates LOINC (Logical Observation Identifiers Names and Codes) from clinical chemistry data.

Overview
--------

LOINC is the universal standard for identifying medical laboratory observations. This action handles various LOINC formats from different vendors and validates extracted codes:

- **Standard format**: 12345-6  
- **With prefixes**: LOINC:12345-6, LN:12345-6
- **Vendor-specific formats**: Test names with embedded LOINC codes
- **Missing/malformed codes**: Maps common test names to LOINC

The action supports multiple vendors including LabCorp, Quest, Mayo, Arivale, Israeli10k, and UKBB.

Parameters
----------

.. code-block:: yaml

   action:
     type: CHEMISTRY_EXTRACT_LOINC
     params:
       input_key: "chemistry_data"
       output_key: "loinc_extracted"
       loinc_column: "loinc_code"
       test_name_column: "test_name"
       vendor: "labcorp"
       validate_format: true
       extract_from_name: true
       use_fallback_mapping: true

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** : str
    Dataset key from context containing chemistry data

**output_key** : str
    Where to store the dataset with extracted LOINC codes

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**loinc_column** : str, default=None
    Column containing LOINC codes

**test_name_column** : str, default=None
    Column with test names for fallback mapping

**test_id_column** : str, default=None
    Column with vendor-specific test IDs

**vendor** : str, default="generic"
    Vendor type: "arivale", "labcorp", "quest", "mayo", "israeli10k", "ukbb", "generic"

**vendor_mapping_file** : str, default=None
    Path to vendor-specific LOINC mapping file

**validate_format** : bool, default=True
    Validate LOINC format (12345-6 pattern)

**validate_checksum** : bool, default=False
    Validate LOINC check digit using mod-10 algorithm

**extract_from_name** : bool, default=True
    Try to extract LOINC from test names

**use_fallback_mapping** : bool, default=True
    Use built-in test name to LOINC mapping

**add_extraction_log** : bool, default=True
    Add columns showing extraction source and validation

LOINC Format Validation
-----------------------

The action validates LOINC codes using multiple patterns:

**Standard Format**
- Pattern: ``^\d{1,5}-\d{1}$``
- Example: 2345-7, 13457-7

**With Prefixes**  
- LOINC:2345-7 → 2345-7
- LN:13457-7 → 13457-7
- loinc:2571-8 → 2571-8

**Embedded in Text**
- "Glucose, Serum (2345-7)" → 2345-7
- "Test ID: LOINC:2571-8" → 2571-8

**Checksum Validation**
When enabled, validates the check digit using LOINC's mod-10 algorithm.

Vendor-Specific Extraction
--------------------------

Arivale Format
~~~~~~~~~~~~~~
- Format: "Test Name (LOINC)"
- Example: "Glucose, Serum (2345-7)" → 2345-7

LabCorp Format
~~~~~~~~~~~~~~
- Separate LOINC column
- Test codes with LC prefix
- Example: LC001453 → lookup in mapping file

Quest Format
~~~~~~~~~~~~
- Test codes with QD prefix
- Requires mapping file
- Example: QD483 → 2345-7 (glucose)

Mayo Clinic Format
~~~~~~~~~~~~~~~~~~
- Abbreviated test codes
- Pattern: [A-Z]{2,4}\d{0,4}
- Example: GLU → 2345-7 (glucose)

UKBB Format
~~~~~~~~~~~
- Field IDs as test identifiers
- Pattern: ^\d{5}$
- Example: 30740 → 2345-7 (glucose)

Built-in Test Mappings
----------------------

The action includes mappings for common clinical chemistry tests:

.. code-block:: python

   {
       # Glucose tests
       "glucose": "2345-7",
       "glucose, serum": "2345-7", 
       "glucose, fasting": "1558-6",
       "blood sugar": "2345-7",
       
       # Cholesterol tests
       "cholesterol": "2093-3",
       "cholesterol, total": "2093-3",
       "ldl cholesterol": "13457-7",
       "hdl cholesterol": "2085-9",
       
       # Liver function
       "alt": "1742-6",
       "ast": "1920-8",
       "alkaline phosphatase": "6768-6",
       "bilirubin, total": "1975-2",
       
       # Kidney function  
       "creatinine": "2160-0",
       "bun": "3094-0",
       "egfr": "33914-3"
   }

Example Usage
-------------

Basic LOINC Extraction
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_loinc_codes
       action:
         type: CHEMISTRY_EXTRACT_LOINC
         params:
           input_key: "lab_results"
           loinc_column: "loinc"
           test_name_column: "test_name"
           validate_format: true
           output_key: "loinc_validated"

Vendor-Specific Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_arivale_loinc
       action:
         type: CHEMISTRY_EXTRACT_LOINC
         params:
           input_key: "arivale_data"
           vendor: "arivale"
           test_name_column: "Test"
           extract_from_name: true
           validate_format: true
           output_key: "arivale_loinc"

Multi-Source Extraction
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_with_fallback
       action:
         type: CHEMISTRY_EXTRACT_LOINC
         params:
           input_key: "mixed_lab_data"
           loinc_column: "LOINC_Code"        # Try direct column first
           test_name_column: "Test_Name"      # Then try name mapping
           test_id_column: "Vendor_Test_ID"   # Finally try vendor mapping
           vendor: "quest"
           vendor_mapping_file: "/data/quest_loinc_mapping.csv"
           extract_from_name: true
           use_fallback_mapping: true
           validate_checksum: true
           output_key: "comprehensive_loinc"

Output Format
-------------

The action outputs the original dataset with added LOINC information:

.. code-block::

   Original Columns + extracted_loinc + (optional) extraction metadata

Example output with logging:

.. code-block::

   test_name          | original_loinc | extracted_loinc | loinc_extraction_source | loinc_valid
   Glucose, Serum     | 2345-7         | 2345-7          | direct_column          | true
   Cholesterol        |                | 2093-3          | test_name_mapping      | true  
   Test (1742-6)      |                | 1742-6          | vendor_arivale         | true
   Unknown Test       |                |                 |                        | false

Statistics Tracking
-------------------

Detailed extraction statistics are provided:

.. code-block:: python

   {
       "total_rows": 1000,
       "rows_with_loinc": 850,
       "extraction_rate": 0.85,
       "valid_loinc_codes": 845,
       "invalid_loinc_codes": 5,
       "extraction_sources": {
           "direct_column": 600,
           "vendor_specific": 150,
           "test_name_mapping": 100,
           "no_extraction": 150
       }
   }

Validation Features
-------------------

Format Validation
~~~~~~~~~~~~~~~~~
- Validates LOINC pattern: \d{1,5}-\d{1}
- Removes common prefixes automatically
- Handles various text encodings

Checksum Validation
~~~~~~~~~~~~~~~~~~
- Implements LOINC mod-10 algorithm
- Validates check digit accuracy
- Optional feature for strict validation

Clinical Chemistry Filter
~~~~~~~~~~~~~~~~~~~~~~~~~
- Focuses on relevant LOINC classes: CHEM, HEM/BC, COAG, UA
- Filters out non-chemistry codes
- Ensures clinical relevance

Error Handling
--------------

The action handles various data quality issues:

- **Missing columns**: Graceful degradation to available sources
- **Invalid formats**: Logs warnings but continues processing
- **Empty values**: Skips null/empty entries
- **Vendor mismatches**: Falls back to generic extraction

Best Practices
--------------

1. **Use multiple extraction sources**: Combine direct columns, vendor mappings, and name fallbacks
2. **Validate aggressively**: Enable format and checksum validation for clinical data
3. **Keep extraction logs**: Track sources for audit and quality assessment
4. **Handle vendor variations**: Use appropriate vendor settings for optimal extraction
5. **Review unmapped tests**: Analyze failed extractions to improve mappings

Integration Examples
--------------------

With Test Harmonization
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_loinc
       action:
         type: CHEMISTRY_EXTRACT_LOINC
         params:
           input_key: "raw_lab_data"
           vendor: "labcorp"
           output_key: "loinc_extracted"

     - name: harmonize_tests
       action:
         type: CHEMISTRY_FUZZY_TEST_MATCH
         params:
           source_key: "loinc_extracted"
           target_key: "reference_tests"
           output_key: "harmonized_chemistry"

With Vendor Harmonization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_loinc_codes
       action:
         type: CHEMISTRY_EXTRACT_LOINC
         params:
           input_key: "multi_vendor_data"
           vendor: "auto"  # Auto-detect vendor
           output_key: "loinc_standardized"

     - name: harmonize_vendors
       action:
         type: CHEMISTRY_VENDOR_HARMONIZATION
         params:
           input_key: "loinc_standardized"
           standardize_test_names: true
           output_key: "fully_harmonized"

Performance Notes
-----------------

- **Regex optimization**: Compiled patterns for fast validation
- **Caching**: Vendor mappings cached for repeated use  
- **Batch processing**: Efficient handling of large datasets
- **Memory management**: Processes data in-place when possible

The LOINC extraction action provides robust, vendor-aware extraction of clinical chemistry test identifiers with comprehensive validation and mapping capabilities.