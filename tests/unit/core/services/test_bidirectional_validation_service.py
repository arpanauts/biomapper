"""Unit tests for BidirectionalValidationService."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from biomapper.core.services.bidirectional_validation_service import BidirectionalValidationService


class TestBidirectionalValidationService:
    """Test cases for BidirectionalValidationService."""
    
    @pytest.fixture
    def service(self):
        """Create a BidirectionalValidationService instance."""
        return BidirectionalValidationService()
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock mapping executor."""
        executor = Mock()
        executor._get_ontology_type = AsyncMock()
        executor._find_best_path = AsyncMock()
        executor._execute_path = AsyncMock()
        return executor
    
    @pytest.fixture
    def successful_mappings(self):
        """Sample successful mappings for testing."""
        return {
            "id1": {
                "source_identifier": "id1",
                "target_identifiers": ["target1", "target2"],
                "status": "success",
                "confidence_score": 0.9
            },
            "id2": {
                "source_identifier": "id2",
                "target_identifiers": ["target3"],
                "status": "success",
                "confidence_score": 0.85
            }
        }
    
    @pytest.mark.asyncio
    async def test_validate_mappings_no_mappings(self, service):
        """Test validation with no successful mappings."""
        result = await service.validate_mappings(
            mapping_executor=Mock(),
            meta_session=Mock(),
            successful_mappings={},
            source_endpoint_name="source",
            target_endpoint_name="target",
            source_property_name="prop1",
            target_property_name="prop2",
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            mapping_session_id="session123"
        )
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_validate_mappings_no_reverse_path(self, service, mock_mapping_executor, successful_mappings):
        """Test validation when no reverse path is found."""
        # Setup mocks
        mock_mapping_executor._get_ontology_type.side_effect = ["SourceOntology", "TargetOntology"]
        mock_mapping_executor._find_best_path.return_value = None  # No reverse path
        
        result = await service.validate_mappings(
            mapping_executor=mock_mapping_executor,
            meta_session=Mock(),
            successful_mappings=successful_mappings,
            source_endpoint_name="source",
            target_endpoint_name="target",
            source_property_name="prop1",
            target_property_name="prop2",
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            mapping_session_id="session123"
        )
        
        # Should return original mappings without validation status
        assert result == successful_mappings
        assert mock_mapping_executor._find_best_path.called
    
    @pytest.mark.asyncio
    async def test_validate_mappings_with_reverse_path(self, service, mock_mapping_executor, successful_mappings):
        """Test validation with a valid reverse path."""
        # Setup mocks
        mock_mapping_executor._get_ontology_type.side_effect = ["SourceOntology", "TargetOntology"]
        
        mock_path = Mock()
        mock_path.name = "ReversePath"
        mock_path.id = 123
        mock_mapping_executor._find_best_path.return_value = mock_path
        
        # Mock reverse mapping results
        reverse_results = {
            "target1": {
                "target_identifiers": ["id1"],
                "mapped_value": "id1"
            },
            "target2": {
                "target_identifiers": ["id1"],
                "mapped_value": "id1"
            },
            "target3": {
                "target_identifiers": ["id2", "id_other"],
                "mapped_value": "id2"
            }
        }
        mock_mapping_executor._execute_path.return_value = reverse_results
        
        result = await service.validate_mappings(
            mapping_executor=mock_mapping_executor,
            meta_session=Mock(),
            successful_mappings=successful_mappings,
            source_endpoint_name="source",
            target_endpoint_name="target",
            source_property_name="prop1",
            target_property_name="prop2",
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            mapping_session_id="session123"
        )
        
        # Check that validation status was added
        assert "validation_status" in result["id1"]
        assert result["id1"]["validation_status"] == "Validated"
        
        assert "validation_status" in result["id2"]
        assert result["id2"]["validation_status"] == "Validated"
    
    @pytest.mark.asyncio
    async def test_extract_target_ids(self, service, successful_mappings):
        """Test extraction of target IDs from mappings."""
        target_ids = service._extract_target_ids(successful_mappings)
        
        expected_ids = {"target1", "target2", "target3"}
        assert target_ids == expected_ids
    
    def test_normalize_arivale_id(self, service):
        """Test Arivale ID normalization."""
        # Test with Arivale prefixes
        assert service._normalize_arivale_id("INF_P12345") == "P12345"
        assert service._normalize_arivale_id("CAM_ABC123") == "ABC123"
        assert service._normalize_arivale_id("CVD_XYZ789") == "XYZ789"
        assert service._normalize_arivale_id("CVD2_TEST456") == "TEST456"
        assert service._normalize_arivale_id("DEV_ID999") == "ID999"
        
        # Test without prefix
        assert service._normalize_arivale_id("REGULAR123") == "REGULAR123"
        
        # Test edge cases
        assert service._normalize_arivale_id(None) is None
        assert service._normalize_arivale_id("") == ""
        assert service._normalize_arivale_id("INF_") == "INF_"  # No part after underscore
    
    def test_reconcile_bidirectional_mappings_validated(self, service):
        """Test reconciliation with validated mappings."""
        forward_mappings = {
            "id1": {
                "source_identifier": "id1",
                "target_identifiers": ["target1"],
                "status": "success"
            }
        }
        
        reverse_results = {
            "target1": {
                "target_identifiers": ["id1"],
                "mapped_value": "id1"
            }
        }
        
        result = service._reconcile_bidirectional_mappings(forward_mappings, reverse_results)
        
        assert result["id1"]["validation_status"] == "Validated"
    
    def test_reconcile_bidirectional_mappings_ambiguous(self, service):
        """Test reconciliation with ambiguous mappings."""
        forward_mappings = {
            "id1": {
                "source_identifier": "id1",
                "target_identifiers": ["target1"],
                "status": "success"
            }
        }
        
        reverse_results = {
            "target1": {
                "target_identifiers": ["id1", "id2"],
                "mapped_value": "id2"  # Different from source
            }
        }
        
        result = service._reconcile_bidirectional_mappings(forward_mappings, reverse_results)
        
        assert result["id1"]["validation_status"] == "Validated (Ambiguous)"
    
    def test_reconcile_bidirectional_mappings_no_reverse_path(self, service):
        """Test reconciliation when no reverse path exists."""
        forward_mappings = {
            "id1": {
                "source_identifier": "id1",
                "target_identifiers": ["target1"],
                "status": "success"
            }
        }
        
        reverse_results = {}  # No reverse results
        
        result = service._reconcile_bidirectional_mappings(forward_mappings, reverse_results)
        
        assert result["id1"]["validation_status"] == "Successful (NoReversePath)"