Quickstart Guide
================

Get BioMapper running in 5 minutes.

Prerequisites
-------------

* Python 3.11+
* Poetry package manager
* Git

Installation
------------

.. code-block:: bash

   # Clone and install
   git clone https://github.com/biomapper/biomapper.git
   cd biomapper
   poetry install --with dev,docs,api
   poetry shell

Start the API
-------------

.. code-block:: bash

   cd biomapper-api
   poetry run uvicorn app.main:app --reload --port 8000

API will be available at http://localhost:8000/docs

Your First Strategy
-------------------

1. **Create a YAML strategy** (``test_strategy.yaml``):

.. code-block:: yaml

   name: protein_harmonization
   description: Harmonize protein identifiers
   
   parameters:
     input_file: "/data/proteins.csv"
     output_dir: "/results"
   
   steps:
     - name: load_proteins
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "${parameters.input_file}"
           identifier_column: "uniprot_id"
           output_key: "proteins"
     
     - name: export_results
       action:
         type: EXPORT_DATASET_V2
         params:
           input_key: "proteins"
           output_file: "${parameters.output_dir}/harmonized.csv"
           format: "csv"

2. **Execute with Python client**:

.. code-block:: python

   from biomapper_client import BiomapperClient
   
   # Simple synchronous execution
   client = BiomapperClient(base_url="http://localhost:8000")
   result = client.run("protein_harmonization", parameters={
       "input_file": "/path/to/your/data.csv",
       "output_dir": "/path/to/output"
   })
   print(f"Success: {result['success']}")

3. **Or use the CLI**:

.. code-block:: bash

   poetry run python scripts/run_strategy.py \
     --strategy test_strategy.yaml \
     --param input_file=/data/proteins.csv \
     --param output_dir=/results

Verify Installation
-------------------

.. code-block:: bash

   # Run tests
   poetry run pytest tests/unit/
   
   # Check API health
   curl http://localhost:8000/health
   
   # View API docs
   open http://localhost:8000/docs

Next Steps
----------

* :doc:`installation` - Detailed setup instructions
* :doc:`first_mapping` - Complete mapping example
* :doc:`../usage` - Advanced usage patterns
* :doc:`../configuration` - Strategy configuration