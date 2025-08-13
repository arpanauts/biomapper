Your First Mapping
==================

Step-by-step tutorial for creating and executing your first biological data mapping.

Overview
--------

This tutorial will walk you through:

1. Preparing sample data
2. Creating a simple strategy
3. Executing the mapping
4. Interpreting results

Sample Data
-----------

For this tutorial, create a file called ``proteins.csv`` with this content:

.. code-block:: csv

    protein_name,uniprot_id,source
    AARSD1,Q9BTE6,Study_A
    ABL1,P00519,Study_A  
    ACE,P12821,Study_A

Create the Strategy
-------------------

Create a file ``my_first_mapping.yaml``:

.. code-block:: yaml

    name: "MY_FIRST_MAPPING"
    description: "Load and analyze a simple protein dataset"
    
    steps:
      - name: load_proteins
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/absolute/path/to/proteins.csv"
            identifier_column: "uniprot_id" 
            output_key: "my_proteins"
            dataset_name: "Tutorial Proteins"

⚠️ **Important**: Replace ``/absolute/path/to/proteins.csv`` with the actual absolute path to your file.

Execute the Strategy
--------------------

Method 1: Python Client
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from biomapper_client import BiomapperClient
    
    # Simple synchronous execution (recommended for beginners)
    client = BiomapperClient(base_url="http://localhost:8000")
    result = client.run("my_first_mapping.yaml")
    
    # Print results
    print("Execution Status:", result['status'])
    print("Job ID:", result.get('job_id'))
    
    # For async execution with progress tracking:
    import asyncio
    
    async def main():
        async with BiomapperClient() as client:
            result = await client.execute_strategy_file("my_first_mapping.yaml")
            
            # Access the loaded data
            if 'datasets' in result.get('results', {}):
                proteins = result['results']['datasets']['my_proteins']
                print(f"Loaded {len(proteins)} proteins")
    
    # Run async version if needed
    # asyncio.run(main())

Method 2: CLI Script
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    poetry run python scripts/client_scripts/execute_strategy.py my_first_mapping.yaml

Understanding Results
---------------------

The execution returns a structure like:

.. code-block:: json

    {
        "status": "success",
        "results": {
            "datasets": {
                "my_proteins": [
                    {"uniprot_id": "Q9BTE6", "protein_name": "AARSD1", "source": "Study_A"},
                    {"uniprot_id": "P00519", "protein_name": "ABL1", "source": "Study_A"},
                    {"uniprot_id": "P12821", "protein_name": "ACE", "source": "Study_A"}
                ]
            },
            "metadata": {
                "my_proteins": {
                    "row_count": 3,
                    "dataset_name": "Tutorial Proteins"
                }
            }
        },
        "execution_time": 0.05
    }

Key components:

* **status**: "success" or "error"
* **datasets**: The actual loaded data
* **metadata**: Statistics and information about each dataset
* **execution_time**: How long the strategy took to execute

Next Steps
----------

Try these extensions to your first mapping:

1. **Load a second dataset** and compare them
2. **Use MERGE_WITH_UNIPROT_RESOLUTION** to resolve historical IDs
3. **Add CALCULATE_SET_OVERLAP** to find overlaps

Example with overlap calculation:

.. code-block:: yaml

    name: "EXTENDED_MAPPING"  
    description: "Load and compare two protein datasets"
    
    steps:
      - name: load_proteins_a
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/path/to/proteins_a.csv"
            identifier_column: "uniprot_id"
            output_key: "proteins_a"
      
      - name: load_proteins_b  
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/path/to/proteins_b.csv"
            identifier_column: "uniprot_id"
            output_key: "proteins_b"
      
      - name: merge_datasets
        action:
          type: MERGE_DATASETS
          params:
            input_keys: ["proteins_a", "proteins_b"]
            output_key: "merged_proteins"
            id_column: "uniprot_id"
      
      - name: compare_datasets
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "proteins_a"
            dataset_b_key: "proteins_b"
            id_column: "uniprot_id"
            output_key: "overlap_analysis"
            generate_venn: true

Available Actions
-----------------

Biomapper includes 35+ self-registering actions. Key ones for beginners:

* **Data Loading**: LOAD_DATASET_IDENTIFIERS
* **Protein Mapping**: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS, PROTEIN_NORMALIZE_ACCESSIONS, MERGE_WITH_UNIPROT_RESOLUTION
* **Metabolite Mapping**: METABOLITE_CTS_BRIDGE, NIGHTINGALE_NMR_MATCH, SEMANTIC_METABOLITE_MATCH
* **Analysis**: CALCULATE_SET_OVERLAP, CALCULATE_THREE_WAY_OVERLAP, GENERATE_METABOLOMICS_REPORT
* **Export**: EXPORT_DATASET_V2, SYNC_TO_GOOGLE_DRIVE_V2

The self-registering architecture makes it easy to add new actions.

Continue Learning
-----------------

* :doc:`../usage` - Comprehensive usage patterns  
* :doc:`../configuration` - Advanced strategy configuration
* :doc:`../architecture/action_system` - Learn how to develop new actions
* :doc:`../actions/index` - Complete action reference
* :doc:`../api/client_reference` - Python client API

---
## Verification Sources
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:
- `biomapper_client/client_v2.py` (client usage examples)
- `biomapper/core/strategy_actions/analysis/calculate_set_overlap.py` (action parameters)
- `scripts/client_scripts/execute_strategy.py` (CLI execution)
- `configs/strategies/` (example strategies)