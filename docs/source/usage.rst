Usage Guide
===========

This guide demonstrates how to use Biomapper's YAML strategy system for biological entity mapping through the REST API.

Installation
------------

Install Biomapper using Poetry:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/arpanauts/biomapper.git
    cd biomapper
    
    # Install dependencies
    poetry install --with dev,docs,api
    
    # Activate the environment
    poetry shell

Quick Start
-----------

Biomapper uses YAML strategies executed through a REST API. Here's the basic workflow:

1. **Start the API Server**

.. code-block:: bash

    cd biomapper-api
    poetry run uvicorn app.main:app --reload --port 8000

2. **Create or Use a Strategy YAML**

Place strategy in ``configs/strategies/`` or create ``my_strategy.yaml``:

.. code-block:: yaml

    # Optional metadata for tracking
    metadata:
      entity_type: "proteins"
      quality_tier: "experimental"
      expected_match_rate: 0.85
    
    # Optional runtime parameters
    parameters:
      data_dir: "${DATA_DIR:-/data}"
      output_dir: "${OUTPUT_DIR:-/tmp/results}"
    
    # Required strategy definition
    name: "BASIC_PROTEIN_MAPPING"
    description: "Map proteins between datasets"
    
    steps:
      - name: load_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "${parameters.data_dir}/proteins.csv"
            identifier_column: "uniprot"
            output_key: "proteins"
            additional_columns: ["gene_name", "description"]
      
      - name: normalize
        action:
          type: PROTEIN_NORMALIZE_ACCESSIONS
          params:
            input_key: "proteins"
            output_key: "normalized_proteins"
      
      - name: calculate_quality
        action:
          type: CALCULATE_MAPPING_QUALITY
          params:
            dataset_key: "normalized_proteins"
            output_key: "quality_metrics"

3. **Execute via Python Client**

.. code-block:: python

    from biomapper_client import BiomapperClient
    
    # Simple synchronous usage (recommended)
    client = BiomapperClient("http://localhost:8000")
    
    # Execute strategy by name (if in configs/strategies/)
    result = client.run("BASIC_PROTEIN_MAPPING")
    
    # Or execute with custom YAML file
    result = client.run("/path/to/my_strategy.yaml")
    
    # Check results
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        stats = result['results'].get('overlap_stats', {})
        print(f"Overlap: {stats.get('jaccard_similarity', 0):.2%}")

4. **Execute via CLI**

.. code-block:: bash

    # Using the biomapper CLI
    poetry run biomapper --help
    poetry run biomapper health
    poetry run biomapper metadata list
    
    # Or use the client directly
    poetry run python -c "from biomapper_client import BiomapperClient; print(BiomapperClient().run('test_metabolite_simple'))"

Core Concepts
-------------

Core Actions
~~~~~~~~~~~~

Biomapper provides 30+ self-registering actions organized by category:

**Data Operations**
  - ``LOAD_DATASET_IDENTIFIERS``: Load identifiers from CSV/TSV files
  - ``MERGE_DATASETS``: Combine multiple datasets
  - ``FILTER_DATASET``: Apply filtering criteria
  - ``EXPORT_DATASET``: Export to various formats
  - ``CUSTOM_TRANSFORM``: Apply Python expressions

**Protein Actions**
  - ``MERGE_WITH_UNIPROT_RESOLUTION``: Historical UniProt ID resolution
  - ``PROTEIN_EXTRACT_UNIPROT_FROM_XREFS``: Extract IDs from compound fields
  - ``PROTEIN_NORMALIZE_ACCESSIONS``: Standardize protein identifiers

**Metabolite Actions**
  - ``CTS_ENRICHED_MATCH``: Chemical Translation Service matching
  - ``SEMANTIC_METABOLITE_MATCH``: AI-powered semantic matching
  - ``NIGHTINGALE_NMR_MATCH``: Nightingale reference matching

**Analysis Actions**
  - ``CALCULATE_SET_OVERLAP``: Jaccard similarity and Venn diagrams
  - ``CALCULATE_THREE_WAY_OVERLAP``: Three-dataset comparison
  - ``GENERATE_METABOLOMICS_REPORT``: Comprehensive reports

Strategy Configuration
~~~~~~~~~~~~~~~~~~~~~~

Strategies are defined in YAML files with these sections:

**Required Fields:**

* ``name``: Strategy identifier (use UPPERCASE_WITH_UNDERSCORES)
* ``description``: Human-readable description  
* ``steps``: Ordered list of actions to execute

**Optional Fields:**

* ``metadata``: Tracking information (version, quality tier, expected match rates)
* ``parameters``: Runtime parameters with environment variable support

Each step contains:

* ``name``: Step identifier
* ``action.type``: One of the registered action types
* ``action.params``: Parameters specific to the action

Data Flow
~~~~~~~~~

1. Data is loaded into a shared context dictionary
2. Each action reads from and writes to this context
3. Actions use ``output_key`` to store results
4. Subsequent actions reference data using these keys
5. Final results include all context data plus execution metadata

Working with Real Data
----------------------

Protein Mapping Example
~~~~~~~~~~~~~~~~~~~~~~~

Here's a complete example mapping UKBB proteins to HPA:

.. code-block:: yaml

    name: "UKBB_HPA_PROTEIN_MAPPING"
    description: "Map UK Biobank proteins to Human Protein Atlas"
    
    steps:
      - name: load_ukbb_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/UKBB_Protein_Meta.tsv"
            identifier_column: "UniProt"
            output_key: "ukbb_proteins"
      
      - name: load_hpa_data  
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/hpa_osps.csv"
            identifier_column: "uniprot"
            output_key: "hpa_proteins"
      
      - name: merge_ukbb_uniprot
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "ukbb_proteins"
            target_dataset_key: "hpa_proteins" 
            source_id_column: "UniProt"
            target_id_column: "uniprot"
            output_key: "ukbb_merged"
      
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "ukbb_merged"
            dataset_b_key: "hpa_proteins"
            output_key: "overlap_analysis"

Multi-Dataset Analysis
~~~~~~~~~~~~~~~~~~~~~~

Compare multiple datasets by loading each one and calculating pairwise overlaps:

.. code-block:: yaml

    name: "MULTI_DATASET_ANALYSIS"
    description: "Compare proteins across multiple sources"
    
    steps:
      # Load all datasets
      - name: load_arivale
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/arivale/proteomics_metadata.tsv"
            identifier_column: "uniprot"
            output_key: "arivale_proteins"
      
      - name: load_qin
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/qin_osps.csv"
            identifier_column: "uniprot"
            output_key: "qin_proteins"
            
      # Calculate overlaps
      - name: arivale_vs_qin
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "arivale_proteins"
            dataset_b_key: "qin_proteins"
            output_key: "arivale_qin_overlap"

Error Handling
--------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**File not found errors**
  Check file paths are absolute and files exist.

**Column not found errors**
  Verify the ``identifier_column`` matches your CSV headers exactly.

**Timeout errors**
  Large datasets may take time. Default timeout is 5 minutes, but can be increased:
  
  .. code-block:: python
  
      client = BiomapperClient(timeout=3600)  # 1 hour

**Validation errors**
  Ensure YAML syntax is correct and all required parameters are provided.

Debugging
~~~~~~~~~

Enable detailed logging:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    async with BiomapperClient("http://localhost:8000") as client:
        result = await client.execute_strategy_file("strategy.yaml")

Check API server logs for detailed error messages and execution progress.

Performance Tips
----------------

* Use environment variables for portable file paths
* For large datasets (>100K rows), increase client timeout and consider chunking
* Monitor API server resources during execution
* Use the ``watch=True`` parameter to see real-time progress:
  
  .. code-block:: python
  
      result = client.run("large_strategy", watch=True)

* Consider using ``CHUNK_PROCESSOR`` action for very large files
* Enable job persistence for recovery from failures

Advanced Features
-----------------

**Environment Variables**

Strategies support variable substitution:

.. code-block:: yaml

    parameters:
      data_dir: "${DATA_DIR:-/default/path}"
    steps:
      - action:
          params:
            file_path: "${parameters.data_dir}/file.csv"

**Progress Tracking**

Use Server-Sent Events for real-time progress:

.. code-block:: python

    result = client.run_with_progress("my_strategy")

**Job Recovery**

Jobs are persisted to SQLite for recovery:

.. code-block:: python

    # Check job status
    job = client.get_job(job_id)
    if job.status == "failed":
        # Retry from last checkpoint
        result = client.retry_job(job_id)

Next Steps
----------

* See :doc:`configuration` for advanced YAML strategy options
* Check :doc:`api/index` for complete API reference  
* Review :doc:`actions/index` for all available actions
* Explore templates in ``configs/strategies/templates/``
* Read :doc:`development/creating_actions` to add custom actions

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper_client/biomapper_client/client_v2.py`` (Client implementation)
- ``biomapper-api/app/main.py`` (API server configuration)
- ``biomapper/core/strategy_actions/registry.py`` (Available actions)
- ``configs/strategies/templates/*.yaml`` (Strategy templates)
- ``CLAUDE.md`` (CLI commands and best practices)
- ``README.md`` (Installation and quick start)