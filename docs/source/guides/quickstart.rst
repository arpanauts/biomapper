Quickstart Guide
================

Get up and running with Biomapper in 5 minutes.

Prerequisites
-------------

* Python 3.11+
* Poetry package manager

Installation
------------

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/your-org/biomapper.git
       cd biomapper

2. Install dependencies:

   .. code-block:: bash

       poetry install --with dev,docs,api

3. Activate the environment:

   .. code-block:: bash

       poetry shell

Start the API Server
--------------------

.. code-block:: bash

    cd biomapper-api
    poetry run uvicorn main:app --reload

The API will be available at http://localhost:8000

Your First Mapping
------------------

1. Create a strategy file ``test_mapping.yaml``:

   .. code-block:: yaml

       name: "TEST_MAPPING"
       description: "Test protein mapping"
       
       steps:
         - name: load_data
           action:
             type: LOAD_DATASET_IDENTIFIERS
             params:
               file_path: "/path/to/your/proteins.csv"
               identifier_column: "uniprot"
               output_key: "proteins"

2. Execute using the Python client:

   .. code-block:: python

       import asyncio
       from biomapper_client import BiomapperClient
       
       async def main():
           async with BiomapperClient() as client:
               result = await client.execute_strategy_file("test_mapping.yaml")
               print(f"Loaded {result['results']['proteins']['count']} proteins")
       
       asyncio.run(main())

Next Steps
----------

* Read the :doc:`../usage` guide for detailed examples
* Learn about :doc:`../configuration` for complex strategies  
* Explore the :doc:`../api/rest_endpoints` reference