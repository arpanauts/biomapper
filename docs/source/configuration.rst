Configuration Guide
===================

Biomapper's flexible configuration system allows you to customize mapping behavior through YAML files. This guide covers the main configuration files and how to create custom mapping strategies.

Configuration Files Overview
-----------------------------

Biomapper uses several configuration files:

1. **protein_config.yaml** - Core protein mapping configuration
2. **mapping_strategies_config.yaml** - YAML strategy definitions
3. **client_config.yaml** - External client configuration
4. **cache_config.yaml** - Caching system configuration

protein_config.yaml
--------------------

This file contains the core configuration for protein mapping operations:

.. code-block:: yaml

    # Database configuration
    database:
      url: "sqlite:///mapping_cache.db"
      echo: false
      pool_size: 10
      max_overflow: 20
    
    # Default mapping providers
    providers:
      primary: uniprot
      secondary: ncbi
      fallback: similarity_search
    
    # Confidence thresholds
    confidence:
      high_threshold: 0.9
      medium_threshold: 0.7
      low_threshold: 0.5
    
    # Timeout settings (in seconds)
    timeouts:
      api_request: 30
      total_mapping: 300
      batch_operation: 600
    
    # Retry configuration
    retry:
      max_attempts: 3
      backoff_factor: 2.0
      retry_status_codes: [500, 502, 503, 504]

mapping_strategies_config.yaml
-------------------------------

This is the heart of biomapper's configuration system. It defines reusable mapping strategies that can be executed by name.

Basic Strategy Structure
~~~~~~~~~~~~~~~~~~~~~~~~

Each strategy is defined with the following structure:

.. code-block:: yaml

    strategy_name:
      description: "Brief description of what this strategy does"
      steps:
        - action: action_name
          name: "Step description"
          parameters:
            parameter1: value1
            parameter2: value2

Complete Example
~~~~~~~~~~~~~~~~

Here's a comprehensive example showing various strategy types:

.. code-block:: yaml

    # Simple direct mapping strategy
    simple_protein_mapping:
      description: "Basic protein mapping using UniProt"
      steps:
        - action: direct_mapping
          name: "Map to UniProt"
          parameters:
            provider: uniprot
            timeout: 30
            min_confidence: 0.8
    
    # Comprehensive multi-step strategy
    comprehensive_protein_mapping:
      description: "Multi-step protein mapping with fallbacks"
      steps:
        - action: direct_mapping
          name: "Primary UniProt mapping"
          parameters:
            provider: uniprot
            timeout: 30
            min_confidence: 0.9
            
        - action: synonym_expansion
          name: "Expand using protein synonyms"
          parameters:
            sources: [protein_synonyms, gene_aliases]
            max_synonyms: 10
            
        - action: direct_mapping
          name: "Retry with synonyms"
          parameters:
            provider: ncbi
            timeout: 45
            min_confidence: 0.8
            
        - action: similarity_search
          name: "Fuzzy matching fallback"
          parameters:
            algorithm: levenshtein
            threshold: 0.85
            max_results: 5
    
    # Species-specific mapping
    human_gene_mapping:
      description: "Human gene mapping with HGNC validation"
      steps:
        - action: species_filter
          name: "Ensure human context"
          parameters:
            species: "Homo sapiens"
            ncbi_taxon_id: 9606
            
        - action: direct_mapping
          name: "Map to HGNC"
          parameters:
            provider: hgnc
            validate_species: true
            timeout: 30
            
        - action: cross_reference
          name: "Cross-reference with Ensembl"
          parameters:
            target_db: ensembl
            relationship_type: gene_id
    
    # Batch processing strategy
    high_throughput_mapping:
      description: "Optimized for large-scale batch operations"
      steps:
        - action: batch_prepare
          name: "Prepare batch processing"
          parameters:
            batch_size: 100
            parallel_workers: 4
            
        - action: cache_lookup
          name: "Check existing mappings"
          parameters:
            cache_key_format: "{entity_type}:{query_id}"
            
        - action: batch_mapping
          name: "Process unmapped entities"
          parameters:
            provider: uniprot
            concurrent_requests: 10
            rate_limit: 100  # requests per minute

Available Actions
-----------------

The following actions are available for use in strategies:

Core Mapping Actions
~~~~~~~~~~~~~~~~~~~~

**direct_mapping**
  Performs direct mapping using a specified provider.
  
  Parameters:
    - ``provider`` (required): The mapping provider to use
    - ``timeout``: Request timeout in seconds (default: 30)
    - ``min_confidence``: Minimum confidence threshold (default: 0.5)
    - ``max_results``: Maximum number of results to return

**batch_mapping**
  Optimized batch processing for multiple entities.
  
  Parameters:
    - ``provider`` (required): The mapping provider to use
    - ``batch_size``: Number of entities per batch (default: 50)
    - ``concurrent_requests``: Number of concurrent API requests
    - ``rate_limit``: Maximum requests per minute

**similarity_search**
  Fuzzy matching for entities that don't have exact matches.
  
  Parameters:
    - ``algorithm``: Similarity algorithm (levenshtein, jaccard, etc.)
    - ``threshold``: Minimum similarity score (0.0 to 1.0)
    - ``max_results``: Maximum number of similar matches to return

Enhancement Actions
~~~~~~~~~~~~~~~~~~~

**synonym_expansion**
  Expands entity names using known synonyms.
  
  Parameters:
    - ``sources``: List of synonym sources to use
    - ``max_synonyms``: Maximum number of synonyms per entity
    - ``include_abbreviations``: Include abbreviated forms

**species_filter**
  Filters or validates entities based on species information.
  
  Parameters:
    - ``species``: Species name (e.g., "Homo sapiens")
    - ``ncbi_taxon_id``: NCBI taxonomy ID
    - ``strict_mode``: Reject entities that don't match species

**cross_reference**
  Cross-references mappings with additional databases.
  
  Parameters:
    - ``target_db``: Target database for cross-referencing
    - ``relationship_type``: Type of relationship to establish
    - ``validate_mapping``: Validate cross-references

Utility Actions
~~~~~~~~~~~~~~~

**cache_lookup**
  Checks for existing mappings in the cache.
  
  Parameters:
    - ``cache_key_format``: Format string for cache keys
    - ``ttl``: Time-to-live for cached results (seconds)

**batch_prepare**
  Prepares data for batch processing.
  
  Parameters:
    - ``batch_size``: Size of each batch
    - ``parallel_workers``: Number of parallel processing workers
    - ``sort_by``: Sort entities before batching

**validation**
  Validates mapping results against specified criteria.
  
  Parameters:
    - ``min_confidence``: Minimum confidence required
    - ``required_fields``: List of required result fields
    - ``custom_validators``: Custom validation functions

Creating Custom Strategies
---------------------------

Step-by-Step Guide
~~~~~~~~~~~~~~~~~~

1. **Identify the mapping workflow**: Determine what steps are needed for your specific use case.

2. **Choose appropriate actions**: Select from the available actions or identify if new actions are needed.

3. **Define the strategy**: Create a YAML definition following the structure above.

4. **Test the strategy**: Execute the strategy with test data to verify it works correctly.

5. **Add to configuration**: Add your strategy to the ``mapping_strategies_config.yaml`` file.

Example: Custom Metabolite Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    metabolite_pubchem_mapping:
      description: "Metabolite mapping prioritizing PubChem with ChEBI fallback"
      steps:
        - action: name_standardization
          name: "Standardize metabolite names"
          parameters:
            remove_prefixes: ["L-", "D-", "DL-"]
            normalize_case: true
            remove_special_chars: ["(", ")", "[", "]"]
            
        - action: direct_mapping
          name: "Map to PubChem"
          parameters:
            provider: pubchem
            search_type: name
            timeout: 45
            min_confidence: 0.85
            
        - action: direct_mapping
          name: "Fallback to ChEBI"
          parameters:
            provider: chebi
            search_type: synonym
            timeout: 30
            min_confidence: 0.75
            only_if_previous_failed: true
            
        - action: inchi_validation
          name: "Validate using InChI keys"
          parameters:
            require_inchi: true
            validate_structure: true

Strategy Execution Context
--------------------------

Strategies can access and modify execution context during runtime:

Context Variables
~~~~~~~~~~~~~~~~~

The following variables are available in all strategies:

- ``entity_names``: List of entities being mapped
- ``entity_type``: Type of entities (protein, gene, metabolite, etc.)
- ``timestamp``: Strategy execution timestamp
- ``user_id``: User identifier (if available)
- ``batch_id``: Unique identifier for the batch operation

Custom Context
~~~~~~~~~~~~~~

You can pass custom context when executing strategies:

.. code-block:: python

    # Pass custom context
    context = {
        "species": "human",
        "experimental_context": "proteomics",
        "confidence_threshold": 0.9,
        "max_processing_time": 300
    }
    
    results = executor.execute_yaml_strategy(
        "comprehensive_protein_mapping",
        entity_names,
        initial_context=context
    )

Context Access in Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Actions can access context variables using the ``${}`` syntax:

.. code-block:: yaml

    context_aware_mapping:
      description: "Strategy that adapts based on context"
      steps:
        - action: direct_mapping
          name: "Context-aware mapping"
          parameters:
            provider: uniprot
            species: "${species}"
            confidence_threshold: "${confidence_threshold}"
            timeout: "${max_processing_time}"

Strategy Validation
-------------------

Schema Validation
~~~~~~~~~~~~~~~~~

All strategies are validated against a JSON schema to ensure correctness:

.. code-block:: yaml

    # This will be validated automatically
    invalid_strategy:
      description: "This strategy has validation errors"
      steps:
        - action: direct_mapping
          # Missing required 'name' field - validation error
          parameters:
            provider: uniprot

Runtime Validation
~~~~~~~~~~~~~~~~~~

Strategies are also validated at runtime:

- Required parameters are checked
- Parameter types are validated
- Provider availability is verified
- Context variables are resolved

Error Handling in Strategies
-----------------------------

Strategies support various error handling approaches:

.. code-block:: yaml

    robust_mapping_strategy:
      description: "Strategy with comprehensive error handling"
      steps:
        - action: direct_mapping
          name: "Primary mapping attempt"
          parameters:
            provider: uniprot
            timeout: 30
          error_handling:
            on_timeout: continue
            on_provider_error: continue
            on_network_error: retry
            max_retries: 3
            
        - action: direct_mapping
          name: "Fallback mapping"
          parameters:
            provider: ncbi
            timeout: 45
          conditions:
            execute_if: previous_step_failed
            
        - action: manual_review_flag
          name: "Flag for manual review"
          parameters:
            reason: "Automated mapping failed"
          conditions:
            execute_if: all_previous_failed

Best Practices
--------------

1. **Use descriptive names**: Both strategy names and step names should clearly indicate their purpose
2. **Include descriptions**: Always provide clear descriptions for strategies and complex steps
3. **Set appropriate timeouts**: Balance performance with reliability
4. **Handle errors gracefully**: Include fallback steps for when primary methods fail
5. **Test thoroughly**: Test strategies with various input types and edge cases
6. **Version your strategies**: Keep track of changes to strategies over time
7. **Document custom actions**: If you create custom actions, document their parameters
8. **Use context appropriately**: Leverage context for dynamic behavior without hardcoding values

Strategy Performance Monitoring
-------------------------------

Monitor strategy performance to optimize mapping operations:

.. code-block:: python

    from biomapper.monitoring import StrategyMetrics
    
    # Get performance metrics for a strategy
    metrics = StrategyMetrics.get_strategy_performance("comprehensive_protein_mapping")
    
    print(f"Average execution time: {metrics.avg_execution_time}s")
    print(f"Success rate: {metrics.success_rate:.2%}")
    print(f"Most common failure point: {metrics.common_failure_step}")

This monitoring helps identify bottlenecks and opportunities for optimization in your mapping strategies.