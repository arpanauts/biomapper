"""Unit tests for the StrategyHandler module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from biomapper.core.engine_components.strategy_handler import StrategyHandler
from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError
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
    async def test_validate_strategy_steps_success(self, strategy_handler, mock_strategy):
        """Test successful strategy validation."""
        warnings = await strategy_handler.validate_strategy_steps(mock_strategy)
        
        # Should have no warnings for a valid strategy
        assert len(warnings) == 0
    
    @pytest.mark.asyncio
    async def test_validate_strategy_steps_no_steps(self, strategy_handler):
        """Test validation with strategy that has no steps."""
        strategy = Mock(spec=MappingStrategy)
        strategy.name = "empty_strategy"
        strategy.steps = []
        
        warnings = await strategy_handler.validate_strategy_steps(strategy)
        
        assert len(warnings) == 1
        assert "has no steps defined" in warnings[0]
    
    @pytest.mark.asyncio
    async def test_validate_strategy_steps_duplicate_orders(self, strategy_handler):
        """Test validation with duplicate step orders."""
        strategy = Mock(spec=MappingStrategy)
        strategy.name = "dup_strategy"
        
        step1 = Mock(spec=MappingStrategyStep)
        step1.step_order = 1
        step1.step_id = "S1"
        step1.action_type = "ACTION1"
        
        step2 = Mock(spec=MappingStrategyStep)
        step2.step_order = 1  # Duplicate order
        step2.step_id = "S2"
        step2.action_type = "ACTION2"
        
        strategy.steps = [step1, step2]
        
        warnings = await strategy_handler.validate_strategy_steps(strategy)
        
        assert len(warnings) == 1
        assert "duplicate step orders" in warnings[0]
    
    @pytest.mark.asyncio
    async def test_validate_strategy_steps_no_action_type(self, strategy_handler):
        """Test validation with step missing action type."""
        strategy = Mock(spec=MappingStrategy)
        strategy.name = "invalid_strategy"
        
        step = Mock(spec=MappingStrategyStep)
        step.step_order = 1
        step.step_id = "S1"
        step.action_type = None  # Missing action type
        step.is_active = True
        step.action_parameters = {}
        
        strategy.steps = [step]
        
        warnings = await strategy_handler.validate_strategy_steps(strategy)
        
        assert len(warnings) == 1
        assert "has no action type defined" in warnings[0]
    
    @pytest.mark.asyncio  
    async def test_validate_strategy_steps_active_no_params(self, strategy_handler):
        """Test validation with active step having no parameters (just a debug log)."""
        strategy = Mock(spec=MappingStrategy)
        strategy.name = "test_strategy"
        
        step = Mock(spec=MappingStrategyStep)
        step.step_order = 1
        step.step_id = "S1"
        step.action_type = "ACTION1"
        step.is_active = True
        step.action_parameters = None  # No parameters
        
        strategy.steps = [step]
        
        # Should not produce warnings, just debug log
        warnings = await strategy_handler.validate_strategy_steps(strategy)
        
        assert len(warnings) == 0
    
    
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


