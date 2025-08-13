Configuration Guide
===================

Biomapper uses YAML strategy files to define mapping workflows. Strategies can include metadata for tracking, runtime parameters with environment variable substitution, and a sequence of self-registering actions. This guide covers strategy configuration, action parameters, and best practices.

Strategy File Structure
-----------------------

Every strategy file follows this structure:

.. code-block:: yaml

    # Optional metadata for tracking and organization
    metadata:
      id: "strategy_unique_id"
      name: "Human Readable Name"
      version: "1.0.0"
      entity_type: "proteins"  # or metabolites, chemistry
      quality_tier: "experimental"  # or production, deprecated
    
    # Optional runtime parameters with defaults
    parameters:
      output_dir: "${OUTPUT_DIR:-/tmp/outputs}"
      threshold: 0.85
      batch_size: 1000
    
    # Required: strategy execution steps
    name: "STRATEGY_NAME" 
    description: "What this strategy does"
    
    steps:
      - name: step1
        action:
          type: ACTION_TYPE
          params:
            parameter1: "${parameters.threshold}"  # Use parameters
            parameter2: "/data/input.csv"
      
      - name: step2  
        action:
          type: ACTION_TYPE
          params:
            input_key: step1_output  # Reference previous outputs
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
  One of the 30+ registered action types (see Action Types section).

**action.params**
  Parameters specific to that action type.

Action Types
------------

Biomapper includes 30+ self-registering actions organized by category:

**Data Operations**

* ``LOAD_DATASET_IDENTIFIERS`` - Load identifiers from CSV/TSV files
* ``MERGE_DATASETS`` - Combine multiple datasets
* ``FILTER_DATASET`` - Apply filtering criteria
* ``EXPORT_DATASET`` - Export to various formats
* ``CUSTOM_TRANSFORM`` - Apply Python expressions

**Protein Actions**

* ``MERGE_WITH_UNIPROT_RESOLUTION`` - Historical UniProt ID resolution
* ``PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`` - Extract IDs from compound fields
* ``PROTEIN_NORMALIZE_ACCESSIONS`` - Standardize protein identifiers
* ``PROTEIN_MULTI_BRIDGE`` - Cross-dataset resolution

**Metabolite Actions**

* ``CTS_ENRICHED_MATCH`` - Chemical Translation Service matching
* ``SEMANTIC_METABOLITE_MATCH`` - AI-powered semantic matching
* ``VECTOR_ENHANCED_MATCH`` - Vector similarity matching
* ``NIGHTINGALE_NMR_MATCH`` - Nightingale reference matching
* ``COMBINE_METABOLITE_MATCHES`` - Merge multiple approaches

**Chemistry Actions**

* ``CHEMISTRY_EXTRACT_LOINC`` - Extract LOINC codes
* ``CHEMISTRY_FUZZY_TEST_MATCH`` - Fuzzy test name matching
* ``CHEMISTRY_VENDOR_HARMONIZATION`` - Harmonize vendor data

**Analysis Actions**

* ``CALCULATE_SET_OVERLAP`` - Jaccard similarity analysis
* ``CALCULATE_THREE_WAY_OVERLAP`` - Three-dataset comparison
* ``CALCULATE_MAPPING_QUALITY`` - Quality metrics
* ``GENERATE_METABOLOMICS_REPORT`` - Comprehensive reports

Common Action Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

**LOAD_DATASET_IDENTIFIERS**

Loads identifiers from CSV/TSV files.

Required Parameters:
* ``file_path``: Path to data file (supports environment variables)
* ``identifier_column``: Column name containing identifiers  
* ``output_key``: Key to store results in context

Optional Parameters:
* ``dataset_name``: Human-readable name for logging
* ``filter_empty``: Remove empty identifiers (default: true)
* ``additional_columns``: List of extra columns to preserve

.. code-block:: yaml

    - name: load_proteins
      action:
        type: LOAD_DATASET_IDENTIFIERS
        params:
          file_path: "${DATA_DIR:-/data}/proteins.csv"  # Environment variable
          identifier_column: "uniprot_id"
          output_key: "protein_list"
          dataset_name: "My Protein Dataset"
          additional_columns: ["gene_name", "description"]

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

**CALCULATE_SET_OVERLAP**

Calculates Jaccard similarity and generates Venn diagrams.

Required Parameters:
* ``dataset_a_key``: Context key of first dataset
* ``dataset_b_key``: Context key of second dataset  
* ``output_key``: Key to store overlap results

Optional Parameters:
* ``generate_venn``: Create Venn diagram (default: true)
* ``output_path``: Path for diagram file

.. code-block:: yaml

    - name: find_overlap
      action:
        type: CALCULATE_SET_OVERLAP
        params:
          dataset_a_key: "proteins_a"
          dataset_b_key: "proteins_b" 
          output_key: "overlap_stats"
          generate_venn: true
          output_path: "${parameters.output_dir}/venn_diagram.png"

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

Organize strategies in the ``configs/strategies/`` directory:

.. code-block:: text

    configs/strategies/
    ├── templates/                 # Reusable templates
    │   ├── protein_mapping_template.yaml
    │   ├── metabolite_mapping_template.yaml
    │   └── chemistry_mapping_template.yaml
    ├── experimental/              # In development
    │   ├── prot_arv_to_kg2c_uniprot_v2.yaml
    │   └── met_multi_to_unified_semantic.yaml
    └── production/               # Validated strategies
        └── (strategies promoted from experimental)

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

Use **absolute paths** or **environment variables** in strategy files:

.. code-block:: yaml

    # Good - absolute path
    file_path: "/data/proteins/ukbb_data.csv"
    
    # Better - environment variable with default
    file_path: "${DATA_DIR:-/data}/proteins/ukbb_data.csv"
    
    # Best - use parameters section
    parameters:
      data_dir: "${DATA_DIR:-/data}"
    steps:
      - action:
          params:
            file_path: "${parameters.data_dir}/proteins/ukbb_data.csv"

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
4. **Document with metadata** including version, quality tier, and expected match rates
5. **Use environment variables** for portable file paths
6. **Follow naming conventions**:
   - Strategy IDs: ``entity_source_to_target_bridge_version``
   - Output keys: ``entity_type_stage`` (e.g., ``proteins_normalized``)
7. **Track data lineage** with source_files and target_files metadata
8. **Set quality expectations** with expected_match_rate

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

Environment Variables
---------------------

Strategies support variable substitution:

* ``${VAR}`` or ``${env.VAR}`` - Environment variable
* ``${VAR:-default}`` - With default value
* ``${parameters.key}`` - Reference parameters section
* ``${metadata.field}`` - Reference metadata fields

Common environment variables:

* ``DATA_DIR`` - Base data directory
* ``OUTPUT_DIR`` - Output directory
* ``BIOMAPPER_CONFIG`` - Configuration path

Next Steps
----------

* See :doc:`usage` for executing strategies
* Check :doc:`actions/index` for complete action reference
* Review templates in ``configs/strategies/templates/``
* Learn about the :doc:`api/rest_endpoints` for programmatic execution

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper/core/strategy_actions/registry.py`` (Available actions)
- ``configs/strategies/templates/*.yaml`` (Strategy templates)
- ``biomapper/core/services/strategy_service_v2_minimal.py`` (Strategy executor)
- ``biomapper/core/strategy_actions/typed_base.py`` (Action base class)
- ``CLAUDE.md`` (Best practices and conventions)
- ``README.md`` (Configuration overview)