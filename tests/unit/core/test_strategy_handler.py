"""Unit tests for the StrategyHandler module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from biomapper.core.engine_components.strategy_handler import StrategyHandler, get_current_utc_time
from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError,
    MappingExecutionError
)
from biomapper.db.models import MappingStrategy, MappingStrategyStep, Endpoint


class TestStrategyHandler:
    """Test cases for StrategyHandler class."""
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock MappingExecutor instance."""
        return Mock()
    
    @pytest.fixture
    def strategy_handler(self, mock_mapping_executor):
        """Create a StrategyHandler instance for testing."""
        return StrategyHandler(mapping_executor=mock_mapping_executor)
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_strategy(self):
        """Create a mock MappingStrategy."""
        strategy = Mock(spec=MappingStrategy)
        strategy.name = "test_strategy"
        strategy.is_active = True
        strategy.default_source_ontology_type = "SOURCE_TYPE"
        strategy.default_target_ontology_type = "TARGET_TYPE"
        
        # Create mock steps
        step1 = Mock(spec=MappingStrategyStep)
        step1.step_id = "S1"
        step1.step_order = 1
        step1.description = "Step 1"
        step1.action_type = "ACTION1"
        step1.is_active = True
        step1.is_required = True
        
        step2 = Mock(spec=MappingStrategyStep)
        step2.step_id = "S2"
        step2.step_order = 2
        step2.description = "Step 2"
        step2.action_type = "ACTION2"
        step2.is_active = True
        step2.is_required = False
        
        strategy.steps = [step1, step2]
        return strategy
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = Mock(spec=Endpoint)
        source.name = "test_source"
        
        target = Mock(spec=Endpoint)
        target.name = "test_target"
        
        return source, target
    
    def test_init(self, strategy_handler, mock_mapping_executor):
        """Test StrategyHandler initialization."""
        assert strategy_handler.mapping_executor == mock_mapping_executor
        assert strategy_handler.action_executor is not None
        assert strategy_handler.logger is not None
    
    @pytest.mark.asyncio
    async def test_load_strategy_success(self, strategy_handler, mock_session, mock_strategy):
        """Test successful strategy loading."""
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_strategy)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        strategy = await strategy_handler.load_strategy(mock_session, "test_strategy")
        
        assert strategy == mock_strategy
        assert mock_session.execute.called
    
    @pytest.mark.asyncio
    async def test_load_strategy_not_found(self, strategy_handler, mock_session):
        """Test loading non-existent strategy."""
        # Mock the database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(StrategyNotFoundError) as exc_info:
            await strategy_handler.load_strategy(mock_session, "missing_strategy")
        
        assert "Strategy 'missing_strategy' not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_load_strategy_inactive(self, strategy_handler, mock_session):
        """Test loading inactive strategy."""
        # Create inactive strategy
        inactive_strategy = Mock(spec=MappingStrategy)
        inactive_strategy.name = "inactive_strategy"
        inactive_strategy.is_active = False
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=inactive_strategy)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(InactiveStrategyError) as exc_info:
            await strategy_handler.load_strategy(mock_session, "inactive_strategy")
        
        assert "Strategy 'inactive_strategy' is not active" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_strategy_success(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test successful strategy execution."""
        source_endpoint, target_endpoint = mock_endpoints
        input_ids = ["id1", "id2", "id3"]
        
        # Mock action executor to return successful results
        mock_action_result = {
            "output_identifiers": ["out1", "out2"],
            "output_ontology_type": "INTERMEDIATE_TYPE",
            "details": {"processed": 2}
        }
        
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            return_value=mock_action_result
        ) as mock_execute:
            result = await strategy_handler.execute_strategy(
                session=mock_session,
                strategy=mock_strategy,
                input_identifiers=input_ids,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                use_cache=True,
                max_cache_age_days=7,
                batch_size=1000,
                min_confidence=0.8
            )
        
        # Verify result structure
        assert result["strategy_name"] == "test_strategy"
        assert result["execution_status"] == "completed"
        assert result["initial_count"] == 3
        assert result["final_count"] == 2  # Based on mock result
        assert len(result["step_results"]) == 2
        
        # Verify action executor was called for each step
        assert mock_execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_strategy_with_progress_callback(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test strategy execution with progress callback."""
        source_endpoint, target_endpoint = mock_endpoints
        progress_calls = []
        
        def progress_callback(step_idx, total_steps, message):
            progress_calls.append((step_idx, total_steps, message))
        
        initial_context = {"progress_callback": progress_callback}
        
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            return_value={"output_identifiers": ["out1"], "output_ontology_type": "TYPE"}
        ):
            await strategy_handler.execute_strategy(
                session=mock_session,
                strategy=mock_strategy,
                input_identifiers=["id1"],
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                initial_context=initial_context
            )
        
        # Verify progress callback was called
        assert len(progress_calls) == 2
        assert progress_calls[0] == (0, 2, "Executing S1")
        assert progress_calls[1] == (1, 2, "Executing S2")
    
    @pytest.mark.asyncio
    async def test_execute_strategy_skip_inactive_step(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test that inactive steps are skipped."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Make second step inactive
        mock_strategy.steps[1].is_active = False
        
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            return_value={"output_identifiers": ["out1"], "output_ontology_type": "TYPE"}
        ) as mock_execute:
            result = await strategy_handler.execute_strategy(
                session=mock_session,
                strategy=mock_strategy,
                input_identifiers=["id1"],
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint
            )
        
        # Only one step should be executed
        assert mock_execute.call_count == 1
        assert len(result["step_results"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_strategy_required_step_failure(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test that failure of required step stops execution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock action executor to fail on first step
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            side_effect=Exception("Step failed")
        ):
            with pytest.raises(MappingExecutionError) as exc_info:
                await strategy_handler.execute_strategy(
                    session=mock_session,
                    strategy=mock_strategy,
                    input_identifiers=["id1"],
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint
                )
            
            assert "Required step 'S1' failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_strategy_optional_step_failure(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test that failure of optional step continues execution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Make first step optional
        mock_strategy.steps[0].is_required = False
        
        # Mock action executor to fail on first step but succeed on second
        side_effects = [
            Exception("Step 1 failed"),
            {"output_identifiers": ["out1"], "output_ontology_type": "TYPE"}
        ]
        
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            side_effect=side_effects
        ):
            result = await strategy_handler.execute_strategy(
                session=mock_session,
                strategy=mock_strategy,
                input_identifiers=["id1"],
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint
            )
        
        # Execution should complete despite first step failure
        assert result["execution_status"] == "completed"
        assert len(result["step_results"]) == 2
        assert result["step_results"][0]["status"] == "failed"
        assert result["step_results"][1]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_execute_strategy_empty_identifiers_stops(
        self, strategy_handler, mock_session, mock_strategy, mock_endpoints
    ):
        """Test that execution stops when no identifiers remain."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock first step to return empty identifiers
        with patch.object(
            strategy_handler.action_executor,
            'execute_action',
            return_value={"output_identifiers": [], "output_ontology_type": "TYPE"}
        ) as mock_execute:
            result = await strategy_handler.execute_strategy(
                session=mock_session,
                strategy=mock_strategy,
                input_identifiers=["id1"],
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint
            )
        
        # Only first step should be executed
        assert mock_execute.call_count == 1
        assert result["final_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_endpoint_by_name(self, strategy_handler, mock_session):
        """Test getting endpoint by name."""
        mock_endpoint = Mock(spec=Endpoint)
        mock_endpoint.name = "test_endpoint"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_endpoint)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        endpoint = await strategy_handler.get_endpoint_by_name(mock_session, "test_endpoint")
        
        assert endpoint == mock_endpoint
        assert mock_session.execute.called


def test_get_current_utc_time():
    """Test get_current_utc_time function."""
    time_before = datetime.now(timezone.utc)
    result = get_current_utc_time()
    time_after = datetime.now(timezone.utc)
    
    assert time_before <= result <= time_after
    assert result.tzinfo == timezone.utc