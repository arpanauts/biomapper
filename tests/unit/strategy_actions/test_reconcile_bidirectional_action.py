"""
Unit tests for ReconcileBidirectionalAction.

Tests cover:
- Basic bidirectional reconciliation
- Forward-only mappings
- Reverse-only mappings
- Complex many-to-one scenarios
- Empty input handling
- Missing context keys
- Parameter validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from biomapper.core.strategy_actions.reconcile_bidirectional_action import ReconcileBidirectionalAction
from biomapper.db.models import Endpoint


class TestReconcileBidirectionalAction:
    """Test suite for ReconcileBidirectionalAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def action(self, mock_session):
        """Create an instance of ReconcileBidirectionalAction."""
        return ReconcileBidirectionalAction(session=mock_session)
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = MagicMock(spec=Endpoint)
        source.name = "UKBB"
        source.entity_type = "protein"
        
        target = MagicMock(spec=Endpoint)
        target.name = "HPA"
        target.entity_type = "protein"
        
        return source, target
    
    @pytest.mark.asyncio
    async def test_basic_bidirectional_reconciliation(self, action, mock_endpoints):
        """Test basic bidirectional reconciliation with perfect matches."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Set up context with forward and reverse mappings
        context = {
            "forward_results": {
                "provenance": [
                    {"source_id": "A", "target_id": "X"},
                    {"source_id": "B", "target_id": "Y"},
                    {"source_id": "C", "target_id": "Z"}
                ]
            },
            "reverse_results": {
                "provenance": [
                    {"source_id": "X", "target_id": "A"},  # X maps back to A
                    {"source_id": "Y", "target_id": "B"},  # Y maps back to B
                    {"source_id": "Z", "target_id": "C"}   # Z maps back to C
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A", "B", "C"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Check the result structure
        assert "output_identifiers" in result
        assert "provenance" in result
        assert "details" in result
        
        # Check that all mappings are bidirectionally confirmed
        reconciled = context["reconciled"]
        assert len(reconciled["bidirectional_pairs"]) == 3
        assert len(reconciled["forward_only_pairs"]) == 0
        assert len(reconciled["reverse_only_pairs"]) == 0
        
        # Verify statistics
        stats = reconciled["statistics"]
        assert stats["total_reconciled"] == 3
        assert stats["bidirectionally_confirmed"] == 3
        assert stats["forward_only_count"] == 0
        assert stats["reverse_only_count"] == 0
        assert stats["unique_source_ids"] == 3
        assert stats["unique_target_ids"] == 3
    
    @pytest.mark.asyncio
    async def test_forward_only_mappings(self, action, mock_endpoints):
        """Test handling of forward-only mappings."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {
                "provenance": [
                    {"source_id": "A", "target_id": "X"},
                    {"source_id": "B", "target_id": "Y"},
                    {"source_id": "C", "target_id": "Z"}
                ]
            },
            "reverse_results": {
                "provenance": [
                    {"source_id": "X", "target_id": "A"},  # Only X maps back to A
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A", "B", "C"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        reconciled = context["reconciled"]
        assert len(reconciled["bidirectional_pairs"]) == 1
        assert len(reconciled["forward_only_pairs"]) == 2
        assert len(reconciled["reverse_only_pairs"]) == 0
        
        # Check that B->Y and C->Z are marked as forward-only
        forward_only_sources = [p["source"] for p in reconciled["forward_only_pairs"]]
        assert "B" in forward_only_sources
        assert "C" in forward_only_sources
    
    @pytest.mark.asyncio
    async def test_reverse_only_mappings(self, action, mock_endpoints):
        """Test handling of reverse-only mappings."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {
                "provenance": [
                    {"source_id": "A", "target_id": "X"},
                ]
            },
            "reverse_results": {
                "provenance": [
                    {"source_id": "X", "target_id": "A"},
                    {"source_id": "Y", "target_id": "B"},  # B wasn't in forward
                    {"source_id": "Z", "target_id": "C"}   # C wasn't in forward
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        reconciled = context["reconciled"]
        assert len(reconciled["bidirectional_pairs"]) == 1
        assert len(reconciled["forward_only_pairs"]) == 0
        assert len(reconciled["reverse_only_pairs"]) == 2
        
        # Check reverse-only pairs
        reverse_only_sources = [p["source"] for p in reconciled["reverse_only_pairs"]]
        assert "B" in reverse_only_sources
        assert "C" in reverse_only_sources
    
    @pytest.mark.asyncio
    async def test_many_to_one_mappings(self, action, mock_endpoints):
        """Test handling of many-to-one mapping scenarios."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {
                "provenance": [
                    {"source_id": "A1", "target_id": "X"},
                    {"source_id": "A2", "target_id": "X"},  # Both A1 and A2 map to X
                    {"source_id": "B", "target_id": "Y"}
                ]
            },
            "reverse_results": {
                "provenance": [
                    {"source_id": "X", "target_id": "A1"},
                    {"source_id": "X", "target_id": "A2"},  # X maps back to both
                    {"source_id": "Y", "target_id": "B"}
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A1", "A2", "B"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        reconciled = context["reconciled"]
        # All should be bidirectionally confirmed
        assert len(reconciled["bidirectional_pairs"]) == 3
        assert len(reconciled["forward_only_pairs"]) == 0
        assert len(reconciled["reverse_only_pairs"]) == 0
        
        # Check that both A1->X and A2->X are confirmed
        bidirectional_mappings = [(p["source"], p["target"]) for p in reconciled["bidirectional_pairs"]]
        assert ("A1", "X") in bidirectional_mappings
        assert ("A2", "X") in bidirectional_mappings
        assert ("B", "Y") in bidirectional_mappings
    
    @pytest.mark.asyncio
    async def test_empty_mapping_results(self, action, mock_endpoints):
        """Test handling of empty mapping results."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {"provenance": []},
            "reverse_results": {"provenance": []}
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        reconciled = context["reconciled"]
        assert len(reconciled["bidirectional_pairs"]) == 0
        assert len(reconciled["forward_only_pairs"]) == 0
        assert len(reconciled["reverse_only_pairs"]) == 0
        assert reconciled["statistics"]["total_reconciled"] == 0
    
    @pytest.mark.asyncio
    async def test_missing_context_keys(self, action, mock_endpoints):
        """Test handling of missing context keys."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Context missing the forward results
        context = {
            "reverse_results": {"provenance": [{"source_id": "X", "target_id": "A"}]}
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Should handle missing keys gracefully
        reconciled = context["reconciled"]
        assert len(reconciled["bidirectional_pairs"]) == 0
        assert len(reconciled["forward_only_pairs"]) == 0
        assert len(reconciled["reverse_only_pairs"]) == 1
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, action, mock_endpoints):
        """Test parameter validation."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Missing forward_mapping_key
        with pytest.raises(ValueError, match="forward_mapping_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={"reverse_mapping_key": "rev", "output_reconciled_key": "out"},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        # Missing reverse_mapping_key
        with pytest.raises(ValueError, match="reverse_mapping_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={"forward_mapping_key": "fwd", "output_reconciled_key": "out"},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        # Missing output_reconciled_key
        with pytest.raises(ValueError, match="output_reconciled_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={"forward_mapping_key": "fwd", "reverse_mapping_key": "rev"},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_provenance_tracking(self, action, mock_endpoints):
        """Test that provenance is properly tracked."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {
                "provenance": [
                    {"source_id": "A", "target_id": "X"},
                    {"source_id": "B", "target_id": "Y"}
                ]
            },
            "reverse_results": {
                "provenance": [
                    {"source_id": "X", "target_id": "A"}  # Only A is bidirectional
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A", "B"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Check provenance records
        provenance = result["provenance"]
        assert len(provenance) == 2  # One for A->X (bidirectional), one for B->Y (forward-only)
        
        # Find the bidirectional provenance
        bidirectional_prov = next(p for p in provenance if p["method"] == "bidirectional_confirmed")
        assert bidirectional_prov["source_id"] == "A"
        assert bidirectional_prov["target_id"] == "X"
        assert bidirectional_prov["confidence"] == 1.0
        assert bidirectional_prov["details"]["found_in_forward"] is True
        assert bidirectional_prov["details"]["found_in_reverse"] is True
        
        # Find the forward-only provenance
        forward_only_prov = next(p for p in provenance if p["method"] == "forward_only")
        assert forward_only_prov["source_id"] == "B"
        assert forward_only_prov["target_id"] == "Y"
        assert forward_only_prov["confidence"] == 0.5
        assert forward_only_prov["details"]["found_in_forward"] is True
        assert forward_only_prov["details"]["found_in_reverse"] is False
    
    @pytest.mark.asyncio
    async def test_complex_scenario(self, action, mock_endpoints):
        """Test a complex scenario with all types of mappings."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            "forward_results": {
                "provenance": [
                    # Bidirectional mappings
                    {"source_id": "A", "target_id": "X"},
                    {"source_id": "B", "target_id": "Y"},
                    # Forward-only mappings
                    {"source_id": "C", "target_id": "Z"},
                    {"source_id": "D", "target_id": "W"},
                    # Many-to-one
                    {"source_id": "E1", "target_id": "V"},
                    {"source_id": "E2", "target_id": "V"}
                ]
            },
            "reverse_results": {
                "provenance": [
                    # Bidirectional confirmations
                    {"source_id": "X", "target_id": "A"},
                    {"source_id": "Y", "target_id": "B"},
                    # Reverse-only mappings
                    {"source_id": "U", "target_id": "F"},
                    {"source_id": "T", "target_id": "G"},
                    # Many-to-one confirmation
                    {"source_id": "V", "target_id": "E1"},
                    {"source_id": "V", "target_id": "E2"}
                ]
            }
        }
        
        action_params = {
            "forward_mapping_key": "forward_results",
            "reverse_mapping_key": "reverse_results",
            "output_reconciled_key": "reconciled"
        }
        
        result = await action.execute(
            current_identifiers=["A", "B", "C", "D", "E1", "E2"],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        reconciled = context["reconciled"]
        
        # Verify counts
        assert len(reconciled["bidirectional_pairs"]) == 4  # A, B, E1, E2
        assert len(reconciled["forward_only_pairs"]) == 2  # C, D
        assert len(reconciled["reverse_only_pairs"]) == 2  # F, G
        
        # Verify statistics
        stats = reconciled["statistics"]
        assert stats["total_reconciled"] == 8
        assert stats["bidirectionally_confirmed"] == 4
        assert stats["forward_only_count"] == 2
        assert stats["reverse_only_count"] == 2
        assert stats["unique_source_ids"] == 8  # A, B, C, D, E1, E2, F, G
        assert stats["unique_target_ids"] == 7  # X, Y, Z, W, V, U, T