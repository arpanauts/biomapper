Architecture Overview
=====================

Biomapper is built on a modern **service-oriented architecture** that provides flexibility, modularity, and extensibility for biological data mapping operations. The architecture has evolved from a monolithic design to a highly modular system where specialized services handle specific aspects of the mapping process.

Core Architectural Principles
-----------------------------

1. **Service-Oriented Design**: Each major functionality is encapsulated in a dedicated service with clear responsibilities
2. **Facade Pattern**: The ``MappingExecutor`` acts as a high-level facade, delegating complex operations to specialized services
3. **Configuration-Driven**: Complex mapping workflows are defined using YAML strategies
4. **Dependency Injection**: Services are composed together using dependency injection for maximum flexibility
5. **Separation of Concerns**: Each service focuses on a single responsibility

High-Level Architecture
-----------------------

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────────┐
    │                        Client Application                        │
    └─────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                        MappingExecutor                           │
    │                          (Facade)                                │
    └─────────────────────┬───────────────────────┬───────────────────┘
                          │                       │
           ┌──────────────┴──────────┐  ┌────────┴──────────────┐
           │                         │  │                       │
           ▼                         ▼  ▼                       ▼
    ┌──────────────┐      ┌─────────────────┐      ┌──────────────────┐
    │  Execution   │      │    Handler      │      │   Supporting     │
    │  Services    │      │   Services      │      │   Components     │
    ├──────────────┤      ├─────────────────┤      ├──────────────────┤
    │ • Iterative  │      │ • Direct        │      │ • PathFinder     │
    │ • DbStrategy │      │   Mapping       │      │ • ClientManager  │
    │ • Yaml       │      │ • Mapping       │      │ • Cache          │
    │   Strategy   │      │   Handler       │      │ • Monitoring     │
    └──────────────┘      └─────────────────┘      └──────────────────┘

Key Components
--------------

MappingExecutor (Facade)
~~~~~~~~~~~~~~~~~~~~~~~~

The ``MappingExecutor`` serves as the primary entry point for all mapping operations. It:

- Provides a clean, high-level API for clients
- Delegates complex operations to appropriate services
- Manages the overall coordination between services
- Handles initialization of the service ecosystem

.. code-block:: python

    from biomapper.core.mapping_executor import MappingExecutor
    
    # The executor automatically initializes all required services
    executor = MappingExecutor()
    
    # Simple API hides the complexity of the underlying services
    results = executor.execute_mapping(entity_names, entity_type)

Execution Services
~~~~~~~~~~~~~~~~~~

These services handle different execution strategies for mapping operations:

**IterativeExecutionService**
  Handles iterative mapping approaches where mappings are attempted through multiple providers or strategies sequentially.

**DbStrategyExecutionService**
  Executes mapping strategies that are stored in the database, allowing for dynamic strategy management.

**YamlStrategyExecutionService**
  Executes mapping workflows defined in YAML configuration files. This is the primary method for defining complex, multi-step mapping pipelines.

Handler Services
~~~~~~~~~~~~~~~~

These services manage the actual mapping operations:

**DirectMappingService**
  Provides direct, single-step mapping operations using configured mapping providers.

**MappingHandlerService**
  Orchestrates complex mapping operations, coordinating between different mapping sources and strategies.

Supporting Components
~~~~~~~~~~~~~~~~~~~~~

**PathFinder**
  Discovers and manages mapping paths between different biological ontologies and namespaces.

**ClientManager**
  Manages connections to external mapping services and APIs, handling connection pooling, retries, and failover.

**Cache System**
  Provides efficient caching of mapping results to minimize redundant API calls and improve performance.

**Monitoring System**
  Tracks performance metrics, success rates, and system health.

YAML Strategy System
--------------------

One of the most powerful features of the new architecture is the YAML-based strategy system. Complex mapping workflows can be defined declaratively:

.. code-block:: yaml

    name: comprehensive_protein_mapping
    description: Multi-step protein mapping with fallback strategies
    steps:
      - action: direct_mapping
        name: Try primary database
        parameters:
          provider: uniprot
          timeout: 30
          
      - action: synonym_expansion
        name: Expand using synonyms
        parameters:
          sources: [protein_synonyms, gene_aliases]
          
      - action: similarity_search
        name: Fallback to similarity
        parameters:
          threshold: 0.85
          algorithm: levenshtein

Service Dependencies
--------------------

The services are composed together using dependency injection, typically handled by the ``MappingExecutorInitializer``:

.. code-block:: text

    MappingExecutorInitializer
            │
            ├─→ Creates ClientManager
            ├─→ Creates PathFinder
            ├─→ Creates DirectMappingService(ClientManager)
            ├─→ Creates MappingHandlerService(DirectMappingService, PathFinder)
            ├─→ Creates ExecutionServices(MappingHandlerService, ...)
            └─→ Creates MappingExecutor(ExecutionServices, ...)

Benefits of the Architecture
----------------------------

1. **Modularity**: Each service can be developed, tested, and deployed independently
2. **Extensibility**: New services and strategies can be added without modifying existing code
3. **Testability**: Services can be easily mocked and tested in isolation
4. **Flexibility**: Different execution strategies can be mixed and matched
5. **Configuration-Driven**: Business logic can be modified without code changes
6. **Performance**: Services can be optimized independently, caching is built-in
7. **Maintainability**: Clear separation of concerns makes the codebase easier to understand

Example: Adding a New Mapping Strategy
--------------------------------------

The architecture makes it easy to extend functionality. Here's how to add a new mapping strategy:

1. **Define the strategy in YAML**:

   .. code-block:: yaml

       name: custom_mapping_strategy
       steps:
         - action: custom_action
           parameters:
             custom_param: value

2. **Implement the action** (if needed):

   .. code-block:: python

       from biomapper.core.strategy_actions import StrategyAction
       
       class CustomAction(StrategyAction):
           def execute(self, context, parameters):
               # Implementation here
               return results

3. **Register and use**:

   .. code-block:: python

       executor.execute_yaml_strategy(
           'custom_mapping_strategy',
           entity_names,
           initial_context={'entity_type': 'protein'}
       )

Migration from Legacy Architecture
----------------------------------

The evolution from the monolithic ``MappingExecutor`` to the service-oriented architecture was driven by:

- Need for better testability
- Requirement for more flexible configuration
- Demand for easier extensibility
- Performance optimization requirements

The facade pattern ensures backward compatibility while providing all the benefits of the new architecture.