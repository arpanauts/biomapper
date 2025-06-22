"""
Unit tests for MappingExecutorBuilder.

This module tests the builder pattern implementation for constructing MappingExecutor instances.
It verifies that the builder correctly initializes components, wires dependencies, and produces
fully functional MappingExecutor instances.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.lifecycle_manager import LifecycleManager


class TestMappingExecutorBuilder:
    """Test suite for MappingExecutorBuilder."""
    
    def test_builder_initialization_with_config_params(self):
        """Test builder initialization with configuration parameters (legacy mode)."""
        builder = MappingExecutorBuilder(
            metamapper_db_url="postgresql://test_meta",
            mapping_cache_db_url="postgresql://test_cache",
            echo_sql=True,
            path_cache_size=200,
            path_cache_expiry_seconds=600,
            max_concurrent_batches=10,
            enable_metrics=False,
            checkpoint_enabled=True,
            checkpoint_dir="/tmp/checkpoints",
            batch_size=50,
            max_retries=5,
            retry_delay=10
        )
        
        # Verify all configuration parameters are stored
        assert builder.metamapper_db_url == "postgresql://test_meta"
        assert builder.mapping_cache_db_url == "postgresql://test_cache"
        assert builder.echo_sql is True
        assert builder.path_cache_size == 200
        assert builder.path_cache_expiry_seconds == 600
        assert builder.max_concurrent_batches == 10
        assert builder.enable_metrics is False
        assert builder.checkpoint_enabled is True
        assert builder.checkpoint_dir == "/tmp/checkpoints"
        assert builder.batch_size == 50
        assert builder.max_retries == 5
        assert builder.retry_delay == 10
        
        # Verify component parameters are None (legacy mode)
        assert builder.session_manager is None
        assert builder.client_manager is None
    
    def test_builder_initialization_with_components(self):
        """Test builder initialization with pre-initialized components (component mode)."""
        # Create mock components
        mock_session_manager = Mock()
        mock_client_manager = Mock()
        mock_config_loader = Mock()
        
        builder = MappingExecutorBuilder(
            session_manager=mock_session_manager,
            client_manager=mock_client_manager,
            config_loader=mock_config_loader,
            batch_size=75
        )
        
        # Verify components are stored
        assert builder.session_manager is mock_session_manager
        assert builder.client_manager is mock_client_manager
        assert builder.config_loader is mock_config_loader
        assert builder.batch_size == 75
        
        # Verify unspecified parameters have defaults
        assert builder.enable_metrics is True
        assert builder.checkpoint_enabled is False
    
    def test_build_creates_mapping_executor(self):
        """Test that build() creates a MappingExecutor instance."""
        builder = MappingExecutorBuilder()
        
        # Build should create a MappingExecutor
        executor = builder.build()
        
        assert isinstance(executor, MappingExecutor)
    
    def test_build_initializes_coordinators(self):
        """Test that build() properly initializes coordinator services."""
        builder = MappingExecutorBuilder()
        
        executor = builder.build()
        
        # Verify coordinators are initialized
        assert hasattr(executor, 'strategy_coordinator')
        assert hasattr(executor, 'mapping_coordinator')
        assert hasattr(executor, 'lifecycle_manager')
        
        assert isinstance(executor.strategy_coordinator, StrategyCoordinatorService)
        assert isinstance(executor.mapping_coordinator, MappingCoordinatorService)
        assert isinstance(executor.lifecycle_manager, LifecycleManager)
    
    def test_build_with_legacy_mode(self):
        """Test building with legacy configuration parameters."""
        builder = MappingExecutorBuilder(
            metamapper_db_url="postgresql://legacy_meta",
            mapping_cache_db_url="postgresql://legacy_cache",
            echo_sql=True,
            enable_metrics=True
        )
        
        executor = builder.build()
        
        # Verify the executor is configured with legacy parameters
        assert executor.metamapper_db_url == "postgresql://legacy_meta"
        assert executor.mapping_cache_db_url == "postgresql://legacy_cache"
        assert executor.echo_sql is True
        assert executor.enable_metrics is True
    
    def test_build_with_component_mode(self):
        """Test building with pre-initialized components."""
        # Create mock components with required attributes
        mock_session_manager = Mock()
        mock_session_manager.async_metamapper_engine = Mock()
        mock_session_manager.async_metamapper_engine.url = "postgresql://comp_meta"
        mock_session_manager.async_metamapper_engine.echo = False
        mock_session_manager.async_cache_engine = Mock()
        mock_session_manager.async_cache_engine.url = "postgresql://comp_cache"
        mock_session_manager.MetamapperSessionFactory = Mock()
        mock_session_manager.async_metamapper_session = Mock()
        mock_session_manager.CacheSessionFactory = Mock()
        mock_session_manager.async_cache_session = Mock()
        
        mock_client_manager = Mock()
        
        builder = MappingExecutorBuilder(
            session_manager=mock_session_manager,
            client_manager=mock_client_manager,
            enable_metrics=False
        )
        
        executor = builder.build()
        
        # Verify components are properly wired
        assert executor.session_manager is mock_session_manager
        assert executor.client_manager is mock_client_manager
        assert executor.enable_metrics is False
    
    def test_build_handles_initialization_errors(self):
        """Test that build() handles initialization errors gracefully."""
        builder = MappingExecutorBuilder()
        
        # Mock the MappingExecutor to raise an error during initialization
        with patch('biomapper.core.engine_components.mapping_executor_builder.MappingExecutor') as mock_executor_class:
            mock_executor_class.side_effect = Exception("Initialization failed")
            
            with pytest.raises(RuntimeError) as exc_info:
                builder.build()
            
            assert "MappingExecutor construction failed" in str(exc_info.value)
            assert "Initialization failed" in str(exc_info.value)
    
    def test_create_bare_executor_not_implemented(self):
        """Test that _create_bare_executor raises NotImplementedError."""
        builder = MappingExecutorBuilder()
        
        with pytest.raises(NotImplementedError) as exc_info:
            builder._create_bare_executor()
        
        assert "Bare executor creation not yet supported" in str(exc_info.value)
    
    def test_initialize_components_delegation(self):
        """Test that _initialize_components delegates to InitializationService."""
        builder = MappingExecutorBuilder(
            metamapper_db_url="postgresql://test",
            batch_size=150
        )
        
        mock_executor = Mock()
        
        with patch('biomapper.core.engine_components.mapping_executor_builder.InitializationService') as mock_init_service_class:
            mock_init_service = Mock()
            mock_init_service.initialize_components.return_value = {
                'session_manager': Mock(),
                'client_manager': Mock(),
                'metadata_query_service': Mock()
            }
            mock_init_service_class.return_value = mock_init_service
            
            components = builder._initialize_components(mock_executor)
            
            # Verify InitializationService was called with correct parameters
            mock_init_service.initialize_components.assert_called_once()
            call_args = mock_init_service.initialize_components.call_args
            assert call_args[0][0] is mock_executor
            assert call_args[1]['metamapper_db_url'] == "postgresql://test"
            assert call_args[1]['batch_size'] == 150
            
            # Verify components are returned
            assert 'session_manager' in components
            assert 'client_manager' in components
    
    def test_create_coordinators(self):
        """Test that _create_coordinators properly creates coordinator services."""
        builder = MappingExecutorBuilder()
        
        # Create mock components
        mock_components = {
            'direct_mapping_service': Mock(),
            'iterative_mapping_service': Mock(),
            'bidirectional_validation_service': Mock(),
            'path_finder': Mock(),
            'async_metamapper_session': Mock(),
            'async_cache_session': Mock(),
            'metadata_query_service': Mock(),
            'session_metrics_service': Mock(),
            'strategy_execution_service': Mock(),
            'strategy_orchestrator': Mock(),
            'robust_execution_coordinator': Mock(),
            'path_execution_service': Mock(),
            'session_manager': Mock(),
            'lifecycle_service': Mock(),
            'client_manager': Mock(),
        }
        
        mock_executor = Mock()
        
        coordinators = builder._create_coordinators(mock_components, mock_executor)
        
        # Verify all coordinators are created
        assert 'strategy_coordinator' in coordinators
        assert 'mapping_coordinator' in coordinators
        assert 'lifecycle_manager' in coordinators
        assert 'result_aggregation_service' in coordinators
        assert 'iterative_execution_service' in coordinators
        assert 'db_strategy_execution_service' in coordinators
        assert 'yaml_strategy_execution_service' in coordinators
        
        # Verify coordinator types
        assert isinstance(coordinators['strategy_coordinator'], StrategyCoordinatorService)
        assert isinstance(coordinators['mapping_coordinator'], MappingCoordinatorService)
        assert isinstance(coordinators['lifecycle_manager'], LifecycleManager)
    
    def test_wire_dependencies(self):
        """Test that _wire_dependencies properly injects all dependencies."""
        builder = MappingExecutorBuilder()
        
        mock_executor = Mock()
        mock_components = {
            'session_manager': Mock(),
            'client_manager': Mock(),
            'cache_manager': Mock(),
        }
        mock_coordinators = {
            'strategy_coordinator': Mock(),
            'mapping_coordinator': Mock(),
            'lifecycle_manager': Mock(),
        }
        
        builder._wire_dependencies(mock_executor, mock_components, mock_coordinators)
        
        # Verify all components are injected
        assert mock_executor.session_manager is mock_components['session_manager']
        assert mock_executor.client_manager is mock_components['client_manager']
        assert mock_executor.cache_manager is mock_components['cache_manager']
        
        # Verify all coordinators are injected
        assert mock_executor.strategy_coordinator is mock_coordinators['strategy_coordinator']
        assert mock_executor.mapping_coordinator is mock_coordinators['mapping_coordinator']
        assert mock_executor.lifecycle_manager is mock_coordinators['lifecycle_manager']
    
    def test_builder_logging(self):
        """Test that builder logs appropriate messages during construction."""
        builder = MappingExecutorBuilder()
        
        with patch.object(builder.logger, 'info') as mock_info:
            with patch.object(builder.logger, 'debug') as mock_debug:
                executor = builder.build()
                
                # Verify logging calls
                mock_info.assert_any_call("Building MappingExecutor instance")
                mock_info.assert_any_call("MappingExecutor instance built successfully")
    
    def test_builder_with_mixed_mode(self):
        """Test builder with both config parameters and some components."""
        mock_session_manager = Mock()
        mock_session_manager.async_metamapper_engine = Mock()
        mock_session_manager.async_metamapper_engine.url = "postgresql://mixed"
        mock_session_manager.async_metamapper_engine.echo = True
        mock_session_manager.async_cache_engine = Mock()
        mock_session_manager.async_cache_engine.url = "postgresql://mixed_cache"
        mock_session_manager.MetamapperSessionFactory = Mock()
        mock_session_manager.async_metamapper_session = Mock()
        mock_session_manager.CacheSessionFactory = Mock()
        mock_session_manager.async_cache_session = Mock()
        
        builder = MappingExecutorBuilder(
            metamapper_db_url="postgresql://ignored",  # Should be ignored in component mode
            session_manager=mock_session_manager,
            batch_size=200,
            enable_metrics=True
        )
        
        executor = builder.build()
        
        # Verify component mode takes precedence
        assert executor.session_manager is mock_session_manager
        assert executor.batch_size == 200
        assert executor.enable_metrics is True