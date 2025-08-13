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
   
   # Run a strategy
   poetry run python scripts/run_strategy.py --strategy test_metabolite_simple
   
   # Or start the API server
   cd biomapper-api && uvicorn app.main:app --reload

.. code-block:: python

   # Python client usage
   from biomapper_client import BiomapperClient
   
   client = BiomapperClient()
   result = client.run("test_metabolite_simple", parameters={
       "input_file": "/data/metabolites.csv"
   })

🏗️ **Architecture**
--------------------

BioMapper follows a modern microservices architecture with three layers:

1. **Client Layer** - Python client library for programmatic access
2. **API Layer** - FastAPI service with job management and SSE progress
3. **Core Layer** - Self-registering actions and strategy execution engine

The system uses a **registry pattern** where actions self-register at import time, a **strategy pattern** for YAML-based workflow configuration, and a **pipeline pattern** for data flow through shared execution context.

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`