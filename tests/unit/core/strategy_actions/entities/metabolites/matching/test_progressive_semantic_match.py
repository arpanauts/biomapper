"""
Test suite for PROGRESSIVE_SEMANTIC_MATCH Stage 2 wrapper.
Tests conservative thresholds and biological accuracy focus.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from actions.entities.metabolites.matching.progressive_semantic_match import (
    ProgressiveSemanticMatch,
    ProgressiveSemanticMatchParams,
)


class TestProgressiveSemanticMatch:
    """Test suite for progressive semantic matching (Stage 2)."""
    
    @pytest.fixture
    def stage1_unmapped_data(self) -> List[Dict[str, Any]]:
        """Sample unmapped metabolites from Stage 1."""
        return [
            {
                "name": "Total cholesterol",
                "csv_name": "Total_C",
                "original_name": "Total-C",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "LDL cholesterol",
                "csv_name": "LDL_C",
                "original_name": "LDL-C",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "HDL cholesterol",
                "csv_name": "HDL_C",
                "original_name": "HDL-C",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "Triglycerides",
                "csv_name": "Serum_TG",
                "original_name": "Serum-TG",
                "for_stage": 2,
                "reason": "no_external_id"
            },
            {
                "name": "Glucose",
                "csv_name": "Glucose",
                "original_name": "Glucose",
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
                "synonyms": ["Total cholesterol", "Blood cholesterol"],
                "category": "Sterol Lipids"
            },
            {
                "id": "HMDB0000564",
                "name": "Low density lipoprotein",
                "description": "LDL cholesterol",
                "synonyms": ["LDL-C", "Bad cholesterol"],
                "category": "Lipoproteins"
            },
            {
                "id": "HMDB0000268",
                "name": "High density lipoprotein",
                "description": "HDL cholesterol",
                "synonyms": ["HDL-C", "Good cholesterol"],
                "category": "Lipoproteins"
            },
            {
                "id": "HMDB0000177",
                "name": "Triglyceride",
                "description": "Triglycerides in serum",
                "synonyms": ["TG", "Serum triglycerides"],
                "category": "Glycerolipids"
            },
            {
                "id": "HMDB0000122",
                "name": "D-Glucose",
                "description": "Blood glucose",
                "synonyms": ["Glucose", "Blood sugar"],
                "category": "Carbohydrates"
            }
        ]
    
    @pytest.fixture
    def mock_context(self, stage1_unmapped_data, reference_metabolites):
        """Mock execution context with Stage 1 results."""
        context = {
            "datasets": {
                "nightingale_matched": [
                    {"name": "Alanine", "pubchem_id": "5950", "confidence": 0.98}
                ] * 38,  # 38 matched from Stage 1
                "nightingale_unmapped": stage1_unmapped_data + [
                    {"name": "Protein1", "uniprot_id": "P12345", "reason": "protein_not_metabolite"}
                ],
                "reference_metabolites": reference_metabolites
            },
            "statistics": {
                "nightingale_bridge": {
                    "stage": 1,
                    "coverage": 0.152,
                    "matched": 38,
                    "name_only_for_stage2": 5
                }
            }
        }
        return context
    
    @pytest.mark.asyncio
    async def test_conservative_thresholds(self, mock_context):
        """Test that conservative thresholds are applied correctly."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams(
            confidence_threshold=0.85,  # Conservative
            embedding_similarity_threshold=0.90,  # Conservative
            max_llm_calls=50
        )
        
        # Mock the semantic matching action
        with patch('actions.entities.metabolites.matching.progressive_semantic_match.SemanticMetaboliteMatchAction') as MockSemantic:
            mock_semantic = MockSemantic.return_value
            mock_semantic.execute_typed = AsyncMock(return_value=Mock(
                success=True,
                data={"llm_calls": 5, "cache_hits": 2}
            ))
            
            # Set up mock results
            mock_context["datasets"]["semantic_matched_semantic"] = [
                {
                    "name": "Total cholesterol",
                    "matched_name": "Cholesterol",
                    "match_confidence": 0.92,
                    "match_method": "semantic_llm"
                }
            ]
            mock_context["datasets"]["semantic_matched_semantic_unmapped"] = [
                {"name": "LDL cholesterol"},
                {"name": "HDL cholesterol"},
                {"name": "Triglycerides"},
                {"name": "Glucose"}
            ]
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
            
            # Verify conservative thresholds were passed
            call_args = mock_semantic.execute_typed.call_args
            semantic_params = call_args[1]["params"]
            assert semantic_params.confidence_threshold == 0.85
            assert semantic_params.embedding_similarity_threshold == 0.90
    
    @pytest.mark.asyncio  
    async def test_fuzzy_fallback(self, mock_context):
        """Test fuzzy matching fallback for unmapped metabolites."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams(
            enable_fuzzy_fallback=True,
            fuzzy_threshold=0.85
        )
        
        # Test fuzzy matching directly
        unmapped = [
            {"name": "HDL cholesterol"},
            {"name": "Triglycerides"}
        ]
        reference = mock_context["datasets"]["reference_metabolites"]
        
        matched, still_unmapped = await action.apply_fuzzy_fallback(
            unmapped, reference, params.fuzzy_threshold
        )
        
        # Should match both with high fuzzy scores
        assert len(matched) >= 1  # At least one should match
        if matched:
            assert matched[0]["match_method"] == "fuzzy_fallback"
            assert matched[0]["match_confidence"] <= 0.8  # Scaled down
    
    @pytest.mark.asyncio
    async def test_cumulative_coverage_calculation(self, mock_context):
        """Test that cumulative coverage is calculated correctly."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams()
        
        with patch('actions.entities.metabolites.matching.progressive_semantic_match.SemanticMetaboliteMatchAction') as MockSemantic:
            mock_semantic = MockSemantic.return_value
            mock_semantic.execute_typed = AsyncMock(return_value=Mock(
                success=True,
                data={"llm_calls": 3, "cache_hits": 0}
            ))
            
            # Set up results: 3 semantic matches
            mock_context["datasets"]["semantic_matched_semantic"] = [
                {"name": "Total cholesterol", "match_confidence": 0.90},
                {"name": "LDL cholesterol", "match_confidence": 0.88},
                {"name": "HDL cholesterol", "match_confidence": 0.87}
            ]
            mock_context["datasets"]["semantic_matched_semantic_unmapped"] = [
                {"name": "Triglycerides"},
                {"name": "Glucose"}
            ]
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
            
            # Stage 1: 38/250 = 15.2%
            # Stage 2: 3 more matched
            # Cumulative: (38+3)/250 = 16.4%
            assert result.success
            assert result.semantic_matched == 3
            expected_coverage = (38 + 3) / 250
            assert abs(result.cumulative_coverage - expected_coverage) < 0.01
    
    @pytest.mark.asyncio
    async def test_confidence_distribution(self, mock_context):
        """Test confidence score distribution tracking."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams(
            enable_fuzzy_fallback=True
        )
        
        with patch('actions.entities.metabolites.matching.progressive_semantic_match.SemanticMetaboliteMatchAction') as MockSemantic:
            mock_semantic = MockSemantic.return_value
            mock_semantic.execute_typed = AsyncMock(return_value=Mock(
                success=True,
                data={"llm_calls": 4, "cache_hits": 1}
            ))
            
            # Set up varied confidence scores
            mock_context["datasets"]["semantic_matched_semantic"] = [
                {"name": "Total cholesterol", "match_confidence": 0.95},  # High
                {"name": "LDL cholesterol", "match_confidence": 0.88},    # Medium
                {"name": "HDL cholesterol", "match_confidence": 0.82}     # Low
            ]
            mock_context["datasets"]["semantic_matched_semantic_unmapped"] = [
                {"name": "Triglycerides"}
            ]
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
            
            # Check distribution
            assert "high_0.9+" in result.confidence_distribution
            assert "medium_0.85-0.9" in result.confidence_distribution
            assert "low_0.8-0.85" in result.confidence_distribution
            assert result.confidence_distribution["high_0.9+"] == 1
            assert result.confidence_distribution["medium_0.85-0.9"] == 1
            assert result.confidence_distribution["low_0.8-0.85"] == 1
    
    @pytest.mark.asyncio
    async def test_no_stage2_candidates(self):
        """Test handling when no Stage 2 candidates exist."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams()
        
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
        assert result.semantic_matched == 0
        assert "No Stage 2 candidates" in result.message
    
    @pytest.mark.asyncio
    async def test_cache_directory_creation(self, mock_context):
        """Test that cache directory is created and set."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams(
            cache_dir="/tmp/test_semantic_cache"
        )
        
        with patch('os.makedirs') as mock_makedirs, \
             patch.dict('os.environ', {}, clear=False) as mock_env, \
             patch('actions.entities.metabolites.matching.progressive_semantic_match.SemanticMetaboliteMatchAction') as MockSemantic:
            
            mock_semantic = MockSemantic.return_value
            mock_semantic.execute_typed = AsyncMock(return_value=Mock(
                success=True,
                data={"llm_calls": 0, "cache_hits": 0}
            ))
            
            mock_context["datasets"]["semantic_matched_semantic"] = []
            mock_context["datasets"]["semantic_matched_semantic_unmapped"] = []
            
            await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
            
            # Verify cache directory setup
            mock_makedirs.assert_called_with("/tmp/test_semantic_cache", exist_ok=True)
            assert mock_env.get("SEMANTIC_MATCH_CACHE_DIR") == "/tmp/test_semantic_cache"
    
    @pytest.mark.asyncio
    async def test_biological_accuracy_priority(self, mock_context):
        """Test that biological accuracy is prioritized over coverage."""
        action = ProgressiveSemanticMatch()
        params = ProgressiveSemanticMatchParams(
            confidence_threshold=0.90,  # Very conservative
            embedding_similarity_threshold=0.95,  # Very conservative
            max_llm_calls=10,  # Limited calls
            enable_fuzzy_fallback=False  # Disable fuzzy for strict testing
        )
        
        with patch('actions.entities.metabolites.matching.progressive_semantic_match.SemanticMetaboliteMatchAction') as MockSemantic:
            mock_semantic = MockSemantic.return_value
            mock_semantic.execute_typed = AsyncMock(return_value=Mock(
                success=True,
                data={"llm_calls": 10, "cache_hits": 0}
            ))
            
            # Only high-confidence matches accepted
            mock_context["datasets"]["semantic_matched_semantic"] = [
                {"name": "Total cholesterol", "match_confidence": 0.95}
            ]
            mock_context["datasets"]["semantic_matched_semantic_unmapped"] = [
                {"name": "LDL cholesterol"},  # Will be unmapped due to disabled fuzzy
                {"name": "HDL cholesterol"},
                {"name": "Triglycerides"},
                {"name": "Glucose"}
            ]
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
            
            # Only 1 high-confidence semantic match accepted
            assert result.semantic_matched == 1
            assert result.fuzzy_matched == 0  # Fuzzy disabled
            assert result.still_unmapped == 4
            # Lower coverage but higher accuracy
            assert result.cumulative_coverage < 0.20  # Less than 20% is acceptable for accuracy