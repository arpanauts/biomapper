BioMapper Documentation
=======================

**BioMapper** is a YAML-based workflow platform built on a self-registering action system. While designed for biological data harmonization, its architecture supports any workflow that can be expressed as a sequence of actions operating on shared data.

.. code-block:: bash

   # Quick Install
   poetry install --with dev,docs,api
   poetry shell
   
   # Optional: Start API Server
   cd biomapper-api && uvicorn app.main:app --reload

Key Features
------------

* **📝 YAML Strategies** - Define workflows as YAML configurations
* **🔌 Self-Registering Actions** - Extensible plugin architecture  
* **🧬 Biological Data Focus** - Specialized actions for proteins, metabolites, chemistry
* **🔄 General Workflow Support** - Any sequential data processing pipeline
* **🚀 Multiple Interfaces** - Python library, REST API, CLI
* **✅ Type Safety** - Pydantic validation throughout

**Note on the API:** The REST API uses standard JSON for HTTP communication but executes YAML-defined strategies. Think of it as a JSON wrapper around YAML workflows.

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