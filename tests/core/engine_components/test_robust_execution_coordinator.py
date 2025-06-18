"""
Unit tests for RobustExecutionCoordinator.

This module tests the robust lifecycle management of strategy execution,
including interaction with StrategyOrchestrator, CheckpointManager, and ProgressReporter.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from typing import Dict, Any, List

from biomapper.core.engine_components.robust_execution_coordinator import RobustExecutionCoordinator
from biomapper.core.exceptions import MappingExecutionError


class TestRobustExecutionCoordinatorInit:
    """Test cases for RobustExecutionCoordinator initialization."""
    
    def test_init_with_all_parameters(self):
        """Test initialization with all parameters provided."""
        # Arrange
        strategy_orchestrator = Mock()
        checkpoint_manager = Mock()
        progress_reporter = Mock()
        logger = Mock()
        
        # Act
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            batch_size=50,
            max_retries=5,
            retry_delay=10,
            checkpoint_enabled=True,
            logger=logger
        )
        
        # Assert
        assert coordinator.strategy_orchestrator is strategy_orchestrator
        assert coordinator.checkpoint_manager is checkpoint_manager
        assert coordinator.progress_reporter is progress_reporter
        assert coordinator.batch_size == 50
        assert coordinator.max_retries == 5
        assert coordinator.retry_delay == 10
        assert coordinator.checkpoint_enabled is True
        assert coordinator.logger is logger
        
    def test_init_with_default_parameters(self):
        """Test initialization with minimal required parameters."""
        # Arrange
        strategy_orchestrator = Mock()
        checkpoint_manager = Mock()
        progress_reporter = Mock()
        
        # Act
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter
        )
        
        # Assert
        assert coordinator.strategy_orchestrator is strategy_orchestrator
        assert coordinator.checkpoint_manager is checkpoint_manager
        assert coordinator.progress_reporter is progress_reporter
        assert coordinator.batch_size == 100  # default
        assert coordinator.max_retries == 3   # default
        assert coordinator.retry_delay == 5   # default
        assert coordinator.checkpoint_enabled is False  # default
        assert coordinator.logger is not None  # should create default logger


class TestRobustExecutionCoordinatorExecuteStrategyRobustly:
    """Test cases for execute_strategy_robustly method."""
    
    @pytest.fixture
    def coordinator_setup(self):
        """Set up coordinator with mocked dependencies."""
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        logger = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            checkpoint_enabled=True,
            logger=logger
        )
        
        return {
            'coordinator': coordinator,
            'strategy_orchestrator': strategy_orchestrator,
            'checkpoint_manager': checkpoint_manager,
            'progress_reporter': progress_reporter,
            'logger': logger
        }
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_checkpoint(self, coordinator_setup):
        """Test successful execution without checkpoint resumption."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        progress_reporter = setup['progress_reporter']
        
        # Mock checkpoint manager to return None (no checkpoint)
        checkpoint_manager.load_checkpoint.return_value = None
        
        # Mock successful strategy execution
        expected_result = {
            'results': [{'id': '1', 'mapped': 'A'}, {'id': '2', 'mapped': 'B'}],
            'metadata': {'source': 'test', 'total': 2}
        }
        strategy_orchestrator.execute_strategy.return_value = expected_result
        
        # Act
        result = await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1', 'id2'],
            resume_from_checkpoint=False
        )
        
        # Assert - checkpoint operations
        checkpoint_manager.load_checkpoint.assert_not_called()
        checkpoint_manager.clear_checkpoint.assert_called_once()
        
        # Assert - strategy execution
        strategy_orchestrator.execute_strategy.assert_called_once()
        call_args = strategy_orchestrator.execute_strategy.call_args[1]
        assert call_args['strategy_name'] == 'test_strategy'
        assert call_args['input_identifiers'] == ['id1', 'id2']
        
        # Assert - progress reporting
        assert progress_reporter.report.call_count == 2  # start and success
        start_call = progress_reporter.report.call_args_list[0][0][0]
        success_call = progress_reporter.report.call_args_list[1][0][0]
        
        assert start_call['type'] == 'execution_started'
        assert start_call['strategy'] == 'test_strategy'
        assert start_call['input_count'] == 2
        assert start_call['checkpoint_resumed'] is False
        
        assert success_call['type'] == 'execution_completed'
        assert success_call['strategy'] == 'test_strategy'
        
        # Assert - result structure
        assert 'robust_execution' in result
        robust_metadata = result['robust_execution']
        assert 'execution_id' in robust_metadata
        assert robust_metadata['checkpointing_enabled'] is True
        assert robust_metadata['checkpoint_used'] is False
        assert robust_metadata['retries_configured'] == 3
        assert robust_metadata['batch_size'] == 100
        
    @pytest.mark.asyncio
    async def test_successful_execution_with_checkpoint(self, coordinator_setup):
        """Test successful execution resuming from checkpoint."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        progress_reporter = setup['progress_reporter']
        
        # Mock checkpoint manager to return checkpoint state
        checkpoint_state = {
            'processed_items': ['id1'],
            'remaining_items': ['id2'],
            'checkpoint_time': '2023-01-01T12:00:00'
        }
        checkpoint_manager.load_checkpoint.return_value = checkpoint_state
        
        # Mock successful strategy execution
        expected_result = {
            'results': [{'id': '2', 'mapped': 'B'}],
            'metadata': {'source': 'test', 'total': 1}
        }
        strategy_orchestrator.execute_strategy.return_value = expected_result
        
        # Act
        result = await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1', 'id2'],
            resume_from_checkpoint=True
        )
        
        # Assert - checkpoint operations
        checkpoint_manager.load_checkpoint.assert_called_once()
        checkpoint_manager.clear_checkpoint.assert_called_once()
        
        # Assert - progress reporting includes checkpoint info
        start_call = progress_reporter.report.call_args_list[0][0][0]
        assert start_call['checkpoint_resumed'] is True
        
        # Assert - result metadata
        robust_metadata = result['robust_execution']
        assert robust_metadata['checkpoint_used'] is True
        
    @pytest.mark.asyncio
    async def test_execution_failure_no_checkpoint_save(self, coordinator_setup):
        """Test execution failure early in process (no checkpoint to save)."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        progress_reporter = setup['progress_reporter']
        
        # Mock no existing checkpoint
        checkpoint_manager.load_checkpoint.return_value = None
        checkpoint_manager.current_checkpoint_file = None
        
        # Mock strategy execution failure
        execution_error = Exception("Strategy execution failed")
        strategy_orchestrator.execute_strategy.side_effect = execution_error
        
        # Act & Assert
        with pytest.raises(MappingExecutionError) as exc_info:
            await coordinator.execute_strategy_robustly(
                strategy_name='test_strategy',
                input_identifiers=['id1', 'id2']
            )
        
        # Assert exception details
        assert "Strategy execution failed: test_strategy" in str(exc_info.value)
        assert exc_info.value.details['checkpoint_available'] is False
        assert exc_info.value.details['error'] == "Strategy execution failed"
        
        # Assert progress reporting
        failure_call = progress_reporter.report.call_args_list[1][0][0]
        assert failure_call['type'] == 'execution_failed'
        assert failure_call['strategy'] == 'test_strategy'
        assert failure_call['error'] == "Strategy execution failed"
        assert failure_call['checkpoint_available'] is False
        
    @pytest.mark.asyncio
    async def test_execution_failure_with_checkpoint_available(self, coordinator_setup):
        """Test execution failure when checkpoint file exists."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        progress_reporter = setup['progress_reporter']
        
        # Mock no existing checkpoint initially
        checkpoint_manager.load_checkpoint.return_value = None
        # Mock that checkpoint file exists (simulating partial progress)
        checkpoint_manager.current_checkpoint_file = '/path/to/checkpoint.file'
        
        # Mock strategy execution failure
        execution_error = Exception("Strategy execution failed mid-process")
        strategy_orchestrator.execute_strategy.side_effect = execution_error
        
        # Act & Assert
        with pytest.raises(MappingExecutionError) as exc_info:
            await coordinator.execute_strategy_robustly(
                strategy_name='test_strategy',
                input_identifiers=['id1', 'id2']
            )
        
        # Assert exception details
        assert exc_info.value.details['checkpoint_available'] is True
        
        # Assert progress reporting
        failure_call = progress_reporter.report.call_args_list[1][0][0]
        assert failure_call['checkpoint_available'] is True
        
    @pytest.mark.asyncio
    async def test_execution_id_generation(self, coordinator_setup):
        """Test that execution ID is generated when not provided."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        # Act
        with patch('biomapper.core.engine_components.robust_execution_coordinator.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value.strftime.return_value = '20230101_120000'
            
            result = await coordinator.execute_strategy_robustly(
                strategy_name='test_strategy',
                input_identifiers=['id1']
            )
        
        # Assert
        expected_execution_id = 'test_strategy_20230101_120000'
        assert result['robust_execution']['execution_id'] == expected_execution_id
        checkpoint_manager.clear_checkpoint.assert_called_with(expected_execution_id)
        
    @pytest.mark.asyncio
    async def test_execution_id_provided(self, coordinator_setup):
        """Test that provided execution ID is used."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        custom_execution_id = 'custom_execution_123'
        
        # Act
        result = await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1'],
            execution_id=custom_execution_id
        )
        
        # Assert
        assert result['robust_execution']['execution_id'] == custom_execution_id
        checkpoint_manager.clear_checkpoint.assert_called_with(custom_execution_id)
        
    @pytest.mark.asyncio
    async def test_checkpoint_disabled_no_operations(self, coordinator_setup):
        """Test that checkpoint operations are skipped when checkpointing is disabled."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        coordinator.checkpoint_enabled = False  # Disable checkpointing
        
        strategy_orchestrator = setup['strategy_orchestrator']
        checkpoint_manager = setup['checkpoint_manager']
        
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        # Act
        result = await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1'],
            resume_from_checkpoint=True  # Should be ignored
        )
        
        # Assert
        checkpoint_manager.load_checkpoint.assert_not_called()
        checkpoint_manager.clear_checkpoint.assert_not_called()
        
        # But robust metadata should still indicate checkpointing status
        assert result['robust_execution']['checkpointing_enabled'] is False
        assert result['robust_execution']['checkpoint_used'] is False


class TestRobustExecutionCoordinatorExecuteWithRetry:
    """Test cases for execute_with_retry method."""
    
    @pytest.fixture
    def coordinator_setup(self):
        """Set up coordinator with mocked dependencies."""
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        logger = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            max_retries=2,  # Set to 2 for easier testing
            retry_delay=0.1,  # Short delay for tests
            logger=logger
        )
        
        return {
            'coordinator': coordinator,
            'strategy_orchestrator': strategy_orchestrator,
            'checkpoint_manager': checkpoint_manager,
            'progress_reporter': progress_reporter,
            'logger': logger
        }
    
    @pytest.mark.asyncio
    async def test_successful_execution_first_attempt(self, coordinator_setup):
        """Test successful execution on first attempt."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        
        expected_result = {'results': [{'id': '1', 'mapped': 'A'}]}
        
        # Mock execute_strategy_robustly to succeed on first call
        with patch.object(coordinator, 'execute_strategy_robustly', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = expected_result
            
            # Act
            result = await coordinator.execute_with_retry(
                strategy_name='test_strategy',
                input_identifiers=['id1']
            )
        
        # Assert
        assert result == expected_result
        mock_execute.assert_called_once_with(
            strategy_name='test_strategy',
            input_identifiers=['id1']
        )
        
    @pytest.mark.asyncio
    async def test_successful_execution_after_retries(self, coordinator_setup):
        """Test successful execution after some failed attempts."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        progress_reporter = setup['progress_reporter']
        
        expected_result = {'results': [{'id': '1', 'mapped': 'A'}]}
        
        # Mock execute_strategy_robustly to fail twice, then succeed
        with patch.object(coordinator, 'execute_strategy_robustly', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                Exception("First attempt failed"),
                Exception("Second attempt failed"),
                expected_result  # Third attempt succeeds
            ]
            
            # Act
            result = await coordinator.execute_with_retry(
                strategy_name='test_strategy',
                input_identifiers=['id1']
            )
        
        # Assert
        assert result == expected_result
        assert mock_execute.call_count == 3
        
        # Check retry reporting
        retry_calls = [call for call in progress_reporter.report.call_args_list 
                      if call[0][0].get('type') == 'execution_retry']
        assert len(retry_calls) == 2  # Two retry reports
        
        # Check first retry report
        first_retry = retry_calls[0][0][0]
        assert first_retry['attempt'] == 1
        assert first_retry['max_retries'] == 2
        assert first_retry['error'] == "First attempt failed"
        
    @pytest.mark.asyncio
    async def test_permanent_failure_after_max_retries(self, coordinator_setup):
        """Test permanent failure after exhausting all retries."""
        # Arrange
        setup = coordinator_setup
        coordinator = setup['coordinator']
        progress_reporter = setup['progress_reporter']
        
        # Mock execute_strategy_robustly to always fail
        with patch.object(coordinator, 'execute_strategy_robustly', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Persistent failure")
            
            # Act & Assert
            with pytest.raises(MappingExecutionError) as exc_info:
                await coordinator.execute_with_retry(
                    strategy_name='test_strategy',
                    input_identifiers=['id1']
                )
        
        # Assert exception details
        assert "Strategy execution failed after 3 attempts" in str(exc_info.value)
        assert exc_info.value.details['attempts'] == 3  # Initial + 2 retries
        assert exc_info.value.details['final_error'] == "Persistent failure"
        
        # Assert all attempts were made
        assert mock_execute.call_count == 3  # Initial + 2 retries
        
        # Check retry reporting (should have 2 retry reports before final failure)
        retry_calls = [call for call in progress_reporter.report.call_args_list 
                      if call[0][0].get('type') == 'execution_retry']
        assert len(retry_calls) == 2


class TestRobustExecutionCoordinatorInteractionWithDependencies:
    """Test correct interaction with all mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_correct_method_call_order_success(self):
        """Test that dependencies are called in the correct order during successful execution."""
        # Arrange
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            checkpoint_enabled=True
        )
        
        # Setup return values
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        # Act
        await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1']
        )
        
        # Assert call order by checking call counts at different points
        # This is a simplified check - in a real scenario, you might use more sophisticated ordering checks
        checkpoint_manager.load_checkpoint.assert_called_once()
        strategy_orchestrator.execute_strategy.assert_called_once()
        checkpoint_manager.clear_checkpoint.assert_called_once()
        
        # Progress reporter should be called twice (start and success)
        assert progress_reporter.report.call_count == 2
        
    @pytest.mark.asyncio
    async def test_checkpoint_manager_called_with_correct_arguments(self):
        """Test that CheckpointManager methods are called with expected arguments."""
        # Arrange
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter,
            checkpoint_enabled=True
        )
        
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        execution_id = 'test_execution_123'
        
        # Act
        await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1'],
            execution_id=execution_id
        )
        
        # Assert
        checkpoint_manager.load_checkpoint.assert_called_once_with(execution_id)
        checkpoint_manager.clear_checkpoint.assert_called_once_with(execution_id)
        
    @pytest.mark.asyncio
    async def test_strategy_orchestrator_called_with_correct_arguments(self):
        """Test that StrategyOrchestrator is called with expected arguments."""
        # Arrange
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter
        )
        
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {'results': []}
        
        # Act
        await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1', 'id2'],
            source_endpoint_name='source_ep',
            target_endpoint_name='target_ep',
            custom_param='custom_value'
        )
        
        # Assert
        strategy_orchestrator.execute_strategy.assert_called_once()
        call_kwargs = strategy_orchestrator.execute_strategy.call_args[1]
        
        assert call_kwargs['strategy_name'] == 'test_strategy'
        assert call_kwargs['input_identifiers'] == ['id1', 'id2']
        assert call_kwargs['source_endpoint_name'] == 'source_ep'
        assert call_kwargs['target_endpoint_name'] == 'target_ep'
        assert call_kwargs['custom_param'] == 'custom_value'
        
    @pytest.mark.asyncio
    async def test_progress_reporter_called_with_correct_data(self):
        """Test that ProgressReporter receives correctly structured progress data."""
        # Arrange
        strategy_orchestrator = AsyncMock()
        checkpoint_manager = AsyncMock()
        progress_reporter = Mock()
        
        coordinator = RobustExecutionCoordinator(
            strategy_orchestrator=strategy_orchestrator,
            checkpoint_manager=checkpoint_manager,
            progress_reporter=progress_reporter
        )
        
        checkpoint_manager.load_checkpoint.return_value = None
        strategy_orchestrator.execute_strategy.return_value = {
            'results': [{'id': '1'}, {'id': '2'}]
        }
        
        execution_id = 'test_execution_123'
        
        # Act
        await coordinator.execute_strategy_robustly(
            strategy_name='test_strategy',
            input_identifiers=['id1', 'id2'],
            execution_id=execution_id
        )
        
        # Assert progress reports
        assert progress_reporter.report.call_count == 2
        
        # Check start report
        start_report = progress_reporter.report.call_args_list[0][0][0]
        expected_start_keys = {'type', 'execution_id', 'strategy', 'input_count', 'checkpoint_resumed'}
        assert set(start_report.keys()) == expected_start_keys
        assert start_report['type'] == 'execution_started'
        assert start_report['execution_id'] == execution_id
        assert start_report['strategy'] == 'test_strategy'
        assert start_report['input_count'] == 2
        
        # Check success report
        success_report = progress_reporter.report.call_args_list[1][0][0]
        expected_success_keys = {'type', 'execution_id', 'strategy', 'execution_time', 'results_count'}
        assert set(success_report.keys()) == expected_success_keys
        assert success_report['type'] == 'execution_completed'
        assert success_report['execution_id'] == execution_id
        assert success_report['strategy'] == 'test_strategy'
        assert success_report['results_count'] == 2
        assert isinstance(success_report['execution_time'], float)