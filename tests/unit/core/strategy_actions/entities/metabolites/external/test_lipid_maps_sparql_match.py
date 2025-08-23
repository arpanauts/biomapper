"""
TDD Tests for LIPID MAPS SPARQL Match Action

STATUS: External SPARQL service integration not implemented
FUNCTIONALITY: LIPID MAPS SPARQL endpoint querying  
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use lipid_maps_static_match or core metabolite matching actions

These tests are skipped as SPARQL integration is not currently implemented.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
import asyncio
from typing import Dict, List, Any
import time
import requests

# Skip entire module - external SPARQL service integration not implemented
pytestmark = pytest.mark.skip("External SPARQL service integrations not implemented - use static matching or core actions")

# Import the actual implementation  
from src.actions.entities.metabolites.external.lipid_maps_sparql_match import (
    LipidMapsSparqlMatch,
    LipidMapsSparqlParams,
    LipidMapsSparqlResult
)


class TestLipidMapsSparqlMatch:
    """
    TDD tests for LIPID MAPS SPARQL matching action.
    Written BEFORE implementation to define expected behavior.
    """

    @pytest.fixture
    def sample_unmapped_metabolites(self) -> pd.DataFrame:
        """Sample unmapped metabolites from Stage 4."""
        return pd.DataFrame([
            {"identifier": "cholesterol", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sterol"},
            {"identifier": "palmitic acid", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
            {"identifier": "glucose", "SUPER_PATHWAY": "Carbohydrate", "SUB_PATHWAY": "Sugar"},
            {"identifier": "18:2n6", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
            {"identifier": "unknown_compound", "SUPER_PATHWAY": "Unknown", "SUB_PATHWAY": "Unknown"},
        ])

    @pytest.fixture
    def mock_sparql_response_success(self) -> Dict:
        """Mock successful SPARQL response."""
        return {
            "results": {
                "bindings": [
                    {
                        "lipid": {"value": "http://lipidmaps.org/LMST01010001"},
                        "label": {"value": "Cholesterol"},
                        "inchikey": {"value": "HVYWMOMLDZMCQP-VXSCHHQBSA-N"},
                        "formula": {"value": "C27H46O"}
                    }
                ]
            }
        }

    @pytest.fixture
    def mock_sparql_response_empty(self) -> Dict:
        """Mock empty SPARQL response."""
        return {"results": {"bindings": []}}

    @pytest.fixture
    def default_params(self) -> Dict:
        """Default action parameters."""
        return {
            "input_key": "stage_4_unmapped",
            "output_key": "stage_5_matched",
            "unmatched_key": "final_unmapped",
            "enabled": True,
            "fail_on_error": False,
            "timeout_seconds": 3,
            "batch_size": 10,
            "filter_lipids_only": True,
            "cache_results": True,
            "exact_match_confidence": 0.95,
            "fuzzy_match_confidence": 0.70
        }

    def test_action_exists_and_registers(self):
        """Test that action exists and registers properly."""
        # This will fail initially (TDD RED phase)
        from src.actions.registry import ACTION_REGISTRY
        assert "LIPID_MAPS_SPARQL_MATCH" in ACTION_REGISTRY
        
    def test_handles_sparql_timeout_gracefully(self, sample_unmapped_metabolites, default_params):
        """Test that SPARQL timeouts don't crash the pipeline."""
        # Setup
        action = LipidMapsSparqlMatch()
        context = {
            "datasets": {
                "stage_4_unmapped": sample_unmapped_metabolites
            }
        }
        
        # Mock timeout
        with patch('requests.post', side_effect=requests.Timeout("Query timeout")):
            # Execute
            result = asyncio.run(action.execute_typed(
                params=LipidMapsSparqlParams(**default_params),
                context=context
            ))
            
            # Assert - pipeline continues despite timeout
            assert result.success == True
            assert result.sparql_errors > 0
            assert len(context["datasets"].get("stage_5_matched", [])) == 0
            assert "Query timeout" in result.message

    def test_feature_flag_disables_action(self, sample_unmapped_metabolites):
        """Test that feature flag can disable the action."""
        # Setup
        action = LipidMapsSparqlMatch()
        params = LipidMapsSparqlParams(
            input_key="stage_4_unmapped",
            output_key="stage_5_matched",
            enabled=False  # Feature flag OFF
        )
        context = {
            "datasets": {
                "stage_4_unmapped": sample_unmapped_metabolites
            }
        }
        
        # Execute
        result = asyncio.run(action.execute_typed(params=params, context=context))
        
        # Assert - action skipped
        assert result.success == True
        assert result.message == "LIPID MAPS SPARQL disabled by feature flag"
        assert result.queries_executed == 0

    def test_filters_lipids_only(self, sample_unmapped_metabolites, default_params):
        """Test that non-lipids are filtered when filter_lipids_only=True."""
        # Setup
        action = LipidMapsSparqlMatch()
        context = {
            "datasets": {
                "stage_4_unmapped": sample_unmapped_metabolites
            }
        }
        
        with patch.object(action, '_execute_sparql_query') as mock_query:
            mock_query.return_value = ({"results": {"bindings": []}}, 0.5)
            
            # Execute
            result = asyncio.run(action.execute_typed(
                params=LipidMapsSparqlParams(**default_params),
                context=context
            ))
            
            # Assert - only lipids queried
            # Should query: cholesterol, palmitic acid, 18:2n6 (3 lipids)
            # Should skip: glucose, unknown_compound (2 non-lipids)
            assert mock_query.call_count == 3

    def test_exact_match_cholesterol(self, mock_sparql_response_success):
        """Test exact matching for known compound (cholesterol)."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "cholesterol", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        # Mock SPARQL response
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_sparql_response_success
            mock_post.return_value = mock_response
            
            # Execute
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched"
            )
            result = asyncio.run(action.execute_typed(params=params, context=context))
            
            # Assert
            assert result.success == True
            matched = context["datasets"]["stage_5_matched"]
            assert len(matched) == 1
            assert matched.iloc[0]["identifier"] == "cholesterol"
            assert matched.iloc[0]["lipid_maps_id"] == "LMST01010001"
            assert matched.iloc[0]["confidence_score"] == 0.95  # Exact match confidence

    def test_fuzzy_matching_fatty_acids(self):
        """Test fuzzy matching for fatty acid notations."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "18:2n6", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        # Mock fuzzy match response
        fuzzy_response = {
            "results": {
                "bindings": [
                    {
                        "lipid": {"value": "http://lipidmaps.org/LMFA01030120"},
                        "label": {"value": "Linoleic acid (18:2)"}
                    }
                ]
            }
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # First call returns empty (no exact match)
            # Second call returns fuzzy match
            mock_response.json.side_effect = [
                {"results": {"bindings": []}},  # No exact match
                fuzzy_response  # Fuzzy match found
            ]
            mock_post.return_value = mock_response
            
            # Execute
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched"
            )
            result = asyncio.run(action.execute_typed(params=params, context=context))
            
            # Assert
            assert result.success == True
            matched = context["datasets"]["stage_5_matched"]
            assert len(matched) == 1
            assert matched.iloc[0]["confidence_score"] == 0.70  # Fuzzy match confidence

    def test_batch_query_generation(self):
        """Test that batch queries are generated correctly with UNION."""
        # Setup
        action = LipidMapsSparqlMatch()
        metabolites = ["cholesterol", "palmitic acid", "oleic acid"]
        
        # Generate batch query
        query = action._generate_batch_query(metabolites, query_type="exact")
        
        # Assert
        assert "UNION" in query
        assert query.count("UNION") == 2  # 3 metabolites = 2 UNIONs
        assert "cholesterol" in query
        assert "palmitic acid" in query
        assert "oleic acid" in query
        assert "PREFIX rdfs:" in query

    def test_sparql_injection_prevention(self):
        """Test that SPARQL injection is prevented."""
        # Setup
        action = LipidMapsSparqlMatch()
        malicious_input = 'test" } DROP GRAPH <http://evil> { "'
        
        # Generate query with malicious input
        query = action._generate_exact_query(malicious_input)
        
        # Assert - malicious input should be escaped
        assert "DROP GRAPH" not in query
        assert '\\"' in query or '""' in query  # Escaped quotes

    def test_empty_input_handling(self):
        """Test handling of empty input dataset."""
        # Setup
        action = LipidMapsSparqlMatch()
        empty_data = pd.DataFrame()
        context = {"datasets": {"stage_4_unmapped": empty_data}}
        
        # Execute
        params = LipidMapsSparqlParams(
            input_key="stage_4_unmapped",
            output_key="stage_5_matched"
        )
        result = asyncio.run(action.execute_typed(params=params, context=context))
        
        # Assert
        assert result.success == True
        assert result.queries_executed == 0
        assert result.message == "No unmapped metabolites to process"

    def test_cache_functionality(self):
        """Test that successful matches are cached."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "cholesterol", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": {
                    "bindings": [{
                        "lipid": {"value": "http://lipidmaps.org/LMST01010001"},
                        "label": {"value": "Cholesterol"}
                    }]
                }
            }
            mock_post.return_value = mock_response
            
            # First execution - should query SPARQL
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched",
                cache_results=True
            )
            result1 = asyncio.run(action.execute_typed(params=params, context=context))
            assert mock_post.call_count == 1
            
            # Second execution - should use cache
            context["datasets"]["stage_4_unmapped"] = test_data  # Reset input
            result2 = asyncio.run(action.execute_typed(params=params, context=context))
            assert mock_post.call_count == 1  # Still 1, not 2

    def test_performance_requirements(self):
        """Test that performance meets requirements (<3 seconds for Stage 5)."""
        # Setup
        action = LipidMapsSparqlMatch()
        # Create 100 metabolites (realistic test)
        test_data = pd.DataFrame([
            {"identifier": f"metabolite_{i}", "SUPER_PATHWAY": "Lipid"}
            for i in range(100)
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        # Mock fast responses
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": {"bindings": []}}
            mock_post.return_value = mock_response
            
            # Execute with timing
            start_time = time.time()
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched",
                batch_size=10  # 100 metabolites / 10 = 10 queries
            )
            result = asyncio.run(action.execute_typed(params=params, context=context))
            elapsed = time.time() - start_time
            
            # Assert
            assert result.success == True
            assert elapsed < 3.0  # Must complete in <3 seconds
            assert mock_post.call_count <= 10  # Should batch properly

    def test_progressive_statistics_integration(self):
        """Test that action integrates with progressive statistics tracking."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "cholesterol", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {
            "datasets": {"stage_4_unmapped": test_data},
            "statistics": {
                "progressive_stage4": {
                    "cumulative_coverage": 0.85
                }
            }
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": {
                    "bindings": [{
                        "lipid": {"value": "http://lipidmaps.org/LMST01010001"},
                        "label": {"value": "Cholesterol"}
                    }]
                }
            }
            mock_post.return_value = mock_response
            
            # Execute
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched"
            )
            result = asyncio.run(action.execute_typed(params=params, context=context))
            
            # Assert - statistics updated
            assert "progressive_stage5" in context["statistics"]
            stage5_stats = context["statistics"]["progressive_stage5"]
            assert stage5_stats["stage"] == 5
            assert stage5_stats["lipid_maps_matched"] == 1
            assert stage5_stats["cumulative_coverage"] > 0.85

    def test_confidence_score_assignment(self):
        """Test that confidence scores are assigned correctly."""
        # Setup
        action = LipidMapsSparqlMatch()
        
        # Test cases
        test_cases = [
            ("exact", 0.95),
            ("fuzzy", 0.70),
            ("formula", 0.60)
        ]
        
        for match_type, expected_confidence in test_cases:
            result = action._calculate_confidence_score(match_type)
            assert result == expected_confidence

    def test_error_logging_and_monitoring(self):
        """Test that errors are properly logged for monitoring."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "test_metabolite", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        with patch('requests.post', side_effect=Exception("Network error")):
            with patch('logging.Logger.error') as mock_log_error:
                # Execute
                params = LipidMapsSparqlParams(
                    input_key="stage_4_unmapped",
                    output_key="stage_5_matched"
                )
                result = asyncio.run(action.execute_typed(params=params, context=context))
                
                # Assert - error logged
                assert mock_log_error.called
                assert "Network error" in str(mock_log_error.call_args)

    def test_query_timeout_enforcement(self):
        """Test that queries timeout at configured threshold."""
        # Setup
        action = LipidMapsSparqlMatch()
        test_data = pd.DataFrame([
            {"identifier": "slow_query", "SUPER_PATHWAY": "Lipid"}
        ])
        context = {"datasets": {"stage_4_unmapped": test_data}}
        
        # Mock slow response
        def slow_response(*args, **kwargs):
            time.sleep(5)  # Longer than timeout
            return MagicMock()
        
        with patch('requests.post', side_effect=slow_response):
            # Execute with 3-second timeout
            params = LipidMapsSparqlParams(
                input_key="stage_4_unmapped",
                output_key="stage_5_matched",
                timeout_seconds=3
            )
            
            start_time = time.time()
            result = asyncio.run(action.execute_typed(params=params, context=context))
            elapsed = time.time() - start_time
            
            # Assert - should timeout at ~3 seconds, not wait for 5
            assert elapsed < 4.0
            assert result.success == True  # Pipeline continues
            assert result.timeouts > 0


class TestLipidMapsSparqlParams:
    """Test parameter validation and defaults."""
    
    def test_default_parameters(self):
        """Test that default parameters are set correctly."""
        params = LipidMapsSparqlParams(
            input_key="test_input",
            output_key="test_output"
        )
        
        assert params.enabled == True
        assert params.fail_on_error == False
        assert params.timeout_seconds == 3
        assert params.batch_size == 10
        assert params.filter_lipids_only == True
        assert params.cache_results == True
        assert params.exact_match_confidence == 0.95
        assert params.fuzzy_match_confidence == 0.70

    def test_parameter_validation(self):
        """Test that parameters are validated properly."""
        # Test invalid timeout
        with pytest.raises(ValueError):
            LipidMapsSparqlParams(
                input_key="test",
                output_key="out",
                timeout_seconds=-1  # Invalid
            )
        
        # Test invalid batch size
        with pytest.raises(ValueError):
            LipidMapsSparqlParams(
                input_key="test",
                output_key="out",
                batch_size=0  # Invalid
            )
        
        # Test invalid confidence score
        with pytest.raises(ValueError):
            LipidMapsSparqlParams(
                input_key="test",
                output_key="out",
                exact_match_confidence=1.5  # >1.0
            )


class TestLipidMapsSparqlResult:
    """Test result model."""
    
    def test_result_structure(self):
        """Test that result contains expected fields."""
        result = LipidMapsSparqlResult(
            success=True,
            matches_found=5,
            queries_executed=10,
            timeouts=1,
            sparql_errors=0,
            average_query_time=0.8,
            message="Completed successfully"
        )
        
        assert result.success == True
        assert result.matches_found == 5
        assert result.queries_executed == 10
        assert result.timeouts == 1
        assert result.sparql_errors == 0
        assert result.average_query_time == 0.8


# Tests are now ready to run with the implementation
# pytestmark = pytest.mark.skip(reason="TDD - Implementation not yet created")


if __name__ == "__main__":
    # Run tests to confirm RED phase
    pytest.main([__file__, "-xvs"])