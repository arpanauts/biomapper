# Prompt: Finalize API Service to Use Real Mapping Engine

**Objective:**

Your task is to modify the `biomapper-api` service to replace the current mock mapping executor with the real `biomapper` engine. This is the final step to enable true end-to-end execution of mapping strategies through the API.

**Context:**

The `UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS` strategy is now correctly configured and loaded by the API. However, when executed via the client script (`run_full_ukbb_hpa_mapping.py`), the API returns a mock success message instead of performing the actual mapping.

Debugging has revealed that `biomapper-api/app/services/mapper_service.py` is hardcoded to use a mock service. We have identified that the real `MappingExecutor` must be constructed using the `MappingExecutorBuilder` from the core `biomapper` library.

**File to Modify:**

*   `/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py`

**Detailed Implementation Steps:**

1.  **Clean Up Imports:**
    *   Remove all imports related to `biomapper_mock`.
    *   Ensure the correct imports from the `biomapper` library are present.

    **Target Imports to Remove/Replace:**
    ```python
    # REMOVE THESE
    from biomapper_mock import load_tabular_file
    from biomapper_mock.core.mapping_executor import MappingExecutor
    # Also remove the try/except block for:
    from biomapper_mock.mapping.relationships.executor import RelationshipMappingExecutor

    # ADD/ENSURE THESE ARE PRESENT
    from biomapper.io.util import load_tabular_file
    from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
    from biomapper.core.models.context import BiomapperContext
    from biomapper.mapping.relationships.executor import RelationshipMappingExecutor
    ```

2.  **Update `MapperServiceForStrategies.__init__`:**
    *   Modify the constructor to build a real `MappingExecutor` instance using the `MappingExecutorBuilder`.

    **New (Real) Implementation:**
    ```python
    def __init__(self):
        """
        Initializes the service by loading all available strategies and building the MappingExecutor.
        """
        logger.info("Initializing MapperServiceForStrategies...")
        try:
            self.strategies: Dict[str, Strategy] = self._load_strategies()
            logger.info(f"Loaded {len(self.strategies)} strategies")
            
            logger.info("Building MappingExecutor...")
            builder = MappingExecutorBuilder()
            # Handle both running in an event loop and not
            try:
                loop = asyncio.get_running_loop()
                self.executor = loop.run_until_complete(builder.build_async())
            except RuntimeError:
                self.executor = asyncio.run(builder.build_async())
            logger.info("MappingExecutor built successfully.")

        except Exception as e:
            logger.exception(f"Failed to initialize MapperServiceForStrategies: {e}")
            raise
    ```

3.  **Update `MapperServiceForStrategies.execute_strategy`:**
    *   Replace the mock execution logic with a call to the real `MappingExecutor`'s `yaml_strategy_execution_service`.

    **New (Real) Implementation:**
    ```python
    async def execute_strategy(self, strategy_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a named strategy with the given context using the real MappingExecutor.
        """
        strategy_model = self.strategies.get(strategy_name)
        if not strategy_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found."
            )

        try:
            logger.info(f"Executing strategy '{strategy_name}' with real executor...")
            biomapper_context = BiomapperContext(initial_data=context)

            final_context = await self.executor.strategy_coordinator.yaml_strategy_execution_service.execute(
                strategy=strategy_model,
                context=biomapper_context
            )
            
            result = final_context.to_dict()
            logger.info(f"Successfully executed strategy '{strategy_name}'.")
            return result

        except Exception as e:
            logger.exception(f"An error occurred during execution of strategy '{strategy_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An internal error occurred while executing the strategy: {e}",
            )
    ```

**Verification:**

After applying the changes, run the client script to confirm the end-to-end pipeline works correctly:

```bash
python3 /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
```

The output should now show the actual results of the mapping strategy, not a mock message. It should contain the final context with keys like `final_hpa_genes`.
