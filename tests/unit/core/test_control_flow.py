"""Comprehensive tests for control flow features in YAML strategies."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import json
from pathlib import Path
import tempfile

from biomapper.core.models.enhanced_strategy import EnhancedStrategy, EnhancedStepDefinition
from biomapper.core.models.control_flow import (
    Condition, ConditionType, ErrorHandling, ErrorAction,
    LoopConfig, BackoffStrategy, ExecutionMode
)
from biomapper.core.services.control_flow_executor import ControlFlowExecutor, StepExecutionError
from biomapper.core.services.expression_evaluator import SafeExpressionEvaluator, ConditionEvaluator


class TestSafeExpressionEvaluator:
    """Test the safe expression evaluator."""
    
    def test_simple_comparison(self):
        """Test simple comparison expressions."""
        context = {'score': 0.8}
        evaluator = SafeExpressionEvaluator(context)
        
        assert evaluator.evaluate("${score} > 0.5") == True
        assert evaluator.evaluate("${score} < 0.5") == False
        assert evaluator.evaluate("${score} == 0.8") == True
    
    def test_nested_variables(self):
        """Test nested variable resolution."""
        context = {
            'steps': {
                'baseline': {
                    'metrics': {
                        'score': 0.75,
                        'count': 100
                    }
                }
            }
        }
        evaluator = SafeExpressionEvaluator(context)
        
        assert evaluator.evaluate("${steps.baseline.metrics.score} > 0.7") == True
        assert evaluator.evaluate("${steps.baseline.metrics.count} == 100") == True
    
    def test_arithmetic_operations(self):
        """Test arithmetic in expressions."""
        context = {'threshold': 0.8, 'adjustment': 0.1}
        evaluator = SafeExpressionEvaluator(context)
        
        assert abs(evaluator.evaluate("${threshold} * 0.9") - 0.72) < 0.0001  # Handle floating point precision
        assert evaluator.evaluate("${threshold} + ${adjustment}") == 0.9
        assert abs(evaluator.evaluate("${threshold} - ${adjustment}") - 0.7) < 0.0001
    
    def test_logical_operations(self):
        """Test logical operations."""
        context = {'enabled': True, 'score': 0.8}
        evaluator = SafeExpressionEvaluator(context)
        
        assert evaluator.evaluate("${enabled} and ${score} > 0.5") == True
        assert evaluator.evaluate("${enabled} or ${score} < 0.5") == True
        assert evaluator.evaluate("not ${enabled}") == False
    
    def test_ternary_operator(self):
        """Test ternary operator conversion."""
        context = {'size': 1500}
        evaluator = SafeExpressionEvaluator(context)
        
        # Should return 0.9 when size > 1000
        result = evaluator.evaluate("${size} > 1000 ? 0.9 : 1.0")
        assert result == 0.9
        
        # Should return 1.0 when size <= 1000
        context['size'] = 500
        evaluator = SafeExpressionEvaluator(context)  # Create new evaluator with updated context
        result = evaluator.evaluate("${size} > 1000 ? 0.9 : 1.0")
        assert result == 1.0
    
    def test_array_indexing(self):
        """Test array indexing in expressions."""
        context = {
            'datasets': [
                {'name': 'dataset1', 'size': 100},
                {'name': 'dataset2', 'size': 200}
            ]
        }
        evaluator = SafeExpressionEvaluator(context)
        
        assert evaluator.evaluate("${datasets[0].size}") == 100
        assert evaluator.evaluate("${datasets[1].name}") == 'dataset2'
    
    def test_safe_functions(self):
        """Test safe built-in functions."""
        context = {'values': [1, 2, 3, 4, 5]}
        evaluator = SafeExpressionEvaluator(context)
        
        assert evaluator.evaluate("len(${values})") == 5
        assert evaluator.evaluate("sum(${values})") == 15
        assert evaluator.evaluate("max(${values})") == 5
        assert evaluator.evaluate("min(${values})") == 1
    
    def test_dangerous_code_rejection(self):
        """Test that dangerous code is rejected."""
        context = {}
        evaluator = SafeExpressionEvaluator(context)
        
        with pytest.raises(Exception):
            evaluator.evaluate("__import__('os').system('ls')")
        
        with pytest.raises(Exception):
            evaluator.evaluate("exec('print(1)')")
        
        with pytest.raises(Exception):
            evaluator.evaluate("eval('1+1')")
    
    def test_default_values(self):
        """Test default values for missing variables."""
        context = {}
        evaluator = SafeExpressionEvaluator(context)
        
        # Test with default value syntax - the result will be a string representation
        result = evaluator.evaluate("${missing_var:-'default'}")
        assert result == "'default'"  # Will return the quoted string
        
        result = evaluator.evaluate("${missing_num:-100}")
        assert result == 100


class TestConditionEvaluator:
    """Test the condition evaluator."""
    
    def test_simple_condition(self):
        """Test simple string condition."""
        context = {'score': 0.8}
        evaluator = ConditionEvaluator(context)
        
        assert evaluator.evaluate_condition("${score} > 0.5") == True
        assert evaluator.evaluate_condition("${score} < 0.5") == False
    
    def test_all_condition(self):
        """Test ALL (AND) condition."""
        context = {'a': True, 'b': True, 'c': False}
        evaluator = ConditionEvaluator(context)
        
        condition = {
            'type': 'all',
            'all': [
                "${a} == True",
                "${b} == True"
            ]
        }
        assert evaluator.evaluate_condition(condition) == True
        
        condition['all'].append("${c} == True")
        assert evaluator.evaluate_condition(condition) == False
    
    def test_any_condition(self):
        """Test ANY (OR) condition."""
        context = {'a': False, 'b': False, 'c': True}
        evaluator = ConditionEvaluator(context)
        
        condition = {
            'type': 'any',
            'any': [
                "${a} == True",
                "${b} == True",
                "${c} == True"
            ]
        }
        assert evaluator.evaluate_condition(condition) == True
        
        # Update context through evaluator
        evaluator.context['c'] = False
        assert evaluator.evaluate_condition(condition) == False
    
    def test_nested_conditions(self):
        """Test nested conditions."""
        context = {'a': True, 'b': False, 'c': True, 'd': True}
        evaluator = ConditionEvaluator(context)
        
        condition = {
            'type': 'all',
            'all': [
                "${a} == True",
                {
                    'type': 'any',
                    'any': [
                        "${b} == True",
                        "${c} == True"
                    ]
                },
                "${d} == True"
            ]
        }
        assert evaluator.evaluate_condition(condition) == True


@pytest.mark.asyncio
class TestControlFlowExecutor:
    """Test the control flow executor."""
    
    async def test_sequential_execution(self):
        """Test basic sequential execution."""
        strategy_dict = {
            'name': 'test_strategy',
            'steps': [
                {
                    'name': 'step1',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {'value': 1}
                    }
                },
                {
                    'name': 'step2',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {'value': 2}
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            mock_action.execute.return_value = {'result': 'success'}
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            assert len(executor.executed_steps) == 2
            assert 'step1' in executor.executed_steps
            assert 'step2' in executor.executed_steps
    
    async def test_conditional_execution(self):
        """Test conditional step execution."""
        strategy_dict = {
            'name': 'test_conditional',
            'variables': {'threshold': 0.5},
            'steps': [
                {
                    'name': 'step1',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    },
                    'set_variables': {'score': 0.3}
                },
                {
                    'name': 'step2',
                    'condition': "${variables.score} > ${variables.threshold}",
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    }
                },
                {
                    'name': 'step3',
                    'condition': "${variables.score} < ${variables.threshold}",
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            mock_action.execute.return_value = {'result': 'success'}
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            assert 'step1' in executor.executed_steps
            assert 'step2' in executor.skipped_steps  # score (0.3) < threshold (0.5)
            assert 'step3' in executor.executed_steps  # score (0.3) < threshold (0.5)
    
    async def test_foreach_loop(self):
        """Test for_each loop execution."""
        strategy_dict = {
            'name': 'test_foreach',
            'parameters': {
                'datasets': ['data1', 'data2', 'data3']
            },
            'steps': [
                {
                    'name': 'process_dataset',
                    'for_each': {
                        'items': "${parameters.datasets}",
                        'as_variable': 'dataset'
                    },
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {
                            'input': "${dataset}"
                        }
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        executed_params = []
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            
            async def capture_params(*args, **kwargs):
                if 'action_params' in kwargs:
                    executed_params.append(kwargs['action_params'])
                return {'result': 'success'}
            
            mock_action.execute.side_effect = capture_params
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            # Should execute 3 times
            assert mock_action.execute.call_count == 3
            assert len(executed_params) == 3
            
            # Check that each dataset was processed
            inputs = [p['input'] for p in executed_params]
            assert 'data1' in inputs
            assert 'data2' in inputs
            assert 'data3' in inputs
    
    async def test_repeat_loop(self):
        """Test repeat loop with while condition."""
        strategy_dict = {
            'name': 'test_repeat',
            'variables': {'counter': 0},
            'steps': [
                {
                    'name': 'increment',
                    'repeat': {
                        'max_iterations': 5,
                        'while_condition': "${variables.counter} < 3"
                    },
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    },
                    'set_variables': {
                        'counter': "${variables.counter} + 1"
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        call_count = 0
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            
            async def increment_counter(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return {'result': 'success'}
            
            mock_action.execute.side_effect = increment_counter
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            
            # Mock the set_variables evaluation to actually increment
            original_evaluate = executor.evaluator.evaluator.evaluate
            
            def mock_evaluate(expr):
                if expr == "${variables.counter} + 1":
                    return executor.variables.get('counter', 0) + 1
                return original_evaluate(expr)
            
            executor.evaluator.evaluator.evaluate = mock_evaluate
            
            result = await executor.execute()
            
            # Should execute 3 times (while counter < 3)
            assert call_count == 3
            assert executor.variables['counter'] == 3
    
    async def test_error_handling_retry(self):
        """Test error handling with retry."""
        strategy_dict = {
            'name': 'test_retry',
            'steps': [
                {
                    'name': 'failing_step',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    },
                    'on_error': {
                        'action': 'retry',
                        'max_attempts': 3,
                        'delay': 0  # No delay for testing
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        attempt_count = 0
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            
            async def fail_then_succeed(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise Exception("Simulated failure")
                return {'result': 'success'}
            
            mock_action.execute.side_effect = fail_then_succeed
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            # Should succeed after 3 attempts
            assert attempt_count == 3
            assert 'failing_step' in executor.executed_steps
            assert 'failing_step' not in executor.failed_steps
    
    async def test_error_handling_continue(self):
        """Test error handling with continue action."""
        strategy_dict = {
            'name': 'test_continue',
            'steps': [
                {
                    'name': 'failing_step',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    },
                    'on_error': 'continue'
                },
                {
                    'name': 'next_step',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {}
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action1 = AsyncMock()
            mock_action1.execute.side_effect = Exception("Simulated failure")
            
            mock_action2 = AsyncMock()
            mock_action2.execute.return_value = {'result': 'success'}
            
            def get_action(action_type):
                if action_type == 'TEST_ACTION':
                    if len(mock_get_action.call_args_list) == 1:
                        return lambda: mock_action1
                    else:
                        return lambda: mock_action2
            
            mock_get_action.side_effect = get_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            # First step should fail but execution continues
            assert 'failing_step' in executor.failed_steps
            assert 'next_step' in executor.executed_steps
    
    async def test_dag_execution(self):
        """Test DAG-based execution with dependencies."""
        strategy_dict = {
            'name': 'test_dag',
            'execution': {
                'mode': 'dag'
            },
            'steps': [
                {
                    'name': 'load_a',
                    'action': {'type': 'TEST_ACTION', 'params': {}}
                },
                {
                    'name': 'load_b',
                    'action': {'type': 'TEST_ACTION', 'params': {}}
                },
                {
                    'name': 'process_a',
                    'depends_on': ['load_a'],
                    'action': {'type': 'TEST_ACTION', 'params': {}}
                },
                {
                    'name': 'process_b',
                    'depends_on': ['load_b'],
                    'action': {'type': 'TEST_ACTION', 'params': {}}
                },
                {
                    'name': 'combine',
                    'depends_on': ['process_a', 'process_b'],
                    'action': {'type': 'TEST_ACTION', 'params': {}}
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        execution_order = []
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            
            async def track_execution(*args, **kwargs):
                # Find which step is being executed
                for step in strategy.steps:
                    if step.name not in execution_order:
                        execution_order.append(step.name)
                        break
                return {'result': 'success'}
            
            mock_action.execute.side_effect = track_execution
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            # Check that dependencies were respected
            assert execution_order.index('load_a') < execution_order.index('process_a')
            assert execution_order.index('load_b') < execution_order.index('process_b')
            assert execution_order.index('process_a') < execution_order.index('combine')
            assert execution_order.index('process_b') < execution_order.index('combine')
    
    async def test_checkpointing(self):
        """Test checkpointing functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategy_dict = {
                'name': 'test_checkpoint',
                'checkpointing': {
                    'enabled': True,
                    'strategy': 'after_each_step',
                    'storage': 'local'
                },
                'steps': [
                    {
                        'name': 'step1',
                        'action': {'type': 'TEST_ACTION', 'params': {}},
                        'checkpoint': 'after'
                    },
                    {
                        'name': 'step2',
                        'action': {'type': 'TEST_ACTION', 'params': {}}
                    }
                ]
            }
            
            strategy = EnhancedStrategy(**strategy_dict)
            
            with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
                mock_action = AsyncMock()
                mock_action.execute.return_value = {'result': 'success'}
                mock_get_action.return_value = lambda: mock_action
                
                executor = ControlFlowExecutor(strategy, checkpoint_dir=tmpdir)
                result = await executor.execute()
                
                # Check that checkpoint was created
                assert len(executor.checkpoints) > 0
                
                # Verify checkpoint file exists
                checkpoint_file = Path(executor.checkpoints[0])
                assert checkpoint_file.exists()
                
                # Load and verify checkpoint content
                with open(checkpoint_file) as f:
                    checkpoint_data = json.load(f)
                
                assert checkpoint_data['strategy_name'] == 'test_checkpoint'
                assert 'step1' in checkpoint_data['executed_steps']
    
    async def test_set_variables(self):
        """Test variable setting during execution."""
        strategy_dict = {
            'name': 'test_variables',
            'variables': {
                'initial_value': 10
            },
            'steps': [
                {
                    'name': 'step1',
                    'action': {'type': 'TEST_ACTION', 'params': {}},
                    'set_variables': {
                        'computed_value': "${variables.initial_value} * 2",
                        'static_value': 'test'
                    }
                },
                {
                    'name': 'step2',
                    'condition': "${variables.computed_value} == 20",
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {
                            'input': "${variables.static_value}"
                        }
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**strategy_dict)
        
        with patch('biomapper.core.services.control_flow_executor.get_action_class') as mock_get_action:
            mock_action = AsyncMock()
            mock_action.execute.return_value = {'result': 'success'}
            mock_get_action.return_value = lambda: mock_action
            
            executor = ControlFlowExecutor(strategy)
            result = await executor.execute()
            
            # Check variables were set
            assert executor.variables['computed_value'] == 20
            assert executor.variables['static_value'] == 'test'
            
            # Check step2 executed (condition was met)
            assert 'step2' in executor.executed_steps


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test backward compatibility with existing strategies."""
    
    async def test_legacy_strategy_format(self):
        """Test that legacy strategy format still works."""
        legacy_strategy = {
            'name': 'legacy_strategy',
            'description': 'A legacy strategy',
            'steps': [
                {
                    'name': 'LOAD_DATA',
                    'action': {
                        'type': 'LOAD_DATASET_IDENTIFIERS',
                        'params': {
                            'file_path': '/path/to/file.csv'
                        }
                    }
                }
            ]
        }
        
        # Should parse without errors
        strategy = EnhancedStrategy(**legacy_strategy)
        assert strategy.name == 'legacy_strategy'
        assert len(strategy.steps) == 1
        assert not strategy.is_control_flow_enabled()
    
    async def test_mixed_format(self):
        """Test strategy with mix of legacy and new features."""
        mixed_strategy = {
            'name': 'mixed_strategy',
            'steps': [
                {
                    'name': 'legacy_step',
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {'value': 1}
                    }
                },
                {
                    'name': 'enhanced_step',
                    'condition': "${variables.enabled} == true",
                    'action': {
                        'type': 'TEST_ACTION',
                        'params': {'value': 2}
                    }
                }
            ]
        }
        
        strategy = EnhancedStrategy(**mixed_strategy)
        assert strategy.is_control_flow_enabled()  # Has condition
        assert len(strategy.steps) == 2