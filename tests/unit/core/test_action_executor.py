"""Unit tests for the ActionExecutor module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from biomapper.core.engine_components.action_executor import ActionExecutor
from biomapper.core.exceptions import MappingExecutionError
from biomapper.db.models import MappingStrategyStep, Endpoint


class TestActionExecutor:
    """Test cases for ActionExecutor class."""
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock MappingExecutor instance."""
        return Mock()
    
    @pytest.fixture
    def action_executor(self, mock_mapping_executor):
        """Create an ActionExecutor instance for testing."""
        return ActionExecutor(mapping_executor=mock_mapping_executor)
    
    @pytest.fixture
    def mock_step(self):
        """Create a mock MappingStrategyStep."""
        step = Mock(spec=MappingStrategyStep)
        step.action_type = "TEST_ACTION"
        step.action_parameters = {"param1": "value1", "param2": 42}
        return step
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = Mock(spec=Endpoint)
        source.name = "test_source"
        
        target = Mock(spec=Endpoint)
        target.name = "test_target"
        
        return source, target
    
    @pytest.fixture
    def mock_action(self):
        """Create a mock action instance."""
        action = AsyncMock()
        action.execute = AsyncMock(return_value={
            "output_identifiers": ["id1", "id2"],
            "output_ontology_type": "TEST_ONTOLOGY",
            "details": {"processed": 2}
        })
        return action
    
    def test_init(self, action_executor, mock_mapping_executor):
        """Test ActionExecutor initialization."""
        assert action_executor.mapping_executor == mock_mapping_executor
        assert action_executor.action_loader is not None
        assert action_executor.logger is not None
    
    def test_process_action_parameters_simple(self, action_executor):
        """Test processing simple action parameters."""
        params = {"key1": "value1", "key2": 123}
        context = {}
        
        processed = action_executor._process_action_parameters(params, context)
        
        assert processed == params
    
    def test_process_action_parameters_context_reference(self, action_executor):
        """Test processing parameters with context references."""
        params = {
            "input_ids": "context.source_identifiers",
            "output_key": "context.results_key",
            "normal_param": "normal_value"
        }
        context = {"source_identifiers": ["id1", "id2"], "results_key": "output"}
        
        processed = action_executor._process_action_parameters(params, context)
        
        assert processed == {
            "input_ids": "source_identifiers",  # context. prefix removed
            "output_key": "results_key",  # context. prefix removed
            "normal_param": "normal_value"
        }
    
    def test_update_context_for_execution(self, action_executor):
        """Test updating context with execution parameters."""
        context = {"existing": "value"}
        db_session = Mock()
        
        action_executor._update_context_for_execution(
            context, db_session, True, 7, 1000, 0.8
        )
        
        assert context["db_session"] == db_session
        assert context["cache_settings"]["use_cache"] is True
        assert context["cache_settings"]["max_cache_age_days"] == 7
        assert context["batch_size"] == 1000
        assert context["min_confidence"] == 0.8
        assert context["existing"] == "value"  # Original values preserved
    
    def test_normalize_action_result_complete(self, action_executor):
        """Test normalizing action result that has all required fields."""
        result = {
            "output_identifiers": ["id1", "id2"],
            "output_ontology_type": "NEW_TYPE",
            "extra_field": "extra_value"
        }
        
        normalized = action_executor._normalize_action_result(
            result, ["old1", "old2"], "OLD_TYPE"
        )
        
        assert normalized == result  # No changes needed
    
    def test_normalize_action_result_missing_fields(self, action_executor):
        """Test normalizing action result with missing fields."""
        result = {"some_field": "value"}
        current_ids = ["id1", "id2"]
        current_type = "CURRENT_TYPE"
        
        normalized = action_executor._normalize_action_result(
            result, current_ids, current_type
        )
        
        assert normalized["output_identifiers"] == current_ids
        assert normalized["output_ontology_type"] == current_type
        assert normalized["some_field"] == "value"
    
    def test_normalize_action_result_with_input_identifiers(self, action_executor):
        """Test normalizing result that has input_identifiers but not output."""
        result = {
            "input_identifiers": ["input1", "input2"],
            "some_field": "value"
        }
        current_ids = ["current1", "current2"]
        
        normalized = action_executor._normalize_action_result(
            result, current_ids, "TYPE"
        )
        
        assert normalized["output_identifiers"] == ["input1", "input2"]
        assert normalized["output_ontology_type"] == "TYPE"
    
    @pytest.mark.asyncio
    async def test_execute_action_success(
        self, action_executor, mock_step, mock_endpoints, mock_action
    ):
        """Test successful action execution."""
        source_endpoint, target_endpoint = mock_endpoints
        current_ids = ["id1", "id2"]
        db_session = AsyncMock()
        context = {}
        
        with patch.object(action_executor.action_loader, 'instantiate_action', return_value=mock_action):
            result = await action_executor.execute_action(
                step=mock_step,
                current_identifiers=current_ids,
                current_ontology_type="SOURCE_TYPE",
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                use_cache=True,
                max_cache_age_days=7,
                batch_size=1000,
                min_confidence=0.8,
                strategy_context=context,
                db_session=db_session
            )
        
        # Verify action was called with correct parameters
        mock_action.execute.assert_called_once()
        call_kwargs = mock_action.execute.call_args.kwargs
        assert call_kwargs["current_identifiers"] == current_ids
        assert call_kwargs["current_ontology_type"] == "SOURCE_TYPE"
        assert call_kwargs["action_params"] == {"param1": "value1", "param2": 42}
        
        # Verify result
        assert result["output_identifiers"] == ["id1", "id2"]
        assert result["output_ontology_type"] == "TEST_ONTOLOGY"
    
    @pytest.mark.asyncio
    async def test_execute_action_with_context_references(
        self, action_executor, mock_endpoints, mock_action
    ):
        """Test action execution with context parameter references."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Create step with context references
        step = Mock(spec=MappingStrategyStep)
        step.action_type = "TEST_ACTION"
        step.action_parameters = {
            "input_key": "context.saved_ids",
            "output_key": "context.result_key"
        }
        
        context = {"saved_ids": ["ctx1", "ctx2"], "result_key": "output"}
        db_session = AsyncMock()
        
        with patch.object(action_executor.action_loader, 'instantiate_action', return_value=mock_action):
            result = await action_executor.execute_action(
                step=step,
                current_identifiers=["id1"],
                current_ontology_type="TYPE",
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                use_cache=False,
                max_cache_age_days=None,
                batch_size=100,
                min_confidence=0.5,
                strategy_context=context,
                db_session=db_session
            )
        
        # Verify processed parameters
        call_kwargs = mock_action.execute.call_args.kwargs
        assert call_kwargs["action_params"] == {
            "input_key": "saved_ids",
            "output_key": "result_key"
        }
    
    @pytest.mark.asyncio
    async def test_execute_action_load_failure(
        self, action_executor, mock_step, mock_endpoints
    ):
        """Test handling action load failure."""
        source_endpoint, target_endpoint = mock_endpoints
        db_session = AsyncMock()
        
        with patch.object(
            action_executor.action_loader,
            'instantiate_action',
            side_effect=Exception("Failed to load action")
        ):
            with pytest.raises(MappingExecutionError) as exc_info:
                await action_executor.execute_action(
                    step=mock_step,
                    current_identifiers=["id1"],
                    current_ontology_type="TYPE",
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    use_cache=True,
                    max_cache_age_days=None,
                    batch_size=1000,
                    min_confidence=0.0,
                    strategy_context={},
                    db_session=db_session
                )
            
            assert "Failed to load action 'TEST_ACTION'" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_action_execution_failure(
        self, action_executor, mock_step, mock_endpoints
    ):
        """Test handling action execution failure."""
        source_endpoint, target_endpoint = mock_endpoints
        db_session = AsyncMock()
        
        # Create failing action
        failing_action = AsyncMock()
        failing_action.execute = AsyncMock(side_effect=RuntimeError("Action failed"))
        
        with patch.object(action_executor.action_loader, 'instantiate_action', return_value=failing_action):
            with pytest.raises(MappingExecutionError) as exc_info:
                await action_executor.execute_action(
                    step=mock_step,
                    current_identifiers=["id1"],
                    current_ontology_type="TYPE",
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    use_cache=True,
                    max_cache_age_days=None,
                    batch_size=1000,
                    min_confidence=0.0,
                    strategy_context={},
                    db_session=db_session
                )
            
            assert "Strategy action TEST_ACTION failed" in str(exc_info.value)
            assert "Action failed" in str(exc_info.value)