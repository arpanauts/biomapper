FILTER_DATASET
==============

Filter datasets by column values using flexible conditions and logical operators.

Purpose
-------

This action provides powerful dataset filtering capabilities with support for:

* Multiple filter conditions with AND/OR logic
* Rich set of comparison operators
* String matching with case sensitivity options
* Regex pattern matching
* Null value handling
* Keep or remove matching rows

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Key of the dataset to filter from context['datasets'].

**filter_conditions** (list of objects)
  List of filter conditions to apply. Each condition contains:
  
  * **column** (string): Column name to filter on
  * **operator** (string): Filter operator (see operators below)
  * **value** (any): Value to compare against (not needed for null checks)
  * **case_sensitive** (boolean): Case sensitivity for string operations (default: true)

**output_key** (string)
  Key where filtered dataset will be stored in context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**logic_operator** (string)
  How to combine multiple conditions: 'AND' or 'OR'.
  Default: 'AND'

**keep_or_remove** (string)
  Whether to 'keep' matching rows or 'remove' matching rows.
  Default: 'keep'

**add_filter_log** (boolean)
  Whether to add detailed metadata about filtering.
  Default: true

Supported Operators
-------------------

**Comparison Operators**
  * ``equals`` - Exact equality match
  * ``not_equals`` - Not equal to value
  * ``greater_than`` - Greater than numeric value
  * ``less_than`` - Less than numeric value
  * ``greater_equal`` - Greater than or equal to
  * ``less_equal`` - Less than or equal to

**String Operators**
  * ``contains`` - String contains substring
  * ``not_contains`` - String does not contain substring
  * ``regex`` - Matches regular expression pattern

**List Operators**
  * ``in_list`` - Value is in provided list
  * ``not_in_list`` - Value is not in provided list

**Null Operators**
  * ``is_null`` - Column value is null/NaN
  * ``not_null`` - Column value is not null/NaN

Example Usage
-------------

Basic Filtering
~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_high_confidence
      action:
        type: FILTER_DATASET
        params:
          input_key: "protein_matches"
          filter_conditions:
            - column: "confidence"
              operator: "greater_equal"
              value: 0.8
          output_key: "high_conf_proteins"

Multiple Conditions with AND Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_quality_proteins
      action:
        type: FILTER_DATASET
        params:
          input_key: "all_proteins"
          filter_conditions:
            - column: "confidence"
              operator: "greater_than"
              value: 0.7
            - column: "category"
              operator: "equals"
              value: "reviewed"
            - column: "uniprot_id"
              operator: "not_null"
          logic_operator: "AND"
          output_key: "quality_proteins"

String Matching with Case Insensitivity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_metabolite_names
      action:
        type: FILTER_DATASET
        params:
          input_key: "metabolites"
          filter_conditions:
            - column: "compound_name"
              operator: "contains"
              value: "glucose"
              case_sensitive: false
          output_key: "glucose_related"

List-Based Filtering
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_target_proteins
      action:
        type: FILTER_DATASET
        params:
          input_key: "protein_data"
          filter_conditions:
            - column: "uniprot_id"
              operator: "in_list"
              value: ["P12345", "Q67890", "O11111"]
          output_key: "target_proteins"

Regex Pattern Matching
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_uniprot_format
      action:
        type: FILTER_DATASET
        params:
          input_key: "identifiers"
          filter_conditions:
            - column: "protein_id"
              operator: "regex"
              value: "^[A-Z][0-9][A-Z0-9]{3}[0-9]$"
          output_key: "valid_uniprot_ids"

Removing Unwanted Data
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: remove_low_quality
      action:
        type: FILTER_DATASET
        params:
          input_key: "raw_data"
          filter_conditions:
            - column: "quality_score"
              operator: "less_than"
              value: 0.3
          keep_or_remove: "remove"
          output_key: "filtered_data"

Complex OR Logic
~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: filter_multiple_categories
      action:
        type: FILTER_DATASET
        params:
          input_key: "compounds"
          filter_conditions:
            - column: "category"
              operator: "equals"
              value: "amino_acids"
            - column: "category"
              operator: "equals"
              value: "lipids"
            - column: "hmdb_id"
              operator: "not_null"
          logic_operator: "OR"
          output_key: "target_compounds"

Output Format
-------------

The action stores the filtered dataset in the context:

.. code-block:: python

    # Context after execution
    {
        "datasets": {
            "filtered_proteins": [
                {
                    "uniprot_id": "P12345",
                    "confidence": 0.95,
                    "category": "reviewed"
                },
                # ... only rows matching filter conditions
            ]
        }
    }

Detailed Statistics
-------------------

When ``add_filter_log`` is true, detailed statistics are included:

.. code-block:: python

    {
        "total_input_rows": 1000,
        "total_output_rows": 234,
        "filter_conditions_count": 2,
        "logic_operator": "AND",
        "keep_or_remove": "keep",
        "input_key": "raw_data",
        "output_key": "filtered_data"
    }

Error Handling
--------------

**Column not found**
  .. code-block::
  
      Error: Column 'missing_col' not found in dataset
      
  Solution: Verify column names match exactly (case-sensitive).

**Invalid regex pattern**
  .. code-block::
  
      Error: Invalid regex pattern 'unterminated[': bad character
      
  Solution: Use valid regex syntax and test patterns.

**Type mismatch**
  .. code-block::
  
      Error: Cannot compare string with numeric value
      
  Solution: Ensure operator and value types are compatible.

Best Practices
--------------

1. **Test regex patterns** before using in production filters
2. **Use appropriate operators** for data types (numeric vs string)
3. **Consider case sensitivity** for string operations
4. **Validate column names** exist in dataset before filtering
5. **Use descriptive output keys** to track filtering steps
6. **Combine conditions logically** - AND for restrictive, OR for inclusive
7. **Handle null values explicitly** when data quality varies

Performance Notes
-----------------

* Filtering is performed using pandas operations for efficiency
* Large datasets (>100K rows) filter quickly
* Regex operations may be slower than simple comparisons
* Multiple conditions are optimized with vectorized operations
* Memory usage scales with output dataset size

Common Use Cases
----------------

**Quality Control**
  Remove low-confidence matches or invalid identifiers

**Data Subset Selection**
  Extract specific categories or value ranges for analysis

**Validation Filtering**
  Keep only records meeting specific format requirements

**Experimental Design**
  Select target compounds or proteins for focused studies

**Outlier Removal**
  Filter extreme values or anomalous data points

Integration
-----------

This action typically follows data loading and precedes analysis:

.. code-block:: yaml

    steps:
      # 1. Load raw data
      - name: load_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/proteins.csv"
            identifier_column: "uniprot_id"
            output_key: "raw_proteins"
      
      # 2. Filter for quality
      - name: quality_filter
        action:
          type: FILTER_DATASET
          params:
            input_key: "raw_proteins"
            filter_conditions:
              - column: "confidence"
                operator: "greater_equal"
                value: 0.8
              - column: "uniprot_id"
                operator: "not_null"
            output_key: "quality_proteins"
      
      # 3. Continue with analysis
      - name: analyze_quality_data
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_key: "quality_proteins"