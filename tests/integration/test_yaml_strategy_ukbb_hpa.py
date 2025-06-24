"""Integration test for YAML-based UKBB to HPA mapping strategy."""

import pytest
import pytest_asyncio

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.db.models import MappingStrategy, MappingStrategyStep


@pytest_asyncio.fixture
async def populated_db(tmp_path):
    """Create and populate a test database."""
    # Create test database URLs
    test_metamapper_db = str(tmp_path / "test_metamapper.db")
    test_cache_db = str(tmp_path / "test_cache.db")
    
    # Create a MappingExecutor to initialize the databases
    config = {
        "metamapper_db_url": f"sqlite+aiosqlite:///{test_metamapper_db}",
        "mapping_cache_db_url": f"sqlite+aiosqlite:///{test_cache_db}",
        "echo_sql": False
    }
    builder = MappingExecutorBuilder(config)
    executor = await builder.build_async()
    
    # Tables are already created by builder.build_async()
    from biomapper.db.models import Base as MetamapperBase
    from biomapper.db.cache_models import Base as CacheBase
    
    # Run populate script to load configurations
    from scripts.setup_and_configuration.populate_metamapper_db import populate_entity_type
    from pathlib import Path
    import yaml
    
    # Load test protein config which contains simpler test strategies
    test_config_path = Path(__file__).parent / "data" / "test_protein_strategy_config.yaml"
    
    async with executor.session_manager.get_async_metamapper_session() as session:
        if test_config_path.exists():
            print(f"Loading test config from: {test_config_path}")
            with open(test_config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            await populate_entity_type(session, "test_protein", config_data)
            await session.commit()
        else:
            # Fall back to the real protein config
            protein_config_path = Path(__file__).parent.parent.parent / "configs" / "protein_config.yaml"
            print(f"Test config not found, trying protein config at: {protein_config_path}")
            if protein_config_path.exists():
                with open(protein_config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                await populate_entity_type(session, "protein", config_data)
                await session.commit()
    
    yield test_metamapper_db, test_cache_db
    
    # Cleanup
    await executor.async_dispose()


@pytest_asyncio.fixture
async def mapping_executor(populated_db):
    """Create a MappingExecutor with populated test database."""
    test_metamapper_db, test_cache_db = populated_db
    
    config = {
        "metamapper_db_url": f"sqlite+aiosqlite:///{test_metamapper_db}",
        "mapping_cache_db_url": f"sqlite+aiosqlite:///{test_cache_db}",
        "echo_sql": False
    }
    builder = MappingExecutorBuilder(config)
    executor = await builder.build_async()
    
    yield executor
    
    # Cleanup
    await executor.async_dispose()


class TestUKBBToHPAYAMLStrategy:
    """Test the UKBB to HPA protein mapping using YAML strategy."""
    
    @pytest.mark.asyncio
    async def test_strategy_loaded_in_database(self, mapping_executor):
        """Test that the basic_linear_strategy is loaded."""
        async with mapping_executor.session_manager.get_async_metamapper_session() as session:
            # Check strategy exists
            from sqlalchemy import select
            stmt = select(MappingStrategy).where(
                MappingStrategy.name == "basic_linear_strategy"
            )
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            
            assert strategy is not None
            assert strategy.entity_type == "test_protein"
            
            # Check steps
            stmt = (
                select(MappingStrategyStep)
                .where(MappingStrategyStep.strategy_id == strategy.id)
                .order_by(MappingStrategyStep.step_order)
            )
            result = await session.execute(stmt)
            steps = result.scalars().all()
            
            assert len(steps) == 2
            assert steps[0].step_id == "S1_CONVERT_TO_GENE"
            assert steps[0].action_type == "CONVERT_IDENTIFIERS_LOCAL"
            assert steps[1].step_id == "S2_GENE_TO_UNIPROT"
            assert steps[1].action_type == "CONVERT_IDENTIFIERS_LOCAL"
    
    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_basic(self, mapping_executor):
        """Test basic execution of the YAML strategy."""
        # Sample test identifiers - using gene symbols that exist in test data
        test_identifiers = ["TEST1", "TEST2"]
        
        # Execute the strategy
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="basic_linear_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=test_identifiers,
            use_cache=False,
            batch_size=100
        )
        
        # Verify result structure
        assert "results" in result
        assert "metadata" in result
        assert "step_results" in result
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["strategy_name"] == "basic_linear_strategy"
        assert metadata["execution_status"] == "completed"
        
        # Check step results
        step_results = result["step_results"]
        assert len(step_results) >= 1  # At least one step executed
        for step in step_results:
            assert "step_id" in step
            assert "action_type" in step
            assert "status" in step
    
    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_with_invalid_strategy(self, mapping_executor):
        """Test execution with non-existent strategy name."""
        with pytest.raises(Exception) as exc_info:
            await mapping_executor.execute_yaml_strategy(
                strategy_name="NON_EXISTENT_STRATEGY",
                source_endpoint_name="test_source",
                target_endpoint_name="test_target",
                input_identifiers=["TEST1"],
                use_cache=False
            )
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_with_progress_callback(self, mapping_executor):
        """Test execution with progress callback."""
        progress_updates = []
        
        def progress_callback(current: int, total: int, status: str):
            progress_updates.append({
                "current": current,
                "total": total,
                "status": status
            })
        
        test_identifiers = ["TEST1", "TEST2"]
        
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="basic_linear_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=test_identifiers,
            progress_callback=progress_callback,
            use_cache=False
        )
        
        # Should have at least one progress update
        assert len(progress_updates) >= 1
        for update in progress_updates:
            assert "current" in update
            assert "total" in update
            assert "status" in update
    
    @pytest.mark.asyncio
    async def test_action_handlers_placeholder_behavior(self, mapping_executor):
        """Test that action handlers return expected placeholder results."""
        test_identifiers = ["TEST1", "TEST2"]
        
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="basic_linear_strategy",
            source_endpoint_name="test_source", 
            target_endpoint_name="test_target",
            input_identifiers=test_identifiers,
            use_cache=False
        )
        
        # With placeholder implementations, identifiers should pass through unchanged
        results = result["results"]
        assert len(results) == len(test_identifiers)
        
        for test_id in test_identifiers:
            assert test_id in results
            result_entry = results[test_id]
            assert "mapped_value" in result_entry
            assert "confidence" in result_entry
            assert "strategy_name" in result_entry
            assert result_entry["strategy_name"] == "basic_linear_strategy"


@pytest.mark.asyncio
async def test_full_yaml_strategy_workflow():
    """Test the complete workflow including database population."""
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test databases
        test_metamapper_db = str(tmp_path / "test_metamapper.db")
        test_cache_db = str(tmp_path / "test_cache.db")
        
        # Create tables using MappingExecutor
        # (No need for separate db_manager initialization)
        
        # Create MappingExecutor
        config = {
            "metamapper_db_url": f"sqlite+aiosqlite:///{test_metamapper_db}",
            "mapping_cache_db_url": f"sqlite+aiosqlite:///{test_cache_db}",
            "echo_sql": False
        }
        builder = MappingExecutorBuilder(config)
        executor = await builder.build_async()
        
        try:
            # Test identifiers
            test_ids = ["HGNC:1234", "HGNC:5678"]
            
            # This would fail without proper database population,
            # demonstrating the need for the populate script
            with pytest.raises(Exception) as exc_info:
                await executor.execute_yaml_strategy(
                    strategy_name="basic_linear_strategy",
                    source_endpoint_name="test_source",
                    target_endpoint_name="test_target",
                    input_identifiers=test_ids
                )
            
            # Either "not found" (strategy doesn't exist) or "no such table" (tables not created)
            error_msg = str(exc_info.value).lower()
            assert "not found" in error_msg or "no such table" in error_msg
            
        finally:
            await executor.async_dispose()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])