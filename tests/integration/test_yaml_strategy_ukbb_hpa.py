"""Integration test for YAML-based UKBB to HPA mapping strategy."""

import pytest
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings
from biomapper.db.session import get_db_manager
from biomapper.db.models import MappingStrategy, MappingStrategyStep


@pytest.fixture
async def populated_db(tmp_path):
    """Create and populate a test database."""
    # Create test database URLs
    test_metamapper_db = str(tmp_path / "test_metamapper.db")
    test_cache_db = str(tmp_path / "test_cache.db")
    
    # Create test database manager
    db_manager = get_db_manager(
        metamapper_db_url=f"sqlite+aiosqlite:///{test_metamapper_db}",
        cache_db_url=f"sqlite+aiosqlite:///{test_cache_db}"
    )
    
    # Initialize databases
    await db_manager.create_all_tables()
    
    # Run populate script to load configurations
    from scripts.populate_metamapper_db import populate_from_configs
    async with db_manager.get_metamapper_session() as session:
        await populate_from_configs(session)
    
    return test_metamapper_db, test_cache_db


@pytest.fixture
async def mapping_executor(populated_db):
    """Create a MappingExecutor with populated test database."""
    test_metamapper_db, test_cache_db = populated_db
    
    executor = MappingExecutor(
        metamapper_db_url=f"sqlite+aiosqlite:///{test_metamapper_db}",
        mapping_cache_db_url=f"sqlite+aiosqlite:///{test_cache_db}",
        echo_sql=False
    )
    
    # Initialize the executor
    await executor.initialize()
    
    yield executor
    
    # Cleanup
    await executor.close()


class TestUKBBToHPAYAMLStrategy:
    """Test the UKBB to HPA protein mapping using YAML strategy."""
    
    @pytest.mark.asyncio
    async def test_strategy_loaded_in_database(self, mapping_executor):
        """Test that the UKBB_TO_HPA_PROTEIN_PIPELINE strategy is loaded."""
        async with mapping_executor.metamapper_session() as session:
            # Check strategy exists
            from sqlalchemy import select
            stmt = select(MappingStrategy).where(
                MappingStrategy.name == "UKBB_TO_HPA_PROTEIN_PIPELINE"
            )
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            
            assert strategy is not None
            assert strategy.entity_type == "protein"
            assert strategy.default_source_ontology_type == "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
            assert strategy.default_target_ontology_type == "HPA_OSP_PROTEIN_ID_ONTOLOGY"
            
            # Check steps
            stmt = (
                select(MappingStrategyStep)
                .where(MappingStrategyStep.strategy_id == strategy.id)
                .order_by(MappingStrategyStep.step_order)
            )
            result = await session.execute(stmt)
            steps = result.scalars().all()
            
            assert len(steps) == 4
            assert steps[0].step_id == "S1_UKBB_NATIVE_TO_UNIPROT"
            assert steps[0].action_type == "CONVERT_IDENTIFIERS_LOCAL"
            assert steps[1].step_id == "S2_RESOLVE_UNIPROT_HISTORY"
            assert steps[1].action_type == "EXECUTE_MAPPING_PATH"
            assert steps[2].step_id == "S3_FILTER_BY_HPA_PRESENCE"
            assert steps[2].action_type == "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
            assert steps[3].step_id == "S4_HPA_UNIPROT_TO_NATIVE"
            assert steps[3].action_type == "CONVERT_IDENTIFIERS_LOCAL"
    
    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_basic(self, mapping_executor):
        """Test basic execution of the YAML strategy."""
        # Sample UKBB protein assay IDs
        test_identifiers = ["ADAMTS13", "ALB", "APOA1", "C3", "CRP"]
        
        # Execute the strategy
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            source_endpoint_name="UKBB_PROTEIN",
            target_endpoint_name="HPA_OSP_PROTEIN",
            input_identifiers=test_identifiers,
            use_cache=False,
            batch_size=100
        )
        
        # Verify result structure
        assert "results" in result
        assert "summary" in result
        
        summary = result["summary"]
        assert summary["strategy_name"] == "UKBB_TO_HPA_PROTEIN_PIPELINE"
        assert summary["total_input"] == len(test_identifiers)
        assert summary["steps_executed"] == 4
        assert "step_results" in summary
        
        # Check step results
        step_results = summary["step_results"]
        assert len(step_results) == 4
        for step in step_results:
            assert "step_id" in step
            assert "action_type" in step
            assert "success" in step
            assert step["success"] is True  # All steps should succeed
    
    @pytest.mark.asyncio
    async def test_execute_yaml_strategy_with_invalid_strategy(self, mapping_executor):
        """Test execution with non-existent strategy name."""
        with pytest.raises(Exception) as exc_info:
            await mapping_executor.execute_yaml_strategy(
                strategy_name="NON_EXISTENT_STRATEGY",
                source_endpoint_name="UKBB_PROTEIN",
                target_endpoint_name="HPA_OSP_PROTEIN",
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
        
        test_identifiers = ["ADAMTS13", "ALB"]
        
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            source_endpoint_name="UKBB_PROTEIN",
            target_endpoint_name="HPA_OSP_PROTEIN",
            input_identifiers=test_identifiers,
            progress_callback=progress_callback,
            use_cache=False
        )
        
        # Should have progress updates for each step
        assert len(progress_updates) >= 4
        for update in progress_updates:
            assert "current" in update
            assert "total" in update
            assert "status" in update
    
    @pytest.mark.asyncio
    async def test_action_handlers_placeholder_behavior(self, mapping_executor):
        """Test that action handlers return expected placeholder results."""
        test_identifiers = ["TEST1", "TEST2"]
        
        result = await mapping_executor.execute_yaml_strategy(
            strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
            source_endpoint_name="UKBB_PROTEIN", 
            target_endpoint_name="HPA_OSP_PROTEIN",
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
            assert result_entry["strategy_name"] == "UKBB_TO_HPA_PROTEIN_PIPELINE"


@pytest.mark.asyncio
async def test_full_yaml_strategy_workflow():
    """Test the complete workflow including database population."""
    import tempfile
    import shutil
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test databases
        test_metamapper_db = str(tmp_path / "test_metamapper.db")
        test_cache_db = str(tmp_path / "test_cache.db")
        
        # Initialize database manager
        db_manager = get_db_manager(
            metamapper_db_url=f"sqlite+aiosqlite:///{test_metamapper_db}",
            cache_db_url=f"sqlite+aiosqlite:///{test_cache_db}"
        )
        
        # Create tables
        await db_manager.create_all_tables()
        
        # Create MappingExecutor
        executor = MappingExecutor(
            metamapper_db_url=f"sqlite+aiosqlite:///{test_metamapper_db}",
            mapping_cache_db_url=f"sqlite+aiosqlite:///{test_cache_db}",
            echo_sql=False
        )
        
        try:
            await executor.initialize()
            
            # Test identifiers
            test_ids = ["ADAMTS13", "ALB", "APOA1"]
            
            # This would fail without proper database population,
            # demonstrating the need for the populate script
            with pytest.raises(Exception) as exc_info:
                await executor.execute_yaml_strategy(
                    strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE",
                    source_endpoint_name="UKBB_PROTEIN",
                    target_endpoint_name="HPA_OSP_PROTEIN",
                    input_identifiers=test_ids
                )
            
            assert "not found" in str(exc_info.value).lower()
            
        finally:
            await executor.close()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])