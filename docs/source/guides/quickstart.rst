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

   # Start from project root (recommended)
   poetry run uvicorn src.api.main:app --reload --port 8000
   
   # Alternative: Check API status
   poetry run biomapper health

API will be available at:

- Interactive docs: http://localhost:8000/api/docs
- Health endpoint: http://localhost:8000/api/health
- Root endpoint: http://localhost:8000/

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
         type: EXPORT_DATASET
         params:
           input_key: "proteins"
           output_file: "${parameters.output_dir}/harmonized.csv"
           format: "csv"

2. **Execute with Python client**:

.. code-block:: python

   from src.client.client_v2 import BiomapperClient
   
   # Simple synchronous execution
   client = BiomapperClient(base_url="http://localhost:8000")
   result = client.run("protein_harmonization", parameters={
       "input_file": "/path/to/your/data.csv",
       "output_dir": "/path/to/output"
   })
   print(f"Success: {result.success}")  # StrategyResult object

3. **Or use the CLI**:

.. code-block:: bash

   # Check available CLI commands
   poetry run biomapper --help
   
   # List available strategies
   poetry run biomapper strategies
   
   # Verify CLI installation
   poetry run biomapper health

Verify Installation
-------------------

.. code-block:: bash

   # Test CLI installation
   poetry run biomapper health
   poetry run biomapper test-import
   
   # Run tests with coverage
   poetry run pytest --cov=src
   
   # Quick unit tests only
   poetry run pytest tests/unit/
   
   # Check API health (if API server is running)
   curl http://localhost:8000/api/health
   
   # View interactive API docs
   open http://localhost:8000/api/docs

Common Actions
--------------

* **LOAD_DATASET_IDENTIFIERS** - Load biological identifiers from CSV/TSV
* **PROTEIN_EXTRACT_UNIPROT_FROM_XREFS** - Extract UniProt IDs from reference fields
* **PROTEIN_NORMALIZE_ACCESSIONS** - Standardize protein accession formats  
* **MERGE_DATASETS** - Combine multiple datasets with deduplication
* **FILTER_DATASET** - Apply filtering criteria to datasets
* **CUSTOM_TRANSFORM_EXPRESSION** - Apply Python expressions to data
* **EXPORT_DATASET** - Export results to various formats
* **SYNC_TO_GOOGLE_DRIVE_V2** - Upload results to Google Drive
* **SEMANTIC_METABOLITE_MATCH** - AI-powered metabolite matching
* **NIGHTINGALE_NMR_MATCH** - Nightingale NMR platform matching
* **CHEMISTRY_FUZZY_TEST_MATCH** - Fuzzy matching for clinical tests

Next Steps
----------

* :doc:`installation` - Detailed setup instructions
* :doc:`../usage` - Advanced usage patterns
* :doc:`../configuration` - Strategy configuration
* :doc:`../actions/index` - Complete action reference

---

---

Verification Sources
--------------------
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- ``/biomapper/pyproject.toml`` (Python 3.11+ requirement, GitHub repository URL, src-layout structure)
- ``/biomapper/CLAUDE.md`` (Essential commands and environment setup procedures)
- ``/biomapper/src/api/main.py`` (FastAPI application with correct import paths and endpoint structure)
- ``/biomapper/src/client/client_v2.py`` (BiomapperClient with run() method returning StrategyResult objects)
- ``/biomapper/src/cli/minimal.py`` (CLI commands including health and test-import)
- ``/biomapper/src/actions/`` (Action registry and organized entity-based action structure)