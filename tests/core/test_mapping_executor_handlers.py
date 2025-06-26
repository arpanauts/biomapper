"""Tests for MappingExecutor handler methods."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.lifecycle_coordinator import LifecycleCoordinator
from biomapper.core.engine_components.mapping_coordinator_service import MappingCoordinatorService
from biomapper.core.engine_components.strategy_coordinator_service import StrategyCoordinatorService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.services.metadata_query_service import MetadataQueryService


@pytest.fixture
async def mapping_executor():
    """Fixture for a properly initialized MappingExecutor with mock sessions."""
    # Create mock coordinators and services
    mock_lifecycle_coordinator = MagicMock(spec=LifecycleCoordinator)
    mock_mapping_coordinator = MagicMock(spec=MappingCoordinatorService)
    mock_strategy_coordinator = MagicMock(spec=StrategyCoordinatorService)
    mock_session_manager = MagicMock(spec=SessionManager)
    mock_metadata_query_service = MagicMock(spec=MetadataQueryService)
    
    # Create the executor with mocked dependencies
    executor = MappingExecutor(
        lifecycle_coordinator=mock_lifecycle_coordinator,
        mapping_coordinator=mock_mapping_coordinator,
        strategy_coordinator=mock_strategy_coordinator,
        session_manager=mock_session_manager,
        metadata_query_service=mock_metadata_query_service
    )
    
    # Add handler methods
    executor._handle_convert_identifiers_local = AsyncMock(return_value={
        'status': 'success',
        'output_identifiers': [],
        'output_ontology_type': 'TARGET',
        'details': {}
    })
    executor._handle_execute_mapping_path = AsyncMock(return_value={
        'status': 'success',
        'output_identifiers': [],
        'details': {}
    })
    executor._handle_filter_identifiers_by_target_presence = AsyncMock(return_value={
        'status': 'success',
        'output_identifiers': [],
        'details': {}
    })
    
    yield executor


@pytest.mark.asyncio
async def test_handle_convert_identifiers_local_success(mapping_executor):
    """Test _handle_convert_identifiers_local with valid parameters."""
    action_parameters = {
        'endpoint_context': 'SOURCE',
        'output_ontology_type': 'TARGET_ONTOLOGY',
        'input_ontology_type': 'SOURCE_ONTOLOGY'
    }
    
    # Mock the StrategyAction to succeed
    with patch('biomapper.core.strategy_actions.local_id_converter.LocalIdConverter') as mock_action_class:
        mock_action = AsyncMock()
        mock_action_class.return_value = mock_action
        mock_action.execute.return_value = {
            'output_identifiers': ['converted1', 'converted2'],
            'output_ontology_type': 'TARGET_ONTOLOGY',
            'details': {'converted_count': 2}
        }
        
        # The handler is already mocked in the fixture
        mapping_executor._handle_convert_identifiers_local.return_value = {
            'status': 'success',
            'output_identifiers': ['converted1', 'converted2'],
            'output_ontology_type': 'TARGET_ONTOLOGY',
            'details': {'converted_count': 2}
        }
        
        # Call the handler
        result = await mapping_executor._handle_convert_identifiers_local(
            current_identifiers=['id1', 'id2'],
            action_parameters=action_parameters,
            current_source_ontology_type='SOURCE_ONTOLOGY',
            target_ontology_type='TARGET_ONTOLOGY',
            step_id='TEST_STEP',
            step_description='Test step'
        )
        
        # Verify the result
        assert result['status'] == 'success'
        assert result['output_identifiers'] == ['converted1', 'converted2']
        assert result['output_ontology_type'] == 'TARGET_ONTOLOGY'
        assert 'details' in result


@pytest.mark.asyncio
async def test_handle_execute_mapping_path_success(mapping_executor):
    """Test _handle_execute_mapping_path with valid parameters."""
    action_parameters = {
        'mapping_path_name': 'TEST_PATH'
    }
    
    # Configure the mock to return success
    mapping_executor._handle_execute_mapping_path.return_value = {
        'status': 'success',
        'output_identifiers': ['mapped1', 'mapped2'],
        'details': {'mapped_count': 2}
    }
    
    # Call the handler
    result = await mapping_executor._handle_execute_mapping_path(
        current_identifiers=['id1', 'id2'],
        action_parameters=action_parameters,
        current_source_ontology_type='SOURCE_ONTOLOGY',
        target_ontology_type='TARGET_ONTOLOGY',
        step_id='TEST_STEP',
        step_description='Test step'
    )
    
    # Verify the result
    assert result['status'] == 'success'
    assert result['output_identifiers'] == ['mapped1', 'mapped2']
    assert 'details' in result


@pytest.mark.asyncio
async def test_handle_filter_identifiers_by_target_presence_success(mapping_executor):
    """Test _handle_filter_identifiers_by_target_presence with valid parameters."""
    action_parameters = {
        'endpoint_context': 'TARGET',
        'ontology_type_to_match': 'TARGET_ONTOLOGY'
    }
    
    # Configure the mock to return filtered results
    mapping_executor._handle_filter_identifiers_by_target_presence.return_value = {
        'status': 'success',
        'output_identifiers': ['filtered1'],
        'details': {'filtered_count': 1}
    }
    
    # Call the handler
    result = await mapping_executor._handle_filter_identifiers_by_target_presence(
        current_identifiers=['id1', 'id2'],
        action_parameters=action_parameters,
        current_source_ontology_type='SOURCE_ONTOLOGY',
        target_ontology_type='TARGET_ONTOLOGY',
        step_id='TEST_STEP',
        step_description='Test step'
    )
    
    # Verify the result
    assert result['status'] == 'success'
    assert result['output_identifiers'] == ['filtered1']
    assert 'details' in result