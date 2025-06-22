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
from unittest.mock import AsyncMock, MagicMock, patch
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
    with patch('biomapper.core.engine_components.session_manager.create_async_engine'):
        executor = MappingExecutor(
            metamapper_db_url="sqlite+aiosqlite:///:memory:",
            mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
            echo_sql=False,
            enable_metrics=False
        )
        
        # Mock the session factories - async_metamapper_session should be a callable
        # that returns an async context manager (AsyncSession)
        def mock_session_factory():
            return AsyncMock()
        executor.async_metamapper_session = mock_session_factory
        executor.CacheSessionFactory = AsyncMock()
        
        # Mock the logger
        executor.logger = MagicMock()
        
        # Mock the identifier_loader service
        executor.identifier_loader = MagicMock()
        
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
        # Setup mock session that will be returned by the context manager
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock the query execution
        mock_result = MagicMock()  # Use MagicMock for non-async result
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
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock the query execution
        mock_result = MagicMock()  # Use MagicMock for non-async result
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await mock_executor.get_strategy("NONEXISTENT_STRATEGY")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_strategy_database_error(self, mock_executor):
        """Test database error handling."""
        from sqlalchemy.exc import SQLAlchemyError
        
        # Setup mock session to raise an exception
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        # Execute and assert - get_strategy returns None on error, not raises
        result = await mock_executor.get_strategy("TEST_STRATEGY")
        assert result is None
        mock_executor.logger.error.assert_called_once()


class TestGetOntologyColumn:
    """Test the get_ontology_column method."""
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_success(
        self, mock_executor, mock_endpoint, mock_property_config, mock_extraction_config
    ):
        """Test successful column retrieval."""
        # Mock the identifier_loader's get_ontology_column method directly
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Execute
        result = await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        # Assert
        assert result == "uniprot_id"
        mock_executor.identifier_loader.get_ontology_column.assert_called_once_with(
            "TEST_ENDPOINT", "UniProt"
        )
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_endpoint_not_found(self, mock_executor):
        """Test endpoint not found error."""
        # Mock the identifier_loader's get_ontology_column method to raise error
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.get_ontology_column = AsyncMock(
            side_effect=ConfigurationError("Endpoint 'NONEXISTENT_ENDPOINT' not found in database")
        )
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("NONEXISTENT_ENDPOINT", "UniProt")
        
        assert "Endpoint 'NONEXISTENT_ENDPOINT' not found in database" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_property_config_not_found(
        self, mock_executor, mock_endpoint
    ):
        """Test property configuration not found error."""
        # Mock the identifier_loader's get_ontology_column method to raise error
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.get_ontology_column = AsyncMock(
            side_effect=ConfigurationError(
                "No property configuration found for ontology type 'UniProt' "
                "in endpoint 'TEST_ENDPOINT'"
            )
        )
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        assert "No property configuration found for ontology type 'UniProt'" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_ontology_column_invalid_json(
        self, mock_executor, mock_endpoint, mock_property_config
    ):
        """Test invalid JSON in extraction pattern."""
        # Mock the identifier_loader's get_ontology_column method to raise error
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.get_ontology_column = AsyncMock(
            side_effect=ConfigurationError("Invalid JSON in extraction pattern: Expecting value: line 1 column 1 (char 0)")
        )
        
        # Execute and assert
        with pytest.raises(ConfigurationError) as exc_info:
            await mock_executor.get_ontology_column("TEST_ENDPOINT", "UniProt")
        
        assert "Invalid JSON in extraction pattern" in str(exc_info.value)


class TestLoadEndpointIdentifiers:
    """Test the load_endpoint_identifiers method."""
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_success(self, mock_executor, mock_endpoint):
        """Test successful identifier loading."""
        # Create test data
        test_df = pd.DataFrame({
            "uniprot_id": ["P12345", "Q67890", "P12345", "R11111", None],
            "other_col": [1, 2, 3, 4, 5]
        })
        
        # Mock the identifier_loader's load_endpoint_identifiers method directly
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.load_endpoint_identifiers = AsyncMock(
            return_value=["P12345", "Q67890", "R11111"]
        )
        
        # Execute
        result = await mock_executor.load_endpoint_identifiers(
            "TEST_ENDPOINT", "UniProt"
        )
        
        # Assert
        assert len(result) == 3  # Unique non-null values
        assert "P12345" in result
        assert "Q67890" in result
        assert "R11111" in result
        mock_executor.identifier_loader.load_endpoint_identifiers.assert_called_once_with(
            endpoint_name="TEST_ENDPOINT", ontology_type="UniProt", return_dataframe=False
        )
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_return_dataframe(
        self, mock_executor, mock_endpoint
    ):
        """Test returning full dataframe."""
        # Create test data
        test_df = pd.DataFrame({
            "uniprot_id": ["P12345", "Q67890"],
            "other_col": [1, 2]
        })
        
        # Mock the identifier_loader's load_endpoint_identifiers method directly
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.load_endpoint_identifiers = AsyncMock(
            return_value=test_df
        )
        
        # Execute
        result = await mock_executor.load_endpoint_identifiers(
            "TEST_ENDPOINT", "UniProt", return_dataframe=True
        )
        
        # Assert
        assert isinstance(result, pd.DataFrame)
        assert result.equals(test_df)
        mock_executor.identifier_loader.load_endpoint_identifiers.assert_called_once_with(
            endpoint_name="TEST_ENDPOINT", ontology_type="UniProt", return_dataframe=True
        )
    
    @pytest.mark.asyncio
    async def test_load_endpoint_identifiers_file_not_found(
        self, mock_executor, mock_endpoint
    ):
        """Test file not found error."""
        # Mock the identifier_loader's load_endpoint_identifiers method to raise error
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.load_endpoint_identifiers = AsyncMock(
            side_effect=FileNotFoundError("Data file not found: /test/data/test_data.csv")
        )
        
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
        # Mock the identifier_loader's load_endpoint_identifiers method to raise error
        mock_executor.identifier_loader = MagicMock()
        mock_executor.identifier_loader.load_endpoint_identifiers = AsyncMock(
            side_effect=KeyError("Column 'missing_column' not found in endpoint data")
        )
        
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
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock the query execution
        mock_result = MagicMock()  # Use MagicMock for non-async result
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
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock the query execution
        mock_result = MagicMock()  # Use MagicMock for non-async result
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
        # NOTE: get_strategy is no longer called in validate_strategy_prerequisites
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock _get_endpoint_by_name
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=mock_endpoint)
        
        # Mock property configs for target
        mock_config = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_config]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
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
        # NOTE: Strategy validation has been removed from validate_strategy_prerequisites
        # as strategies are now loaded from YAML via ConfigLoader instead of database.
        # This test now validates endpoints only.
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock endpoints not found
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=None)
        
        # Execute
        result = await mock_executor.validate_strategy_prerequisites(
            "NONEXISTENT_STRATEGY", "SOURCE", "TARGET"
        )
        
        # Assert - should have errors for missing endpoints
        assert result["valid"] is False
        assert "Source endpoint 'SOURCE' not found" in result["errors"]
        assert "Target endpoint 'TARGET' not found" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_inactive_strategy(
        self, mock_executor, mock_strategy, mock_endpoint
    ):
        """Test validation when strategy is inactive."""
        # NOTE: Strategy active/inactive check has been removed from validate_strategy_prerequisites.
        # This test now validates successful endpoint checks.
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock endpoints found
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=mock_endpoint)
        
        # Mock get_ontology_column to avoid database access
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Mock property configs for target
        mock_config = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_config]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Mock file exists
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}):
            with patch("os.path.exists", return_value=True):
                # Execute
                result = await mock_executor.validate_strategy_prerequisites(
                    "TEST_STRATEGY", "SOURCE", "TARGET"
                )
        
        # Assert - should be valid since endpoints exist
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_prerequisites_endpoint_not_found(
        self, mock_executor, mock_strategy
    ):
        """Test validation when endpoint doesn't exist."""
        # Setup mocks
        # NOTE: get_strategy is no longer called in validate_strategy_prerequisites
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
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
        # NOTE: get_strategy is no longer called in validate_strategy_prerequisites
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Mock async_metamapper_session to return an async context manager
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None
        mock_executor.async_metamapper_session = lambda: mock_session_cm
        
        # Mock endpoint found
        mock_executor._get_endpoint_by_name = AsyncMock(return_value=mock_endpoint)
        
        # Mock get_ontology_column to avoid database access  
        mock_executor.get_ontology_column = AsyncMock(return_value="uniprot_id")
        
        # Mock property configs for target to avoid scalars().all() issue
        mock_config = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_config]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
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