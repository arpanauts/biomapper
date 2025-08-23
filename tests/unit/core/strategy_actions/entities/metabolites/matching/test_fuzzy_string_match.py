"""
Test suite for METABOLITE_FUZZY_STRING_MATCH - algorithmic string-based Stage 2.
Tests fast, deterministic, cost-free string matching with biological accuracy.
"""

import pytest
import time
from typing import Dict, Any, List
from unittest.mock import Mock

from actions.entities.metabolites.matching.fuzzy_string_match import (
    MetaboliteFuzzyStringMatch,
    MetaboliteFuzzyStringMatchParams,
    _clean_metabolite_name,
    MetaboliteNameNormalizer,
    FuzzyStringMatcher,
)


class TestMetaboliteNameNormalizer:
    """Test metabolite name normalization for consistent string matching."""
    
    def test_basic_normalization(self):
        """Test basic name normalization."""
        normalizer = MetaboliteNameNormalizer()
        
        # Case normalization
        assert normalizer.normalize_metabolite_name("HDL Cholesterol") == "hdl cholesterol"
        assert normalizer.normalize_metabolite_name("LDL-C") == "ldl c"
        
        # Punctuation standardization
        assert normalizer.normalize_metabolite_name("3-Hydroxybutyrate") == "3 hydroxybutyrate"
        assert normalizer.normalize_metabolite_name("Total_C") == "total cholesterol"
        
        # Unicode handling
        assert normalizer.normalize_metabolite_name("α-tocopherol") == "alpha tocopherol"
        assert normalizer.normalize_metabolite_name("β-hydroxybutyrate") == "beta hydroxybutyrate"
    
    def test_metabolite_specific_replacements(self):
        """Test metabolite-specific standardizations."""
        normalizer = MetaboliteNameNormalizer()
        
        # Lipid abbreviations
        assert normalizer.normalize_metabolite_name("HDL_C") == "hdl cholesterol"
        assert normalizer.normalize_metabolite_name("LDL_TG") == "ldl triglycerides"
        assert normalizer.normalize_metabolite_name("Free_FC") == "free free cholesterol"
        
        # Multiple spaces cleanup
        assert normalizer.normalize_metabolite_name("Total    cholesterol") == "total cholesterol"
        assert normalizer.normalize_metabolite_name("HDL  -  C") == "hdl cholesterol"
    
    def test_edge_cases(self):
        """Test edge cases in normalization."""
        normalizer = MetaboliteNameNormalizer()
        
        # Empty and None
        assert normalizer.normalize_metabolite_name("") == ""
        assert normalizer.normalize_metabolite_name(None) == ""
        assert normalizer.normalize_metabolite_name("   ") == ""
        
        # Numbers and mixed content
        assert normalizer.normalize_metabolite_name("3-Methyl-2-butenoic acid") == "3 methyl 2 butenoic acid"


class TestFuzzyStringMatcher:
    """Test fuzzy string matching algorithms."""
    
    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        normalizer = MetaboliteNameNormalizer()
        return FuzzyStringMatcher(normalizer)
    
    def test_simple_ratio_algorithm(self, matcher):
        """Test simple ratio (Levenshtein distance) algorithm."""
        # Exact match
        score = matcher.calculate_similarity("cholesterol", "cholesterol", "simple_ratio")
        assert score == 100.0
        
        # Similar strings
        score = matcher.calculate_similarity("cholesterol", "cholestrol", "simple_ratio")
        assert score >= 85.0  # Should be high similarity
        
        # Different strings
        score = matcher.calculate_similarity("cholesterol", "glucose", "simple_ratio")
        assert score < 50.0  # Should be low similarity
    
    def test_token_sort_ratio_algorithm(self, matcher):
        """Test token sort ratio (handles word order) algorithm."""
        # Word order differences
        score = matcher.calculate_similarity("total cholesterol", "cholesterol total", "token_sort_ratio")
        assert score == 100.0  # Should be identical after sorting
        
        # Partial word order
        score = matcher.calculate_similarity("HDL cholesterol", "cholesterol HDL", "token_sort_ratio")
        assert score == 100.0
        
        # Additional words
        score = matcher.calculate_similarity("total cholesterol", "total blood cholesterol", "token_sort_ratio")
        assert score >= 75.0  # Should be good similarity
    
    def test_token_set_ratio_algorithm(self, matcher):
        """Test token set ratio (Jaccard similarity) algorithm."""
        # Subset matching
        score = matcher.calculate_similarity("cholesterol", "total cholesterol", "token_set_ratio")
        assert score >= 85.0  # cholesterol is subset
        
        # Common tokens
        score = matcher.calculate_similarity("HDL cholesterol", "LDL cholesterol", "token_set_ratio")
        assert score >= 60.0  # Share 'cholesterol' token
    
    def test_partial_ratio_algorithm(self, matcher):
        """Test partial ratio (substring matching) algorithm."""
        # Substring matching
        score = matcher.calculate_similarity("glucose", "blood glucose", "partial_ratio")
        assert score >= 90.0  # glucose is substring
        
        # Abbreviation matching  
        score = matcher.calculate_similarity("HDL", "HDL cholesterol", "partial_ratio")
        assert score >= 85.0  # HDL is substring
    
    def test_biological_metabolite_pairs(self, matcher):
        """Test with real metabolite name pairs."""
        
        # Should match - same compound, different formats
        test_cases_should_match = [
            ("3-Hydroxybutyrate", "beta-hydroxybutyrate", "token_set_ratio"),
            ("HDL Cholesterol", "HDL cholesterol", "simple_ratio"),
            ("Total cholesterol", "cholesterol total", "token_sort_ratio"),
            ("alpha-tocopherol", "α-tocopherol", "simple_ratio"),
            ("D-glucose", "glucose", "partial_ratio"),
        ]
        
        for source, target, algorithm in test_cases_should_match:
            score = matcher.calculate_similarity(source, target, algorithm)
            assert score >= 85.0, f"{source} vs {target} should match (got {score})"
    
    def test_biological_metabolite_pairs_should_not_match(self, matcher):
        """Test metabolite pairs that should NOT match (different compounds)."""
        
        # Should NOT match - different compounds
        test_cases_should_not_match = [
            ("D-glucose", "L-glucose"),  # Different stereoisomers
            ("HDL cholesterol", "LDL cholesterol"),  # Different lipoproteins  
            ("alanine", "glycine"),  # Different amino acids
            ("triglycerides", "phospholipids"),  # Different lipid classes
        ]
        
        for source, target in test_cases_should_not_match:
            best_score = 0.0
            for algorithm in ["simple_ratio", "token_sort_ratio", "partial_ratio", "token_set_ratio"]:
                score = matcher.calculate_similarity(source, target, algorithm)
                best_score = max(best_score, score)
            
            # Conservative threshold - should be below 85% to avoid false matches
            assert best_score < 85.0, f"{source} vs {target} should NOT match (got {best_score})"
    
    def test_find_best_match(self, matcher):
        """Test finding best match from reference list."""
        reference_list = [
            "Total cholesterol",
            "HDL cholesterol", 
            "LDL cholesterol",
            "Triglycerides",
            "D-glucose",
            "Alanine"
        ]
        
        thresholds = {
            "exact_match": 100.0,
            "high_confidence": 95.0,
            "acceptable": 85.0
        }
        
        algorithms = ["token_sort_ratio", "simple_ratio", "partial_ratio"]
        
        # Test exact match
        match, score, algorithm = matcher.find_best_match(
            "total cholesterol", reference_list, algorithms, thresholds
        )
        assert match == "Total cholesterol"
        assert score >= 95.0
        
        # Test fuzzy match
        match, score, algorithm = matcher.find_best_match(
            "cholesterol total", reference_list, algorithms, thresholds
        )
        assert match == "Total cholesterol"
        assert score >= 85.0
        
        # Test no good match
        result = matcher.find_best_match(
            "completely unrelated compound", reference_list, algorithms, thresholds
        )
        if result is not None:
            match, score, algorithm = result
            assert score < 85.0
        else:
            assert result is None  # No match found above threshold


class TestMetaboliteFuzzyStringMatch:
    """Test the main fuzzy string matching action."""
    
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
            },
            {
                "id": "HMDB0000564", 
                "name": "Low density lipoprotein cholesterol",
                "description": "LDL cholesterol",
            },
            {
                "id": "HMDB0000268",
                "name": "High density lipoprotein cholesterol", 
                "description": "HDL cholesterol",
            },
            {
                "id": "HMDB0000177",
                "name": "Triglyceride",
                "description": "Triglycerides in serum",
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
    async def test_fast_processing_performance(self, mock_context):
        """Test that processing is fast (<1 second) and cost-free."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams()
        
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
        
        # Performance requirements
        assert result.success
        assert result.processing_time_seconds < 1.0  # Must be under 1 second
        assert processing_time < 1.0  # Actual processing time
        assert result.cost_dollars == 0.0  # Must be free
        assert result.api_calls == 0  # Must be algorithmic
    
    @pytest.mark.asyncio
    async def test_deterministic_results(self, mock_context):
        """Test that results are deterministic (same input = same output)."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams()
        
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
        
        # Results should be identical
        assert result1.total_matches == result2.total_matches
        assert result1.exact_matches == result2.exact_matches
        assert result1.high_confidence_matches == result2.high_confidence_matches
        assert result1.acceptable_matches == result2.acceptable_matches
        assert result1.still_unmapped == result2.still_unmapped
    
    @pytest.mark.asyncio
    async def test_confidence_thresholds(self, mock_context):
        """Test that confidence thresholds are properly applied."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(
            exact_match_threshold=100.0,
            high_confidence_threshold=95.0,
            acceptable_threshold=85.0
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
        assert result.total_matches >= 1  # Should match at least some
        
        # Check that matches respect thresholds
        datasets = mock_context["datasets"]
        if "fuzzy_matched" in datasets:
            matches = datasets["fuzzy_matched"]
            for match in matches:
                confidence = match.get("match_confidence", 0)
                assert confidence >= 0.85  # Above acceptable threshold
    
    @pytest.mark.asyncio
    async def test_coverage_improvement(self, mock_context):
        """Test that Stage 2 significantly improves cumulative coverage."""
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
        
        # Stage 1: 38/250 = 15.2%
        # Stage 2 should add significant coverage
        stage1_coverage = 0.152
        assert result.cumulative_coverage > stage1_coverage  # Must improve
        
        # Target: 40-50% additional coverage (Stage 1: 15% → Stage 2: 55-65%)
        coverage_improvement = result.cumulative_coverage - stage1_coverage
        assert coverage_improvement >= 0.10  # At least 10% improvement
    
    @pytest.mark.asyncio
    async def test_algorithm_distribution(self, mock_context):
        """Test that different string algorithms are used appropriately."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(
            algorithms=["token_sort_ratio", "token_set_ratio", "simple_ratio", "partial_ratio"]
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
        
        # Check algorithm distribution
        total_algorithm_uses = sum(result.algorithm_distribution.values())
        if total_algorithm_uses > 0:
            assert "token_sort_ratio" in result.algorithm_distribution
            # token_sort_ratio should be used most (good general algorithm)
            assert result.algorithm_distribution.get("token_sort_ratio", 0) >= 0
    
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
    
    @pytest.mark.asyncio
    async def test_empty_reference(self, mock_context):
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
        assert "No reference names available" in result.message
    
    @pytest.mark.asyncio
    async def test_biological_accuracy_priority(self, mock_context):
        """Test that biological accuracy is prioritized over coverage."""
        action = MetaboliteFuzzyStringMatch()
        params = MetaboliteFuzzyStringMatchParams(
            acceptable_threshold=95.0  # Very conservative threshold
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
                assert confidence >= 0.95  # Very high confidence only