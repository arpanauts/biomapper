Usage Guide
===========

This guide demonstrates how to use biomapper's service-oriented architecture for biological entity mapping. The examples progress from simple use cases to more advanced scenarios.

Quick Start
-----------

The simplest way to use biomapper is through the ``MappingExecutor`` facade:

.. code-block:: python

    from biomapper.core.mapping_executor import MappingExecutor
    
    # Initialize the executor - all services are automatically configured
    executor = MappingExecutor()
    
    # Map protein names
    protein_names = ["BRCA1", "TP53", "EGFR"]
    results = executor.execute_mapping(
        entity_names=protein_names,
        entity_type="protein"
    )
    
    # Access mapping results
    for result in results:
        print(f"{result.query_id} -> {result.mapped_id} (confidence: {result.confidence})")

Basic Usage Examples
--------------------

Mapping Different Entity Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Biomapper supports various biological entity types:

.. code-block:: python

    # Gene mapping
    gene_results = executor.execute_mapping(
        entity_names=["BRCA1", "BRCA2", "MLH1"],
        entity_type="gene"
    )
    
    # Metabolite/compound mapping
    metabolite_results = executor.execute_mapping(
        entity_names=["glucose", "ATP", "NADH"],
        entity_type="metabolite"
    )
    
    # Disease mapping
    disease_results = executor.execute_mapping(
        entity_names=["diabetes", "hypertension", "Alzheimer's disease"],
        entity_type="disease"
    )

Handling Mapping Results
~~~~~~~~~~~~~~~~~~~~~~~~

Mapping results contain rich information about the mapping process:

.. code-block:: python

    results = executor.execute_mapping(["BRCA1", "p53"], "protein")
    
    for result in results:
        print(f"Query: {result.query_id}")
        print(f"Mapped to: {result.mapped_id}")
        print(f"Confidence: {result.confidence}")
        print(f"Source: {result.source}")
        
        # Check if mapping was successful
        if result.confidence > 0.8:
            print("High confidence mapping!")
        elif result.confidence > 0.5:
            print("Medium confidence - review recommended")
        else:
            print("Low confidence - manual verification needed")

Advanced Usage: YAML Strategies
-------------------------------

For complex mapping workflows, use YAML-defined strategies:

.. code-block:: python

    # Execute a pre-defined YAML strategy
    results = executor.execute_yaml_strategy(
        strategy_name="comprehensive_protein_mapping",
        entity_names=["BRCA1", "invalid_protein_123", "P53"],
        initial_context={
            "entity_type": "protein",
            "require_high_confidence": True
        }
    )

Custom Context Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass custom parameters through the initial context:

.. code-block:: python

    # Configure strategy behavior through context
    context = {
        "entity_type": "gene",
        "species": "human",
        "fallback_enabled": True,
        "timeout": 60,
        "min_confidence": 0.7
    }
    
    results = executor.execute_yaml_strategy(
        strategy_name="species_specific_mapping",
        entity_names=gene_list,
        initial_context=context
    )

Working with Batch Operations
-----------------------------

For large-scale mapping operations:

.. code-block:: python

    # Process large lists efficiently
    large_protein_list = load_proteins_from_file("proteins.txt")
    
    # Biomapper automatically handles batching for optimal performance
    results = executor.execute_mapping(
        entity_names=large_protein_list,
        entity_type="protein"
    )
    
    # Process results
    successful_mappings = [r for r in results if r.confidence > 0.8]
    failed_mappings = [r for r in results if r.confidence < 0.3]
    
    print(f"Successfully mapped: {len(successful_mappings)}/{len(results)}")

Error Handling
--------------

Biomapper provides comprehensive error handling:

.. code-block:: python

    try:
        results = executor.execute_mapping(
            entity_names=["BRCA1", "TP53"],
            entity_type="protein"
        )
    except ValueError as e:
        print(f"Invalid input: {e}")
    except ConnectionError as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    # Results include error information for individual entities
    for result in results:
        if result.error:
            print(f"Error mapping {result.query_id}: {result.error}")

Accessing Mapping Metrics
-------------------------

Monitor mapping performance and quality:

.. code-block:: python

    from biomapper.monitoring import MetricsCollector
    
    # Execute mapping with metrics collection
    results = executor.execute_mapping(proteins, "protein")
    
    # Access metrics
    metrics = MetricsCollector.get_instance()
    stats = metrics.get_summary_stats()
    
    print(f"Total mappings: {stats['total_mappings']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Average confidence: {stats['avg_confidence']:.3f}")
    print(f"Average response time: {stats['avg_response_time']:.2f}s")

Custom Strategy Execution
-------------------------

For maximum control, execute custom strategies programmatically:

.. code-block:: python

    # Define a custom execution flow
    custom_strategy = {
        "name": "custom_flow",
        "steps": [
            {
                "action": "direct_mapping",
                "parameters": {"provider": "uniprot"}
            },
            {
                "action": "synonym_expansion",
                "parameters": {"max_synonyms": 5}
            }
        ]
    }
    
    # Execute with custom strategy
    results = executor.execute_custom_strategy(
        strategy=custom_strategy,
        entity_names=["BRCA1", "TP53"],
        context={"entity_type": "protein"}
    )

Integration Examples
--------------------

Web Application Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from flask import Flask, request, jsonify
    from biomapper.core.mapping_executor import MappingExecutor
    
    app = Flask(__name__)
    executor = MappingExecutor()
    
    @app.route('/map', methods=['POST'])
    def map_entities():
        data = request.json
        entity_names = data.get('entities', [])
        entity_type = data.get('type', 'protein')
        
        try:
            results = executor.execute_mapping(entity_names, entity_type)
            return jsonify({
                'success': True,
                'mappings': [r.to_dict() for r in results]
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

Data Pipeline Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pandas as pd
    from biomapper.core.mapping_executor import MappingExecutor
    
    # Load data
    df = pd.read_csv('experimental_data.csv')
    executor = MappingExecutor()
    
    # Map protein names to standard IDs
    protein_names = df['protein_name'].unique().tolist()
    mapping_results = executor.execute_mapping(protein_names, 'protein')
    
    # Create mapping dictionary
    mapping_dict = {
        r.query_id: r.mapped_id 
        for r in mapping_results 
        if r.confidence > 0.8
    }
    
    # Apply mappings to dataframe
    df['protein_id'] = df['protein_name'].map(mapping_dict)
    
    # Handle unmapped entities
    unmapped = df[df['protein_id'].isna()]['protein_name'].unique()
    print(f"Unable to map {len(unmapped)} proteins")

Best Practices
--------------

1. **Always specify entity type**: This helps biomapper choose the most appropriate mapping strategy
2. **Handle low-confidence mappings**: Set confidence thresholds appropriate for your use case
3. **Use YAML strategies for complex workflows**: They're easier to maintain and modify
4. **Monitor performance**: Use the metrics system to track mapping quality
5. **Cache results**: Biomapper automatically caches results, but consider application-level caching for repeated queries
6. **Batch operations**: Process entities in batches for better performance
7. **Error handling**: Always implement proper error handling for production use

Next Steps
----------

- Explore :doc:`configuration` to learn about YAML strategy configuration
- Read :doc:`architecture` to understand the service-oriented design
- Check :doc:`api/core` for detailed API documentation
- See :doc:`tutorials/examples` for more complex examples