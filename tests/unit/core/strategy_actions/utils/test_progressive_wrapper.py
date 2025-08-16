"""Unit tests for progressive wrapper system.

Tests the progressive wrapper functionality for filtering unmatched identifiers
and tracking stage statistics, following the 2025 standardization framework.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from biomapper.core.strategy_actions.utils.progressive_wrapper import (
    ProgressiveWrapper,
    ProgressiveStage,
    ProgressiveOrchestrator
)
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.standards.context_handler import UniversalContext


class MockActionParams:
    """Mock parameters for testing."""
    pass

class MockActionResult:
    """Mock result for testing."""
    pass

class MockAction:
    """Mock action for testing progressive wrapper."""
    
    def __init__(self, matched_identifiers: List[str] = None):
        """Initialize mock action with expected matches."""
        self.matched_identifiers = matched_identifiers or []
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Any = None,
        target_endpoint: Any = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Mock execute method that returns predefined matches."""
        # Simulate matches from the provided identifiers
        matched = [id for id in current_identifiers if id in self.matched_identifiers]
        
        return {
            "input_identifiers": current_identifiers,
            "output_identifiers": matched,
            "output_ontology_type": current_ontology_type,
            "provenance": [],
            "details": {
                "matched_identifiers": matched,
                "method": "mock_matching"
            }
        }


class TestProgressiveStage:
    """Test progressive stage statistics tracking."""
    
    def test_stage_initialization(self):
        """Test level 1: Stage initialization with basic parameters."""
        stage = ProgressiveStage("test_stage", "test_method", 1)
        
        assert stage.name == "test_stage"
        assert stage.method == "test_method"
        assert stage.stage_number == 1
        assert stage.matched == 0
        assert stage.new_matches == 0
        assert stage.cumulative_matched == 0
    
    def test_stage_to_dict(self):
        """Test level 1: Stage conversion to dictionary format."""
        stage = ProgressiveStage("test_stage", "test_method", 1)
        stage.matched = 100
        stage.new_matches = 50
        stage.cumulative_matched = 150
        stage.execution_time = 2.5
        
        result = stage.to_dict()
        
        expected = {
            "name": "test_stage",
            "matched": 100,
            "unmatched": 0,
            "new_matches": 50,
            "cumulative_matched": 150,
            "method": "test_method",
            "time": "2.5s"
        }
        
        assert result == expected


class TestProgressiveWrapper:
    """Test progressive wrapper functionality."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context for testing."""
        return {
            "datasets": {},
            "statistics": {},
            "output_files": [],
            "current_identifiers": ["P12345", "Q67890", "O00123", "P99999", "Q11111"]
        }
    
    @pytest.fixture
    def sample_params(self):
        """Create sample parameters for testing."""
        return {
            "input_key": "test_dataset",
            "output_key": "results",
            "identifiers": ["P12345", "Q67890", "O00123", "P99999", "Q11111"],
            "threshold": 0.8
        }
    
    def test_level_1_wrapper_initialization(self):
        """Test level 1: Basic wrapper initialization."""
        wrapper = ProgressiveWrapper(1, "test_stage", "test_method")
        
        assert wrapper.stage_number == 1
        assert wrapper.stage_name == "test_stage"
        assert wrapper.method == "test_method"
        assert len(wrapper._matched_identifiers) == 0
        assert wrapper._current_stage.name == "test_stage"
    
    def test_level_1_get_identifiers_from_params(self):
        """Test level 1: Identifier extraction from parameters."""
        wrapper = ProgressiveWrapper(1, "test_stage")
        
        # Test standard parameter names
        params_variants = [
            {"identifiers": ["P12345", "Q67890"]},
            {"input_identifiers": ["P12345", "Q67890"]},
            {"current_identifiers": ["P12345", "Q67890"]},
            {"protein_identifiers": ["P12345", "Q67890"]},
        ]
        
        for params in params_variants:
            identifiers = wrapper._get_identifiers_from_params(params)
            assert identifiers == ["P12345", "Q67890"]
    
    def test_level_1_filter_to_unmatched(self, sample_params, sample_context):
        """Test level 1: Filtering to unmatched identifiers."""
        wrapper = ProgressiveWrapper(1, "test_stage")
        ctx = UniversalContext.wrap(sample_context)
        
        # Pre-mark some identifiers as matched
        wrapper._matched_identifiers.update(["P12345", "O00123"])
        
        filtered_params = wrapper._filter_to_unmatched(sample_params, ctx)
        
        # Should only contain unmatched identifiers
        filtered_identifiers = set(filtered_params["identifiers"])
        expected_unmatched = {"Q67890", "P99999", "Q11111"}
        
        assert filtered_identifiers == expected_unmatched
    
    @pytest.mark.asyncio
    async def test_level_2_execute_stage_basic(self, sample_params, sample_context):
        """Test level 2: Basic stage execution with mock action."""
        # Create mock action that matches specific identifiers
        mock_action = MockAction(matched_identifiers=["P12345", "Q67890"])
        
        wrapper = ProgressiveWrapper(1, "direct_match", "Direct UniProt")
        
        result = await wrapper.execute_stage(mock_action, sample_params, sample_context)
        
        # Verify result structure
        assert "input_identifiers" in result
        assert "output_identifiers" in result
        assert result["output_identifiers"] == ["P12345", "Q67890"]
        
        # Verify progressive stats were updated
        assert "progressive_stats" in sample_context
        stats = sample_context["progressive_stats"]
        assert "stages" in stats
        assert 1 in stats["stages"]
        
        stage_stats = stats["stages"][1]
        assert stage_stats["name"] == "direct_match"
        assert stage_stats["new_matches"] == 2
        assert stage_stats["method"] == "Direct UniProt"
    
    @pytest.mark.asyncio
    async def test_level_2_multiple_stages_filtering(self, sample_context):
        """Test level 2: Multiple stages with progressive filtering."""
        # Stage 1: Matches P12345, Q67890
        stage1_params = {
            "identifiers": ["P12345", "Q67890", "O00123", "P99999", "Q11111"]
        }
        mock_action1 = MockAction(matched_identifiers=["P12345", "Q67890"])
        wrapper1 = ProgressiveWrapper(1, "stage1", "Method1")
        
        # Execute stage 1
        await wrapper1.execute_stage(mock_action1, stage1_params, sample_context)
        
        # Stage 2: Should only see unmatched identifiers
        stage2_params = {
            "identifiers": ["P12345", "Q67890", "O00123", "P99999", "Q11111"]  # Same original list
        }
        mock_action2 = MockAction(matched_identifiers=["O00123"])
        
        # Use the same matched set from stage 1
        wrapper2 = ProgressiveWrapper(2, "stage2", "Method2")
        wrapper2._matched_identifiers = wrapper1._matched_identifiers.copy()
        
        # Execute stage 2
        result2 = await wrapper2.execute_stage(mock_action2, stage2_params, sample_context)
        
        # Stage 2 should only have processed unmatched identifiers
        assert set(result2["input_identifiers"]) == {"O00123", "P99999", "Q11111"}
        assert result2["output_identifiers"] == ["O00123"]
        
        # Check cumulative statistics
        stats = sample_context["progressive_stats"]
        assert len(stats["stages"]) == 2
        
        # Stage 1 stats
        assert stats["stages"][1]["new_matches"] == 2
        assert stats["stages"][1]["cumulative_matched"] == 2
        
        # Stage 2 stats
        assert stats["stages"][2]["new_matches"] == 1
        assert stats["stages"][2]["cumulative_matched"] == 3  # 2 + 1
    
    @pytest.mark.asyncio
    async def test_level_3_performance_large_dataset(self):
        """Test level 3: Performance with large dataset (production subset)."""
        # Generate large dataset (5000 identifiers)
        large_identifiers = [f"P{i:05d}" for i in range(5000)]
        large_params = {"identifiers": large_identifiers}
        large_context = {"current_identifiers": large_identifiers}
        
        # Mock action that matches 80% of identifiers
        matched_subset = large_identifiers[:4000]  # 80% match rate
        mock_action = MockAction(matched_identifiers=matched_subset)
        
        wrapper = ProgressiveWrapper(1, "large_test", "Bulk Processing")
        
        import time
        start_time = time.time()
        
        result = await wrapper.execute_stage(mock_action, large_params, large_context)
        
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete within 1 second
        assert len(result["output_identifiers"]) == 4000
        assert len(wrapper._matched_identifiers) == 4000
        
        # Verify progressive stats
        stats = large_context["progressive_stats"]
        assert stats["stages"][1]["new_matches"] == 4000
        assert stats["final_match_rate"] == 0.8  # 4000/5000
    
    def test_level_1_context_initialization(self, sample_context):
        """Test level 1: Progressive stats initialization."""
        wrapper = ProgressiveWrapper(1, "test_stage")
        ctx = UniversalContext.wrap(sample_context)
        
        wrapper._initialize_progressive_stats(ctx)
        
        assert ctx.has_key("progressive_stats")
        stats = ctx.get("progressive_stats")
        assert "stages" in stats
        assert "total_processed" in stats
        assert "final_match_rate" in stats
        assert "total_time" in stats
    
    def test_level_1_extract_matched_identifiers(self):
        """Test level 1: Extraction of matched identifiers from result."""
        wrapper = ProgressiveWrapper(1, "test_stage")
        
        result = {
            "output_identifiers": ["P12345", "Q67890"],
            "details": {
                "matched_identifiers": ["O00123"],
                "method": "test"
            }
        }
        
        matched = wrapper._extract_matched_identifiers(result)
        
        # Should combine from both output_identifiers and details
        expected = {"P12345", "Q67890", "O00123"}
        assert matched == expected
    
    @pytest.mark.asyncio
    async def test_level_2_error_handling(self, sample_params, sample_context):
        """Test level 2: Error handling during stage execution."""
        # Create mock action that raises an exception
        class FailingAction:
            async def execute(self, *args, **kwargs):
                raise Exception("Test error")
        
        mock_action = FailingAction()
        wrapper = ProgressiveWrapper(1, "error_test", "Error Method")
        
        with pytest.raises(Exception, match="Test error"):
            await wrapper.execute_stage(mock_action, sample_params, sample_context)
        
        # Verify that partial statistics are still stored
        assert "progressive_stats" in sample_context
        stats = sample_context["progressive_stats"]
        assert 1 in stats["stages"]
        
        # Execution time should be recorded even on error
        stage_stats = stats["stages"][1]
        assert "time" in stage_stats
    
    def test_level_1_reset_statistics(self):
        """Test level 1: Statistics reset functionality."""
        wrapper = ProgressiveWrapper(1, "test_stage")
        
        # Add some matched identifiers and update stage
        wrapper._matched_identifiers.update(["P12345", "Q67890"])
        wrapper._current_stage.new_matches = 10
        wrapper._current_stage.cumulative_matched = 15
        
        # Reset
        wrapper.reset_statistics()
        
        assert len(wrapper._matched_identifiers) == 0
        assert wrapper._current_stage.new_matches == 0
        assert wrapper._current_stage.cumulative_matched == 0


class TestProgressiveOrchestrator:
    """Test progressive orchestrator functionality."""
    
    def test_level_1_orchestrator_initialization(self):
        """Test level 1: Orchestrator initialization."""
        orchestrator = ProgressiveOrchestrator()
        
        assert len(orchestrator.stages) == 0
    
    def test_level_1_add_stage(self):
        """Test level 1: Adding stages to orchestrator."""
        orchestrator = ProgressiveOrchestrator()
        mock_action = MockAction()
        params = {"test": "params"}
        
        orchestrator.add_stage(1, "stage1", mock_action, params, "method1")
        orchestrator.add_stage(3, "stage3", mock_action, params, "method3")
        orchestrator.add_stage(2, "stage2", mock_action, params, "method2")
        
        assert len(orchestrator.stages) == 3
        
        # Should be ordered by stage number
        stage_numbers = [stage["stage_number"] for stage in orchestrator.stages]
        assert stage_numbers == [1, 2, 3]
        
        stage_names = [stage["stage_name"] for stage in orchestrator.stages]
        assert stage_names == ["stage1", "stage2", "stage3"]
    
    @pytest.mark.asyncio
    async def test_level_2_execute_all_stages(self):
        """Test level 2: Executing all stages in sequence."""
        orchestrator = ProgressiveOrchestrator()
        context = {"current_identifiers": ["P12345", "Q67890", "O00123"]}
        
        # Add three stages with different match patterns
        mock_action1 = MockAction(matched_identifiers=["P12345"])
        mock_action2 = MockAction(matched_identifiers=["Q67890"])
        mock_action3 = MockAction(matched_identifiers=["O00123"])
        
        params = {"identifiers": ["P12345", "Q67890", "O00123"]}
        
        orchestrator.add_stage(1, "stage1", mock_action1, params, "method1")
        orchestrator.add_stage(2, "stage2", mock_action2, params, "method2")
        orchestrator.add_stage(3, "stage3", mock_action3, params, "method3")
        
        result = await orchestrator.execute_all(context)
        
        # Verify structure
        assert "stages" in result
        assert "final_context" in result
        assert len(result["stages"]) == 3
        
        # Each stage should have executed
        for i, stage_result in enumerate(result["stages"], 1):
            assert stage_result["stage_number"] == i
            assert stage_result["stage_name"] == f"stage{i}"
            assert "result" in stage_result
        
        # Verify progressive stats in final context
        final_context = result["final_context"]
        assert "progressive_stats" in final_context
        
        stats = final_context["progressive_stats"]
        assert len(stats["stages"]) == 3
    
    @pytest.mark.asyncio
    async def test_level_2_error_in_stage(self):
        """Test level 2: Error handling when one stage fails."""
        orchestrator = ProgressiveOrchestrator()
        context = {"current_identifiers": ["P12345", "Q67890"]}
        
        # Stage 1: Success
        mock_action1 = MockAction(matched_identifiers=["P12345"])
        
        # Stage 2: Failure
        class FailingAction:
            async def execute(self, *args, **kwargs):
                raise Exception("Stage 2 failed")
        mock_action2 = FailingAction()
        
        # Stage 3: Success
        mock_action3 = MockAction(matched_identifiers=["Q67890"])
        
        params = {"identifiers": ["P12345", "Q67890"]}
        
        orchestrator.add_stage(1, "stage1", mock_action1, params, "method1")
        orchestrator.add_stage(2, "stage2", mock_action2, params, "method2")
        orchestrator.add_stage(3, "stage3", mock_action3, params, "method3")
        
        result = await orchestrator.execute_all(context)
        
        # Should have results for all stages
        assert len(result["stages"]) == 3
        
        # Stage 1: Success
        assert "result" in result["stages"][0]
        assert result["stages"][0]["stage_number"] == 1
        
        # Stage 2: Error
        assert "error" in result["stages"][1]
        assert result["stages"][1]["stage_number"] == 2
        assert "Stage 2 failed" in result["stages"][1]["error"]
        
        # Stage 3: Success (should continue despite stage 2 failure)
        assert "result" in result["stages"][2]
        assert result["stages"][2]["stage_number"] == 3


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_identifiers(self):
        """Test handling of empty identifier lists."""
        wrapper = ProgressiveWrapper(1, "empty_test")
        mock_action = MockAction()
        
        params = {"identifiers": []}
        context = {}
        
        result = await wrapper.execute_stage(mock_action, params, context)
        
        assert result["input_identifiers"] == []
        assert result["output_identifiers"] == []
    
    @pytest.mark.asyncio
    async def test_no_identifiers_in_params(self):
        """Test handling when no identifiers are found in parameters."""
        wrapper = ProgressiveWrapper(1, "no_ids_test")
        mock_action = MockAction()
        
        params = {"some_other_param": "value"}
        context = {}
        
        result = await wrapper.execute_stage(mock_action, params, context)
        
        # Should handle gracefully with empty identifiers
        assert result["input_identifiers"] == []
    
    def test_context_type_variations(self):
        """Test different context types (dict, object, adapter)."""
        wrapper = ProgressiveWrapper(1, "context_test")
        
        # Test dict context
        dict_context = {"test_key": "test_value"}
        ctx1 = UniversalContext.wrap(dict_context)
        wrapper._initialize_progressive_stats(ctx1)
        assert ctx1.has_key("progressive_stats")
        
        # Test object context
        class MockContext:
            def __init__(self):
                self.test_key = "test_value"
        
        obj_context = MockContext()
        ctx2 = UniversalContext.wrap(obj_context)
        wrapper._initialize_progressive_stats(ctx2)
        assert hasattr(obj_context, "_fallback_dict") or hasattr(obj_context, "progressive_stats")
    
    def test_malformed_result_handling(self):
        """Test handling of malformed action results."""
        wrapper = ProgressiveWrapper(1, "malformed_test")
        
        # Test with missing expected fields
        malformed_result = {"unexpected_field": "value"}
        matched = wrapper._extract_matched_identifiers(malformed_result)
        assert len(matched) == 0
        
        # Test with non-list identifier fields
        malformed_result2 = {"output_identifiers": "single_string"}
        matched2 = wrapper._extract_matched_identifiers(malformed_result2)
        assert matched2 == {"single_string"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])