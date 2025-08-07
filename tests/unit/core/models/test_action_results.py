"""Test ActionResult model."""

import pytest
from datetime import datetime

from biomapper.core.models.action_results import ActionResult, ProvenanceRecord


class TestProvenanceRecord:
    """Test ProvenanceRecord model."""

    def test_valid_provenance_creation(self):
        """Test creating valid ProvenanceRecord."""
        timestamp = datetime.now()
        provenance = ProvenanceRecord(
            source="UniProt API",
            version="2024.01",
            timestamp=timestamp,
            confidence_score=0.95,
            method="direct_mapping",
            evidence_codes=["ECO:0000269", "ECO:0000305"],
        )

        assert provenance.source == "UniProt API"
        assert provenance.version == "2024.01"
        assert provenance.timestamp == timestamp
        assert provenance.confidence_score == 0.95
        assert provenance.method == "direct_mapping"
        assert provenance.evidence_codes == ["ECO:0000269", "ECO:0000305"]

    def test_minimal_provenance_creation(self):
        """Test creating ProvenanceRecord with only required fields."""
        timestamp = datetime.now()
        provenance = ProvenanceRecord(source="HGNC", timestamp=timestamp)

        assert provenance.source == "HGNC"
        assert provenance.timestamp == timestamp
        assert provenance.version is None
        assert provenance.confidence_score is None
        assert provenance.method is None
        assert provenance.evidence_codes is None

    def test_provenance_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValueError, match="source"):
            ProvenanceRecord(timestamp=datetime.now())

        with pytest.raises(ValueError, match="timestamp"):
            ProvenanceRecord(source="UniProt")

    def test_confidence_score_validation(self):
        """Test confidence_score must be between 0 and 1 if provided."""
        timestamp = datetime.now()

        with pytest.raises(ValueError, match="confidence_score"):
            ProvenanceRecord(
                source="UniProt", timestamp=timestamp, confidence_score=-0.1
            )

        with pytest.raises(ValueError, match="confidence_score"):
            ProvenanceRecord(
                source="UniProt", timestamp=timestamp, confidence_score=1.5
            )

        # Test edge cases (should be valid)
        prov_zero = ProvenanceRecord(
            source="UniProt", timestamp=timestamp, confidence_score=0.0
        )
        assert prov_zero.confidence_score == 0.0

        prov_one = ProvenanceRecord(
            source="UniProt", timestamp=timestamp, confidence_score=1.0
        )
        assert prov_one.confidence_score == 1.0


class TestActionResult:
    """Test ActionResult model."""

    def test_valid_result_creation(self):
        """Test creating valid ActionResult."""
        timestamp = datetime.now()
        provenance = ProvenanceRecord(
            source="UniProt",
            version="2024.01",
            timestamp=timestamp,
            confidence_score=0.95,
        )

        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            mapped_identifier="ENSG00000139618",
            status="success",
            provenance=provenance,
            metadata={
                "gene_name": "BRCA2",
                "organism": "Homo sapiens",
                "mapping_path": ["uniprot", "hgnc", "ensembl"],
            },
        )

        assert result.action_type == "execute_mapping_path"
        assert result.identifier == "P12345"
        assert result.source_type == "uniprot"
        assert result.target_type == "ensembl"
        assert result.mapped_identifier == "ENSG00000139618"
        assert result.status == "success"
        assert result.provenance == provenance
        assert result.metadata["gene_name"] == "BRCA2"
        assert result.metadata["organism"] == "Homo sapiens"
        assert result.metadata["mapping_path"] == ["uniprot", "hgnc", "ensembl"]

    def test_minimal_result_creation(self):
        """Test creating ActionResult with only required fields."""
        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="Q9Y6K9",
            source_type="uniprot",
            target_type="hgnc",
            status="pending",
        )

        assert result.action_type == "execute_mapping_path"
        assert result.identifier == "Q9Y6K9"
        assert result.source_type == "uniprot"
        assert result.target_type == "hgnc"
        assert result.mapped_identifier is None
        assert result.status == "pending"
        assert result.provenance is None
        assert result.metadata == {}  # Expected default
        assert result.error is None

    def test_failed_result_creation(self):
        """Test creating ActionResult for failed mapping."""
        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="INVALID123",
            source_type="uniprot",
            target_type="ensembl",
            status="failed",
            error="Identifier not found in UniProt database",
            metadata={"attempted_at": datetime.now().isoformat()},
        )

        assert result.action_type == "execute_mapping_path"
        assert result.identifier == "INVALID123"
        assert result.status == "failed"
        assert result.mapped_identifier is None
        assert result.error == "Identifier not found in UniProt database"
        assert "attempted_at" in result.metadata

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing action_type
        with pytest.raises(ValueError, match="action_type"):
            ActionResult(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
            )

        # Missing identifier
        with pytest.raises(ValueError, match="identifier"):
            ActionResult(
                action_type="execute_mapping_path",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
            )

        # Missing source_type
        with pytest.raises(ValueError, match="source_type"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                target_type="ensembl",
                status="success",
            )

        # Missing target_type
        with pytest.raises(ValueError, match="target_type"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                source_type="uniprot",
                status="success",
            )

        # Missing status
        with pytest.raises(ValueError, match="status"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
            )

    def test_status_validation(self):
        """Test status must be one of allowed values."""
        with pytest.raises(ValueError, match="status"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                status="completed",  # Should be 'success', 'failed', or 'pending'
            )

    def test_empty_identifier_handling(self):
        """Test that empty identifier is handled properly."""
        # Empty string should be invalid
        with pytest.raises(ValueError, match="identifier"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
            )

        # Whitespace-only should be invalid
        with pytest.raises(ValueError, match="identifier"):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="   ",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
            )

    def test_type_safety(self):
        """Test that fields have correct types."""
        # Test invalid type for string fields
        with pytest.raises(ValueError):
            ActionResult(
                action_type=123,  # Should be string
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
            )

        # Test invalid type for provenance
        with pytest.raises(ValueError):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
                provenance={"source": "UniProt"},  # Should be ProvenanceRecord
            )

        # Test invalid type for metadata
        with pytest.raises(ValueError):
            ActionResult(
                action_type="execute_mapping_path",
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                status="success",
                metadata="some metadata",  # Should be dict
            )

    def test_provenance_record_validation(self):
        """Test that provenance must be valid ProvenanceRecord if provided."""
        # This should work
        provenance = ProvenanceRecord(
            source="UniProt", timestamp=datetime.now(), confidence_score=0.9
        )

        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            mapped_identifier="ENSG00000139618",
            status="success",
            provenance=provenance,
        )

        assert result.provenance.source == "UniProt"
        assert result.provenance.confidence_score == 0.9

    def test_model_export(self):
        """Test model export methods."""
        timestamp = datetime.now()
        provenance = ProvenanceRecord(
            source="UniProt", timestamp=timestamp, confidence_score=0.95
        )

        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            mapped_identifier="ENSG00000139618",
            status="success",
            provenance=provenance,
            metadata={"gene_name": "BRCA2"},
        )

        # Test dict export
        result_dict = result.model_dump()
        assert result_dict["action_type"] == "execute_mapping_path"
        assert result_dict["identifier"] == "P12345"
        assert result_dict["source_type"] == "uniprot"
        assert result_dict["target_type"] == "ensembl"
        assert result_dict["mapped_identifier"] == "ENSG00000139618"
        assert result_dict["status"] == "success"
        assert result_dict["provenance"]["source"] == "UniProt"
        assert result_dict["metadata"]["gene_name"] == "BRCA2"

        # Test JSON export
        result_json = result.model_dump_json()
        assert isinstance(result_json, str)
        assert "execute_mapping_path" in result_json
        assert "P12345" in result_json
        assert "ENSG00000139618" in result_json

    def test_model_copy(self):
        """Test model copy with updates."""
        original = ActionResult(
            action_type="execute_mapping_path",
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            status="pending",
        )

        # Test copy with update
        updated = original.model_copy(
            update={"status": "success", "mapped_identifier": "ENSG00000139618"}
        )

        assert updated.identifier == "P12345"
        assert updated.status == "success"
        assert updated.mapped_identifier == "ENSG00000139618"

        # Ensure original is unchanged
        assert original.status == "pending"
        assert original.mapped_identifier is None

    def test_complex_metadata(self):
        """Test handling complex metadata structures."""
        result = ActionResult(
            action_type="execute_mapping_path",
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            status="success",
            metadata={
                "mapping_path": ["uniprot", "hgnc", "ensembl"],
                "scores": {"confidence": 0.95, "coverage": 0.88},
                "timestamps": {
                    "started": datetime.now().isoformat(),
                    "completed": datetime.now().isoformat(),
                },
                "intermediate_ids": {"hgnc": "HGNC:1101", "entrez": "675"},
            },
        )

        assert result.metadata["mapping_path"] == ["uniprot", "hgnc", "ensembl"]
        assert result.metadata["scores"]["confidence"] == 0.95
        assert result.metadata["scores"]["coverage"] == 0.88
        assert "started" in result.metadata["timestamps"]
        assert result.metadata["intermediate_ids"]["hgnc"] == "HGNC:1101"
