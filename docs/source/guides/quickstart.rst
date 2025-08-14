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
   git clone https://github.com/arpanauts/biomapper.git
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

   # Using the biomapper CLI
   poetry run biomapper run test_strategy.yaml \
     --parameters '{"input_file": "/data/proteins.csv", "output_dir": "/results"}' \
     --watch

Verify Installation
-------------------

.. code-block:: bash

   # Run tests with coverage
   poetry run pytest --cov=biomapper
   
   # Quick unit tests only
   poetry run pytest tests/unit/
   
   # Check API health
   curl http://localhost:8000/health
   
   # View interactive API docs
   open http://localhost:8000/docs

Common Actions
--------------

* **LOAD_DATASET_IDENTIFIERS** - Load biological identifiers
* **PROTEIN_EXTRACT_UNIPROT_FROM_XREFS** - Extract UniProt IDs
* **METABOLITE_CTS_BRIDGE** - Chemical Translation Service
* **CALCULATE_SET_OVERLAP** - Dataset comparison
* **EXPORT_DATASET_V2** - Export results

Next Steps
----------

* :doc:`installation` - Detailed setup instructions
* :doc:`first_mapping` - Complete mapping example
* :doc:`../usage` - Advanced usage patterns
* :doc:`../configuration` - Strategy configuration
* :doc:`../actions/index` - Complete action reference

---
## Verification Sources
*Last verified: 2025-08-14*

This documentation was verified against the following project resources:

- `/biomapper/biomapper-api/app/main.py` (uvicorn server startup command)
- `/biomapper/biomapper_client/biomapper_client/client_v2.py` (BiomapperClient.run() method)
- `/biomapper/biomapper_client/biomapper_client/cli_v2.py` (biomapper run CLI command)
- `/biomapper/biomapper/core/strategy_actions/registry.py` (action registration)
- `/biomapper/pyproject.toml` (Python 3.11+ requirement, repository URL)