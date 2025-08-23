"""
Integration tests for the Unified BiOMapper Agent.

Tests framework routing, confidence scoring, and automatic activation.

STATUS: Unified agent framework not implemented
FUNCTIONALITY: Intent detection, framework routing, confidence scoring
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use specific strategy execution patterns directly
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Skip entire module - unified agent framework not implemented
pytestmark = pytest.mark.skip("Unified agent framework not implemented - use direct strategy execution")

from src.core.safety.unified_agent import (
    UnifiedBiomapperAgent,
    FrameworkRouter, 
    FrameworkType,
    IntentScore
)


class TestFrameworkRouter:
    """Test the framework routing logic."""
    
    @pytest.fixture
    def router(self):
        """Create a router instance."""
        return FrameworkRouter()
    
    def test_surgical_intent_detection(self, router):
        """Test surgical framework detection from natural language."""
        test_messages = [
            "The statistics show 3675 proteins but should count unique entities",
            "Internal logic is broken in the calculation",
            "Fix the counting issue in the action",
            "The merge logic is overcounting duplicates",
        ]
        
        for message in test_messages:
            framework, score = router.route_intent(message)
            assert framework == FrameworkType.SURGICAL
            assert score.confidence >= 0.4  # Above activation threshold
            assert len(score.matched_patterns) > 0
    
    def test_circuitous_intent_detection(self, router):
        """Test circuitous framework detection."""
        test_messages = [
            "Parameters not flowing between pipeline steps",
            "The strategy orchestration is broken",
            "Parameter substitution is failing",
            "Pipeline flow is interrupted at step 3",
            "Context not passing between actions",
        ]
        
        for message in test_messages:
            framework, score = router.route_intent(message)
            assert framework == FrameworkType.CIRCUITOUS
            assert score.confidence >= 0.4
    
    def test_interstitial_intent_detection(self, router):
        """Test interstitial framework detection."""
        test_messages = [
            "Interface between actions broken",
            "Backward compatibility issue with new parameter",
            "The API change broke existing strategies",
            "New parameter names not compatible",
            "Contract evolution breaking downstream",
        ]
        
        for message in test_messages:
            framework, score = router.route_intent(message)
            assert framework == FrameworkType.INTERSTITIAL
            assert score.confidence >= 0.4
    
    def test_no_framework_activation(self, router):
        """Test messages that shouldn't activate any framework."""
        test_messages = [
            "Run the metabolomics pipeline",
            "Show me the results",
            "What is the coverage percentage?",
            "Load the dataset",
        ]
        
        for message in test_messages:
            framework, score = router.route_intent(message)
            assert framework == FrameworkType.NONE
            assert score.confidence < 0.4
    
    def test_ambiguity_resolution(self, router):
        """Test resolution of ambiguous cases using priority."""
        # Message that could match multiple frameworks
        ambiguous = "The action parameter handling is broken internally"
        
        framework, score = router.route_intent(ambiguous)
        # Should resolve to surgical (highest priority)
        assert framework in [FrameworkType.SURGICAL, FrameworkType.CIRCUITOUS]
        assert score.confidence >= 0.4
    
    def test_confidence_scoring(self, router):
        """Test confidence score calculation."""
        # Very specific surgical message
        high_confidence = "fix internal counting logic statistics duplicate issue broken"
        framework, score = router.route_intent(high_confidence)
        assert score.confidence >= 0.7  # High confidence
        
        # Less specific message
        low_confidence = "something wrong with the action"
        framework, score = router.route_intent(low_confidence)
        if framework != FrameworkType.NONE:
            assert score.confidence < 0.7  # Lower confidence
    
    def test_target_extraction(self, router):
        """Test extraction of target entities from messages."""
        # Action name extraction
        message = "Fix GENERATE_MAPPING_VISUALIZATIONS statistics"
        framework, score = router.route_intent(message)
        # Note: Would need ACTION_REGISTRY mock for full test
        
        # Strategy name extraction
        message = "prot_arv_to_kg2c_uniprot_v3.0 pipeline broken"
        framework, score = router.route_intent(message)
        if framework == FrameworkType.CIRCUITOUS:
            assert score.extracted_target is not None
            assert "prot_arv_to_kg2c" in score.extracted_target.lower()


class TestUnifiedAgent:
    """Test the unified agent orchestration."""
    
    @pytest.fixture
    def agent(self):
        """Create an agent instance."""
        with patch('src.core.safety.unified_agent.SurgicalModeAgent'):
            with patch('src.core.safety.unified_agent.CircuitousFramework'):
                with patch('src.core.safety.unified_agent.InterstitialFramework'):
                    return UnifiedBiomapperAgent()
    
    def test_process_user_message_surgical(self, agent):
        """Test processing a surgical intent message."""
        message = "The statistics are counting duplicates instead of unique entities"
        
        result = agent.process_user_message(message)
        
        assert result['framework'] == 'surgical'
        assert result['mode'] == 'active'
        assert 'confidence' in result
        assert result['confidence'] >= 0.4
        assert 'response' in result
        assert 'Surgical mode activated' in result['response']
    
    def test_process_user_message_circuitous(self, agent):
        """Test processing a circuitous intent message."""
        message = "Parameters not flowing between pipeline steps"
        
        result = agent.process_user_message(message)
        
        assert result['framework'] == 'circuitous'
        assert result['mode'] == 'active'
        assert 'Circuitous mode activated' in result['response']
    
    def test_process_user_message_interstitial(self, agent):
        """Test processing an interstitial intent message."""
        message = "New parameter names broke backward compatibility"
        
        result = agent.process_user_message(message)
        
        assert result['framework'] == 'interstitial'
        assert result['mode'] == 'active'
        assert '100% guaranteed' in result['response']
    
    def test_process_user_message_no_framework(self, agent):
        """Test processing a message that doesn't activate any framework."""
        message = "Show me the protein mapping results"
        
        result = agent.process_user_message(message)
        
        assert result['framework'] is None
        assert 'No specialized framework needed' in result['message']
    
    def test_execute_framework_operation_surgical(self, agent):
        """Test executing surgical framework operations."""
        # Activate surgical framework first
        agent.active_framework = FrameworkType.SURGICAL
        agent.active_context = {'target': 'TEST_ACTION'}
        
        result = agent.execute_framework_operation('validate')
        assert result['status'] == 'completed'
        assert result['operation'] == 'validate'
        
        result = agent.execute_framework_operation('apply')
        assert result['status'] == 'completed'
        assert result['operation'] == 'apply'
    
    def test_execute_framework_operation_circuitous(self, agent):
        """Test executing circuitous framework operations."""
        agent.active_framework = FrameworkType.CIRCUITOUS
        agent.active_context = {'target': 'test_strategy.yaml'}
        
        # Mock the circuitous framework's diagnose method
        agent.circuitous.diagnose_strategy = Mock(return_value={
            'issues_found': 2,
            'flow_analysis': {'total_steps': 5}
        })
        
        result = agent.execute_framework_operation('diagnose')
        assert result['status'] == 'completed'
        assert 'diagnosis' in result
    
    def test_execute_framework_operation_interstitial(self, agent):
        """Test executing interstitial framework operations."""
        agent.active_framework = FrameworkType.INTERSTITIAL
        agent.active_context = {'target': 'TEST_ACTION'}
        
        # Mock the interstitial framework's analyze method
        agent.interstitial.analyze_interface_evolution = Mock(return_value={
            'compatibility_issues': [],
            'current_interface': {}
        })
        
        result = agent.execute_framework_operation('analyze')
        assert result['status'] == 'completed'
        assert 'analysis' in result
    
    def test_execute_operation_no_framework(self, agent):
        """Test executing operation with no active framework."""
        agent.active_framework = None
        
        result = agent.execute_framework_operation('validate')
        assert 'error' in result
        assert result['error'] == 'No framework active'
    
    def test_get_status(self, agent):
        """Test getting agent status."""
        status = agent.get_status()
        
        assert 'active_framework' in status
        assert 'frameworks_available' in status
        assert status['frameworks_available'] == ['surgical', 'circuitous', 'interstitial']
        assert status['router_status'] == 'ready'
        assert status['confidence_threshold'] == 0.4


class TestFrameworkInteractions:
    """Test interactions between frameworks."""
    
    @pytest.fixture
    def agent(self):
        """Create a fully mocked agent."""
        with patch('src.core.safety.unified_agent.SurgicalModeAgent'):
            with patch('src.core.safety.unified_agent.CircuitousFramework'):
                with patch('src.core.safety.unified_agent.InterstitialFramework'):
                    return UnifiedBiomapperAgent()
    
    def test_surgical_to_interstitial_flow(self, agent):
        """Test surgical changes triggering interstitial validation."""
        # First activate surgical
        surgical_msg = "Fix the internal counting logic"
        result1 = agent.process_user_message(surgical_msg)
        assert result1['framework'] == 'surgical'
        
        # Then user mentions compatibility concern
        compat_msg = "Make sure this doesn't break backward compatibility"
        result2 = agent.process_user_message(compat_msg)
        assert result2['framework'] == 'interstitial'
    
    def test_circuitous_to_surgical_flow(self, agent):
        """Test pipeline issue leading to surgical fix."""
        # Pipeline issue detected
        pipeline_msg = "Parameters not flowing in the strategy"
        result1 = agent.process_user_message(pipeline_msg)
        assert result1['framework'] == 'circuitous'
        
        # Root cause in action logic
        action_msg = "The issue is in the action's internal parameter handling"
        result2 = agent.process_user_message(action_msg)
        assert result2['framework'] == 'surgical'
    
    def test_confidence_threshold_adjustment(self, agent):
        """Test that confidence threshold can be adjusted."""
        original_threshold = agent.router.ACTIVATION_THRESHOLD
        
        # Adjust threshold
        agent.router.ACTIVATION_THRESHOLD = 0.8
        
        # Message with medium confidence shouldn't activate
        message = "maybe something wrong with the action"
        result = agent.process_user_message(message)
        assert result['framework'] is None
        
        # Restore threshold
        agent.router.ACTIVATION_THRESHOLD = original_threshold


class TestPatternCaching:
    """Test pattern compilation and caching."""
    
    def test_pattern_compilation(self):
        """Test that patterns are pre-compiled on initialization."""
        router = FrameworkRouter()
        
        # Check pattern cache is populated
        assert len(router._pattern_cache) == 3
        assert FrameworkType.SURGICAL in router._pattern_cache
        assert FrameworkType.CIRCUITOUS in router._pattern_cache
        assert FrameworkType.INTERSTITIAL in router._pattern_cache
        
        # Check patterns are compiled
        for framework_patterns in router._pattern_cache.values():
            for pattern in framework_patterns:
                assert hasattr(pattern, 'search')  # Compiled regex has search method


@pytest.mark.parametrize("message,expected_framework", [
    ("statistics showing wrong count", FrameworkType.SURGICAL),
    ("pipeline orchestration broken", FrameworkType.CIRCUITOUS),
    ("backward compatibility issue", FrameworkType.INTERSTITIAL),
    ("run the analysis", FrameworkType.NONE),
])
def test_parametrized_routing(message, expected_framework):
    """Parametrized test for various routing scenarios."""
    router = FrameworkRouter()
    framework, score = router.route_intent(message)
    assert framework == expected_framework