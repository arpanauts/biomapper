EXPORT_DATASET
==============

Export datasets from the execution context to files in various formats.

Purpose
-------

This action saves processed datasets to files for external use, sharing, or archival. It provides:

* Multiple output formats (TSV, CSV, JSON, Excel)
* Selective column export
* Automatic directory creation
* Integration with output file tracking
* Flexible path specification

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Key of the dataset to export from context['datasets'].

**output_path** (string)
  Full file path where the dataset will be saved. Supports absolute and relative paths.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**format** (string)
  Export format: 'tsv', 'csv', 'json', or 'xlsx'.
  Default: 'tsv'

**columns** (list of strings)
  Specific columns to export. If not specified, all columns are exported.
  Default: None (export all columns)

Supported Formats
-----------------

**TSV (Tab-Separated Values)**
  * Extension: .tsv, .txt
  * Delimiter: Tab character
  * Headers: Included
  * Best for: Large datasets, programmatic processing

**CSV (Comma-Separated Values)**
  * Extension: .csv
  * Delimiter: Comma
  * Headers: Included
  * Best for: Excel compatibility, general data exchange

**JSON (JavaScript Object Notation)**
  * Extension: .json
  * Format: Array of objects (records orientation)
  * Indented: 2 spaces for readability
  * Best for: Web applications, APIs

**Excel (XLSX)**
  * Extension: .xlsx
  * Format: Excel workbook
  * Headers: Included
  * Best for: Manual analysis, reporting

Example Usage
-------------

Basic TSV Export
~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_results
      action:
        type: EXPORT_DATASET
        params:
          input_key: "final_proteins"
          output_path: "/results/protein_matches.tsv"
          format: "tsv"

Export Specific Columns
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_summary
      action:
        type: EXPORT_DATASET
        params:
          input_key: "metabolite_matches"
          output_path: "/output/metabolite_summary.csv"
          format: "csv"
          columns: ["compound_name", "hmdb_id", "confidence", "category"]

JSON Export for Web Use
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_api_data
      action:
        type: EXPORT_DATASET
        params:
          input_key: "processed_compounds"
          output_path: "/web/data/compounds.json"
          format: "json"

Excel Export for Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_excel_report
      action:
        type: EXPORT_DATASET
        params:
          input_key: "comprehensive_results"
          output_path: "/reports/analysis_${date}.xlsx"
          format: "xlsx"

Multiple Exports
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_tsv
      action:
        type: EXPORT_DATASET
        params:
          input_key: "final_data"
          output_path: "/output/data.tsv"
          format: "tsv"

    - name: export_excel
      action:
        type: EXPORT_DATASET
        params:
          input_key: "final_data"
          output_path: "/output/data.xlsx"
          format: "xlsx"
          columns: ["id", "name", "description", "category"]

Variable Substitution in Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_timestamped
      action:
        type: EXPORT_DATASET
        params:
          input_key: "results"
          output_path: "${OUTPUT_DIR}/results_${timestamp}.csv"
          format: "csv"

Output Format Examples
----------------------

**TSV Format**
.. code-block:: tsv

    uniprot_id	gene_name	confidence	category
    P12345	EXAMPLE1	0.95	reviewed
    Q67890	EXAMPLE2	0.87	reviewed

**CSV Format**
.. code-block:: csv

    uniprot_id,gene_name,confidence,category
    P12345,EXAMPLE1,0.95,reviewed
    Q67890,EXAMPLE2,0.87,reviewed

**JSON Format**
.. code-block:: json

    [
      {
        "uniprot_id": "P12345",
        "gene_name": "EXAMPLE1",
        "confidence": 0.95,
        "category": "reviewed"
      },
      {
        "uniprot_id": "Q67890",
        "gene_name": "EXAMPLE2",
        "confidence": 0.87,
        "category": "reviewed"
      }
    ]

Context Integration
-------------------

The action updates the execution context with output file information:

.. code-block:: python

    # Context after execution
    {
        "output_files": {
            "final_proteins": "/results/protein_matches.tsv"
        }
    }

This enables downstream actions to reference exported files.

Path Handling
-------------

**Absolute Paths**
  Use full file system paths: ``/home/user/data/results.csv``

**Relative Paths**
  Relative to current working directory: ``./output/data.tsv``

**Directory Creation**
  Parent directories are created automatically if they don't exist.

**Path Variables**
  Support for environment variables and strategy parameters:
  
  * ``${OUTPUT_DIR}/results.csv``
  * ``${parameters.output_path}``
  * ``${metadata.timestamp}``

Error Handling
--------------

**Dataset not found**
  .. code-block::
  
      Error: Dataset 'missing_data' not found in context
      
  Solution: Verify the input_key exists in context['datasets'].

**Unsupported format**
  .. code-block::
  
      Error: Unsupported format: xml
      
  Solution: Use supported formats: tsv, csv, json, xlsx.

**Permission denied**
  .. code-block::
  
      Error: Export failed: Permission denied
      
  Solution: Check write permissions for output directory.

**Invalid columns**
  .. code-block::
  
      Error: Column 'missing_col' not found in dataset
      
  Solution: Verify column names exist in the dataset.

Best Practices
--------------

1. **Use descriptive filenames** including dataset type and timestamp
2. **Choose appropriate formats** for intended use:
   
   * TSV/CSV for data processing
   * JSON for web applications
   * Excel for manual analysis

3. **Specify column subsets** to reduce file size and focus on key data
4. **Use absolute paths** in production environments
5. **Include metadata** in filenames (date, version, parameters)
6. **Plan directory structure** for organized output management

Performance Notes
-----------------

* Export speed depends on dataset size and format complexity
* TSV exports are fastest for large datasets
* Excel exports may be slower due to formatting overhead
* JSON exports with many columns can be memory-intensive
* Column filtering reduces export time and file size

File Size Considerations
------------------------

**Large Datasets (>100K rows)**
  * Prefer TSV format for efficiency
  * Consider column filtering to reduce size
  * Use compression if supported by downstream tools

**Memory Usage**
  * Scales with dataset size
  * JSON format uses more memory during export
  * Excel format may require significant memory for large datasets

Integration Patterns
--------------------

**End-of-Pipeline Export**
.. code-block:: yaml

    steps:
      # ... processing steps ...
      
      - name: export_final_results
        action:
          type: EXPORT_DATASET
          params:
            input_key: "processed_data"
            output_path: "/results/final_analysis.tsv"

**Multi-Format Export**
.. code-block:: yaml

    steps:
      # ... processing steps ...
      
      - name: export_for_analysis
        action:
          type: EXPORT_DATASET
          params:
            input_key: "results"
            output_path: "/output/analysis.xlsx"
            format: "xlsx"
      
      - name: export_for_api
        action:
          type: EXPORT_DATASET
          params:
            input_key: "results"
            output_path: "/api/data.json"
            format: "json"
            columns: ["id", "name", "value"]

**Conditional Export**
.. code-block:: yaml

    steps:
      # ... processing steps ...
      
      - name: export_if_successful
        action:
          type: EXPORT_DATASET
          params:
            input_key: "validated_results"
            output_path: "/output/success_${date}.tsv"
            format: "tsv"

---

## Verification Sources
*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/export_dataset.py` (implementation with format support and column selection)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class)
- `/biomapper/src/actions/registry.py` (action registration via decorator)
- `/biomapper/src/core/standards/context_handler.py` (UniversalContext for context handling)
- `/biomapper/src/core/standards/base_models.py` (ActionParamsBase and FlexibleBaseModel)
- `/biomapper/CLAUDE.md` (standardized parameter naming conventions)