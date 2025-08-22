LOAD_DATASET_IDENTIFIERS
========================

Load identifiers from CSV/TSV files with flexible column mapping and data validation.

Purpose
-------

This action loads biological identifiers from tabular data files, providing:

* Flexible column mapping for different file formats
* Data validation and cleaning
* Metadata preservation for downstream analysis
* Support for various biological entity types

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**file_path** (string)
  Path to the data file (CSV or TSV format). Supports absolute and relative paths.

**identifier_column** (string)
  Name of the column containing the biological identifiers.

**output_key** (string)  
  Key name to store the loaded data in the execution context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**file_type** (string)
  File format specification: "csv", "tsv", or "auto" for automatic detection.
  Default: "auto"

**strip_prefix** (string)
  Prefix to remove from identifiers (e.g., "UniProtKB:").
  Default: None

**filter_column** (string)
  Column name to apply filtering on.
  Default: None

**filter_values** (list of strings)
  Values or regex patterns to match for filtering.
  Default: None

**filter_mode** (string)
  Filter mode: "include" to keep matches, "exclude" to remove matches.
  Default: "include"

**drop_empty_ids** (boolean)
  Whether to remove rows with empty identifier values.
  Default: true

Example Usage
-------------

Basic Protein Loading
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: load_proteins
      action:
        type: LOAD_DATASET_IDENTIFIERS
        params:
          file_path: "/data/proteins/ukbb_proteins.csv"
          identifier_column: "UniProt"
          output_key: "ukbb_proteins"

Input File Format
~~~~~~~~~~~~~~~~~

The action expects CSV or TSV files with headers:

.. code-block:: csv

    protein_name,UniProt,panel,description
    AARSD1,Q9BTE6,Oncology,Alanyl-tRNA synthetase domain
    ABL1,P00519,Oncology,Tyrosine-protein kinase ABL1
    ACE,P12821,Cardiology,Angiotensin-converting enzyme

Output Format
-------------

The action stores data in the context under the specified ``output_key``:

.. code-block:: python

    # Context after execution
    {
        "datasets": {
            "ukbb_proteins": [
                {
                    "protein_name": "AARSD1",
                    "UniProt": "Q9BTE6", 
                    "panel": "Oncology",
                    "description": "Alanyl-tRNA synthetase domain"
                },
                # ... more rows
            ]
        },
        "metadata": {
            "ukbb_proteins": {
                "source_file": "/data/proteins/ukbb_proteins.csv",
                "row_count": 1463,
                "identifier_column": "UniProt",
                "columns": ["protein_name", "UniProt", "panel", "description", "_row_number", "_source_file"],
                "filtered": false,
                "prefix_stripped": false
            }
        }
    }

Supported File Types
--------------------

**CSV Files** (.csv)
  Comma-separated values with headers

**TSV Files** (.tsv, .txt)  
  Tab-separated values with headers

**Auto-Detection**
  File format is auto-detected based on extension (.tsv files use tab delimiter, others use comma)

Data Validation
---------------

The action performs several validation steps:

1. **File existence**: Verifies the file exists and is readable
2. **Header validation**: Ensures specified columns exist
3. **Empty value handling**: Optionally removes rows with empty identifier values
4. **Robust file loading**: Uses BiologicalFileLoader for enhanced parsing
5. **Filter validation**: Validates filter columns exist before applying filters

Error Handling
--------------

Common errors and solutions:

**File not found**
  .. code-block:: 
  
      Error: File not found: /data/proteins.csv
      
  Solution: Use absolute paths and verify file exists.

**Column not found**
  .. code-block::
  
      Error: Column 'uniprot' not found. Available: ['UniProt', 'protein_name']
      
  Solution: Check column name matches exactly (case-sensitive).

**Empty dataset**
  .. code-block::
  
      Warning: No valid identifiers found in dataset
      
  Solution: Verify identifier column contains data.

Best Practices
--------------

1. **Use absolute file paths** to avoid path resolution issues
2. **Match column names exactly** (case-sensitive)
3. **Clean data beforehand** to remove empty rows
4. **Use descriptive output keys** like "ukbb_proteins" instead of "data1"
5. **Add dataset names** for better logging and debugging

Advanced Features
-----------------

**Prefix Stripping**
  Remove common prefixes while preserving original values:
  
  .. code-block:: yaml
  
      params:
        strip_prefix: "UniProtKB:"
        # Transforms "UniProtKB:P12345" to "P12345"
        # Original saved as "UniProt_original" column

**Regex Filtering**
  Filter rows based on pattern matching:
  
  .. code-block:: yaml
  
      params:
        filter_column: "panel"
        filter_values: ["Oncology", "Cardiology"]
        filter_mode: "include"

**Metadata Tracking**
  Each row gets tracking columns:
  
  * ``_row_number``: Original file row number (1-based, accounting for header)
  * ``_source_file``: Absolute path to source file
  * ``[identifier_column]_original``: Original value if prefix stripping is applied

Performance Notes
-----------------

* Uses pandas for reliable file parsing with automatic format detection
* Handles various encodings and delimiters based on file extension
* Memory efficient for large files (tested with 100K+ rows) 
* TSV files parse faster than CSV due to simpler delimiter structure
* Adds metadata columns for row tracking and provenance

Integration
-----------

This action is typically used as the first step in mapping strategies:

.. code-block:: yaml

    steps:
      # 1. Load source data
      - name: load_source
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/source.csv"
            identifier_column: "id"
            output_key: "source_data"
      
      # 2. Load target data  
      - name: load_target
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/target.csv"
            identifier_column: "uniprot"
            output_key: "target_data"
      
      # 3. Process the loaded data
      - name: merge_data
        action:
          type: MERGE_DATASETS
          params:
            input_key: "source_data"
            secondary_key: "target_data"
            output_key: "merged_result"
            merge_strategy: "union"

---

## Verification Sources
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/load_dataset_identifiers.py` (actual implementation using pandas with dual context support)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class and StandardActionResult)
- `/biomapper/src/actions/registry.py` (self-registration mechanism via @register_action decorator)
- `/biomapper/CLAUDE.md` (2025 standardizations and parameter naming conventions)
- `/biomapper/pyproject.toml` (project dependencies including pandas for file loading)