Configuration Guide
===================

Biomapper uses YAML strategy files to define mapping workflows. This guide covers strategy configuration, action parameters, and best practices.

Strategy File Structure
-----------------------

Every strategy file follows this basic structure:

.. code-block:: yaml

    name: "STRATEGY_NAME" 
    description: "What this strategy does"
    
    steps:
      - name: step1
        action:
          type: ACTION_TYPE
          params:
            parameter1: value1
            parameter2: value2
      
      - name: step2  
        action:
          type: ACTION_TYPE
          params:
            input_key: step1_output
            output_key: final_result

Required Fields
~~~~~~~~~~~~~~~

**name**
  Unique identifier for the strategy. Use UPPERCASE_WITH_UNDERSCORES.

**description** 
  Human-readable description of what the strategy accomplishes.

**steps**
  List of actions to execute in order.

Each step requires:

**name**
  Step identifier within the strategy.

**action.type**
  One of the three MVP action types.

**action.params**
  Parameters specific to that action type.

MVP Action Configuration
------------------------

LOAD_DATASET_IDENTIFIERS
~~~~~~~~~~~~~~~~~~~~~~~~~

Loads identifiers from CSV/TSV files.

Required Parameters:
* ``file_path``: Absolute path to data file
* ``identifier_column``: Column name containing identifiers  
* ``output_key``: Key to store results in context

Optional Parameters:
* ``dataset_name``: Human-readable name for logging

.. code-block:: yaml

    - name: load_proteins
      action:
        type: LOAD_DATASET_IDENTIFIERS
        params:
          file_path: "/data/proteins.csv"
          identifier_column: "uniprot_id"
          output_key: "protein_list"
          dataset_name: "My Protein Dataset"

MERGE_WITH_UNIPROT_RESOLUTION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Merges two datasets with historical UniProt identifier resolution.

Required Parameters:
* ``source_dataset_key``: Context key of source dataset
* ``target_dataset_key``: Context key of target dataset  
* ``source_id_column``: Column name in source data
* ``target_id_column``: Column name in target data
* ``output_key``: Key to store merged results

.. code-block:: yaml

    - name: merge_data
      action:
        type: MERGE_WITH_UNIPROT_RESOLUTION  
        params:
          source_dataset_key: "dataset_a"
          target_dataset_key: "dataset_b"
          source_id_column: "UniProt"
          target_id_column: "uniprot"
          output_key: "merged_dataset"

CALCULATE_SET_OVERLAP
~~~~~~~~~~~~~~~~~~~~~

Calculates overlap statistics between two datasets.

Required Parameters:
* ``dataset_a_key``: Context key of first dataset
* ``dataset_b_key``: Context key of second dataset  
* ``output_key``: Key to store overlap results

.. code-block:: yaml

    - name: find_overlap
      action:
        type: CALCULATE_SET_OVERLAP
        params:
          dataset_a_key: "proteins_a"
          dataset_b_key: "proteins_b" 
          output_key: "overlap_stats"

Example Configurations
----------------------

Basic Protein Mapping
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    name: "BASIC_PROTEIN_MAPPING"
    description: "Load and analyze protein overlap"
    
    steps:
      - name: load_source
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/source_proteins.csv"
            identifier_column: "protein_id"
            output_key: "source_proteins"
      
      - name: load_target
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/target_proteins.csv"  
            identifier_column: "uniprot_ac"
            output_key: "target_proteins"
      
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "source_proteins"
            dataset_b_key: "target_proteins"
            output_key: "analysis_results"

Multi-Dataset Comparison
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    name: "MULTI_DATASET_COMPARISON"
    description: "Compare multiple protein datasets with UniProt resolution"
    
    steps:
      - name: load_arivale
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/arivale/proteomics_metadata.tsv"
            identifier_column: "uniprot"
            output_key: "arivale_proteins"
            dataset_name: "Arivale Proteomics"
      
      - name: load_hpa
        action:
          type: LOAD_DATASET_IDENTIFIERS  
          params:
            file_path: "/data/hpa_osps.csv"
            identifier_column: "uniprot"
            output_key: "hpa_proteins"
            dataset_name: "Human Protein Atlas"
      
      - name: merge_arivale_hpa
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "arivale_proteins"
            target_dataset_key: "hpa_proteins"
            source_id_column: "uniprot" 
            target_id_column: "uniprot"
            output_key: "arivale_hpa_merged"
      
      - name: analyze_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "arivale_hpa_merged"
            dataset_b_key: "hpa_proteins"
            output_key: "final_analysis"

Strategy Organization
---------------------

File Naming
~~~~~~~~~~~

Use descriptive names that indicate the datasets and purpose:

* ``ukbb_hpa_mapping.yaml`` - Maps UKBB to HPA
* ``multi_protein_comparison.yaml`` - Compares multiple sources  
* ``arivale_qin_overlap.yaml`` - Analyzes Arivale vs QIN overlap

Directory Structure
~~~~~~~~~~~~~~~~~~~

Organize strategies in the ``configs/`` directory:

.. code-block:: text

    configs/
    ├── ukbb_hpa_mapping.yaml
    ├── arivale_hpa_mapping.yaml  
    ├── qin_hpa_mapping.yaml
    ├── kg2c_hpa_mapping.yaml
    └── spoke_hpa_mapping.yaml

Data Requirements
-----------------

File Formats
~~~~~~~~~~~~

Strategies work with CSV and TSV files. Ensure your data files:

* Have headers in the first row
* Use consistent delimiter (comma for CSV, tab for TSV)
* Contain the identifier columns referenced in strategies
* Use UTF-8 encoding

File Paths
~~~~~~~~~~

Always use **absolute paths** in strategy files:

.. code-block:: yaml

    # Good - absolute path
    file_path: "/data/proteins/ukbb_data.csv"
    
    # Bad - relative path (may fail) 
    file_path: "../data/ukbb_data.csv"

Column Names  
~~~~~~~~~~~~

Ensure the ``identifier_column`` exactly matches your CSV headers:

.. code-block:: yaml

    # If your CSV header is "UniProt_ID"
    identifier_column: "UniProt_ID"
    
    # Not "uniprot_id" or "UniProt"

Best Practices
--------------

1. **Use descriptive names** for steps and output keys
2. **Test with small datasets** before running on large files  
3. **Keep strategies focused** on specific comparisons
4. **Document complex strategies** with clear descriptions
5. **Validate file paths** before execution
6. **Use consistent naming** across related strategies

Troubleshooting
---------------

Common Configuration Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**YAML syntax errors**
  Validate YAML syntax with an online checker.

**Missing required parameters**  
  Check that all required params are provided for each action.

**File path issues**
  Use absolute paths and verify files exist.

**Column name mismatches**
  Ensure identifier_column matches CSV headers exactly.

**Key conflicts**
  Use unique output_key names within each strategy.

Validation
~~~~~~~~~~

Before deploying strategies:

1. Check YAML syntax is valid
2. Verify all file paths exist and are readable
3. Confirm column names match data files  
4. Test with small sample datasets first
5. Review logs for any warnings or errors

Next Steps
----------

* See :doc:`usage` for executing strategies
* Check :doc:`actions/load_dataset_identifiers` for detailed parameter reference
* Review example strategies in the ``configs/`` directory
* Learn about the :doc:`api/rest_endpoints` for programmatic execution