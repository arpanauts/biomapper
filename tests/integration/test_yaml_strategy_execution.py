"""Integration tests for YAML-defined mapping strategy execution.

This module tests the end-to-end functionality of YAML-defined mapping strategies,
from parsing configurations to executing strategies via MappingExecutor.
"""

import os
import tempfile
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, List, AsyncGenerator
import pytest
import pytest_asyncio
import yaml
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import Base
from biomapper.db.session import get_db_manager
from biomapper.core.exceptions import BiomapperError, StrategyNotFoundError, MappingExecutionError


@pytest_asyncio.fixture(scope="function")
async def setup_test_environment():
    """Sets up the test environment including database, executor, and mock files."""
    # 1. Create temp_db_path
    temp_dir = tempfile.mkdtemp()
    metamapper_db_path = os.path.join(temp_dir, "test_metamapper.db")
    cache_db_path = os.path.join(temp_dir, "test_mapping_cache.db")

    # 2. Set up test_metamapper_db (engine, tables)
    metamapper_engine = create_async_engine(f"sqlite+aiosqlite:///{metamapper_db_path}")
    async with metamapper_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Load YAML config
    config_path = Path(__file__).parent / "data" / "test_protein_strategy_config.yaml"
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # 4. Call populate_test_data (defined elsewhere in this file)
    async with AsyncSession(metamapper_engine) as session:
        await populate_test_data(session, config_data)
        await session.commit()

    # 5. Create MappingExecutor instance
    executor = MappingExecutor(
        metamapper_db_url=f"sqlite+aiosqlite:///{metamapper_db_path}",
        mapping_cache_db_url=f"sqlite+aiosqlite:///{cache_db_path}"
    )

    yield executor

    # 6. Handle cleanup
    await metamapper_engine.dispose()
    shutil.rmtree(temp_dir)


@pytest_asyncio.fixture(scope="function")
async def setup_optional_test_environment():
    """Sets up test environment with optional steps config."""
    # 1. Create temp_db_path with unique name to avoid conflicts
    temp_dir = tempfile.mkdtemp()
    metamapper_db_path = os.path.join(temp_dir, "test_optional_metamapper.db")
    cache_db_path = os.path.join(temp_dir, "test_optional_cache.db")

    # 2. Set up test_metamapper_db (engine, tables)
    metamapper_engine = create_async_engine(f"sqlite+aiosqlite:///{metamapper_db_path}")
    async with metamapper_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Load optional steps YAML config
    config_path = Path(__file__).parent / "data" / "test_optional_steps_config.yaml"
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # 4. Call populate_test_data
    async with AsyncSession(metamapper_engine) as session:
        await populate_test_data(session, config_data)
        await session.commit()

    # 5. Create MappingExecutor instance
    executor = MappingExecutor(
        metamapper_db_url=f"sqlite+aiosqlite:///{metamapper_db_path}",
        mapping_cache_db_url=f"sqlite+aiosqlite:///{cache_db_path}"
    )

    yield executor

    # 6. Handle cleanup
    await metamapper_engine.dispose()
    shutil.rmtree(temp_dir)






async def populate_test_data(session: AsyncSession, config: Dict[str, Any]):
    """Helper to populate test data using the actual populate functions."""
    from scripts.setup_and_configuration.populate_metamapper_db import (
        populate_ontologies,
        populate_endpoints_and_properties,
        populate_mapping_resources,
        populate_mapping_paths,
        populate_mapping_strategies,
        populate_entity_type
    )
    
    # Process entity types - use the full configuration to let populate_entity_type handle everything
    for entity_name, entity_config in config.get("entity_types", {}).items():
        # Create full config for populate_entity_type to handle all the data population
        full_config = {
            'ontologies': config.get("ontologies", {}),
            'databases': config.get("databases", {}),
            'mapping_paths': config.get("mapping_paths", []),  # Top-level mapping paths
            'mapping_strategies': config.get("mapping_strategies", {}),  # Top-level mapping strategies
            'additional_resources': config.get("additional_resources", [])  # Top-level additional resources
        }
        
        # Let populate_entity_type handle all the population logic internally
        await populate_entity_type(session, entity_name, full_config)


@pytest.fixture
def mock_client_files():
    """Create mock client data files for testing."""
    base_path = Path(__file__).parent / "data" / "mock_client_files"
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Create test UniProt file
    uniprot_file = base_path / "test_uniprot.tsv"
    uniprot_file.write_text(
        "Entry\tEntry Name\tGene Names\n"
        "P12345\tTEST1_HUMAN\tTEST1 TST1\n"
        "Q67890\tTEST2_HUMAN\tTEST2\n"
        "A12345\tTEST3_HUMAN\tTEST3\n"
    )
    
    # Create test HGNC file
    hgnc_file = base_path / "test_hgnc.tsv"
    hgnc_file.write_text(
        "hgnc_id\tsymbol\tname\tuniprot_ids\n"
        "HGNC:1234\tTEST1\tTest gene 1\tP12345\n"
        "HGNC:5678\tTEST2\tTest gene 2\tQ67890\n"
        "HGNC:9012\tTEST3\tTest gene 3\tA12345\n"
    )
    
    # Create test filter target file
    filter_target_file = base_path / "test_filter_target.csv"
    filter_target_file.write_text(
        "id,name\n"
        "P12345,Protein 1\n"
        "HGNC:1234,Gene 1\n"
        "ENSG00000123,Ensembl 1\n"
    )
    
    return {
        "uniprot": str(uniprot_file),
        "hgnc": str(hgnc_file),
        "filter_target": str(filter_target_file)
    }


@pytest.mark.asyncio
class TestYAMLStrategyExecution:
    """Test cases for YAML-defined mapping strategy execution."""
    
    async def test_basic_linear_strategy(self, setup_test_environment, mock_client_files):
        """Test a basic linear strategy with CONVERT_IDENTIFIERS_LOCAL steps."""
        # Initial identifiers
        initial_ids = ["TEST1", "TEST2", "TEST3"]
        
        executor = setup_test_environment
        
        # Execute strategy
        result = await executor.execute_yaml_strategy(
            strategy_name="basic_linear_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc"
        )
        
        # Assertions
        assert isinstance(result, dict)
        assert "results" in result
        assert "summary" in result
        assert result["summary"]["strategy_name"] == "basic_linear_strategy"
        assert result["summary"]["total_mapped"] > 0
        
        # Check step results
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 2  # Two conversion steps
        assert all(step.get("action_type") == "CONVERT_IDENTIFIERS_LOCAL" 
                  for step in step_results)
    
    async def test_strategy_with_execute_mapping_path(self, setup_test_environment, mock_client_files):
        """Test a strategy that uses EXECUTE_MAPPING_PATH action."""
        initial_ids = ["P12345", "Q67890"]
        
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="strategy_with_path_execution",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids
        )
        
        assert "summary" in result
        assert result["summary"]["total_input"] == len(initial_ids)
        
        # Find the EXECUTE_MAPPING_PATH step
        step_results = result["summary"].get("step_results", [])
        path_steps = [s for s in step_results 
                     if s.get("action_type") == "EXECUTE_MAPPING_PATH"]
        assert len(path_steps) > 0
        assert path_steps[0].get("success", False)
    
    async def test_strategy_with_filter_action(self, setup_test_environment, mock_client_files):
        """Test a strategy with FILTER_IDENTIFIERS_BY_TARGET_PRESENCE action."""
        initial_ids = ["P12345", "Q67890", "INVALID123"]
        
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="strategy_with_filter",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids
        )
        
        assert "summary" in result
        
        # Check that filtering occurred
        step_results = result["summary"].get("step_results", [])
        filter_steps = [s for s in step_results 
                       if s.get("action_type") == "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"]
        assert len(filter_steps) > 0
    
    async def test_mixed_action_strategy(self, setup_test_environment, mock_client_files):
        """Test a strategy combining all action types."""
        initial_ids = ["TEST1", "TEST2", "INVALID"]
        
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="complex_mixed_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc"
        )
        
        assert "summary" in result
        
        # Verify different action types were executed
        step_results = result["summary"].get("step_results", [])
        action_types = {step.get("action_type") for step in step_results}
        assert "CONVERT_IDENTIFIERS_LOCAL" in action_types
        assert "EXECUTE_MAPPING_PATH" in action_types
        assert "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE" in action_types
    
    async def test_strategy_not_found(self, setup_test_environment):
        """Test calling execute_yaml_strategy with non-existent strategy name."""
        executor = setup_test_environment
        
        with pytest.raises((BiomapperError, StrategyNotFoundError)) as exc_info:
            await executor.execute_yaml_strategy(
                strategy_name="non_existent_strategy",
                source_endpoint_name="test_source",
                target_endpoint_name="test_target",
                input_identifiers=["TEST1"]
            )
        
        assert "not found" in str(exc_info.value).lower()
    
    async def test_empty_initial_identifiers(self, setup_test_environment):
        """Test running a strategy with empty initial identifiers."""
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="basic_linear_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=[],
            source_ontology_type="hgnc"
        )
        
        assert "summary" in result
        assert result["summary"]["total_input"] == 0
        assert result["summary"]["total_mapped"] == 0
    
    async def test_step_failure_handling(self, setup_test_environment):
        """Test strategy execution when a step fails."""
        executor = setup_test_environment
        
        # This should raise an error due to non-existent resource
        with pytest.raises(MappingExecutionError) as exc_info:
            await executor.execute_yaml_strategy(
                strategy_name="strategy_with_failing_step",
                source_endpoint_name="test_source",
                target_endpoint_name="test_target",
                input_identifiers=["TEST1"]
            )
        
        assert "failed" in str(exc_info.value).lower()
    
    async def test_ontology_type_tracking(self, setup_test_environment):
        """Test that current_source_ontology_type is properly tracked."""
        initial_ids = ["HGNC:1234", "HGNC:5678"]
        
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="ontology_tracking_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
            target_ontology_type="uniprot"
        )
        
        assert "summary" in result
        
        # Check step results track ontology changes
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) > 0
        
        # Verify conversion steps exist
        conversion_steps = [s for s in step_results if s.get("action_type") == "CONVERT_IDENTIFIERS_LOCAL"]
        assert len(conversion_steps) > 0
    
    async def test_filter_with_conversion_path(self, setup_test_environment, mock_client_files):
        """Test filter action with conversion_path_to_match_ontology."""
        initial_ids = ["P12345", "Q67890", "A12345"]
        
        executor = setup_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="filter_with_conversion",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids
        )
        
        assert "summary" in result
        
        # Verify filter step exists
        step_results = result["summary"].get("step_results", [])
        filter_steps = [s for s in step_results 
                       if s.get("action_type") == "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"]
        assert len(filter_steps) > 0
    
    async def test_strategy_with_conditional_branching(self, setup_test_environment):
        """Test strategy execution with conditional logic (if implemented)."""
        # This test assumes conditional branching might be added later
        pytest.skip("Conditional branching not yet implemented")
    
    async def test_parallel_action_execution(self, setup_test_environment):
        """Test strategy with parallel action execution (if implemented)."""
        # This test assumes parallel execution might be added later
        pytest.skip("Parallel action execution not yet implemented")
    
    # ====== Optional Steps Tests (is_required=False) ======
    
    async def test_all_optional_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy where all steps are optional, including failures."""
        initial_ids = ["TEST1", "TEST2", "TEST3"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="all_optional_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc"
        )
        
        # Should complete even with optional failures
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        # Check step results
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 3
        
        # First step should succeed (valid mapping)
        assert step_results[0]["success"] is True
        assert step_results[0]["step_id"] == "S1_OPTIONAL_CONVERT"
        
        # Second step should fail (non-existent file)
        assert step_results[1]["success"] is False
        assert step_results[1]["step_id"] == "S2_OPTIONAL_FAIL"
        assert "error" in step_results[1] or "status" in step_results[1]
        
        # Third step should still execute
        assert step_results[2]["step_id"] == "S3_OPTIONAL_FILTER"
        
        # Overall strategy should show failed steps
        assert result["summary"]["failed_steps"] >= 1
    
    async def test_mixed_required_optional_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy with both required and optional steps."""
        initial_ids = ["TEST1", "TEST2"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="mixed_required_optional_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        # Should complete because optional step failure doesn't halt execution
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 3
        
        # First required step should succeed
        assert step_results[0]["success"] is True
        assert step_results[0]["step_id"] == "S1_REQUIRED"
        
        # Second optional step should fail but not halt execution
        assert step_results[1]["success"] is False
        assert step_results[1]["step_id"] == "S2_OPTIONAL_FAIL"
        
        # Third required step should still execute
        assert step_results[2]["success"] is True
        assert step_results[2]["step_id"] == "S3_REQUIRED_FILTER"
    
    async def test_optional_fail_first_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy where first step is optional and fails."""
        initial_ids = ["TEST1", "TEST2"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="optional_fail_first_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 2
        
        # First optional step fails
        assert step_results[0]["success"] is False
        assert step_results[0]["step_id"] == "S1_OPTIONAL_FAIL_FIRST"
        
        # Second required step still executes
        assert step_results[1]["success"] is True
        assert step_results[1]["step_id"] == "S2_REQUIRED_CONVERT"
    
    async def test_optional_fail_last_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy where last step is optional and fails."""
        initial_ids = ["TEST1", "TEST2", "TEST3"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="optional_fail_last_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 2
        
        # First required step succeeds
        assert step_results[0]["success"] is True
        assert step_results[0]["step_id"] == "S1_REQUIRED_SUCCESS"
        
        # Last optional step fails but doesn't affect overall status
        assert step_results[1]["success"] is False
        assert step_results[1]["step_id"] == "S2_OPTIONAL_FAIL_LAST"
    
    async def test_multiple_optional_failures_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy with multiple optional steps failing in sequence."""
        initial_ids = ["TEST1", "TEST2"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="multiple_optional_failures_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 4
        
        # Check multiple optional failures
        assert step_results[0]["success"] is False  # S1_OPTIONAL_FAIL_1
        assert step_results[1]["success"] is False  # S2_OPTIONAL_FAIL_2
        assert step_results[2]["success"] is True   # S3_REQUIRED_SUCCESS
        assert step_results[3]["success"] is False  # S4_OPTIONAL_FAIL_3
        
        # Should have 3 failed steps
        assert result["summary"]["failed_steps"] == 3
    
    async def test_required_fail_after_optional_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy where required step fails after optional steps."""
        initial_ids = ["TEST1", "TEST2"]
        
        executor = setup_optional_test_environment
        
        # This should raise an error because required step fails
        with pytest.raises(MappingExecutionError) as exc_info:
            await executor.execute_yaml_strategy(
                strategy_name="required_fail_after_optional_strategy",
                source_endpoint_name="test_source",
                target_endpoint_name="test_target",
                input_identifiers=initial_ids,
                source_ontology_type="hgnc",
                )
        
        assert "failed" in str(exc_info.value).lower()
    
    async def test_all_optional_fail_strategy(self, setup_optional_test_environment, mock_client_files):
        """Test strategy where all optional steps fail."""
        initial_ids = ["TEST1", "TEST2", "TEST3"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="all_optional_fail_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        # Should complete even though all steps fail
        assert "summary" in result
        assert result["summary"]["execution_status"] == "completed"
        
        step_results = result["summary"].get("step_results", [])
        assert len(step_results) == 3
        
        # All steps should fail
        assert all(step["success"] is False for step in step_results)
        assert result["summary"]["failed_steps"] == 3
        
        # But strategy still completes because all are optional
        assert result["summary"]["total_steps"] == 3
    
    # ====== Required Steps Failing Tests (is_required=True) ======
    
    async def test_required_step_explicit_true(self, setup_test_environment):
        """Test that explicitly setting is_required=true works correctly."""
        # This uses the existing strategy_with_failing_step which has required steps
        executor = setup_test_environment
        
        with pytest.raises(MappingExecutionError) as exc_info:
            await executor.execute_yaml_strategy(
                strategy_name="strategy_with_failing_step",
                source_endpoint_name="test_source",
                target_endpoint_name="test_target",
                input_identifiers=["TEST1"],
                source_ontology_type="hgnc"
            )
        
        # Should fail because step is required (default)
        assert "failed" in str(exc_info.value).lower()
    
    async def test_mapping_result_bundle_tracking(self, setup_optional_test_environment, mock_client_files):
        """Test that MappingResultBundle correctly tracks optional step failures."""
        initial_ids = ["TEST1", "TEST2"]
        
        executor = setup_optional_test_environment
        
        result = await executor.execute_yaml_strategy(
            strategy_name="mixed_required_optional_strategy",
            source_endpoint_name="test_source",
            target_endpoint_name="test_target",
            input_identifiers=initial_ids,
            source_ontology_type="hgnc",
        )
        
        # Verify detailed tracking
        assert "summary" in result
        summary = result["summary"]
        
        # Check counts
        assert summary["total_steps"] == 3
        assert summary["completed_steps"] == 3  # All steps complete (even if failed)
        assert summary["failed_steps"] == 1     # One optional step failed
        
        # Check step results detail
        step_results = summary.get("step_results", [])
        failed_steps = [s for s in step_results if not s["success"]]
        assert len(failed_steps) == 1
        assert failed_steps[0]["step_id"] == "S2_OPTIONAL_FAIL"