metabolite_extract_identifiers
==============================

The ``METABOLITE_EXTRACT_IDENTIFIERS`` action extracts multiple types of metabolite identifiers from compound datasets with normalization and validation.

Overview
--------

This action processes metabolomics datasets to extract and standardize various metabolite identifier types:

- **HMDB** (Human Metabolome Database) identifiers
- **InChIKey** (International Chemical Identifier Key)
- **CHEBI** (Chemical Entities of Biological Interest)
- **KEGG** (Kyoto Encyclopedia of Genes and Genomes) compound IDs
- **PubChem** CID (Compound Identifier)

The action handles various identifier formats, applies normalization rules, and provides flexible output options for downstream analysis.

Parameters
----------

.. code-block:: yaml

   action:
     type: METABOLITE_EXTRACT_IDENTIFIERS
     params:
       input_key: "compound_data"
       id_types: ["hmdb", "inchikey", "chebi"]
       source_columns:
         hmdb: "HMDB_ID,Metabolite_HMDB"
         inchikey: "InChIKey,Chemical_InChIKey"
         chebi: "CHEBI_ID,ChEBI"
       output_key: "extracted_identifiers"
       normalize_ids: true
       validate_formats: true
       handle_multiple: "expand_rows"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** : str
    Dataset key from context containing compound data

**id_types** : list[str]
    List of identifier types to extract: "hmdb", "inchikey", "chebi", "kegg", "pubchem"

**source_columns** : dict[str, str]
    Column mapping per identifier type (comma-separated column names)

**output_key** : str
    Where to store the results with extracted identifiers

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**normalize_ids** : bool, default=True
    Apply format normalization to extracted identifiers

**validate_formats** : bool, default=True
    Validate extracted identifiers against expected patterns

**handle_multiple** : str, default="expand_rows"
    How to handle multiple identifiers per row: "expand_rows", "list", "first"

Identifier Format Specifications
--------------------------------

HMDB Identifiers
~~~~~~~~~~~~~~~~
- **Standard format**: HMDB0001234 (7-digit zero-padded)
- **Variations handled**: HMDB:1234, hmdb:1234, HMDB1234, 1234
- **Normalization**: Converts to HMDB0001234 format
- **Validation pattern**: ^HMDB\d{7}$

InChIKey Identifiers
~~~~~~~~~~~~~~~~~~~
- **Standard format**: XXXXXXXXXXXXXX-YYYYYYYYYY-Z
- **Example**: WQZGKKKJIJFFOK-GASJEMHNSA-N
- **Variations handled**: InChIKey:, InChIKey=, inchikey: prefixes
- **Normalization**: Removes prefixes, converts to uppercase
- **Validation pattern**: ^[A-Z]{14}-[A-Z]{10}-[A-Z]$

CHEBI Identifiers
~~~~~~~~~~~~~~~~
- **Standard format**: Numeric part only (12345)
- **Variations handled**: CHEBI:12345, ChEBI:12345, chebi:12345
- **Normalization**: Extracts numeric part only
- **Validation pattern**: ^\d+$

KEGG Compound IDs
~~~~~~~~~~~~~~~~
- **Standard format**: C12345 (C followed by 5 digits)
- **Variations handled**: KEGG:C12345, kegg:12345, 12345
- **Normalization**: Ensures C prefix with zero-padding
- **Validation pattern**: ^C\d{5}$

PubChem CIDs
~~~~~~~~~~~
- **Standard format**: Numeric (12345)
- **Variations handled**: PUBCHEM:12345, PubChem:12345, pubchem:12345
- **Normalization**: Extracts numeric part only
- **Validation pattern**: ^\d+$

Multiple Identifier Handling
----------------------------

The action provides three strategies for handling multiple identifiers in a single field:

Expand Rows (default)
~~~~~~~~~~~~~~~~~~~~~
Creates separate rows for each identifier:

```
Input:  compound_1 | HMDB0000001;HMDB0000002
Output: compound_1 | HMDB0000001
        compound_1 | HMDB0000002
```

List Format
~~~~~~~~~~~
Keeps identifiers as lists in single rows:

```
Input:  compound_1 | HMDB0000001;HMDB0000002  
Output: compound_1 | [HMDB0000001, HMDB0000002]
```

First Only
~~~~~~~~~~
Takes only the first identifier found:

```
Input:  compound_1 | HMDB0000001;HMDB0000002
Output: compound_1 | HMDB0000001
```

Example Usage
-------------

Basic Identifier Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_metabolite_ids
       action:
         type: METABOLITE_EXTRACT_IDENTIFIERS
         params:
           input_key: "metabolomics_data"
           id_types: ["hmdb", "inchikey"]
           source_columns:
             hmdb: "HMDB_ID"
             inchikey: "InChIKey"
           output_key: "standardized_metabolites"

Multi-Column Extraction
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: comprehensive_extraction
       action:
         type: METABOLITE_EXTRACT_IDENTIFIERS
         params:
           input_key: "compound_database"
           id_types: ["hmdb", "inchikey", "chebi", "kegg", "pubchem"]
           source_columns:
             hmdb: "HMDB_ID,Metabolite_HMDB,HMDB_Accession"
             inchikey: "InChIKey,Chemical_InChIKey,Standard_InChI_Key"
             chebi: "CHEBI_ID,ChEBI,CHEBI_Accession"
             kegg: "KEGG_ID,KEGG_Compound,Compound_ID"
             pubchem: "PubChem_CID,PUBCHEM_ID,CID"
           normalize_ids: true
           validate_formats: true
           handle_multiple: "expand_rows"
           output_key: "multi_source_identifiers"

Conservative Extraction
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: conservative_extract
       action:
         type: METABOLITE_EXTRACT_IDENTIFIERS
         params:
           input_key: "curated_compounds"
           id_types: ["hmdb"]
           source_columns:
             hmdb: "Primary_HMDB_ID"
           normalize_ids: true
           validate_formats: true
           handle_multiple: "first"    # Take first valid ID only
           output_key: "primary_hmdb_ids"

Normalization Examples
---------------------

The action applies comprehensive normalization:

**HMDB Normalization**:
```
HMDB:123        → HMDB0000123
hmdb:1234       → HMDB0001234  
HMDB12345       → HMDB0012345
123456          → HMDB0123456
```

**InChIKey Normalization**:
```
InChIKey:WQZGKKKJIJFFOK-GASJEMHNSA-N → WQZGKKKJIJFFOK-GASJEMHNSA-N
inchikey=WQZGKKKJIJFFOK-GASJEMHNSA-N → WQZGKKKJIJFFOK-GASJEMHNSA-N
wqzgkkkjijffok-gasjemhnsa-n          → WQZGKKKJIJFFOK-GASJEMHNSA-N
```

**CHEBI Normalization**:
```
CHEBI:12345     → 12345
ChEBI:67890     → 67890
chebi:123       → 123
```

**KEGG Normalization**:
```
KEGG:C12345     → C12345
kegg:12345      → C12345
12345           → C12345
C123            → C00123
```

Output Format
-------------

The action outputs the original dataset with added identifier columns:

.. code-block::

   Original Columns + Extracted ID Columns

Example output with expand_rows:

.. code-block::

   compound_name    | original_data | hmdb        | inchikey                     | chebi
   Glucose          | [original]    | HMDB0000122 | WQZGKKKJIJFFOK-GASJEMHNSA-N | 4167
   Glucose          | [original]    | HMDB0001549 | WQZGKKKJIJFFOK-GASJEMHNSA-N | 17234
   Alanine          | [original]    | HMDB0000161 | QNAYBMKLOCPYGJ-REOHCLBHSA-N | 16449

Statistics Tracking
-------------------

Comprehensive extraction statistics are provided:

.. code-block:: python

   {
       "total_rows_processed": 1000,
       "identifiers_extracted": {
           "hmdb": {
               "count": 856,
               "unique": 789,
               "coverage": 0.856
           },
           "inchikey": {
               "count": 723,
               "unique": 723,
               "coverage": 0.723
           },
           "chebi": {
               "count": 445,
               "unique": 432,
               "coverage": 0.445
           }
       }
   }
```

Validation and Quality Control
------------------------------

Format Validation
~~~~~~~~~~~~~~~~~
- Each identifier type has specific validation patterns
- Invalid formats are flagged but not removed
- Validation statistics tracked for quality assessment

Duplicate Detection
~~~~~~~~~~~~~~~~~~
- Identifies duplicate identifiers within and across types
- Reports unique vs total counts
- Helps assess data quality and redundancy

Coverage Analysis
~~~~~~~~~~~~~~~~
- Calculates extraction coverage per identifier type
- Identifies data completeness gaps
- Guides prioritization of identifier types

Error Handling
--------------

The action handles various data quality issues gracefully:

- **Missing columns**: Skips unavailable columns with warnings
- **Empty values**: Ignores null, empty, or whitespace-only entries
- **Invalid formats**: Logs warnings but continues processing
- **Mixed data types**: Converts all values to strings before processing

Best Practices
--------------

1. **Use multiple source columns**: Specify all possible column names for each ID type
2. **Enable normalization**: Ensures consistent identifier formats
3. **Validate formats**: Catches data quality issues early
4. **Choose appropriate handling**: Use "expand_rows" for comprehensive analysis
5. **Monitor statistics**: Review extraction coverage and validation results

Integration Examples
--------------------

With Normalization Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_identifiers
       action:
         type: METABOLITE_EXTRACT_IDENTIFIERS
         params:
           input_key: "raw_metabolites"
           id_types: ["hmdb", "inchikey"]
           source_columns:
             hmdb: "HMDB_ID,Metabolite_HMDB"
             inchikey: "InChIKey"
           output_key: "extracted_metabolites"

     - name: normalize_hmdb
       action:
         type: METABOLITE_NORMALIZE_HMDB
         params:
           input_key: "extracted_metabolites"
           hmdb_columns: ["hmdb"]
           output_key: "normalized_metabolites"

With Translation Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: extract_source_ids
       action:
         type: METABOLITE_EXTRACT_IDENTIFIERS
         params:
           input_key: "experimental_data"
           id_types: ["hmdb"]
           source_columns:
             hmdb: "Metabolite_ID"
           output_key: "hmdb_extracted"

     - name: translate_to_inchikey
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "hmdb_extracted"
           source_id_column: "hmdb"
           source_id_type: "hmdb"
           target_id_type: "inchikey"
           output_key: "translated_identifiers"

Performance Considerations
--------------------------

- **Memory efficient**: Processes data row-by-row for large datasets
- **Regex optimization**: Compiled patterns for fast validation
- **Batch normalization**: Efficient processing of identifier lists
- **Streaming support**: Handles datasets larger than available memory

The identifier extraction action provides a robust foundation for metabolomics data standardization and enables reliable downstream analysis and integration.