"""Test fixtures for integration tests with proper MappingExecutor setup."""

from unittest.mock import AsyncMock, MagicMock, Mock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService


def create_mock_mapping_executor():
    """Create a fully mocked MappingExecutor for integration tests."""
    # Create mock services
    execution_session_service = MagicMock()
    execution_session_service.start_session = AsyncMock(return_value=1)
    execution_session_service.end_session = AsyncMock()
    execution_session_service.create_progress_tracker = MagicMock()
    
    checkpoint_service = MagicMock()
    checkpoint_service.save = AsyncMock()
    checkpoint_service.load = AsyncMock(return_value=None)
    
    resource_disposal_service = MagicMock()
    resource_disposal_service.dispose_all = AsyncMock()
    
    # Create lifecycle coordinator
    lifecycle_coordinator = LifecycleCoordinator(
        execution_session_service=execution_session_service,
        checkpoint_service=checkpoint_service,
        resource_disposal_service=resource_disposal_service
    )
    
    # Create session manager mock
    session_manager = MagicMock(spec=SessionManager)
    
    # Mock the session context managers
    mock_meta_session = AsyncMock(spec=AsyncSession)
    mock_cache_session = AsyncMock(spec=AsyncSession)
    
    # Create async context managers
    mock_meta_context = AsyncMock()
    mock_meta_context.__aenter__.return_value = mock_meta_session
    mock_meta_context.__aexit__.return_value = None
    
    mock_cache_context = AsyncMock()
    mock_cache_context.__aenter__.return_value = mock_cache_session
    mock_cache_context.__aexit__.return_value = None
    
    # Set up session manager to return contexts
    session_manager.async_metamapper_session = MagicMock(return_value=mock_meta_context)
    session_manager.async_cache_session = MagicMock(return_value=mock_cache_context)
    
    # Create metadata query service
    metadata_query_service = MagicMock(spec=MetadataQueryService)
    metadata_query_service.get_endpoint = AsyncMock()
    metadata_query_service.get_ontology_type = AsyncMock()
    
    # Create mapping coordinator
    iterative_execution_service = MagicMock()
    iterative_execution_service.execute_mapping = AsyncMock(return_value={})
    iterative_execution_service.set_composite_handler = MagicMock()
    
    path_execution_service = MagicMock()
    path_execution_service.execute_path = AsyncMock(return_value={})
    path_execution_service.set_composite_handler = MagicMock()
    
    mapping_coordinator = MagicMock(spec=MappingCoordinatorService)
    mapping_coordinator.iterative_execution_service = iterative_execution_service
    mapping_coordinator.path_execution_service = path_execution_service
    
    # Mock execute_mapping to return empty dict by default
    mapping_coordinator.execute_mapping = AsyncMock(return_value={})
    
    # Create strategy coordinator
    db_strategy_execution_service = MagicMock()
    db_strategy_execution_service.execute_strategy = AsyncMock()
    
    yaml_strategy_execution_service = MagicMock()
    yaml_strategy_execution_service.execute_strategy = AsyncMock()
    
    robust_execution_coordinator = MagicMock()
    robust_execution_coordinator.execute_with_retry = AsyncMock()
    
    strategy_coordinator = StrategyCoordinatorService(
        db_strategy_execution_service=db_strategy_execution_service,
        yaml_strategy_execution_service=yaml_strategy_execution_service,
        robust_execution_coordinator=robust_execution_coordinator
    )
    
    # Create the executor
    executor = MappingExecutor(
        lifecycle_coordinator=lifecycle_coordinator,
        mapping_coordinator=mapping_coordinator,
        strategy_coordinator=strategy_coordinator,
        session_manager=session_manager,
        metadata_query_service=metadata_query_service
    )
    
    # Add some commonly mocked methods directly to executor for backward compatibility
    executor._create_mapping_session_log = AsyncMock(return_value=1)
    executor._update_mapping_session_log = AsyncMock()
    executor._check_cache = AsyncMock(return_value={})
    executor._cache_results = AsyncMock()
    executor._execute_path = AsyncMock(return_value={})
    
    # Add path finder mock
    path_finder = MagicMock()
    path_finder.find_mapping_paths = AsyncMock(return_value=[])
    executor.path_finder = path_finder
    
    # Add wrapper to handle old-style execute_mapping calls
    original_execute_mapping = executor.execute_mapping
    
    async def execute_mapping_wrapper(**kwargs):
        if 'source_endpoint_name' in kwargs:
            # Convert old-style call to new style
            identifiers = kwargs.get('input_identifiers', [])
            source_ontology = kwargs.get('source_property_name')
            target_ontology = kwargs.get('target_property_name')
            options = {
                'use_cache': kwargs.get('use_cache', True),
                'mapping_direction': kwargs.get('mapping_direction', 'forward'),
                'try_reverse_mapping': kwargs.get('try_reverse_mapping', False),
                'source_endpoint': kwargs.get('source_endpoint_name'),
                'target_endpoint': kwargs.get('target_endpoint_name'),
            }
            return await original_execute_mapping(identifiers, source_ontology, target_ontology, None, options)
        else:
            # New style call - shouldn't happen in wrapper
            return {}
    
    executor.execute_mapping = execute_mapping_wrapper
    
    return executor, mock_meta_session, mock_cache_session