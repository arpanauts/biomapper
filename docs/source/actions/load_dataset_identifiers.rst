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
  Absolute path to the data file (CSV or TSV format).

**identifier_column** (string)
  Name of the column containing the biological identifiers.

**output_key** (string)  
  Key name to store the loaded data in the execution context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**dataset_name** (string)
  Human-readable name for the dataset, used in logging and metadata.
  Default: Derived from filename

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
          dataset_name: "UK Biobank Proteins"

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
                "row_count": 1463,
                "dataset_name": "UK Biobank Proteins",
                "identifier_column": "UniProt",
                "file_path": "/data/proteins/ukbb_proteins.csv"
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
  File format is auto-detected based on content and extension

Data Validation
---------------

The action performs several validation steps:

1. **File existence**: Verifies the file exists and is readable
2. **Header validation**: Ensures specified columns exist
3. **Data type consistency**: Basic type checking for identifiers
4. **Empty value handling**: Skips rows with empty identifier values

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

Performance Notes
-----------------

* Large files (>100K rows) are processed efficiently
* Memory usage scales with file size
* Consider splitting extremely large datasets (>1M rows)
* TSV files generally parse faster than CSV

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
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "source_data"
            target_dataset_key: "target_data"
            output_key: "merged_result"