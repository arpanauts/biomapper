#!/usr/bin/env python
"""
Test script to verify the context initialization fix.
"""
import asyncio
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder

async def test_context_fix():
    """Test if the input_identifiers key is in the context."""
    # Create executor
    builder = MappingExecutorBuilder()
    executor = await builder.build_async()
    
    # Test identifiers
    test_ids = ["TEST1", "TEST2", "TEST3"]
    
    try:
        # Execute strategy
        result = await executor.execute_yaml_strategy(
            strategy_name="UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS",
            source_endpoint_name="UKBB_PROTEIN_ASSAY_ID",
            target_endpoint_name="HPA_GENE_NAME",
            input_identifiers=test_ids,
            initial_context={"test_key": "test_value"}
        )
        
        print(f"Strategy executed successfully!")
        print(f"Step results: {result.get('step_results', [])}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await executor.async_dispose()

if __name__ == "__main__":
    asyncio.run(test_context_fix())