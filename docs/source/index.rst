Welcome to biomapper's documentation!
=====================================

biomapper is a modular, extensible Python framework for biological data harmonization and ontology mapping. Built on a service-oriented architecture, biomapper provides flexible configuration-driven workflows for mapping biological entities across different naming systems and ontologies.

Key Features
------------

* **Service-Oriented Architecture**: Modular design with specialized services for different aspects of mapping execution
* **Configuration-Driven**: Define complex mapping pipelines using YAML-based strategies
* **Extensible**: Easy to add new mapping services, strategies, and data sources
* **Multi-Provider Support**: Integrate with various biological databases and name resolution services
* **Efficient Caching**: Built-in caching mechanisms for improved performance
* **Comprehensive Monitoring**: Track and analyze mapping operations with detailed metrics

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   guides/getting_started
   usage
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   
   tutorials/llm_mapper
   tutorials/multi_provider
   tutorials/protein
   tutorials/examples

.. toctree::
   :maxdepth: 2
   :caption: Architecture
   
   architecture
   architecture/overview
   architecture/resource_metadata_system
   architecture/testing

.. toctree::
   :maxdepth: 2
   :caption: UI Documentation
   
   ui/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/services
   api/core
   api/mapping
   api/monitoring
   api/standardization
   api/utils
   api/schemas