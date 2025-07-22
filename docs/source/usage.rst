Usage Guide
===========

This guide demonstrates how to use Biomapper's YAML strategy system for biological entity mapping through the REST API.

Installation
------------

Install Biomapper using Poetry:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/your-org/biomapper.git
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
    poetry run uvicorn main:app --reload

2. **Create a Strategy YAML**

Create a file ``my_strategy.yaml``:

.. code-block:: yaml

    name: "BASIC_PROTEIN_MAPPING"
    description: "Map proteins between datasets"
    
    steps:
      - name: load_data
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/path/to/proteins.csv"
            identifier_column: "uniprot"
            output_key: "proteins"
      
      - name: merge_uniprot
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "proteins"
            target_dataset_key: "proteins"
            output_key: "merged_proteins"
      
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "proteins" 
            dataset_b_key: "merged_proteins"
            output_key: "overlap_stats"

3. **Execute via Python Client**

.. code-block:: python

    import asyncio
    from biomapper_client import BiomapperClient
    
    async def main():
        async with BiomapperClient("http://localhost:8000") as client:
            # Execute strategy
            result = await client.execute_strategy_file("my_strategy.yaml")
            
            # Check results
            print(f"Status: {result['status']}")
            print(f"Overlap: {result['results']['overlap_stats']['overlap_percentage']}")
    
    # Run the async function
    asyncio.run(main())

4. **Execute via CLI**

.. code-block:: bash

    # Execute strategy using CLI
    poetry run python scripts/client_scripts/execute_strategy.py my_strategy.yaml

Core Concepts
-------------

Core Actions
~~~~~~~~~~~~

Biomapper provides three core action types that handle most mapping scenarios:

**LOAD_DATASET_IDENTIFIERS**
  Load identifiers from CSV/TSV files with flexible column mapping.

**MERGE_WITH_UNIPROT_RESOLUTION** 
  Merge datasets with historical UniProt identifier resolution.

**CALCULATE_SET_OVERLAP**
  Calculate overlap statistics between two datasets.

Strategy Configuration
~~~~~~~~~~~~~~~~~~~~~~

Strategies are defined in YAML files with these key sections:

* **name**: Strategy identifier
* **description**: Human-readable description  
* **steps**: Ordered list of actions to execute

Each step contains:

* **name**: Step identifier
* **action**: Action configuration with type and parameters

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
  Large datasets may take time. The client has a 3-hour timeout by default.

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

* Use absolute file paths to avoid path resolution issues
* For large datasets, ensure adequate memory and timeout settings  
* Monitor API server resources during execution
* Consider breaking large strategies into smaller steps for debugging

Next Steps
----------

* See :doc:`configuration` for advanced YAML strategy options
* Check :doc:`api/rest_endpoints` for complete API reference  
* Review :doc:`actions/load_dataset_identifiers` for detailed parameter options
* Explore example strategies in the ``configs/`` directory