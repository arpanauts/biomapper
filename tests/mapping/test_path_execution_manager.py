"""Tests for PathExecutionManager functionality."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from biomapper.core.engine_components.path_execution_manager import PathExecutionManager
from biomapper.core.engine_components.cache_manager import CacheManager
from biomapper.db.models import MappingPath, MappingPathStep, MappingResource
from biomapper.core.exceptions import ClientExecutionError


# Helper classes for testing
class MockStepClient:
    """Mock mapping client for testing _run_path_steps."""
    def __init__(self, results=None, raise_error=False, error_msg=None):
        self.results = results or {}
        self.raise_error = raise_error
        self.error_msg = error_msg or "Simulated client error"
        self.called_with = None

    async def map_identifiers(self, ids, **kwargs):
        """Mock implementation that returns predefined results or raises an error."""
        self.called_with = ids

        if self.raise_error:
            raise ClientExecutionError(self.error_msg, client_name=self.__class__.__name__)
            
        # Return results in the expected format for _run_path_steps
        results = {}
        for id_ in ids:
            if id_ in self.results:
                result = self.results[id_]
                # Format: {'primary_ids': [...], 'was_resolved': bool}
                results[id_] = result
            else:
                # No mapping for this ID
                results[id_] = {'primary_ids': [], 'was_resolved': False}
        return results
    
    async def close(self):
        """Mock cleanup method."""
        pass


def create_mock_step(step_id=1, resource_id=1, step_order=1, resource=None):
    """Helper to create a mock MappingPathStep."""
    mock_step = MagicMock(spec=MappingPathStep)
    mock_step.id = step_id
    mock_step.mapping_resource_id = resource_id
    mock_step.step_order = step_order
    mock_step.mapping_resource = resource or MagicMock()
    return mock_step


def create_mock_resource(resource_id=1, name="TestResource", resource_config=None):
    """Helper to create a mock MappingResource."""
    mock_resource = MagicMock(spec=MappingResource)
    mock_resource.id = resource_id
    mock_resource.name = name
    mock_resource.resource_config = resource_config or {}
    mock_resource.client_module_path = "tests.core.test_path_execution_manager"
    mock_resource.client_class_name = "MockStepClient"
    return mock_resource


@pytest.fixture
async def path_execution_manager():
    """Fixture for PathExecutionManager with mocked dependencies."""
    # Create mock dependencies
    mock_session_manager = MagicMock()
    mock_cache_manager = MagicMock(spec=CacheManager)
    
    # Create the PathExecutionManager with mocked dependencies
    manager = PathExecutionManager(
        metamapper_session_factory=mock_session_manager,
        cache_manager=mock_cache_manager,
        logger=None,
        semaphore=None,
        max_retries=3,
        retry_delay=1,
        batch_size=250,
        max_concurrent_batches=5,
        enable_metrics=True,
        load_client_func=None,
        execute_mapping_step_func=None,  # Will use default implementation
        calculate_confidence_score_func=None,
        create_mapping_path_details_func=None,
        determine_mapping_source_func=None,
        track_mapping_metrics_func=None
    )
    
    # Add a client_manager mock for the tests
    manager.client_manager = MagicMock()
    
    # Create a mock implementation of _execute_mapping_step that uses the client
    async def mock_execute_mapping_step(step, input_values, is_reverse=False):
        # Get the mock client from client_manager
        client = await manager.client_manager.get_client_instance(step.mapping_resource)
        if client:
            # Call the client's map_identifiers method
            results = await client.map_identifiers(input_values)
            # Transform results to expected format
            return {
                id_: (result.get('primary_ids', []), None)
                for id_, result in results.items()
            }
        return {}
    
    # Replace the default implementation with our mock
    manager._execute_mapping_step = mock_execute_mapping_step
    
    yield manager


@pytest.mark.asyncio
async def test_run_path_steps_basic(path_execution_manager):
    """Test basic execution of execute_path with a single step."""
    # Create a mock path with a single step
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 1
    mock_path.name = "TestPath"
    
    # Configure the mock resource with expected results
    mock_resource = create_mock_resource()
    mock_step = create_mock_step(resource=mock_resource)
    mock_path.steps = [mock_step]
    
    # Patch _load_and_initialize_client to return our MockStepClient
    client_results = {
        "input1": {"primary_ids": ["output1"], "was_resolved": False},
        "input2": {"primary_ids": ["output2"], "was_resolved": False}
    }
    mock_client = MockStepClient(results=client_results)
    
    with patch.object(path_execution_manager.client_manager, 'get_client_instance', new=AsyncMock(return_value=mock_client)):
        # Run the function through execute_path
        results_dict = await path_execution_manager.execute_path(
            path=mock_path,
            input_identifiers=["input1", "input2"],
            source_ontology="SOURCE",
            target_ontology="TARGET"
        )
        
        # Transform results to match expected format for the test
        results = {}
        for input_id, result in results_dict.items():
            if result.get('status') == 'success' and result.get('target_identifiers'):
                results[input_id] = {
                    'final_ids': result['target_identifiers'],
                    'provenance': [{
                        'path_id': mock_path.id,
                        'path_name': mock_path.name,
                        'steps_details': []
                    }]
                }
        
        # Verify the results structure
        assert "input1" in results_dict
        assert "input2" in results_dict


@pytest.mark.asyncio
async def test_execute_path_multi_step():
    """Test path execution with multiple sequential steps."""
    # Create mock dependencies
    mock_session_manager = MagicMock()
    mock_cache_manager = MagicMock(spec=CacheManager)
    
    manager = PathExecutionManager(
        metamapper_session_factory=mock_session_manager,
        cache_manager=mock_cache_manager
    )
    
    # Create a mock path with two steps
    mock_path = MagicMock(spec=MappingPath)
    mock_path.id = 1
    mock_path.name = "TestPath"
    
    # Configure mock resources
    mock_resource1 = create_mock_resource(resource_id=1, name="Step1Resource")
    mock_resource2 = create_mock_resource(resource_id=2, name="Step2Resource") 
    
    mock_step1 = create_mock_step(step_id=1, resource_id=1, step_order=1, resource=mock_resource1)
    mock_step2 = create_mock_step(step_id=2, resource_id=2, step_order=2, resource=mock_resource2)
    
    mock_path.steps = [mock_step1, mock_step2]
    
    # Configure first client to map input1->intermediate1 and input2->intermediate2
    client1_results = {
        "input1": {"primary_ids": ["intermediate1"], "was_resolved": False},
        "input2": {"primary_ids": ["intermediate2"], "was_resolved": False}
    }
    mock_client1 = MockStepClient(results=client1_results)
    
    # Configure second client to map intermediate values to final outputs
    client2_results = {
        "intermediate1": {"primary_ids": ["output1"], "was_resolved": False},
        "intermediate2": {"primary_ids": ["output2"], "was_resolved": False}
    }
    mock_client2 = MockStepClient(results=client2_results)
    
    # Mock client loading
    manager.client_manager = MagicMock()
    
    async def mock_get_client(resource):
        if resource.id == 1:
            return mock_client1
        elif resource.id == 2:
            return mock_client2
        return None
    
    manager.client_manager.get_client_instance = AsyncMock(side_effect=mock_get_client)
    
    # Execute the path
    results = await manager.execute_path(
        path=mock_path,
        input_identifiers=["input1", "input2"],
        source_ontology="SOURCE",
        target_ontology="TARGET"
    )
    
    # Verify results
    assert "input1" in results
    assert "input2" in results