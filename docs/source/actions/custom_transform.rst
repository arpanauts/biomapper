CUSTOM_TRANSFORM
================

Apply custom data transformations with flexible operations and error handling.

Purpose
-------

This action provides powerful data transformation capabilities for complex data processing that doesn't fit standard action patterns. It supports:

* Chained transformation operations
* Multiple transformation types
* Conditional transformations
* Schema validation
* Comprehensive error handling
* Flexible output options

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Key of the input dataset to transform from context['datasets'].

**output_key** (string)
  Key where the transformed dataset will be stored.

**transformations** (list of objects)
  List of transformation operations to apply sequentially. Each transformation contains:
  
  * **type** (string): Transformation type (see types below)
  * **params** (object): Parameters specific to the transformation type
  * **condition** (string, optional): Conditional expression for applying transformation

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**validate_schema** (boolean)
  Whether to validate output schema matches expectations.
  Default: true

**expected_columns** (list of strings)
  Expected columns in output dataset (for validation).
  Default: None

**preserve_index** (boolean)
  Whether to preserve original DataFrame index.
  Default: true

**error_handling** (string)
  How to handle transformation errors: 'strict', 'warn', or 'ignore'.
  Default: 'strict'

Transformation Types
--------------------

**Column Operations**

**column_rename**
  Rename columns using a mapping dictionary.
  
  Parameters:
  * ``mapping``: Dictionary of {old_name: new_name}

**column_add**
  Add new columns with specified values or functions.
  
  Parameters:
  * ``columns``: Dictionary of {column_name: value_or_function}

**column_drop**
  Remove specified columns.
  
  Parameters:
  * ``columns``: List of column names to drop

**column_transform**
  Transform values in a specific column.
  
  Parameters:
  * ``column``: Column name to transform
  * ``function``: Transformation function (string or callable)

**Data Operations**

**filter_rows**
  Filter rows based on conditions.
  
  Parameters:
  * ``query``: Pandas query string, OR
  * ``conditions``: Dictionary of column-based conditions

**merge_columns**
  Combine multiple columns into a new column.
  
  Parameters:
  * ``new_column``: Name of new column
  * ``source_columns``: List of columns to merge
  * ``separator``: String to join values (default: "_")

**split_column**
  Split a column into multiple new columns.
  
  Parameters:
  * ``source_column``: Column to split
  * ``separator``: Split delimiter (default: "_")
  * ``new_columns``: List of new column names

**Data Cleaning**

**deduplicate**
  Remove duplicate rows.
  
  Parameters:
  * ``subset``: Columns to consider for duplication (optional)
  * ``keep``: Which duplicate to keep ('first', 'last', False)

**fill_na**
  Fill missing values.
  
  Parameters:
  * ``method``: Fill method ('value', 'forward', 'backward')
  * ``value``: Fill value (if method='value')

**sort**
  Sort dataset by columns.
  
  Parameters:
  * ``by``: List of columns to sort by
  * ``ascending``: Sort order (boolean or list of booleans)

Example Usage
-------------

Basic Column Operations
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: clean_protein_data
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "raw_proteins"
          output_key: "cleaned_proteins"
          transformations:
            - type: "column_rename"
              params:
                mapping:
                  "UniProt": "uniprot_id"
                  "Gene": "gene_name"
            - type: "column_transform"
              params:
                column: "gene_name"
                function: "upper"
            - type: "fill_na"
              params:
                method: "value"
                value: "UNKNOWN"

Complex Data Processing
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: process_metabolite_data
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "metabolite_raw"
          output_key: "metabolite_processed"
          transformations:
            - type: "column_add"
              params:
                columns:
                  "processing_date": "2024-01-01"
                  "data_source": "nmr_platform"
            - type: "merge_columns"
              params:
                new_column: "compound_identifier"
                source_columns: ["hmdb_id", "chebi_id"]
                separator: "|"
            - type: "filter_rows"
              params:
                conditions:
                  confidence:
                    operator: ">="
                    value: 0.8
            - type: "deduplicate"
              params:
                subset: ["compound_identifier"]
                keep: "first"

String Transformations
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: standardize_names
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "compound_names"
          output_key: "standardized_names"
          transformations:
            - type: "column_transform"
              params:
                column: "compound_name"
                function: "lower"
            - type: "column_transform"
              params:
                column: "compound_name"
                function: "strip"
            - type: "column_transform"
              params:
                column: "compound_name"
                function: "replace:_: "  # Replace underscores with spaces

Conditional Transformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: conditional_processing
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "mixed_data"
          output_key: "processed_data"
          transformations:
            - type: "column_add"
              params:
                columns:
                  "high_confidence": "True"
              condition: "df['confidence'].mean() > 0.8"
            - type: "filter_rows"
              params:
                query: "confidence >= 0.7"
              condition: "len(df) > 100"

Advanced Column Splitting
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: split_identifiers
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "compound_data"
          output_key: "split_data"
          transformations:
            - type: "split_column"
              params:
                source_column: "compound_ids"
                separator: "|"
                new_columns: ["primary_id", "secondary_id", "tertiary_id"]
            - type: "column_drop"
              params:
                columns: ["compound_ids"]  # Remove original column

Schema Validation
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: validated_transform
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "input_data"
          output_key: "validated_data"
          validate_schema: true
          expected_columns: ["uniprot_id", "gene_name", "confidence"]
          transformations:
            - type: "column_rename"
              params:
                mapping:
                  "UniProt": "uniprot_id"
                  "Gene": "gene_name"

Error Handling Examples
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: robust_transform
      action:
        type: CUSTOM_TRANSFORM
        params:
          input_key: "noisy_data"
          output_key: "cleaned_data"
          error_handling: "warn"  # Continue on errors
          transformations:
            - type: "column_transform"
              params:
                column: "numeric_field"
                function: "float"  # May fail on non-numeric values
            - type: "filter_rows"
              params:
                query: "numeric_field > 0"  # Only valid after conversion

Transformation Functions
-------------------------

**String Functions**
  * ``lower`` - Convert to lowercase
  * ``upper`` - Convert to uppercase
  * ``strip`` - Remove leading/trailing whitespace
  * ``replace:old:new`` - Replace substring

**Custom Functions**
  Functions can be provided as Python callables for complex transformations.

**Query Expressions**
  Use pandas query syntax for complex row filtering:
  
  * ``confidence > 0.8 and category == 'reviewed'``
  * ``gene_name.str.contains('BRCA')``
  * ``@external_variable > threshold``

Output Format
-------------

The action stores the transformed dataset in the context:

.. code-block:: python

    # Context after execution
    {
        "datasets": {
            "processed_data": [
                {
                    "uniprot_id": "P12345",
                    "gene_name": "EXAMPLE1",
                    "confidence": 0.95,
                    "processing_date": "2024-01-01"
                }
                # ... transformed rows
            ]
        }
    }

Transformation Result
---------------------

The action returns detailed information about the transformation:

.. code-block:: python

    {
        "success": True,
        "rows_processed": 1000,
        "columns_before": 5,
        "columns_after": 7,
        "transformations_applied": 4,
        "transformations_failed": 0,
        "warnings": [],
        "schema_validation_passed": True
    }

Error Handling Modes
---------------------

**Strict Mode (strict)**
  Stops execution on first error. Best for critical transformations.

**Warning Mode (warn)**
  Logs errors but continues processing. Best for exploratory analysis.

**Ignore Mode (ignore)**
  Silently continues on errors. Use with caution.

Best Practices
--------------

1. **Plan transformation sequences** carefully - order matters
2. **Use descriptive transformation names** in complex pipelines
3. **Validate schemas** for critical data transformations
4. **Handle missing data** explicitly with fill_na operations
5. **Test transformations** on sample data before production
6. **Use appropriate error handling** based on data quality expectations
7. **Document complex transformations** with clear parameter descriptions

Performance Notes
-----------------

* Transformations are applied sequentially using pandas operations
* Large datasets (>100K rows) process efficiently
* String operations may be slower than numeric transformations
* Memory usage scales with dataset size and transformation complexity
* Consider chunking for extremely large datasets

Common Use Cases
----------------

**Data Standardization**
  Normalize column names, formats, and value representations

**Data Enrichment**
  Add computed columns, metadata, or derived values

**Quality Control**
  Remove duplicates, handle missing values, filter invalid data

**Format Conversion**
  Transform data between different structural representations

**Experimental Preprocessing**
  Apply domain-specific transformations for analysis

Integration
-----------

This action typically follows data loading and precedes specific analysis:

.. code-block:: yaml

    steps:
      # 1. Load raw data
      - name: load_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/raw_proteins.csv"
            identifier_column: "UniProt"
            output_key: "raw_data"
      
      # 2. Custom transformations
      - name: clean_and_process
        action:
          type: CUSTOM_TRANSFORM
          params:
            input_key: "raw_data"
            output_key: "processed_data"
            transformations:
              - type: "column_rename"
                params:
                  mapping: {"UniProt": "uniprot_id"}
              - type: "column_transform"
                params:
                  column: "confidence"
                  function: "float"
              - type: "filter_rows"
                params:
                  query: "confidence >= 0.8"
      
      # 3. Continue with analysis
      - name: analyze_data
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_key: "processed_data"

---

## Verification Sources
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/utils/data_processing/custom_transform_expression.py` (actual implementation with expression-based transformations)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class)
- `/biomapper/src/actions/registry.py` (dual registration for CUSTOM_TRANSFORM and CUSTOM_TRANSFORM_EXPRESSION)
- `/biomapper/CLAUDE.md` (2025 standardizations and parameter naming conventions)
- `/biomapper/pyproject.toml` (pandas dependency for DataFrame operations)