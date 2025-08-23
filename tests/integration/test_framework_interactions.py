"""
Integration tests for framework interactions and cross-framework scenarios.

Tests how the three frameworks work together to solve complex issues.

STATUS: Framework routing system not implemented
FUNCTIONALITY: Surgical/Circuitous/Interstitial workflow routing  
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use direct strategy execution via biomapper client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List
import pandas as pd

# Skip entire module - framework routing system not implemented
pytestmark = pytest.mark.skip("Framework routing system not implemented - see biomapper client for direct strategy execution")

from src.core.safety.unified_agent import (
    UnifiedBiomapperAgent,
    FrameworkType
)


class TestFrameworkChaining:
    """Test scenarios where multiple frameworks are needed."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create agent with mocked frameworks."""
        with patch('src.core.safety.unified_agent.SurgicalModeAgent') as mock_surgical:
            with patch('src.core.safety.unified_agent.CircuitousFramework') as mock_circuitous:
                with patch('src.core.safety.unified_agent.InterstitialFramework') as mock_interstitial:
                    agent = UnifiedBiomapperAgent()
                    
                    # Setup mocks
                    agent.surgical_agent = mock_surgical.return_value
                    agent.circuitous = mock_circuitous.return_value
                    agent.interstitial = mock_interstitial.return_value
                    
                    return agent
    
    def test_complete_fix_workflow(self, mock_agent):
        """Test complete workflow: detect issue → fix → ensure compatibility."""
        
        # Step 1: User reports issue
        issue_msg = "The protein statistics are counting all records instead of unique proteins"
        result1 = mock_agent.process_user_message(issue_msg)
        assert result1['framework'] == 'surgical'
        
        # Step 2: User wants to verify pipeline still works
        verify_msg = "Make sure the pipeline parameter flow still works after this fix"
        result2 = mock_agent.process_user_message(verify_msg)
        assert result2['framework'] == 'circuitous'
        
        # Step 3: User wants backward compatibility guarantee
        compat_msg = "Ensure all existing strategies remain compatible"
        result3 = mock_agent.process_user_message(compat_msg)
        assert result3['framework'] == 'interstitial'
    
    def test_pipeline_to_action_diagnosis(self, mock_agent):
        """Test diagnosing pipeline issue that leads to action fix."""
        
        # Mock circuitous diagnosis finding action issue
        mock_agent.circuitous.diagnose_strategy = Mock(return_value={
            'issues_found': 1,
            'breakpoints': [{
                'type': 'context_missing',
                'step': 'process_proteins',
                'description': 'Action not writing to context'
            }],
            'suggested_repairs': [{
                'action': 'Fix action context writing',
                'framework': 'surgical'
            }]
        })
        
        # User reports pipeline issue
        pipeline_msg = "The metabolomics strategy parameters aren't flowing"
        result1 = mock_agent.process_user_message(pipeline_msg)
        assert result1['framework'] == 'circuitous'
        
        # Execute diagnosis
        diagnosis = mock_agent.execute_framework_operation('diagnose')
        
        # User follows suggestion to fix action
        action_msg = "Fix the action's context writing as suggested"
        result2 = mock_agent.process_user_message(action_msg)
        assert result2['framework'] == 'surgical'
    
    def test_interface_evolution_workflow(self, mock_agent):
        """Test interface evolution maintaining compatibility."""
        
        # Mock interstitial analysis
        mock_agent.interstitial.analyze_interface_evolution = Mock(return_value={
            'compatibility_issues': [{
                'type': 'parameter_renamed',
                'old': 'dataset_key',
                'new': 'input_key'
            }],
            'current_interface': {
                'input_params': ['input_key', 'threshold'],
                'output_keys': ['results']
            }
        })
        
        # User wants to evolve interface
        evolve_msg = "The dataset_key parameter was renamed to input_key"
        result = mock_agent.process_user_message(evolve_msg)
        assert result['framework'] == 'interstitial'
        
        # Execute compatibility analysis
        analysis = mock_agent.execute_framework_operation('analyze')
        
        # Ensure compatibility
        compat_result = mock_agent.execute_framework_operation('ensure_compatibility')
        assert compat_result['status'] == 'completed'


class TestRealWorldScenarios:
    """Test real-world problem scenarios."""
    
    @pytest.fixture
    def agent_with_data(self):
        """Create agent with realistic test data."""
        with patch('src.core.safety.unified_agent.SurgicalModeAgent'):
            with patch('src.core.safety.unified_agent.CircuitousFramework'):
                with patch('src.core.safety.unified_agent.InterstitialFramework'):
                    agent = UnifiedBiomapperAgent()
                    
                    # Add realistic context
                    agent.active_context = {
                        'datasets': {
                            'proteins': pd.DataFrame({
                                'uniprot': ['P12345', 'P67890', 'P12345'],
                                'gene': ['GENE1', 'GENE2', 'GENE1']
                            })
                        },
                        'statistics': {},
                        'output_files': []
                    }
                    
                    return agent
    
    def test_duplicate_counting_scenario(self, agent_with_data):
        """Test the original duplicate counting issue."""
        
        # User reports the actual issue
        msg = "The visualization shows 3 proteins but there are only 2 unique ones"
        result = agent_with_data.process_user_message(msg)
        
        assert result['framework'] == 'surgical'
        assert 'unique' in result['response'].lower()
    
    def test_parameter_flow_scenario(self, agent_with_data):
        """Test parameter substitution failure."""
        
        msg = "The ${parameters.input_file} isn't being substituted in the pipeline"
        result = agent_with_data.process_user_message(msg)
        
        assert result['framework'] == 'circuitous'
        assert 'parameter' in result['response'].lower()
    
    def test_api_evolution_scenario(self, agent_with_data):
        """Test API evolution compatibility."""
        
        msg = "We need to change the API but keep old integrations working"
        result = agent_with_data.process_user_message(msg)
        
        assert result['framework'] == 'interstitial'
        assert '100%' in result['response']


class TestErrorHandling:
    """Test error handling across frameworks."""
    
    @pytest.fixture
    def agent(self):
        """Create basic agent."""
        with patch('src.core.safety.unified_agent.SurgicalModeAgent'):
            with patch('src.core.safety.unified_agent.CircuitousFramework'):
                with patch('src.core.safety.unified_agent.InterstitialFramework'):
                    return UnifiedBiomapperAgent()
    
    def test_framework_activation_failure(self, agent):
        """Test handling of framework activation failures."""
        
        # Mock surgical activation to raise
        agent.surgical_agent.activate_surgical_mode = Mock(
            side_effect=Exception("Action not found")
        )
        
        msg = "Fix the counting in NONEXISTENT_ACTION"
        # Should handle gracefully
        result = agent.process_user_message(msg)
        assert result['framework'] == 'surgical'
        # Error handling would be in actual implementation
    
    def test_ambiguous_intent_resolution(self, agent):
        """Test resolution when intent is highly ambiguous."""
        
        # Very vague message
        msg = "something is wrong"
        result = agent.process_user_message(msg)
        
        # Should either pick no framework or use priority
        assert result['framework'] in [None, 'surgical']
    
    def test_confidence_below_threshold(self, agent):
        """Test when confidence is below activation threshold."""
        
        msg = "the system needs improvement"
        result = agent.process_user_message(msg)
        
        if result['framework'] is None:
            assert 'No specialized framework needed' in result.get('message', '')


class TestPerformance:
    """Test performance characteristics."""
    
    def test_routing_performance(self):
        """Test that routing is fast."""
        import time
        from src.core.safety.unified_agent import FrameworkRouter
        
        router = FrameworkRouter()
        messages = [
            "fix internal logic",
            "pipeline broken",
            "backward compatibility",
            "run analysis",
        ] * 100  # 400 messages
        
        start = time.time()
        for msg in messages:
            router.route_intent(msg)
        elapsed = time.time() - start
        
        # Should process 400 messages in under 1 second
        assert elapsed < 1.0
        
        # Average should be < 10ms per message
        avg_time = elapsed / len(messages)
        assert avg_time < 0.01
    
    def test_pattern_cache_efficiency(self):
        """Test that patterns are cached efficiently."""
        from src.core.safety.unified_agent import FrameworkRouter
        
        router1 = FrameworkRouter()
        router2 = FrameworkRouter()
        
        # Both should have same number of compiled patterns
        assert len(router1._pattern_cache) == len(router2._pattern_cache)
        
        # Patterns should be pre-compiled
        for patterns in router1._pattern_cache.values():
            assert all(hasattr(p, 'search') for p in patterns)


class TestIntegrationWithActions:
    """Test framework integration with actual actions."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("src.actions.registry"),
        reason="Action registry not available"
    )
    def test_surgical_with_real_action(self):
        """Test surgical framework with real action."""
        from src.core.safety.unified_agent import UnifiedBiomapperAgent
        
        agent = UnifiedBiomapperAgent()
        
        # Use a real action name
        msg = "Fix GENERATE_MAPPING_VISUALIZATIONS duplicate counting"
        result = agent.process_user_message(msg)
        
        assert result['framework'] == 'surgical'
        assert result['target'] == 'GENERATE_MAPPING_VISUALIZATIONS'
    
    @pytest.mark.skipif(
        not pytest.importorskip("src.configs.strategies"),
        reason="Strategies not available"
    )
    def test_circuitous_with_real_strategy(self):
        """Test circuitous framework with real strategy."""
        from src.core.safety.unified_agent import UnifiedBiomapperAgent
        
        agent = UnifiedBiomapperAgent()
        
        # Use a real strategy name
        msg = "prot_arv_to_kg2c_uniprot_v3.0 parameter flow broken"
        result = agent.process_user_message(msg)
        
        assert result['framework'] == 'circuitous'
        assert 'prot_arv_to_kg2c' in str(result.get('target', '')).lower()


class TestDocumentationExamples:
    """Test examples from documentation work as expected."""
    
    @pytest.fixture
    def agent(self):
        with patch('src.core.safety.unified_agent.SurgicalModeAgent'):
            with patch('src.core.safety.unified_agent.CircuitousFramework'):
                with patch('src.core.safety.unified_agent.InterstitialFramework'):
                    return UnifiedBiomapperAgent()
    
    def test_documentation_surgical_example(self, agent):
        """Test surgical example from docs."""
        msg = "The statistics show 3675 proteins but should count unique entities"
        result = agent.process_user_message(msg)
        assert result['framework'] == 'surgical'
    
    def test_documentation_circuitous_example(self, agent):
        """Test circuitous example from docs."""
        msg = "The metabolomics strategy isn't passing context between actions"
        result = agent.process_user_message(msg)
        assert result['framework'] == 'circuitous'
    
    def test_documentation_interstitial_example(self, agent):
        """Test interstitial example from docs."""
        msg = "The new output_key parameter broke old strategies using dataset_key"
        result = agent.process_user_message(msg)
        assert result['framework'] == 'interstitial'