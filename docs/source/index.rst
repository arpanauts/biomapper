BioMapper Documentation
=======================

BioMapper is a YAML-based workflow platform built on a self-registering action system. While originally designed for biological data harmonization (proteins, metabolites, chemistry), its extensible architecture supports any workflow that can be expressed as a sequence of actions operating on shared execution context.

🎯 **Key Features**
-------------------

* **Self-registering action system** - Actions automatically register via decorators
* **Type-safe parameters** - Pydantic models provide validation and IDE support  
* **YAML workflow definition** - Declarative strategies without coding
* **Real-time progress tracking** - SSE events for long-running jobs
* **Extensible architecture** - Easy to add new actions and entity types
* **AI-ready design** - Built for integration with Claude Code and LLM assistance

🚀 **Quick Start**
------------------

.. code-block:: bash

   # Install with Poetry
   poetry install --with dev,docs,api
   poetry shell
   
   # Start the API server
   cd biomapper-api && poetry run uvicorn app.main:app --reload --port 8000
   
   # Or use the CLI (from root directory)
   poetry run biomapper --help
   poetry run biomapper health

.. code-block:: python

   # Python client usage
   from biomapper_client import BiomapperClient
   
   client = BiomapperClient("http://localhost:8000")
   result = client.run("test_metabolite_simple", parameters={
       "input_file": "/data/metabolites.csv",
       "output_dir": "/tmp/results"
   })
   print(f"Status: {result['status']}")

🏗️ **Architecture**
--------------------

BioMapper follows a modern microservices architecture with three layers:

1. **Client Layer** - Python client library (``biomapper_client``) for programmatic access
2. **API Layer** - FastAPI service with SQLite job persistence and SSE progress tracking
3. **Core Layer** - 30+ self-registering actions with strategy execution engine

The system uses a **registry pattern** where actions self-register via ``@register_action`` decorators, a **strategy pattern** for YAML-based workflow configuration, and a **pipeline pattern** for data flow through shared execution context. Actions are organized by biological entity (proteins, metabolites, chemistry) and automatically discovered at runtime.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   
   guides/quickstart
   guides/installation
   guides/first_mapping

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   usage
   configuration
   api_client

.. toctree::
   :maxdepth: 2
   :caption: Reference
   
   actions/index
   api/index
   architecture/index

.. toctree::
   :maxdepth: 1
   :caption: Development
   
   development/creating_actions
   development/testing
   development/contributing

📚 **Available Actions**
------------------------

BioMapper includes 30+ actions across categories:

* **Data Operations**: Load, merge, filter, export, transform
* **Protein Mapping**: UniProt resolution, accession normalization, multi-bridge
* **Metabolite Matching**: CTS, semantic, vector, NMR matching
* **Chemistry**: LOINC extraction, fuzzy matching, vendor harmonization
* **Analysis**: Set overlap, quality metrics, comprehensive reports

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``biomapper/core/strategy_actions/registry.py`` (Action registry)
- ``biomapper_client/biomapper_client/client_v2.py`` (Client implementation)
- ``biomapper-api/app/main.py`` (API server)
- ``configs/strategies/test_metabolite_simple.yaml`` (Example strategy)
- ``README.md`` (Project overview)
- ``CLAUDE.md`` (Commands and patterns)