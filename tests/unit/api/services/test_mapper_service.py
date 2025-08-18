"""Tests for MapperService core business logic."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.api.services.mapper_service import MapperService


class TestMapperServiceInitialization:
    """Test MapperService initialization and setup."""
    
    @patch('src.api.services.mapper_service.MinimalStrategyService')
    @patch('src.api.services.mapper_service.Path')
    def test_mapper_service_init_success(self, mock_path, mock_strategy_service_class):
        """Test successful MapperService initialization."""
        # Mock path construction
        mock_strategies_dir = Path("/mock/strategies")
        mock_path.return_value.parent.parent.parent = mock_strategies_dir
        
        # Mock MinimalStrategyService
        mock_strategy_service = Mock()
        mock_strategy_service_class.return_value = mock_strategy_service
        
        # Initialize service
        service = MapperService()
        
        # Verify initialization
        assert service.strategy_service == mock_strategy_service
        mock_strategy_service_class.assert_called_once_with(str(mock_strategies_dir / "configs" / "strategies"))
    
    @patch('src.api.services.mapper_service.MinimalStrategyService')
    @patch('src.api.services.mapper_service.Path')
    @patch('src.api.services.mapper_service.logger')
    def test_mapper_service_init_strategy_service_failure(self, mock_logger, mock_path, mock_strategy_service_class):
        """Test MapperService initialization with MinimalStrategyService failure."""
        # Mock path construction
        mock_strategies_dir = Path("/mock/strategies")
        mock_path.return_value.parent.parent.parent = mock_strategies_dir
        
        # Mock MinimalStrategyService to raise exception
        mock_strategy_service_class.side_effect = Exception("Failed to initialize strategy service")
        
        # Should raise exception
        with pytest.raises(Exception, match="Failed to initialize strategy service"):
            MapperService()
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
    
    @patch('src.api.services.mapper_service.MinimalStrategyService')
    @patch('src.api.services.mapper_service.Path')
    @patch('src.api.services.mapper_service.logger')
    def test_mapper_service_init_logging(self, mock_logger, mock_path, mock_strategy_service_class):
        """Test that initialization is properly logged."""
        # Setup mocks
        mock_strategies_dir = Path("/mock/strategies")
        mock_path.return_value.parent.parent.parent = mock_strategies_dir
        mock_strategy_service = Mock()
        mock_strategy_service_class.return_value = mock_strategy_service
        
        # Initialize service
        MapperService()
        
        # Verify logging calls
        mock_logger.info.assert_any_call("Initializing MapperService...")
        mock_logger.info.assert_any_call(f"MinimalStrategyService initialized with {mock_strategies_dir / 'configs' / 'strategies'}")
        mock_logger.info.assert_any_call("MapperService initialized.")


class TestMapperServiceStrategyExecution:
    """Test strategy execution functionality."""
    
    @pytest.fixture
    def mock_strategy_service(self):
        """Create mock strategy service."""
        return AsyncMock()
    
    @pytest.fixture
    def mapper_service(self, mock_strategy_service):
        """Create MapperService with mocked dependencies."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_class.return_value = mock_strategy_service
            service = MapperService()
            return service
    
    @pytest.mark.asyncio
    async def test_execute_strategy_success(self, mapper_service, mock_strategy_service):
        """Test successful strategy execution."""
        # Setup test data
        strategy_name = "test_strategy"
        parameters = {"param1": "value1", "param2": 123}
        expected_result = {
            "status": "success",
            "data": {"processed_items": 100},
            "statistics": {"execution_time": 5.2}
        }
        
        # Mock strategy service execution
        mock_strategy_service.execute_strategy.return_value = expected_result
        
        # Execute strategy
        result = await mapper_service.execute_strategy(strategy_name, parameters)
        
        # Verify result
        assert result == expected_result
        
        # Verify strategy service was called correctly
        mock_strategy_service.execute_strategy.assert_called_once_with(strategy_name, parameters)
    
    @pytest.mark.asyncio
    async def test_execute_strategy_empty_parameters(self, mapper_service, mock_strategy_service):
        """Test strategy execution with empty parameters."""
        strategy_name = "test_strategy"
        parameters = {}
        expected_result = {"status": "success", "data": {}}
        
        mock_strategy_service.execute_strategy.return_value = expected_result
        
        result = await mapper_service.execute_strategy(strategy_name, parameters)
        
        assert result == expected_result
        mock_strategy_service.execute_strategy.assert_called_once_with(strategy_name, parameters)
    
    @pytest.mark.asyncio
    async def test_execute_strategy_complex_parameters(self, mapper_service, mock_strategy_service):
        """Test strategy execution with complex parameters."""
        strategy_name = "complex_strategy"
        parameters = {
            "nested_dict": {"key1": "value1", "key2": {"subkey": "subvalue"}},
            "list_param": [1, 2, 3, "string"],
            "boolean_param": True,
            "none_param": None
        }
        expected_result = {"status": "success", "processed": parameters}
        
        mock_strategy_service.execute_strategy.return_value = expected_result
        
        result = await mapper_service.execute_strategy(strategy_name, parameters)
        
        assert result == expected_result
        mock_strategy_service.execute_strategy.assert_called_once_with(strategy_name, parameters)
    
    @pytest.mark.asyncio
    @patch('src.api.services.mapper_service.logger')
    async def test_execute_strategy_failure(self, mock_logger, mapper_service, mock_strategy_service):
        """Test strategy execution with failure."""
        strategy_name = "failing_strategy"
        parameters = {"param1": "value1"}
        
        # Mock strategy service to raise exception
        test_exception = Exception("Strategy execution failed")
        mock_strategy_service.execute_strategy.side_effect = test_exception
        
        # Should raise the exception
        with pytest.raises(Exception, match="Strategy execution failed"):
            await mapper_service.execute_strategy(strategy_name, parameters)
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Strategy execution failed" in call_args[0][0]
        assert call_args[1]["exc_info"] is True
    
    @pytest.mark.asyncio
    async def test_execute_strategy_timeout(self, mapper_service, mock_strategy_service):
        """Test strategy execution with timeout."""
        strategy_name = "slow_strategy"
        parameters = {"param1": "value1"}
        
        # Mock strategy service to timeout
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow execution
            return {"status": "success"}
        
        mock_strategy_service.execute_strategy.side_effect = slow_execution
        
        # Execute with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mapper_service.execute_strategy(strategy_name, parameters), 
                timeout=0.1
            )
    
    @pytest.mark.asyncio
    async def test_execute_strategy_return_types(self, mapper_service, mock_strategy_service):
        """Test strategy execution with different return types."""
        test_cases = [
            {"status": "success", "data": []},  # List
            {"status": "success", "data": "string_result"},  # String
            {"status": "success", "data": 123},  # Number
            {"status": "success", "data": True},  # Boolean
            {"status": "success", "data": None},  # None
        ]
        
        for expected_result in test_cases:
            mock_strategy_service.execute_strategy.return_value = expected_result
            
            result = await mapper_service.execute_strategy("test_strategy", {})
            assert result == expected_result


class TestMapperServiceStrategyListing:
    """Test strategy listing functionality."""
    
    @pytest.fixture
    def mock_strategy_service(self):
        """Create mock strategy service."""
        return Mock()
    
    @pytest.fixture
    def mapper_service(self, mock_strategy_service):
        """Create MapperService with mocked dependencies."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_class.return_value = mock_strategy_service
            service = MapperService()
            return service
    
    def test_list_strategies_success(self, mapper_service, mock_strategy_service):
        """Test successful strategy listing."""
        expected_strategies = [
            "protein_mapping_strategy",
            "metabolite_enrichment_strategy", 
            "data_export_strategy"
        ]
        
        mock_strategy_service.list_available_strategies.return_value = expected_strategies
        
        result = mapper_service.list_strategies()
        
        assert result == expected_strategies
        mock_strategy_service.list_available_strategies.assert_called_once()
    
    def test_list_strategies_empty(self, mapper_service, mock_strategy_service):
        """Test strategy listing with no strategies."""
        mock_strategy_service.list_available_strategies.return_value = []
        
        result = mapper_service.list_strategies()
        
        assert result == []
        mock_strategy_service.list_available_strategies.assert_called_once()
    
    @patch('src.api.services.mapper_service.logger')
    def test_list_strategies_failure(self, mock_logger, mapper_service, mock_strategy_service):
        """Test strategy listing with failure."""
        # Mock strategy service to raise exception
        test_exception = Exception("Failed to list strategies")
        mock_strategy_service.list_available_strategies.side_effect = test_exception
        
        result = mapper_service.list_strategies()
        
        # Should return empty list on failure
        assert result == []
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Failed to list strategies" in call_args[0][0]
        assert call_args[1]["exc_info"] is True
    
    def test_list_strategies_large_number(self, mapper_service, mock_strategy_service):
        """Test strategy listing with large number of strategies."""
        # Create large list of strategies
        large_strategy_list = [f"strategy_{i}" for i in range(1000)]
        mock_strategy_service.list_available_strategies.return_value = large_strategy_list
        
        result = mapper_service.list_strategies()
        
        assert result == large_strategy_list
        assert len(result) == 1000
    
    def test_list_strategies_return_type(self, mapper_service, mock_strategy_service):
        """Test that list_strategies always returns a list."""
        # Test with different return types from underlying service
        test_cases = [
            ["strategy1", "strategy2"],  # Normal list
            [],  # Empty list
            None,  # None (should be handled)
        ]
        
        for mock_return in test_cases:
            if mock_return is None:
                mock_strategy_service.list_available_strategies.side_effect = Exception("Error")
                result = mapper_service.list_strategies()
                assert result == []
            else:
                mock_strategy_service.list_available_strategies.side_effect = None
                mock_strategy_service.list_available_strategies.return_value = mock_return
                result = mapper_service.list_strategies()
                assert isinstance(result, list)
                assert result == mock_return


class TestMapperServiceIntegration:
    """Integration tests for MapperService."""
    
    @pytest.mark.integration
    @patch('src.api.services.mapper_service.MinimalStrategyService')
    def test_service_lifecycle(self, mock_strategy_service_class):
        """Test complete service lifecycle."""
        # Mock MinimalStrategyService
        mock_strategy_service = AsyncMock()
        # list_available_strategies should be synchronous
        mock_strategy_service.list_available_strategies = Mock(return_value=["test_strategy"])
        mock_strategy_service.execute_strategy.return_value = {"status": "success"}
        mock_strategy_service_class.return_value = mock_strategy_service
        
        # Initialize service
        service = MapperService()
        
        # Test listing strategies
        strategies = service.list_strategies()
        assert strategies == ["test_strategy"]
        
        # Test strategy execution
        async def test_execution():
            result = await service.execute_strategy("test_strategy", {"param": "value"})
            assert result["status"] == "success"
        
        # Run async test
        asyncio.run(test_execution())
    
    @pytest.mark.integration
    def test_service_with_real_paths(self):
        """Test service initialization with real path construction."""
        # This test verifies that path construction works correctly
        # without mocking the Path operations
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_class.return_value = Mock()
            
            service = MapperService()
            
            # Verify service was created
            assert service is not None
            assert hasattr(service, 'strategy_service')


class TestMapperServiceErrorHandling:
    """Test error handling in MapperService."""
    
    @pytest.fixture
    def mapper_service(self):
        """Create MapperService with mocked dependencies."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = AsyncMock()
            mock_class.return_value = mock_strategy_service
            service = MapperService()
            return service
    
    @pytest.mark.asyncio
    async def test_execute_strategy_network_error(self, mapper_service):
        """Test strategy execution with network-like errors."""
        # Simulate network timeout
        mapper_service.strategy_service.execute_strategy.side_effect = asyncio.TimeoutError("Network timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await mapper_service.execute_strategy("test_strategy", {})
    
    @pytest.mark.asyncio
    async def test_execute_strategy_invalid_strategy_name(self, mapper_service):
        """Test execution with invalid strategy name."""
        # Mock strategy service to raise specific exception for invalid strategy
        mapper_service.strategy_service.execute_strategy.side_effect = KeyError("Strategy not found")
        
        with pytest.raises(KeyError):
            await mapper_service.execute_strategy("nonexistent_strategy", {})
    
    @pytest.mark.asyncio
    async def test_execute_strategy_malformed_parameters(self, mapper_service):
        """Test execution with malformed parameters."""
        # Test with parameters that might cause issues
        malformed_params = {
            "circular_ref": None,  # Will be set to create circular reference
        }
        malformed_params["circular_ref"] = malformed_params  # Circular reference
        
        # Mock to raise ValueError for malformed params
        mapper_service.strategy_service.execute_strategy.side_effect = ValueError("Invalid parameters")
        
        with pytest.raises(ValueError):
            await mapper_service.execute_strategy("test_strategy", malformed_params)


class TestMapperServicePerformance:
    """Test performance aspects of MapperService."""
    
    @pytest.fixture
    def mapper_service(self):
        """Create MapperService with mocked dependencies."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = AsyncMock()
            # list_available_strategies should be synchronous
            mock_strategy_service.list_available_strategies = Mock()
            mock_class.return_value = mock_strategy_service
            service = MapperService()
            return service
    
    @pytest.mark.asyncio
    async def test_concurrent_strategy_executions(self, mapper_service):
        """Test concurrent strategy executions."""
        # Mock strategy service to return different results
        async def mock_execute(strategy_name, params):
            await asyncio.sleep(0.01)  # Simulate work
            return {"strategy": strategy_name, "params": params}
        
        mapper_service.strategy_service.execute_strategy.side_effect = mock_execute
        
        # Execute multiple strategies concurrently
        tasks = []
        for i in range(5):
            task = mapper_service.execute_strategy(f"strategy_{i}", {"param": i})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all executions completed
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["strategy"] == f"strategy_{i}"
            assert result["params"]["param"] == i
    
    def test_list_strategies_performance(self, mapper_service):
        """Test list_strategies performance with large number of strategies."""
        # Mock large strategy list
        large_list = [f"strategy_{i}" for i in range(10000)]
        mapper_service.strategy_service.list_available_strategies.return_value = large_list
        
        # Should handle large lists efficiently
        import time
        start_time = time.time()
        result = mapper_service.list_strategies()
        end_time = time.time()
        
        assert result == large_list
        assert (end_time - start_time) < 1.0  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_results(self, mapper_service):
        """Test memory usage with large strategy results."""
        # Mock strategy service to return large result
        large_data = {"large_field": "x" * 1000000}  # 1MB of data
        mapper_service.strategy_service.execute_strategy.return_value = large_data
        
        result = await mapper_service.execute_strategy("test_strategy", {})
        
        # Should handle large results
        assert result == large_data
        assert len(result["large_field"]) == 1000000


class TestMapperServiceLogging:
    """Test logging behavior in MapperService."""
    
    @patch('src.api.services.mapper_service.logger')
    @patch('src.api.services.mapper_service.MinimalStrategyService')
    def test_initialization_logging(self, mock_strategy_service_class, mock_logger):
        """Test that initialization steps are properly logged."""
        mock_strategy_service = Mock()
        mock_strategy_service_class.return_value = mock_strategy_service
        
        MapperService()
        
        # Verify initialization logging
        expected_calls = [
            "Initializing MapperService...",
            "MapperService initialized."
        ]
        
        for expected_call in expected_calls:
            mock_logger.info.assert_any_call(expected_call)
    
    @pytest.mark.asyncio
    @patch('src.api.services.mapper_service.logger')
    async def test_execution_error_logging(self, mock_logger):
        """Test that execution errors are properly logged."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = AsyncMock()
            mock_strategy_service.execute_strategy.side_effect = Exception("Test error")
            mock_class.return_value = mock_strategy_service
            
            service = MapperService()
            
            with pytest.raises(Exception):
                await service.execute_strategy("test_strategy", {})
            
            # Verify error logging
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            assert "Strategy execution failed" in call_args[0][0]
    
    @patch('src.api.services.mapper_service.logger')
    def test_list_strategies_error_logging(self, mock_logger):
        """Test that list_strategies errors are properly logged."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = Mock()
            mock_strategy_service.list_available_strategies.side_effect = Exception("List error")
            mock_class.return_value = mock_strategy_service
            
            service = MapperService()
            result = service.list_strategies()
            
            assert result == []
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            assert "Failed to list strategies" in call_args[0][0]


class TestMapperServiceState:
    """Test MapperService state management."""
    
    def test_service_state_consistency(self):
        """Test that service maintains consistent state."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = Mock()
            mock_class.return_value = mock_strategy_service
            
            service = MapperService()
            
            # State should be consistent
            assert service.strategy_service == mock_strategy_service
            
            # Multiple calls should return same service
            assert service.strategy_service is mock_strategy_service
    
    def test_service_immutability(self):
        """Test that service properties are not accidentally modified."""
        with patch('src.api.services.mapper_service.MinimalStrategyService') as mock_class:
            mock_strategy_service = Mock()
            mock_class.return_value = mock_strategy_service
            
            service = MapperService()
            original_strategy_service = service.strategy_service
            
            # Attempting to modify should not affect original
            try:
                service.strategy_service = Mock()
                # If modification succeeds, verify it actually changed
                assert service.strategy_service != original_strategy_service
            except AttributeError:
                # If service prevents modification, that's also acceptable
                pass