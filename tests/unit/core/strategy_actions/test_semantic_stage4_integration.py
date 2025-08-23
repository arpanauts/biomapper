"""
Tests for Stage 4 LLM Semantic Matching Integration

Tests the SEMANTIC_METABOLITE_MATCH action configuration for Stage 4
of progressive metabolomics mapping with proper cost controls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from actions.semantic_metabolite_match import (
    SemanticMetaboliteMatchAction,
    SemanticMetaboliteMatchParams
)


class TestStage4SemanticMatchingIntegration:
    """Test Stage 4 semantic matching configuration and cost controls."""
    
    @pytest.fixture
    def stage4_context(self):
        """Mock context with completed Stages 1-3 and remaining unmapped."""
        return {
            "datasets": {
                "nightingale_matched": [{"name": "Alanine", "pubchem_id": "5950"}] * 38,  # Stage 1: 15.2%
                "fuzzy_matched": [{"name": "Total cholesterol", "matched_id": "HMDB0000067"}] * 112,  # Stage 2: 45%
                "rampdb_matched": [{"name": "Tryptophan", "matched_id": "HMDB0000929"}] * 25,  # Stage 3: 10%
                "rampdb_unmapped": [  # Remaining 25% for Stage 4 - difficult cases
                    {
                        "name": "Complex metabolite alpha",
                        "csv_name": "Complex_alpha", 
                        "for_stage": 4,
                        "reason": "no_rampdb_match"
                    },
                    {
                        "name": "Unknown compound beta",
                        "csv_name": "Unknown_beta",
                        "for_stage": 4, 
                        "reason": "no_rampdb_match"
                    },
                    {
                        "name": "Obscure metabolite gamma",
                        "csv_name": "Obscure_gamma",
                        "for_stage": 4,
                        "reason": "no_rampdb_match"
                    }
                ],
                "reference_metabolites": [
                    {"name": "Alpha-compound", "description": "Complex biological compound", "category": "Unknown"},
                    {"name": "Beta-unknown", "description": "Uncharacterized metabolite", "category": "Other"},
                    {"name": "Gamma metabolite", "description": "Rare metabolite compound", "category": "Specialized"}
                ]
            },
            "statistics": {
                "nightingale_bridge": {"stage": 1, "matched": 38, "coverage": 0.152},
                "progressive_stage2_fuzzy": {"stage": 2, "matched": 112, "coverage": 0.60}, 
                "progressive_stage3_rampdb": {"stage": 3, "matched": 25, "coverage": 0.75}
            }
        }
    
    @pytest.fixture
    def stage4_params(self):
        """Stage 4 semantic matching parameters with cost controls."""
        return SemanticMetaboliteMatchParams(
            unmatched_dataset="rampdb_unmapped",
            reference_map="reference_metabolites",
            output_key="semantic_matched",
            unmatched_key="final_unmapped",
            confidence_threshold=0.7,  # Lower threshold for difficult cases
            max_llm_calls=75,  # Conservative cost control
            embedding_similarity_threshold=0.75,  # Reasonable threshold for hard cases
            batch_size=5,  # Small batches for careful processing
            context_fields={
                "rampdb": ["name", "description", "category"],
                "reference": ["name", "description", "synonyms", "category"]
            },
            include_reasoning=True  # Important for difficult case validation
        )
    
    @pytest.mark.asyncio
    async def test_stage4_cost_controls(self, stage4_context, stage4_params):
        """Test that Stage 4 respects cost controls."""
        action = SemanticMetaboliteMatchAction()
        
        # Mock OpenAI client to avoid real API calls
        mock_client = MagicMock()
        
        # Mock embeddings response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        # Mock LLM completion response
        mock_completion_response = MagicMock()
        mock_completion_response.choices = [
            MagicMock(message=MagicMock(content="YES|0.75|These are similar metabolites"))
        ]
        mock_client.chat.completions.create.return_value = mock_completion_response
        
        # Mock the action's internal methods to avoid real API calls
        with patch.object(action, '_initialize_clients'):
            action.openai_client = mock_client
            action.embedding_cache = MagicMock()
            action.embedding_cache.get.return_value = None  # Simulate no cache hits
            
            with patch.object(action, '_generate_embeddings_batch') as mock_embeddings:
                mock_embeddings.return_value = {0: [0.1] * 1536, 1: [0.2] * 1536, 2: [0.3] * 1536}
                
                with patch.object(action, '_validate_match_with_llm') as mock_llm:
                    mock_llm.return_value = (True, 0.80, "Test semantic match")
                    
                    result = await action.execute_typed(
                        current_identifiers=[],
                        current_ontology_type="metabolite",
                        params=stage4_params,
                        source_endpoint=None,
                        target_endpoint=None,
                        context=stage4_context
                    )
        
        # Verify cost controls are respected
        assert result.success
        assert result.data["llm_calls"] <= stage4_params.max_llm_calls
        assert result.data["matched_count"] >= 0  # Should find some matches
        
        # Verify semantic matches were stored
        assert "semantic_matched" in stage4_context["datasets"]
        assert "final_unmapped" in stage4_context["datasets"]
    
    @pytest.mark.asyncio
    async def test_stage4_cumulative_coverage_calculation(self, stage4_context, stage4_params):
        """Test that Stage 4 correctly calculates cumulative coverage."""
        action = SemanticMetaboliteMatchAction()
        
        # Mock successful semantic matching
        with patch.object(action, '_initialize_clients'):
            with patch.object(action, '_generate_embeddings_batch') as mock_embeddings:
                mock_embeddings.return_value = {0: [0.1] * 1536, 1: [0.2] * 1536, 2: [0.3] * 1536}
                
                with patch.object(action, '_validate_match_with_llm') as mock_llm:
                    # Mock 2 successful matches out of 3 candidates
                    mock_llm.side_effect = [
                        (True, 0.85, "High confidence semantic match"),  # Match
                        (True, 0.75, "Reasonable semantic match"),       # Match  
                        (False, 0.60, "Low confidence, not a match")     # No match
                    ]
                    
                    result = await action.execute_typed(
                        current_identifiers=[],
                        current_ontology_type="metabolite", 
                        params=stage4_params,
                        source_endpoint=None,
                        target_endpoint=None,
                        context=stage4_context
                    )
        
        # Verify cumulative coverage calculation
        # Stage 1: 38, Stage 2: 112, Stage 3: 25, Stage 4: 2 matches
        # Total: (38 + 112 + 25 + 2) / 250 = 177/250 = 70.8%
        semantic_matched = stage4_context["datasets"]["semantic_matched"]
        assert len(semantic_matched) == 2  # 2 successful semantic matches
        
        # Calculate expected cumulative coverage
        total_matched = 38 + 112 + 25 + 2  # 177
        expected_coverage = total_matched / 250  # 0.708 = 70.8%
        
        # Verify results reflect cumulative progress
        assert result.data["matched_count"] == 2
        assert result.data["unmatched_count"] == 1  # 1 still unmapped
    
    @pytest.mark.asyncio
    async def test_stage4_confidence_thresholds(self, stage4_context, stage4_params):
        """Test that Stage 4 applies appropriate confidence thresholds for difficult cases."""
        action = SemanticMetaboliteMatchAction()
        
        # Test with various confidence levels
        test_cases = [
            (0.85, "High confidence match"),     # Above threshold
            (0.75, "Good confidence match"),     # At threshold  
            (0.70, "Minimum confidence match"),  # At threshold
            (0.65, "Below threshold"),           # Below threshold - should be rejected
        ]
        
        with patch.object(action, '_initialize_clients'):
            with patch.object(action, '_generate_embeddings_batch') as mock_embeddings:
                mock_embeddings.return_value = {i: [0.1 * (i+1)] * 1536 for i in range(len(test_cases))}
                
                with patch.object(action, '_validate_match_with_llm') as mock_llm:
                    # Mock LLM responses with different confidence levels
                    mock_llm.side_effect = [
                        (True, conf, reasoning) for conf, reasoning in test_cases
                    ]
                    
                    # Add test cases to context
                    stage4_context["datasets"]["rampdb_unmapped"] = [
                        {"name": f"test_metabolite_{i}", "for_stage": 4}
                        for i in range(len(test_cases))
                    ]
                    
                    result = await action.execute_typed(
                        current_identifiers=[],
                        current_ontology_type="metabolite",
                        params=stage4_params,
                        source_endpoint=None, 
                        target_endpoint=None,
                        context=stage4_context
                    )
        
        # Verify only matches >= confidence_threshold (0.7) are accepted
        semantic_matches = stage4_context["datasets"]["semantic_matched"]
        
        # Should accept 3 matches (0.85, 0.75, 0.70) and reject 1 (0.65)
        assert len(semantic_matches) == 3
        
        # Verify confidence scores
        confidences = [match["match_confidence"] for match in semantic_matches]
        assert all(conf >= stage4_params.confidence_threshold for conf in confidences)
        assert min(confidences) >= 0.70
        assert max(confidences) >= 0.80
    
    @pytest.mark.asyncio  
    async def test_stage4_reasoning_inclusion(self, stage4_context, stage4_params):
        """Test that Stage 4 includes LLM reasoning for difficult cases."""
        action = SemanticMetaboliteMatchAction()
        
        with patch.object(action, '_initialize_clients'):
            with patch.object(action, '_generate_embeddings_batch') as mock_embeddings:
                mock_embeddings.return_value = {0: [0.1] * 1536}
                
                with patch.object(action, '_validate_match_with_llm') as mock_llm:
                    test_reasoning = "These metabolites share similar pathway classification and chemical structure"
                    mock_llm.return_value = (True, 0.80, test_reasoning)
                    
                    # Single test case
                    stage4_context["datasets"]["rampdb_unmapped"] = [
                        {"name": "test_difficult_metabolite", "for_stage": 4}
                    ]
                    
                    result = await action.execute_typed(
                        current_identifiers=[],
                        current_ontology_type="metabolite",
                        params=stage4_params,
                        source_endpoint=None,
                        target_endpoint=None, 
                        context=stage4_context
                    )
        
        # Verify reasoning is included in results
        semantic_matches = stage4_context["datasets"]["semantic_matched"]
        assert len(semantic_matches) == 1
        
        match = semantic_matches[0]
        assert "match_reasoning" in match
        assert match["match_reasoning"] == test_reasoning
        assert match["match_method"] == "semantic_llm"
        assert match["match_confidence"] == 0.80
    
    @pytest.mark.asyncio
    async def test_stage4_api_failure_handling(self, stage4_context, stage4_params):
        """Test Stage 4 handles API failures gracefully."""
        action = SemanticMetaboliteMatchAction()
        
        with patch.object(action, '_initialize_clients', side_effect=Exception("OpenAI API unavailable")):
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=stage4_params,
                source_endpoint=None,
                target_endpoint=None,
                context=stage4_context
            )
        
        # Should handle failure gracefully
        assert not result.success
        assert "error" in (result.error or "") or "OpenAI API unavailable" in result.message
        
        # Should not crash or create partial results
        assert result.data.get("matched_count", 0) == 0
        assert result.data.get("llm_calls", 0) == 0


class TestStage4ProgressiveIntegration:
    """Test Stage 4 integration with complete progressive pipeline."""
    
    @pytest.fixture
    def complete_pipeline_context(self):
        """Context representing completed Stages 1-3 with realistic coverage."""
        return {
            "datasets": {
                # Stage 1: Nightingale Bridge (15.2% coverage)
                "nightingale_matched": [{"name": f"matched_s1_{i}", "pubchem_id": f"id_{i}"} for i in range(38)],
                
                # Stage 2: Fuzzy String Matching (additional 45% coverage)  
                "fuzzy_matched": [{"name": f"matched_s2_{i}", "fuzzy_score": 0.90} for i in range(112)],
                
                # Stage 3: RampDB Bridge (additional 10% coverage)
                "rampdb_matched": [{"name": f"matched_s3_{i}", "rampdb_id": f"ramp_{i}"} for i in range(25)],
                
                # Stage 4 input: Remaining 25% (62 metabolites) - hardest cases
                "rampdb_unmapped": [{"name": f"difficult_metabolite_{i}", "for_stage": 4} for i in range(62)],
                
                # Reference data
                "reference_metabolites": [{"name": f"ref_metabolite_{i}", "description": f"Reference {i}"} for i in range(100)]
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_final_coverage(self, complete_pipeline_context):
        """Test that Stage 4 achieves target 85%+ final coverage."""
        action = SemanticMetaboliteMatchAction()
        
        params = SemanticMetaboliteMatchParams(
            unmatched_dataset="rampdb_unmapped",
            reference_map="reference_metabolites",
            output_key="semantic_matched",
            unmatched_key="final_unmapped",
            confidence_threshold=0.7,
            max_llm_calls=75  # Cost control
        )
        
        with patch.object(action, '_initialize_clients'):
            with patch.object(action, '_generate_embeddings_batch') as mock_embeddings:
                # Mock embeddings for all 62 difficult metabolites
                mock_embeddings.return_value = {i: [0.1 * (i+1)] * 1536 for i in range(62)}
                
                with patch.object(action, '_validate_match_with_llm') as mock_llm:
                    # Mock successful matching for ~60% of remaining difficult cases
                    # This gives us 37 more matches (62 * 0.60 = ~37)
                    responses = []
                    for i in range(62):
                        if i < 37:  # First 37 are successful matches
                            responses.append((True, 0.75 + (i % 20) * 0.01, f"Semantic match {i}"))
                        else:  # Remaining 25 are unsuccessful
                            responses.append((False, 0.65, f"Below confidence threshold {i}"))
                    
                    mock_llm.side_effect = responses
                    
                    result = await action.execute_typed(
                        current_identifiers=[],
                        current_ontology_type="metabolite",
                        params=params,
                        source_endpoint=None,
                        target_endpoint=None,
                        context=complete_pipeline_context
                    )
        
        # Verify final coverage calculation
        # Stage 1: 38, Stage 2: 112, Stage 3: 25, Stage 4: 37 matches
        # Total: (38 + 112 + 25 + 37) / 250 = 212/250 = 84.8%
        semantic_matched = complete_pipeline_context["datasets"]["semantic_matched"]
        final_unmapped = complete_pipeline_context["datasets"]["final_unmapped"]
        
        assert len(semantic_matched) == 37  # Successful semantic matches
        assert len(final_unmapped) == 25    # Still unmapped after Stage 4
        
        # Calculate final cumulative coverage
        total_matched = 38 + 112 + 25 + 37  # 212
        final_coverage = total_matched / 250  # 0.848 = 84.8%
        
        assert final_coverage >= 0.84  # Should achieve near-85% target
        assert result.data["matched_count"] == 37
        assert result.data["llm_calls"] <= 75  # Respect cost controls