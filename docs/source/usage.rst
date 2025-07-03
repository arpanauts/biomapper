Usage Guide
===========

This guide demonstrates how to use Biomapper's service-oriented architecture for biological entity mapping. All operations in Biomapper are asynchronous, requiring the use of ``async/await`` patterns.

Installation
------------

Install Biomapper using Poetry:

.. code-block:: bash

    poetry add biomapper

Or clone the repository and install in development mode:

.. code-block:: bash

    git clone https://github.com/your-org/biomapper.git
    cd biomapper
    poetry install --with dev,docs,api

Quick Start
-----------

Biomapper uses an async API. Here's a simple example:

.. code-block:: python

    import asyncio
    from biomapper.core import MappingExecutor, MappingExecutorBuilder
    from biomapper.core.models import DatabaseConfig, CacheConfig
    
    async def main():
        # Configure the executor
        db_config = DatabaseConfig(url="sqlite+aiosqlite:///data/mapping.db")
        cache_config = CacheConfig(backend="memory")
        
        # Build the executor
        executor = MappingExecutorBuilder.create(
            db_config=db_config,
            cache_config=cache_config
        )
        
        # Initialize
        await executor.initialize()
        
        try:
            # Execute a mapping
            result = await executor.execute(
                entity_names=["BRCA1", "TP53", "EGFR"],
                entity_type="protein"
            )
            
            # Process results
            for mapping in result.mappings:
                print(f"{mapping.query_id} -> {mapping.mapped_id}")
                
        finally:
            # Clean up
            await executor.shutdown()
    
    # Run the async function
    asyncio.run(main())

Basic Usage Examples
--------------------

Using YAML Strategies
~~~~~~~~~~~~~~~~~~~~~

The most common way to use Biomapper is with predefined YAML strategies:

.. code-block:: python

    async def map_with_strategy():
        # Initialize executor as shown above
        executor = await create_executor()
        
        # Execute a YAML strategy
        result = await executor.execute_yaml_strategy(
            strategy_file="configs/strategies/protein_mapping.yaml",
            input_data={
                "entities": ["BRCA1", "TP53", "EGFR"],
                "entity_type": "protein"
            },
            options={}
        )
        
        # Access results
        if result.success:
            for item in result.data:
                print(f"Mapped: {item}")
        else:
            print(f"Error: {result.error}")

Handling Different Entity Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Biomapper supports various biological entity types:

.. code-block:: python

    async def map_different_entities(executor):
        # Gene mapping
        gene_result = await executor.execute(
            entity_names=["BRCA1", "BRCA2", "MLH1"],
            entity_type="gene"
        )
        
        # Metabolite mapping
        metabolite_result = await executor.execute(
            entity_names=["glucose", "ATP", "NADH"],
            entity_type="metabolite"
        )
        
        # Disease mapping
        disease_result = await executor.execute(
            entity_names=["diabetes", "hypertension"],
            entity_type="disease"
        )

Advanced Usage
--------------

Composite Strategies
~~~~~~~~~~~~~~~~~~~~

Execute multiple strategies in a single operation:

.. code-block:: python

    async def composite_mapping(executor):
        strategies = [
            {
                "name": "primary_mapping",
                "file": "configs/strategies/uniprot_direct.yaml"
            },
            {
                "name": "fallback_mapping", 
                "file": "configs/strategies/synonym_search.yaml"
            }
        ]
        
        result = await executor.execute_composite_strategy(
            strategies=strategies,
            input_data={"entities": protein_list},
            merge_strategy="confidence_based"
        )

Database-Stored Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~

Load and execute strategies from the database:

.. code-block:: python

    async def database_strategy(executor):
        # Execute a strategy stored in the database
        result = await executor.execute_db_strategy(
            strategy_name="comprehensive_protein_mapping",
            input_data={"entities": protein_names},
            version="latest"  # or specific version
        )

Context Management
~~~~~~~~~~~~~~~~~~

Pass custom context through the execution pipeline:

.. code-block:: python

    async def custom_context_execution(executor):
        # Define custom context
        context = {
            "species": "human",
            "confidence_threshold": 0.85,
            "include_synonyms": True,
            "max_results_per_entity": 5
        }
        
        # Execute with context
        result = await executor.execute_yaml_strategy(
            strategy_file="configs/strategies/species_specific.yaml",
            input_data={"entities": gene_list},
            options=context
        )

Error Handling
--------------

Comprehensive error handling for production use:

.. code-block:: python

    from biomapper.core.exceptions import (
        MappingExecutorError,
        StrategyNotFoundError,
        ValidationError,
        ExecutionError
    )
    
    async def robust_mapping(executor, entities):
        try:
            result = await executor.execute_yaml_strategy(
                strategy_file="configs/strategies/mapping.yaml",
                input_data={"entities": entities}
            )
            return result
            
        except StrategyNotFoundError as e:
            print(f"Strategy not found: {e}")
            # Fall back to default strategy
            return await executor.execute(entities, "protein")
            
        except ValidationError as e:
            print(f"Invalid input: {e}")
            raise
            
        except ExecutionError as e:
            print(f"Execution failed: {e}")
            # Check if partial results are available
            if hasattr(e, 'partial_results'):
                return e.partial_results
            raise
            
        except MappingExecutorError as e:
            print(f"General executor error: {e}")
            raise

Batch Processing
----------------

Process large datasets efficiently:

.. code-block:: python

    async def batch_processing(executor, csv_file):
        import pandas as pd
        
        # Load data
        df = pd.read_csv(csv_file)
        
        # Process in batches
        batch_size = 1000
        all_results = []
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            entities = batch['entity_name'].tolist()
            
            # Execute batch
            result = await executor.execute(
                entity_names=entities,
                entity_type="protein"
            )
            
            all_results.extend(result.mappings)
            
            # Progress update
            print(f"Processed {i+len(batch)}/{len(df)} entities")
        
        return all_results

Integration Examples
--------------------

FastAPI Integration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fastapi import FastAPI, HTTPException
    from biomapper.core import MappingExecutor, MappingExecutorBuilder
    
    app = FastAPI()
    executor = None
    
    @app.on_event("startup")
    async def startup_event():
        global executor
        executor = MappingExecutorBuilder.create(
            db_config=DatabaseConfig(url="sqlite+aiosqlite:///data/api.db"),
            cache_config=CacheConfig(backend="redis")
        )
        await executor.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        if executor:
            await executor.shutdown()
    
    @app.post("/map")
    async def map_entities(entities: list[str], entity_type: str = "protein"):
        try:
            result = await executor.execute(
                entity_names=entities,
                entity_type=entity_type
            )
            return {"mappings": result.dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

Jupyter Notebook Usage
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # In Jupyter notebooks, use nest_asyncio for async support
    import nest_asyncio
    nest_asyncio.apply()
    
    # Create and use executor
    executor = MappingExecutorBuilder.create(
        db_config=DatabaseConfig(url="sqlite+aiosqlite:///data/notebook.db"),
        cache_config=CacheConfig(backend="memory")
    )
    
    await executor.initialize()
    
    # Now you can use await directly in notebook cells
    result = await executor.execute(["BRCA1", "TP53"], "protein")

Performance Optimization
------------------------

Concurrent Execution
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    
    async def concurrent_mapping(executor, entity_groups):
        # Create tasks for concurrent execution
        tasks = []
        for group_name, entities in entity_groups.items():
            task = executor.execute(
                entity_names=entities,
                entity_type="protein"
            )
            tasks.append((group_name, task))
        
        # Execute concurrently
        results = {}
        for group_name, task in tasks:
            try:
                result = await task
                results[group_name] = result
            except Exception as e:
                results[group_name] = {"error": str(e)}
        
        return results

Caching Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from biomapper.core.models import CacheConfig
    
    # Redis cache for production
    cache_config = CacheConfig(
        backend="redis",
        redis_url="redis://localhost:6379",
        ttl=3600,  # 1 hour
        max_size=10000
    )
    
    # Memory cache for development
    cache_config = CacheConfig(
        backend="memory",
        max_size=1000,
        ttl=600  # 10 minutes
    )

Best Practices
--------------

1. **Always use async/await**: All Biomapper operations are asynchronous
2. **Initialize properly**: Always call ``executor.initialize()`` before use
3. **Clean up resources**: Call ``executor.shutdown()`` when done
4. **Handle errors gracefully**: Use specific exception types for better error handling
5. **Use context managers**: When available, use async context managers
6. **Configure caching**: Choose appropriate cache backend for your use case
7. **Monitor performance**: Use built-in metrics for production monitoring
8. **Batch large operations**: Process large datasets in manageable chunks

CLI Usage
---------

Biomapper also provides a command-line interface:

.. code-block:: bash

    # Check system health
    poetry run biomapper health
    
    # List available strategies
    poetry run biomapper metadata list
    
    # Execute a mapping
    poetry run biomapper metamapper execute --strategy protein_mapping --input proteins.csv

Next Steps
----------

- Explore :doc:`tutorials/yaml_mapping_strategies` for creating custom strategies
- Read :doc:`architecture` to understand the service architecture
- Check :doc:`api/README` for REST API documentation
- See :doc:`configuration` for detailed configuration options