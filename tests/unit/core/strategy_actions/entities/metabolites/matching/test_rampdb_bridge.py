"""
Tests for METABOLITE_RAMPDB_BRIDGE - Stage 3 Progressive Metabolite Matching

STATUS: External RampDB API integration not implemented
FUNCTIONALITY: RampDB API bridge for metabolite matching  
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use core metabolite matching actions (fuzzy, vector, semantic)

These tests are skipped as RampDB API integration is not currently implemented.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Skip entire module - external RampDB API integration not implemented
pytestmark = pytest.mark.skip("External RampDB API integrations not implemented - use core metabolite matching actions")

from actions.entities.metabolites.matching.rampdb_bridge import (
    MetaboliteRampdbBridge,
    MetaboliteRampdbBridgeParams
)
from actions.entities.metabolites.external.ramp_client_modern import MetaboliteMatch


class TestMetaboliteRampdbBridgeParams:
    """Test parameter validation for RampDB bridge."""
    
    def test_default_parameters(self):
        """Test default parameter values."""
        params = MetaboliteRampdbBridgeParams()
        
        assert params.unmapped_key == "fuzzy_unmapped"
        assert params.output_key == "rampdb_matched"
        assert params.confidence_threshold == 0.8
        assert params.batch_size == 10
        assert params.max_requests_per_second == 5.0
        assert params.api_timeout == 30
    
    def test_parameter_validation(self):
        """Test parameter validation constraints."""
        # Valid parameters
        params = MetaboliteRampdbBridgeParams(
            confidence_threshold=0.85,
            batch_size=15,
            max_requests_per_second=3.0
        )
        assert params.confidence_threshold == 0.85
        assert params.batch_size == 15
        assert params.max_requests_per_second == 3.0
        
        # Test edge cases
        with pytest.raises(ValueError):
            MetaboliteRampdbBridgeParams(confidence_threshold=1.5)  # > 1.0
            
        with pytest.raises(ValueError):
            MetaboliteRampdbBridgeParams(batch_size=0)  # < 1


class TestMetaboliteRampdbBridge:
    """Test the main RampDB bridge action."""
    
    @pytest.fixture
    def stage2_unmapped_data(self) -> List[Dict[str, Any]]:
        """Sample unmapped metabolites from Stage 2."""
        return [
            {
                "name": "Tryptophan",
                "csv_name": "Trp", 
                "for_stage": 3,
                "reason": "no_fuzzy_match"
            },
            {
                "name": "Phenylalanine",
                "csv_name": "Phe",
                "for_stage": 3,
                "reason": "no_fuzzy_match"
            },
            {
                "name": "Tyrosine", 
                "csv_name": "Tyr",
                "for_stage": 3,
                "reason": "no_fuzzy_match"
            },
            {
                "name": "Unknown_metabolite_X",
                "csv_name": "Unknown_X",
                "for_stage": 3,
                "reason": "no_fuzzy_match"
            }
        ]
    
    @pytest.fixture
    def mock_rampdb_matches(self) -> List[MetaboliteMatch]:
        """Mock RampDB matches for testing."""
        return [
            MetaboliteMatch(
                query_name="Tryptophan",
                matched_id="HMDB0000929",
                matched_name="L-Tryptophan",
                database_source="HMDB",
                confidence_score=0.90,
                pathways_count=5,
                chemical_class="Amino acid",
                match_method="rampdb_cross_reference"
            ),
            MetaboliteMatch(
                query_name="Phenylalanine", 
                matched_id="HMDB0000159",
                matched_name="L-Phenylalanine",
                database_source="HMDB",
                confidence_score=0.88,
                pathways_count=8,
                chemical_class="Amino acid",
                match_method="rampdb_cross_reference"
            ),
            MetaboliteMatch(
                query_name="Tyrosine",
                matched_id="HMDB0000158", 
                matched_name="L-Tyrosine",
                database_source="HMDB",
                confidence_score=0.85,
                pathways_count=6,
                chemical_class="Amino acid",
                match_method="rampdb_cross_reference"
            )
        ]
    
    @pytest.fixture
    def mock_context(self, stage2_unmapped_data):
        """Mock execution context with Stage 2 results."""
        return {
            "datasets": {
                "nightingale_matched": [{"name": "Alanine", "pubchem_id": "5950"}] * 38,
                "fuzzy_matched": [{"name": "Total cholesterol", "matched_id": "HMDB0000067"}] * 112,
                "fuzzy_unmapped": stage2_unmapped_data
            },
            "statistics": {
                "nightingale_bridge": {"stage": 1, "coverage": 0.152, "matched": 38},
                "progressive_stage2_fuzzy": {"stage": 2, "coverage": 0.60, "matched": 112}
            }
        }
    
    @pytest.mark.asyncio
    async def test_stage3_rampdb_processing(self, mock_context, mock_rampdb_matches):
        """Test Stage 3 RampDB processing with successful matches."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams(
            confidence_threshold=0.85,
            batch_size=10
        )
        
        # Mock the entire RampDB matching method to avoid async context manager complexity
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mock_rampdb_matches, {
                'api_calls': 1,
                'success_rate': 1.0,
                'avg_confidence': 0.87,
                'sources_used': ['HMDB']
            })
            
            # Execute action
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="metabolite",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
        
        # Verify results
        assert result.success
        assert result.stage3_input_count == 4  # 4 Stage 3 candidates
        assert result.total_matches == 3  # 3 matches above 0.85 threshold
        assert result.still_unmapped == 1  # Unknown_metabolite_X not matched
        assert result.api_calls_made == 1
        assert result.api_success_rate == 1.0
        assert result.average_confidence > 0.8
        
        # Verify dataset updates
        assert "rampdb_matched" in mock_context["datasets"]
        assert "rampdb_unmapped" in mock_context["datasets"]
        
        rampdb_matches = mock_context["datasets"]["rampdb_matched"]
        assert len(rampdb_matches) == 3
        
        # Verify match structure
        first_match = rampdb_matches[0]
        assert "match_confidence" in first_match
        assert "database_source" in first_match
        assert "pathways_count" in first_match
        assert first_match["stage"] == 3
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, mock_context):
        """Test that confidence threshold filtering works correctly."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams(
            confidence_threshold=0.90  # High threshold
        )
        
        # Mock matches with varying confidence
        mixed_confidence_matches = [
            MetaboliteMatch(
                query_name="Tryptophan", matched_id="HMDB0000929", matched_name="L-Tryptophan",
                database_source="HMDB", confidence_score=0.95, match_method="rampdb_cross_reference"
            ),
            MetaboliteMatch(
                query_name="Phenylalanine", matched_id="HMDB0000159", matched_name="L-Phenylalanine", 
                database_source="HMDB", confidence_score=0.85, match_method="rampdb_cross_reference"  # Below threshold
            ),
            MetaboliteMatch(
                query_name="Tyrosine", matched_id="HMDB0000158", matched_name="L-Tyrosine",
                database_source="HMDB", confidence_score=0.92, match_method="rampdb_cross_reference"
            )
        ]
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mixed_confidence_matches, {
                'api_calls': 1,
                'success_rate': 1.0,
                'avg_confidence': 0.90,
                'sources_used': ['HMDB']
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None, 
                context=mock_context
            )
        
        # Only 2 matches should pass 0.90 threshold (0.95 and 0.92)
        assert result.total_matches == 2
        assert result.still_unmapped == 2  # 2 below threshold + unmatchable ones
    
    @pytest.mark.asyncio
    async def test_api_failure_handling(self, mock_context, stage2_unmapped_data):
        """Test handling of RampDB API failures."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            # Simulate API failure
            mock_perform.side_effect = Exception("RampDB API unavailable")
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=mock_context
            )
        
        # Should fail gracefully
        assert not result.success
        assert "Stage 3 failed" in result.message
        assert result.api_calls_made == 0
        assert result.total_matches == 0
    
    @pytest.mark.asyncio
    async def test_api_health_check_failure(self, mock_context):
        """Test handling when RampDB API health check fails."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            # Simulate health check failure - return empty results  
            mock_perform.return_value = ([], {
                'api_calls': 0,
                'success_rate': 0.0,
                'avg_confidence': 0.0,
                'sources_used': []
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=mock_context
            )
        
        # Should complete but with no matches due to API health failure
        assert result.success
        assert result.total_matches == 0
        assert result.api_calls_made == 0  # No actual matching calls made
    
    @pytest.mark.asyncio
    async def test_no_stage3_candidates(self):
        """Test handling when no Stage 3 candidates exist."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        # Context with no Stage 3 candidates
        context = {
            "datasets": {
                "fuzzy_unmapped": []  # Empty unmapped list
            }
        }
        
        result = await action.execute_typed(
            current_identifiers=[], current_ontology_type="metabolite",
            params=params, source_endpoint=None, target_endpoint=None,
            context=context
        )
        
        assert result.success
        assert result.stage3_input_count == 0
        assert result.total_matches == 0
        assert "No Stage 3 candidates" in result.message
        assert result.processing_time_seconds < 1.0
    
    @pytest.mark.asyncio
    async def test_progressive_statistics_update(self, mock_context, mock_rampdb_matches):
        """Test that progressive statistics are updated correctly."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mock_rampdb_matches, {
                'api_calls': 2,
                'success_rate': 1.0,
                'avg_confidence': 0.87,
                'sources_used': ['HMDB']
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=mock_context
            )
        
        # Check statistics structure
        stats = mock_context["statistics"]
        assert "progressive_stage3_rampdb" in stats
        
        s3_stats = stats["progressive_stage3_rampdb"]
        assert s3_stats["stage"] == 3
        assert s3_stats["method"] == "rampdb_cross_reference"
        assert s3_stats["api_calls"] == 2
        assert "sources_used" in s3_stats
        assert "estimated_cost_dollars" in s3_stats
        assert s3_stats["processing_time_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_cost_estimation(self, mock_context, mock_rampdb_matches):
        """Test cost estimation and tracking."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mock_rampdb_matches, {
                'api_calls': 5,
                'success_rate': 1.0,
                'avg_confidence': 0.87,
                'sources_used': ['HMDB']
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=mock_context
            )
        
        # Verify cost calculations
        assert result.estimated_cost_dollars > 0.0  # Should have some cost estimate
        assert result.cost_per_metabolite >= 0.0
        
        # Cost should be reasonable (5 API calls * $0.005 = $0.025)
        assert result.estimated_cost_dollars == 0.025
    
    @pytest.mark.asyncio 
    async def test_cumulative_coverage_calculation(self, mock_context, mock_rampdb_matches):
        """Test that cumulative coverage is calculated correctly."""
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams()
        
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mock_rampdb_matches, {
                'api_calls': 1,
                'success_rate': 1.0,
                'avg_confidence': 0.87,
                'sources_used': ['HMDB']
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=mock_context
            )
        
        # Stage 1: 38, Stage 2: 112, Stage 3: 3, Total: 250
        # Expected coverage: (38 + 112 + 3) / 250 = 153/250 = 0.612 = 61.2%
        expected_coverage = (38 + 112 + 3) / 250
        assert abs(result.cumulative_coverage - expected_coverage) < 0.001
        assert result.cumulative_coverage > 0.60  # Should improve from Stage 2


class TestRampDBIntegration:
    """Integration tests for RampDB client and bridge interaction."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_integration_mock(self):
        """Test end-to-end integration with mocked RampDB responses."""
        # This would be expanded for full integration testing
        action = MetaboliteRampdbBridge()
        params = MetaboliteRampdbBridgeParams(batch_size=5)
        
        test_context = {
            "datasets": {
                "nightingale_matched": [{"name": "matched_metabolite"}] * 38,
                "fuzzy_matched": [{"name": "fuzzy_matched"}] * 112, 
                "fuzzy_unmapped": [
                    {"name": "L-Tryptophan", "for_stage": 3},
                    {"name": "L-Phenylalanine", "for_stage": 3}
                ]
            },
            "statistics": {}
        }
        
        # Mock successful RampDB interaction using the same pattern as other tests
        mock_matches = [
            MetaboliteMatch(
                query_name="L-Tryptophan", matched_id="HMDB0000929",
                matched_name="Tryptophan", database_source="HMDB", 
                confidence_score=0.92, match_method="rampdb_cross_reference"
            )
        ]
        
        # Use the same mocking pattern as successful tests - mock the internal method
        with patch.object(action, '_perform_rampdb_matching') as mock_perform:
            mock_perform.return_value = (mock_matches, {
                'api_calls': 1,
                'success_rate': 1.0,
                'avg_confidence': 0.92,
                'sources_used': ['HMDB']
            })
            
            result = await action.execute_typed(
                current_identifiers=[], current_ontology_type="metabolite",
                params=params, source_endpoint=None, target_endpoint=None,
                context=test_context
            )
        
        # Integration assertions
        assert result.success
        assert result.total_matches == 1
        assert result.cumulative_coverage > 0.60  # Improved from previous stages
        assert "progressive_stage3_rampdb" in test_context["statistics"]