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

    import asyncio
    from biomapper_client import BiomapperClient
    
    async def main():
        async with BiomapperClient() as client:
            result = await client.execute_strategy_file("my_first_mapping.yaml")
            
            # Print results
            print("Execution Status:", result['status'])
            print("Datasets loaded:", list(result['results']['datasets'].keys()))
            
            # Access the loaded data
            proteins = result['results']['datasets']['my_proteins']
            print(f"Loaded {len(proteins)} proteins")
    
    # Run the mapping
    asyncio.run(main())

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
      
      - name: compare_datasets
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "proteins_a"
            dataset_b_key: "proteins_b"
            output_key: "overlap_analysis"

Extensible Architecture
-----------------------

The actions used in this tutorial (LOAD_DATASET_IDENTIFIERS, MERGE_WITH_UNIPROT_RESOLUTION, CALCULATE_SET_OVERLAP) are the three foundational actions that ship with Biomapper. However, the architecture is designed to be extensible - new specialized actions can be easily added to support more sophisticated mapping approaches as requirements evolve.

Continue Learning
-----------------

* :doc:`../usage` - Comprehensive usage patterns  
* :doc:`../configuration` - Advanced strategy configuration
* :doc:`../architecture/action_system` - Learn how to develop new actions
* :doc:`../actions/load_dataset_identifiers` - Detailed action reference