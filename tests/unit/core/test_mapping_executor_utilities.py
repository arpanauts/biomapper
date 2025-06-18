"""
Unit tests for MappingExecutor utility methods.

Tests the new API methods that were refactored from script utilities:
- get_strategy
- get_ontology_column
- load_endpoint_identifiers
- get_strategy_info
- validate_strategy_prerequisites
- execute_strategy_with_comprehensive_results
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
import pandas as pd
import os

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.exceptions import (
    DatabaseQueryError,
    ConfigurationError,
    StrategyNotFoundError
)
from biomapper.db.models import (
    MappingStrategy,
    MappingStrategyStep,
    Endpoint,
    EndpointPropertyConfig,
    PropertyExtractionConfig
)


@pytest.fixture
def mock_executor():
    """Create a MappingExecutor instance with mocked database connections."""
    with patch('biomapper.core.mapping_executor.create_async_engine'):
        executor = MappingExecutor(
            metamapper_db_url="sqlite+aiosqlite:///:memory:",
            mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
            echo_sql=False,
            enable_metrics=False
        )
        
        # Mock the session factories
        executor.async_metamapper_session = AsyncMock()
        executor.CacheSessionFactory = AsyncMock()
        
        # Mock the logger
        executor.logger = MagicMock()
        
        return executor


@pytest.fixture
def mock_strategy():
    """Create a mock MappingStrategy object."""
    strategy = MagicMock(spec=MappingStrategy)
    strategy.name = "TEST_STRATEGY"
    strategy.description = "Test strategy description"
    strategy.is_active = True
    strategy.default_source_ontology_type = "UniProt"
    strategy.default_target_ontology_type = "Gene"
    strategy.version = "1.0"
    
    # Mock steps
    step1 = MagicMock(spec=MappingStrategyStep)
    step1.step_id = "S1"
    step1.step_order = 1
    step1.action_type = "CONVERT_IDENTIFIERS_LOCAL"
    step1.description = "Convert identifiers"
    step1.parameters = json.dumps({"param1": "value1"})
    
    strategy.steps = [step1]
    
    return strategy


@pytest.fixture
def mock_endpoint():
    """Create a mock Endpoint object."""
    endpoint = MagicMock(spec=Endpoint)
    endpoint.id = 1
    endpoint.name = "TEST_ENDPOINT"
    endpoint.type = "file_csv"
    endpoint.connection_details = json.dumps({
        "file_path": "${DATA_DIR}/test_data.csv",
        "delimiter": ","
    })
    return endpoint


@pytest.fixture
def mock_property_config():
    """Create a mock EndpointPropertyConfig object."""
    config = MagicMock(spec=EndpointPropertyConfig)
    config.id = 1
    config.endpoint_id = 1
    config.ontology_type = "UniProt"
    config.property_extraction_config_id = 1
    return config


@pytest.fixture
def mock_extraction_config():
    """Create a mock PropertyExtractionConfig object."""
    config = MagicMock(spec=PropertyExtractionConfig)
    config.id = 1
    config.extraction_pattern = json.dumps({"column": "uniprot_id"})
    return config


class TestGetStrategy:
    """Test the get_strategy method."""
    
    @pytest.mark.asyncio
    async def test_get_strategy_success(self, mock_executor, mock_strategy):
        """Test successful strategy retrieval."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query execution
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await mock_executor.get_strategy("TEST_STRATEGY")
        
        # Assert
        assert result == mock_strategy
        assert mock_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_strategy_not_found(self, mock_executor):
        """Test strategy not found returns None."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query execution
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await mock_executor.get_strategy("NONEXISTENT_STRATEGY")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_strategy_database_error(self, mock_executor):
        """Test database error handling."""
        # Setup mock session to raise an exception
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database error")
        
        # Execute and assert
        with pytest.raises(DatabaseQueryError) as exc_info:
            await mock_executor.get_strategy("TEST_STRATEGY")
        
        assert "Failed to retrieve strategy TEST_STRATEGY" in str(exc_info.value)


class TestGetOntologyColumn:
    """Test the get_ontology_column method."""
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_success(
        self, mock_executor, mock_endpoint, mock_property_config, mock_extraction_config
    ):
        """Test successful column retrieval."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query executions in order
        mock_results = [
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_endpoint)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_property_config)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_extraction_config))
        ]
        mock_session.execute.side_effect = mock_results
        
        # Execute
        result = await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        # Assert
        assert result == "uniprot_id"
        assert mock_session.execute.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_endpoint_not_found(self, mock_executor):
        """Test endpoint not found error."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("NONEXISTENT_ENDPOINT", "UniProt")
        
        assert "Endpoint 'NONEXISTENT_ENDPOINT' not found in database" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_property_config_not_found(
        self, mock_executor, mock_endpoint
    ):
        """Test property configuration not found error."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query executions
        mock_results = [
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_endpoint)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=None))  # No property config
        ]
        mock_session.execute.side_effect = mock_results
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        assert "No property configuration found for ontology type 'UniProt'" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_invalid_json(
        self, mock_executor, mock_endpoint, mock_property_config
    ):
        """Test invalid JSON in extraction pattern."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Create extraction config with invalid JSON
        mock_extraction_config = MagicMock(spec=PropertyExtractionConfig)
        mock_extraction_config.extraction_pattern = "invalid json"
        
        # Mock the query executions
        mock_results = [
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_endpoint)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_property_config)),
            AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_extraction_config))
        ]
        mock_session.execute.side_effect = mock_results
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        assert "Invalid JSON in extraction pattern" in str(exc_info.value)


class TestLoadEndpointIdentifiers:
    """Test the load_endpoint_identifiers method."""
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_success(self, mock_executor, mock_endpoint):
        """Test successful identifier loading."""
        # Setup mocks
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_endpoint
        mock_session.execute.return_value = mock_result
        
        # Create test data
        test_df = pd.DataFrame({
            "uniprot_id": ["P12345", "Q67890", "P12345", "R11111", None],
            "other_col": [1, 2, 3, 4, 5]
        })
        
        # Mock file operations
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=True):
                with patch("pandas.read_csv", return_value=test_df):
                    # Execute
                    result = await mock_executor.load_endpoint_identifiers(
                        "TEST_ENDPOINT", "UniProt"
                    )
        
        # Assert
        assert len(result) == 3  # Unique non-null values
        assert "P12345" in result
        assert "Q67890" in result
        assert "R11111" in result
        mock_executor.logger.info.assert_any_call(
            "Found 3 unique identifiers in column 'uniprot_id'"
        )
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_return_dataframe(
        self, mock_executor, mock_endpoint
    ):
        """Test returning full dataframe."""
        # Setup mocks
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_endpoint
        mock_session.execute.return_value = mock_result
        
        # Create test data
        test_df = pd.DataFrame({
            "uniprot_id": ["P12345", "Q67890"],
            "other_col": [1, 2]
        })
        
        # Mock file operations
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=True):
                with patch("pandas.read_csv", return_value=test_df):
                    # Execute
                    result = await mock_executor.load_endpoint_identifiers(
                        "TEST_ENDPOINT", "UniProt", return_dataframe=True
                    )
        
        # Assert
        assert isinstance(result, pd.DataFrame)
        assert result.equals(test_df)
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_file_not_found(
        self, mock_executor, mock_endpoint
    ):
        """Test file not found error."""
        # Setup mocks
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_endpoint
        mock_session.execute.return_value = mock_result
        
        # Mock file not exists
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=False):
                # Execute and assert
                with pytest.raises(FileNotFoundError) as exc_info:
                    await mock_executor.load_endpoint_identifiers(
                        "TEST_ENDPOINT", "UniProt"
                    )
                
                assert "Data file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_column_not_found(
        self, mock_executor, mock_endpoint
    ):
        """Test column not found error."""
        # Setup mocks
        mock_executor.get_ontology_column = AsyncMock(return_value="missing_column")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_endpoint
        mock_session.execute.return_value = mock_result
        
        # Create test data without the required column
        test_df = pd.DataFrame({
            "other_col": [1, 2, 3]
        })
        
        # Mock file operations
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=True):
                with patch("pandas.read_csv", return_value=test_df):
                    # Execute and assert
                    with pytest.raises(KeyError) as exc_info:
                        await mock_executor.load_endpoint_identifiers(
                            "TEST_ENDPOINT", "UniProt"
                        )
                    
                    assert "Column 'missing_column' not found" in str(exc_info.value)


class TestGetStrategyInfo:
    """Test the get_strategy_info method."""
    
    @pytest.mark.asyncio
    async def test_get_strategy_info_success(self, mock_executor, mock_strategy):
        """Test successful strategy info retrieval."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query execution
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await mock_executor.get_strategy_info("TEST_STRATEGY")
        
        # Assert
        assert result["name"] == "TEST_STRATEGY"
        assert result["description"] == "Test strategy description"
        assert result["is_active"] is True
        assert result["source_ontology_type"] == "UniProt"
        assert result["target_ontology_type"] == "Gene"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step_id"] == "S1"
        assert result["steps"][0]["action_type"] == "CONVERT_IDENTIFIERS_LOCAL"
    
    @pytest.mark.asyncio
    async def test_get_strategy_info_not_found(self, mock_executor):
        """Test strategy not found error."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock the query execution
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute and assert
        with pytest.raises(StrategyNotFoundError) as exc_info:
            await mock_executor.get_strategy_info("NONEXISTENT_STRATEGY")
        
        assert "Strategy 'NONEXISTENT_STRATEGY' not found" in str(exc_info.value)


class TestValidateStrategyPrerequisites:
    """Test the validate_strategy_prerequisites method."""
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_all_valid(
        self, mock_executor, mock_strategy, mock_endpoint
    ):
        """Test validation when all prerequisites are met."""
        # Setup mocks
        mock_executor.get_strategy = AsyncMock(return_value=mock_strategy)
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock _get_endpoint_by_name
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=mock_endpoint)
        
        # Mock property configs for target
        mock_config = MagicMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_config]
        mock_session.execute.return_value = mock_result
        
        # Mock file exists
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=True):
                # Execute
                result = await mock_executor.validate_strategy_prerequisites(
                    "TEST_STRATEGY", "SOURCE_ENDPOINT", "TARGET_ENDPOINT"
                )
        
        # Assert
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
        assert result["strategy_info"]["name"] == "TEST_STRATEGY"
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_strategy_not_found(self, mock_executor):
        """Test validation when strategy doesn't exist."""
        # Setup mocks
        mock_executor.get_strategy = AsyncMock(return_value=None)
        
        # Execute
        result = await mock_executor.validate_strategy_prerequisites(
            "NONEXISTENT_STRATEGY", "SOURCE", "TARGET"
        )
        
        # Assert
        assert result["valid"] is False
        assert "Strategy 'NONEXISTENT_STRATEGY' not found in database" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_inactive_strategy(
        self, mock_executor, mock_strategy
    ):
        """Test validation when strategy is inactive."""
        # Make strategy inactive
        mock_strategy.is_active = False
        mock_executor.get_strategy = AsyncMock(return_value=mock_strategy)
        
        # Execute
        result = await mock_executor.validate_strategy_prerequisites(
            "TEST_STRATEGY", "SOURCE", "TARGET"
        )
        
        # Assert
        assert result["valid"] is False
        assert "Strategy 'TEST_STRATEGY' is not active" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_endpoint_not_found(
        self, mock_executor, mock_strategy
    ):
        """Test validation when endpoint doesn't exist."""
        # Setup mocks
        mock_executor.get_strategy = AsyncMock(return_value=mock_strategy)
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint not found
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=None)
        
        # Execute
        result = await mock_executor.validate_strategy_prerequisites(
            "TEST_STRATEGY", "NONEXISTENT_SOURCE", "TARGET"
        )
        
        # Assert
        assert result["valid"] is False
        assert "Source endpoint 'NONEXISTENT_SOURCE' not found" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_file_not_found(
        self, mock_executor, mock_strategy, mock_endpoint
    ):
        """Test validation when data file doesn't exist."""
        # Setup mocks
        mock_executor.get_strategy = AsyncMock(return_value=mock_strategy)
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_executor.async_metamapper_session.return_value.__aenter__.return_value = mock_session
        
        # Mock endpoint found
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=mock_endpoint)
        
        # Mock file not exists
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=False):
                # Execute
                result = await mock_executor.validate_strategy_prerequisites(
                    "TEST_STRATEGY", "SOURCE_ENDPOINT", "TARGET_ENDPOINT"
                )
        
        # Assert
        assert result["valid"] is False
        assert any("Source data file not found" in error for error in result["errors"])


class TestExecuteStrategyWithComprehensiveResults:
    """Test the execute_strategy_with_comprehensive_results method."""
    
    @pytest.mark.asyncio
    async def test_execute_comprehensive_success(self, mock_executor):
        """Test successful comprehensive execution."""
        # Mock the execute_yaml_strategy method
        mock_result = {
            "results": {
                "ID1": {"status": "success"},
                "ID2": {"status": "success"},
                "ID3": {"status": "failed"}
            },
            "final_identifiers": ["MAPPED1", "MAPPED2"],
            "summary": {
                "total_input": 3,
                "successful_mappings": 2,
                "failed_mappings": 1
            }
        }
        mock_executor.execute_yaml_strategy = AsyncMock(return_value=mock_result)
        
        # Execute
        with patch("time.time", side_effect=[100.0, 110.5]):  # 10.5 second execution
            result = await mock_executor.execute_strategy_with_comprehensive_results(
                strategy_name="TEST_STRATEGY",
                source_endpoint="SOURCE",
                target_endpoint="TARGET",
                input_identifiers=["ID1", "ID2", "ID3"]
            )
        
        # Assert
        assert "metrics" in result
        assert result["metrics"]["total_execution_time"] == 10.5
        
        assert result["summary"]["success_rate"] == pytest.approx(66.67, rel=0.01)
        assert result["summary"]["execution_time_seconds"] == 10.5
        assert result["summary"]["status_breakdown"] == {
            "success": 2,
            "failed": 1
        }
        
        # Verify logging
        mock_executor.logger.info.assert_any_call(
            "Strategy execution completed in 10.50 seconds"
        )
        mock_executor.logger.info.assert_any_call(
            "Success rate: 66.7%"
        )
    
    @pytest.mark.asyncio
    async def test_execute_comprehensive_with_empty_results(self, mock_executor):
        """Test execution with no successful mappings."""
        # Mock the execute_yaml_strategy method
        mock_result = {
            "results": {},
            "final_identifiers": [],
            "summary": {
                "total_input": 5,
                "successful_mappings": 0,
                "failed_mappings": 5
            }
        }
        mock_executor.execute_yaml_strategy = AsyncMock(return_value=mock_result)
        
        # Execute
        with patch("time.time", side_effect=[100.0, 105.0]):
            result = await mock_executor.execute_strategy_with_comprehensive_results(
                strategy_name="TEST_STRATEGY",
                source_endpoint="SOURCE",
                target_endpoint="TARGET",
                input_identifiers=["ID1", "ID2", "ID3", "ID4", "ID5"]
            )
        
        # Assert
        assert result["summary"]["success_rate"] == 0
        assert result["metrics"]["total_execution_time"] == 5.0