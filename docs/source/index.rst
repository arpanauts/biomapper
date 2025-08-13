BioMapper Documentation
=======================

**BioMapper** is a modular bioinformatics platform for harmonizing biological data across databases and platforms.

.. code-block:: bash

   # Quick Install
   poetry install --with dev,docs,api
   poetry shell
   
   # Start API
   cd biomapper-api && uvicorn app.main:app --reload

Key Features
------------

* **🧬 Multi-Entity Support** - Proteins, metabolites, chemistry data
* **📝 YAML Workflows** - Define pipelines without coding  
* **🔌 Self-Registering Actions** - Extensible plugin architecture
* **🚀 REST API** - Execute strategies remotely
* **✅ Type Safety** - Pydantic validation throughout

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