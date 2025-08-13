protein_normalize_accessions
============================

The ``PROTEIN_NORMALIZE_ACCESSIONS`` action standardizes UniProt accession identifiers to ensure consistent formatting across protein datasets.

Overview
--------

UniProt accessions can appear in various formats that need normalization:

- Different cases (P12345 vs p12345)
- Various prefixes (sp|P12345|GENE, tr|Q67890|PROTEIN)
- Version suffixes (P12345.1, P12345.2)
- Isoform suffixes (P12345-1, P12345-2)

This action normalizes these variations to a consistent format for accurate protein matching.

Parameters
----------

.. code-block:: yaml

   action:
     type: PROTEIN_NORMALIZE_ACCESSIONS
     params:
       input_key: "protein_data"
       id_columns: ["uniprot_id", "accession"]
       strip_isoforms: true
       strip_versions: true
       validate_format: true
       output_key: "normalized_proteins"
       add_normalization_log: true

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** : str
    Dataset key from context['datasets'] containing protein identifiers

**id_columns** : list[str]
    Column names containing UniProt IDs to normalize

**output_key** : str
    Where to store the normalized dataset

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**strip_isoforms** : bool, default=True
    Remove isoform suffixes (-1, -2, etc.)

**strip_versions** : bool, default=True
    Remove version numbers (.1, .2, etc.)

**validate_format** : bool, default=True
    Validate UniProt ID format and flag invalid entries

**add_normalization_log** : bool, default=True
    Add columns showing what was normalized

Normalization Rules
-------------------

1. **Case Normalization**: All accessions converted to uppercase
2. **Prefix Removal**: Common prefixes are stripped:
   - sp|P12345|GENE → P12345
   - tr|Q67890|PROTEIN → Q67890
   - UniProt:P12345 → P12345

3. **Version Removal**: Version suffixes removed if enabled:
   - P12345.1 → P12345
   - Q67890.2 → Q67890

4. **Isoform Handling**: Isoform suffixes removed if enabled:
   - P12345-1 → P12345
   - Q67890-2 → Q67890

5. **Format Validation**: Validates against UniProt pattern:
   - Standard: [A-Z][0-9][A-Z0-9]{4,8}
   - Examples: P12345, Q123A5, A0A123456

Example Usage
-------------

Basic Normalization
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_uniprot_ids
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "raw_protein_data"
           id_columns: ["protein_id"]
           output_key: "normalized_proteins"

Multiple Columns with Detailed Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_multiple_columns
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "protein_annotations"
           id_columns: ["primary_accession", "secondary_accession", "related_proteins"]
           strip_isoforms: true
           strip_versions: true
           validate_format: true
           add_normalization_log: true
           output_key: "clean_proteins"

Conservative Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: conservative_normalize
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "sensitive_protein_data"
           id_columns: ["uniprot_id"]
           strip_isoforms: false  # Keep isoform information
           strip_versions: false  # Keep version information
           validate_format: false # Don't reject potentially valid IDs
           output_key: "conservatively_normalized"

Output Format
-------------

The action outputs a dataset with normalized identifiers and optional logging columns:

.. code-block::

   original_data + normalized columns + (optional) logging columns

Example output with logging enabled:

.. code-block::

   protein_name    | uniprot_id | uniprot_id_original | uniprot_id_normalized
   Insulin         | P01308     | sp|P01308|INS_HUMAN | true
   Hemoglobin      | P69905     | P69905.1            | true
   Albumin         | P02768     | p02768              | true

Statistics Tracking
-------------------

The action tracks comprehensive normalization statistics:

.. code-block:: python

   {
       "total_processed": 1000,
       "case_normalized": 150,
       "prefixes_stripped": 200,
       "versions_removed": 50,
       "isoforms_handled": 30,
       "validation_failures": 5
   }

Validation Patterns
-------------------

The action uses strict UniProt format validation:

- **Standard Format**: [A-Z][0-9][A-Z0-9]{4,8}
- **Must start**: Letter followed by digit
- **Length**: 6-10 characters total
- **Examples**: P12345, Q123A5, A0A123456, O95342

Invalid examples that would be flagged:
- PP12345 (starts with two letters)
- 123456 (starts with digit)
- P1234 (too short)

Error Handling
--------------

The action handles various error conditions gracefully:

- **Missing columns**: Returns error with specific column names
- **Empty values**: Skips null/empty entries without errors
- **Invalid formats**: Logs warnings but continues processing
- **Non-string values**: Converts to string before processing

Best Practices
--------------

1. **Always validate**: Keep ``validate_format=True`` to catch data quality issues
2. **Log changes**: Use ``add_normalization_log=True`` for audit trails
3. **Handle isoforms carefully**: Consider whether your analysis needs isoform-specific data
4. **Batch process**: Process multiple columns together for efficiency
5. **Review statistics**: Check normalization statistics to identify data quality patterns

Integration Examples
--------------------

With Database Matching
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_for_database
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "experimental_proteins"
           id_columns: ["protein_accession"]
           strip_isoforms: true    # Database typically stores canonical forms
           strip_versions: true    # Use latest version
           validate_format: true   # Ensure compatibility
           output_key: "db_ready_proteins"

     - name: match_to_uniprot
       action:
         type: MERGE_WITH_UNIPROT_RESOLUTION
         params:
           dataset_key: "db_ready_proteins"
           # ... other parameters

With Cross-Dataset Comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_dataset_a
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "dataset_a"
           id_columns: ["protein_id"]
           output_key: "normalized_a"

     - name: normalize_dataset_b
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "dataset_b"
           id_columns: ["uniprot_accession"]
           output_key: "normalized_b"

     - name: calculate_overlap
       action:
         type: CALCULATE_SET_OVERLAP
         params:
           dataset_a: "normalized_a"
           dataset_b: "normalized_b"
           # ... other parameters

Performance Notes
-----------------

- **Memory efficient**: Processes data in-place when possible
- **Regex optimized**: Uses compiled patterns for fast validation
- **Statistics tracking**: Minimal overhead for comprehensive metrics
- **Batch friendly**: Handles large datasets efficiently

The normalization is highly optimized for large protein datasets while maintaining data integrity and providing detailed audit trails.