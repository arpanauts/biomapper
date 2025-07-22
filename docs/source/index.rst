Welcome to biomapper's documentation!
=====================================

biomapper is a streamlined Python framework for biological data harmonization and ontology mapping. Built around YAML-based strategies and core action types, biomapper provides flexible workflows for mapping biological entities like proteins, metabolites, and genes.

Key Features
------------

* **YAML Strategy Configuration**: Define mapping workflows using simple YAML files
* **Core Action Types**: Three essential actions handle most mapping scenarios
* **API-First Design**: REST API for executing strategies remotely
* **Multi-Dataset Support**: Load and compare data from multiple biological sources
* **Type Safety**: Pydantic models ensure data validation throughout
* **Performance Tracking**: Built-in timing metrics for benchmarking

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
   :caption: Actions Reference
   
   actions/load_dataset_identifiers
   actions/merge_with_uniprot_resolution
   actions/calculate_set_overlap

.. toctree::
   :maxdepth: 2
   :caption: API Documentation
   
   api/rest_endpoints
   api/strategy_execution

.. toctree::
   :maxdepth: 2
   :caption: Architecture
   
   architecture/overview
   architecture/yaml_strategies
   architecture/action_system