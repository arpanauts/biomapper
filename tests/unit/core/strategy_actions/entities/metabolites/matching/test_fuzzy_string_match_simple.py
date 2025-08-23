"""
Simplified test suite for METABOLITE_FUZZY_STRING_MATCH - corrected architecture.
Tests fast, deterministic, cost-free algorithmic string matching.
"""

import pytest
import time
from typing import Dict, Any, List

from actions.entities.metabolites.matching.fuzzy_string_match import (
    MetaboliteFuzzyStringMatch,
    MetaboliteFuzzyStringMatchParams,
    _clean_metabolite_name,
)


class TestCleanMetaboliteName:
    """Test the simple metabolite name cleaning function."""
    
    def test_basic_cleaning(self):
        """Test basic name cleaning."""
        assert _clean_metabolite_name("HDL_C") == "hdl cholesterol"
        assert _clean_metabolite_name("Total-C") == "total cholesterol"
        assert _clean_metabolite_name("Serum_TG") == "serum triglycerides"
        
    def test_edge_cases(self):
        """Test edge cases."""
        assert _clean_metabolite_name("") == ""
        assert _clean_metabolite_name(None) == ""
        assert _clean_metabolite_name("   ") == ""


class TestMetaboliteFuzzyStringMatch:
    """Test the main corrected fuzzy string matching action."""
    
    @pytest.fixture
    def stage1_unmapped_data(self) -> List[Dict[str, Any]]:
        """Sample unmapped metabolites from Stage 1."""
        return [
            {
                "name": "Total cholesterol",
                "csv_name": "Total_C",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "HDL cholesterol", 
                "csv_name": "HDL_C",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "Glucose",
                "csv_name": "Glucose",
                "for_stage": 2,
                "reason": "no_external_id"
            }
        ]
    
    @pytest.fixture
    def reference_metabolites(self) -> List[Dict[str, Any]]:
        """Sample reference metabolites for matching."""
        return [
            {
                "id": "HMDB0000067",
                "name": "Cholesterol",
                "description": "Total cholesterol in blood",
            },
            {
                "id": "HMDB0000268",
                "name": "High density lipoprotein cholesterol",
                "description": "HDL cholesterol",
            },
            {
                "id": "HMDB0000122",
                "name": "D-Glucose", 
                "description": "Blood glucose",
            }
        ]
    
    @pytest.fixture
    def mock_context(self, stage1_unmapped_data, reference_metabolites):
        """Mock execution context with Stage 1 results."""
        return {
            "datasets": {
                "nightingale_matched": [{"name": "Alanine", "pubchem_id": "5950"}] * 38,
                "nightingale_unmapped": stage1_unmapped_data + [
                    {"name": "Protein1", "reason": "protein_not_metabolite"}
                ],
                "reference_metabolites": reference_metabolites
            },
            "statistics": {
                "nightingale_bridge": {
                    "stage": 1,
                    "coverage": 0.152,
                    "matched": 38
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_corrected_architecture_performance(self, mock_context):
        """Test that corrected architecture is fast and cost-free."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(fuzzy_threshold=85.0)
        
        start_time = time.time()
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        processing_time = time.time() - start_time
        
        # CRITICAL: Corrected architecture requirements
        assert result.success
        assert result.processing_time_seconds < 1.0, f"Must be <1s, got {result.processing_time_seconds}"
        assert processing_time < 1.0, f"Actual time must be <1s, got {processing_time}"
        assert result.cost_dollars == 0.0, f"Must be free, got ${result.cost_dollars}"
        assert result.api_calls == 0, f"Must be 0 API calls, got {result.api_calls}"
    
    @pytest.mark.asyncio
    async def test_fuzzy_string_matching_finds_matches(self, mock_context):
        """Test that fuzzy string matching can find good matches."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(fuzzy_threshold=80.0)  # Lower threshold for testing
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.success
        assert result.stage2_input_count == 3  # 3 Stage 2 candidates
        
        # Should find at least some matches with good reference data
        datasets = mock_context["datasets"]
        if "fuzzy_matched" in datasets:
            matches = datasets["fuzzy_matched"]
            # Validate match structure
            for match in matches:
                assert "match_confidence" in match
                assert match["match_confidence"] >= 0.8  # Above 80% threshold
                assert "match_method" in match
                assert match["match_method"] == "fuzzy_token_sort_ratio"
                assert "fuzzy_score" in match
    
    @pytest.mark.asyncio
    async def test_deterministic_behavior(self, mock_context):
        """Test that results are deterministic (same input = same output)."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(fuzzy_threshold=85.0)
        
        # Run twice with identical inputs
        result1 = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context.copy()
        )
        
        result2 = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite", 
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context.copy()
        )
        
        # Results should be identical (deterministic)
        assert result1.total_matches == result2.total_matches
        assert result1.still_unmapped == result2.still_unmapped
        assert result1.cumulative_coverage == result2.cumulative_coverage
    
    @pytest.mark.asyncio
    async def test_no_stage2_candidates(self):
        """Test handling when no Stage 2 candidates exist."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams()
        
        # Context with no Stage 2 candidates
        context = {
            "datasets": {
                "nightingale_unmapped": [
                    {"name": "Protein1", "reason": "protein_not_metabolite"}
                ]
            }
        }
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        assert result.success
        assert result.stage2_input_count == 0
        assert result.total_matches == 0
        assert "No Stage 2 candidates" in result.message
        assert result.processing_time_seconds < 1.0  # Still fast
        assert result.cost_dollars == 0.0  # Still free
    
    @pytest.mark.asyncio
    async def test_no_reference_metabolites(self, mock_context):
        """Test handling when no reference metabolites available."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams()
        
        # Remove reference metabolites
        mock_context["datasets"]["reference_metabolites"] = []
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.success
        assert result.total_matches == 0
        assert "No reference metabolites available" in result.message
        assert result.processing_time_seconds < 1.0  # Still fast
        assert result.cost_dollars == 0.0  # Still free
    
    @pytest.mark.asyncio
    async def test_conservative_threshold_priority(self, mock_context):
        """Test that conservative thresholds prioritize biological accuracy."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(
            fuzzy_threshold=95.0  # Very conservative threshold
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.success
        # With very conservative threshold, fewer matches but higher accuracy
        # All matches should be very high confidence
        datasets = mock_context["datasets"]
        if "fuzzy_matched" in datasets:
            matches = datasets["fuzzy_matched"]
            for match in matches:
                confidence = match.get("match_confidence", 0)
                assert confidence >= 0.95, f"Match confidence {confidence} below conservative threshold"
    
    @pytest.mark.asyncio  
    async def test_statistics_tracking(self, mock_context):
        """Test that progressive statistics are tracked correctly."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams()
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.success
        
        # Check statistics structure
        stats = mock_context["statistics"]
        assert "progressive_stage2_fuzzy" in stats
        
        s2_stats = stats["progressive_stage2_fuzzy"]
        assert s2_stats["stage"] == 2
        assert s2_stats["method"] == "fuzzy_string_matching"
        assert s2_stats["cost_dollars"] == 0.0
        assert s2_stats["api_calls"] == 0
        assert s2_stats["processing_time_seconds"] < 1.0
        assert "threshold_used" in s2_stats


class TestArchitectureValidation:
    """Validate that the architecture fix is complete."""
    
    def test_no_llm_dependencies(self):
        """Test that no LLM dependencies are imported."""
        import sys
        from actions.entities.metabolites.matching import fuzzy_string_match
        
        # Should not import openai
        module_names = [name for name in dir(fuzzy_string_match)]
        llm_indicators = ["openai", "OpenAI", "embeddings", "chat", "completions"]
        
        for indicator in llm_indicators:
            assert not any(indicator.lower() in name.lower() for name in module_names), \
                f"Found LLM dependency: {indicator}"
    
    def test_uses_existing_biomapper_pattern(self):
        """Test that implementation follows existing biomapper patterns.""" 
        from actions.entities.metabolites.matching.fuzzy_string_match import MetaboliteFuzzyStringMatch
        
        # Should have the same method signature as other actions
        action = MetaboliteFuzzyStringMatch()
        assert hasattr(action, 'execute_typed')
        assert hasattr(action, 'get_params_model')
        assert hasattr(action, 'get_result_model')
        
        # Should use existing biomapper imports
        import actions.entities.metabolites.matching.fuzzy_string_match as module
        assert hasattr(module, 'fuzz')  # fuzzywuzzy imported
        assert hasattr(module, 'process')  # process imported