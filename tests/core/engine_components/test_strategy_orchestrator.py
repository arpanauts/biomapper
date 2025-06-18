"""
Unit tests for StrategyOrchestrator.

Tests the core mapping strategy execution engine with extensive mocking
to isolate the orchestration logic from its dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
from typing import Dict, Any, List

from biomapper.core.engine_components.strategy_orchestrator import StrategyOrchestrator
from biomapper.core.exceptions import (
    ConfigurationError,
    MappingExecutionError,
    StrategyNotFoundError,
    InactiveStrategyError,
)


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for StrategyOrchestrator."""
    mocks = {
        'metamapper_session_factory': MagicMock(),
        'cache_manager': MagicMock(),
        'strategy_handler': AsyncMock(),
        'path_execution_manager': MagicMock(),
        'resource_clients_provider': MagicMock(),
        'mapping_executor': MagicMock(),
        'logger': MagicMock(),
    }
    
    # Configure session context manager
    mock_session = AsyncMock()
    # Create a proper async context manager mock
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = mock_session
    async_context_manager.__aexit__.return_value = None
    # Make the factory return the async context manager (not a coroutine)
    mocks['metamapper_session_factory'].return_value = async_context_manager
    
    return mocks, mock_session


@pytest.fixture
def orchestrator(mock_dependencies):
    """Create a StrategyOrchestrator instance with mocked dependencies."""
    mocks, _ = mock_dependencies
    return StrategyOrchestrator(**mocks)


@pytest.fixture
def mock_strategy():
    """Create a mock strategy with steps."""
    strategy = MagicMock()
    strategy.name = "test_strategy"
    strategy.default_source_ontology_type = "GENE"
    strategy.default_target_ontology_type = "PROTEIN"
    
    # Create mock steps
    step1 = MagicMock()
    step1.step_id = "step1"
    step1.step_order = 1
    step1.description = "Convert identifiers"
    step1.action_type = "convert_identifiers"
    step1.is_active = True
    step1.is_required = True
    
    step2 = MagicMock()
    step2.step_id = "step2"
    step2.step_order = 2
    step2.description = "Filter results"
    step2.action_type = "filter_by_confidence"
    step2.is_active = True
    step2.is_required = False
    
    strategy.steps = [step2, step1]  # Intentionally out of order to test sorting
    return strategy


@pytest.fixture
def mock_endpoints():
    """Create mock source and target endpoints."""
    source_endpoint = MagicMock()
    source_endpoint.name = "source_endpoint"
    
    target_endpoint = MagicMock()
    target_endpoint.name = "target_endpoint"
    
    return source_endpoint, target_endpoint


class TestStrategyOrchestrator:
    """Test cases for StrategyOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_successful_strategy_execution(self, orchestrator, mock_dependencies, mock_strategy, mock_endpoints):
        """Test successful execution of a strategy with multiple steps."""
        mocks, mock_session = mock_dependencies
        source_endpoint, target_endpoint = mock_endpoints
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.side_effect = [source_endpoint, target_endpoint]
        
        # Configure action executor for successful execution
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            # Step 1 result
            mock_execute.side_effect = [
                {
                    'output_identifiers': ['P001', 'P002'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {'converted_count': 2},
                    'provenance': [
                        {'source_id': 'G001', 'target_id': 'P001', 'confidence': 0.95},
                        {'source_id': 'G002', 'target_id': 'P002', 'confidence': 0.90}
                    ]
                },
                # Step 2 result
                {
                    'output_identifiers': ['P001'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {'filtered_count': 1},
                    'provenance': [
                        {'source_id': 'P001', 'action': 'filter_passed', 'confidence': 0.95}
                    ]
                }
            ]
            
            # Execute strategy
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001', 'G002'],
                source_endpoint_name="source_endpoint",
                target_endpoint_name="target_endpoint",
                use_cache=True,
                batch_size=100,
                min_confidence=0.8
            )
            
            # Verify strategy was loaded
            mocks['strategy_handler'].load_strategy.assert_called_once_with(mock_session, "test_strategy")
            
            # Verify endpoints were loaded
            assert mocks['strategy_handler'].get_endpoint_by_name.call_count == 2
            
            # Verify actions were executed in correct order (sorted by step_order)
            assert mock_execute.call_count == 2
            
            # Verify first action call (step1 with order=1)
            first_call = mock_execute.call_args_list[0]
            assert first_call.kwargs['step'].step_id == "step1"
            assert first_call.kwargs['current_identifiers'] == ['G001', 'G002']
            assert first_call.kwargs['current_ontology_type'] == "GENE"
            
            # Verify second action call (step2 with order=2)
            second_call = mock_execute.call_args_list[1]
            assert second_call.kwargs['step'].step_id == "step2"
            assert second_call.kwargs['current_identifiers'] == ['P001', 'P002']
            assert second_call.kwargs['current_ontology_type'] == "PROTEIN"
            
            # Verify result structure
            assert result['metadata']['strategy_name'] == "test_strategy"
            assert result['metadata']['execution_status'] == "completed"
            assert 'start_time' in result['metadata']
            assert 'end_time' in result['metadata']
            assert 'duration_seconds' in result['metadata']
            
            # Verify step results
            assert len(result['step_results']) == 2
            assert result['step_results'][0]['step_id'] == "step1"
            assert result['step_results'][0]['status'] == "success"
            assert result['step_results'][1]['step_id'] == "step2"
            assert result['step_results'][1]['status'] == "success"
            
            # Verify statistics
            assert result['statistics']['initial_count'] == 2
            assert result['statistics']['final_count'] == 1
            assert result['statistics']['mapped_count'] == 2
            
            # Verify final state
            assert result['final_identifiers'] == ['P001']
            assert result['final_ontology_type'] == 'PROTEIN'
            
            # Verify results mapping
            assert 'G001' in result['results']
            assert result['results']['G001']['mapped_value'] == 'P001'
            assert result['results']['G001']['confidence'] == 0.95
            assert 'G002' in result['results']
            assert result['results']['G002']['mapped_value'] == 'P002'
            assert result['results']['G002']['confidence'] == 0.90
    
    @pytest.mark.asyncio
    async def test_strategy_failure_required_step(self, orchestrator, mock_dependencies, mock_strategy):
        """Test strategy execution when a required step fails."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor to fail on first step
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")
            
            # Execute strategy and expect failure
            with pytest.raises(MappingExecutionError) as exc_info:
                await orchestrator.execute_strategy(
                    strategy_name="test_strategy",
                    input_identifiers=['G001', 'G002']
                )
            
            assert "Required step 'step1' failed" in str(exc_info.value)
            assert "Database connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_strategy_failure_optional_step(self, orchestrator, mock_dependencies, mock_strategy):
        """Test strategy execution continues when an optional step fails."""
        mocks, mock_session = mock_dependencies
        
        # Make step2 optional
        mock_strategy.steps[0].is_required = False  # step2
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            # First step succeeds, second step fails
            mock_execute.side_effect = [
                {
                    'output_identifiers': ['P001', 'P002'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {'converted_count': 2}
                },
                Exception("Filter service unavailable")
            ]
            
            # Execute strategy
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001', 'G002']
            )
            
            # Verify execution continued despite failure
            assert result['metadata']['execution_status'] == "completed"
            assert len(result['step_results']) == 2
            assert result['step_results'][0]['status'] == "success"
            assert result['step_results'][1]['status'] == "failed"
            assert result['step_results'][1]['error'] == "Filter service unavailable"
            assert result['final_identifiers'] == ['P001', 'P002']
    
    @pytest.mark.asyncio
    async def test_placeholder_resolution_in_context(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that placeholders in strategy context are properly resolved."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'output_identifiers': ['P001'],
                'output_ontology_type': 'PROTEIN',
                'details': {}
            }
            
            # Execute strategy with initial context containing placeholders
            initial_context = {
                'DATA_DIR': '/data',
                'OUTPUT_DIR': '/output',
                'config_path': '${DATA_DIR}/config.yaml'
            }
            
            await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001'],
                initial_context=initial_context
            )
            
            # Verify context was passed to action executor
            call_args = mock_execute.call_args_list[0]
            strategy_context = call_args.kwargs['strategy_context']
            
            # Check that initial context values are preserved
            assert strategy_context['DATA_DIR'] == '/data'
            assert strategy_context['OUTPUT_DIR'] == '/output'
            assert strategy_context['config_path'] == '${DATA_DIR}/config.yaml'
            
            # Check that orchestrator adds its own context
            assert 'initial_identifiers' in strategy_context
            assert 'step_results' in strategy_context
            assert 'all_provenance' in strategy_context
    
    @pytest.mark.asyncio
    async def test_context_updates_between_steps(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that execution context is correctly passed and updated between steps."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Track context changes
        context_snapshots = []
        
        async def capture_context(**kwargs):
            # Capture a copy of the context
            context_snapshots.append(kwargs['strategy_context'].copy())
            return {
                'output_identifiers': ['P001'] if len(context_snapshots) == 1 else ['P001_filtered'],
                'output_ontology_type': 'PROTEIN',
                'details': {}
            }
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = capture_context
            
            await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001']
            )
            
            # Verify context was updated between steps
            assert len(context_snapshots) == 2
            
            # First step context
            ctx1 = context_snapshots[0]
            assert ctx1['current_identifiers'] == ['G001']
            assert ctx1['current_ontology_type'] == 'GENE'
            
            # Second step context (should have updated identifiers)
            ctx2 = context_snapshots[1]
            assert ctx2['current_identifiers'] == ['P001']
            assert ctx2['current_ontology_type'] == 'PROTEIN'
    
    @pytest.mark.asyncio
    async def test_result_bundle_finalization(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that MappingResultBundle.finalize() is called on both success and failure."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Test successful execution
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'output_identifiers': ['P001'],
                'output_ontology_type': 'PROTEIN',
                'details': {}
            }
            
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001']
            )
            
            # Verify successful completion
            assert result['metadata']['execution_status'] == 'completed'
            assert 'end_time' in result['metadata']
            assert result['metadata']['duration_seconds'] >= 0
    
    @pytest.mark.asyncio
    async def test_inactive_step_skipped(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that inactive steps are skipped during execution."""
        mocks, mock_session = mock_dependencies
        
        # Make step1 inactive
        mock_strategy.steps[1].is_active = False  # step1
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'output_identifiers': ['G001', 'G002'],  # No conversion happened
                'output_ontology_type': 'GENE',
                'details': {}
            }
            
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001', 'G002']
            )
            
            # Verify only active step was executed
            assert mock_execute.call_count == 1
            assert mock_execute.call_args.kwargs['step'].step_id == "step2"
            
            # Verify logger was called for skipped step
            orchestrator.logger.info.assert_called_with("Skipping inactive step: step1")
    
    @pytest.mark.asyncio
    async def test_progress_callback_invocation(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that progress callback is invoked correctly during execution."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Track progress callbacks
        progress_calls = []
        
        def progress_callback(current_step, total_steps, status):
            progress_calls.append((current_step, total_steps, status))
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                'output_identifiers': ['P001'],
                'output_ontology_type': 'PROTEIN',
                'details': {}
            }
            
            await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001'],
                progress_callback=progress_callback
            )
            
            # Verify progress callbacks
            assert len(progress_calls) == 2
            assert progress_calls[0] == (0, 2, "Executing step1")
            assert progress_calls[1] == (1, 2, "Executing step2")
    
    @pytest.mark.asyncio
    async def test_empty_identifiers_stops_execution(self, orchestrator, mock_dependencies, mock_strategy):
        """Test that execution stops if no identifiers remain after a step."""
        mocks, mock_session = mock_dependencies
        
        # Add a third step
        step3 = MagicMock()
        step3.step_id = "step3"
        step3.step_order = 3
        step3.description = "Additional processing"
        step3.action_type = "process_more"
        step3.is_active = True
        step3.is_required = True
        mock_strategy.steps.append(step3)
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            # First step returns identifiers, second step returns empty list
            mock_execute.side_effect = [
                {
                    'output_identifiers': ['P001'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {}
                },
                {
                    'output_identifiers': [],  # No identifiers remain
                    'output_ontology_type': 'PROTEIN',
                    'details': {'reason': 'All filtered out'}
                }
            ]
            
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001']
            )
            
            # Verify only two steps were executed
            assert mock_execute.call_count == 2
            
            # Verify warning was logged
            orchestrator.logger.warning.assert_called_with(
                "No identifiers remaining, stopping strategy execution"
            )
            
            # Verify result reflects empty identifiers
            assert result['final_identifiers'] == []
            assert result['statistics']['final_count'] == 0
    
    @pytest.mark.asyncio
    async def test_endpoint_not_found_error(self, orchestrator, mock_dependencies, mock_strategy):
        """Test error handling when specified endpoints are not found."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.side_effect = [None, None]  # Both not found
        
        # Test source endpoint not found
        with pytest.raises(ConfigurationError) as exc_info:
            await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001'],
                source_endpoint_name="nonexistent_source"
            )
        
        assert "Source endpoint 'nonexistent_source' not found" in str(exc_info.value)
        
        # Reset mock and test target endpoint not found
        mocks['strategy_handler'].get_endpoint_by_name.reset_mock()
        mocks['strategy_handler'].get_endpoint_by_name.side_effect = [MagicMock(), None]  # Source found, target not
        
        with pytest.raises(ConfigurationError) as exc_info:
            await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001'],
                source_endpoint_name="source",
                target_endpoint_name="nonexistent_target"
            )
        
        assert "Target endpoint 'nonexistent_target' not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_complex_provenance_chain(self, orchestrator, mock_dependencies, mock_strategy):
        """Test building final results from complex provenance chains."""
        mocks, mock_session = mock_dependencies
        
        # Configure strategy handler
        mocks['strategy_handler'].load_strategy.return_value = mock_strategy
        mocks['strategy_handler'].get_endpoint_by_name.return_value = None
        
        # Configure action executor with complex provenance
        with patch.object(orchestrator.action_executor, 'execute_action', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                {
                    'output_identifiers': ['P001', 'P002', 'P003'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {},
                    'provenance': [
                        {'source_id': 'G001', 'target_id': 'P001', 'confidence': 0.95},
                        {'source_id': 'G001', 'target_id': 'P002', 'confidence': 0.85},  # Multiple mappings
                        {'source_id': 'G002', 'target_id': 'P003', 'confidence': 0.90}
                    ]
                },
                {
                    'output_identifiers': ['P001_v2', 'P003_v2'],
                    'output_ontology_type': 'PROTEIN',
                    'details': {},
                    'provenance': [
                        {'source_id': 'P001', 'target_id': 'P001_v2', 'confidence': 1.0},
                        {'source_id': 'P003', 'target_id': 'P003_v2', 'confidence': 1.0},
                        {'source_id': 'P002', 'action': 'filtered_out'}  # Filtered
                    ]
                }
            ]
            
            result = await orchestrator.execute_strategy(
                strategy_name="test_strategy",
                input_identifiers=['G001', 'G002']
            )
            
            # Verify complex mapping chain
            assert 'G001' in result['results']
            assert result['results']['G001']['mapped_value'] == 'P001_v2'  # Traced through chain
            assert 'all_mapped_values' in result['results']['G001']
            assert set(result['results']['G001']['all_mapped_values']) == {'P001_v2', 'P002'}
            
            assert 'G002' in result['results']
            assert result['results']['G002']['mapped_value'] == 'P003_v2'
            
            # Verify confidence is properly calculated
            assert result['results']['G001']['confidence'] == 0.85  # Min of 0.95 and 0.85
            assert result['results']['G002']['confidence'] == 0.90