"""Test ExecuteMappingPathParams model."""

import pytest
from datetime import datetime
from typing import Optional

from biomapper.core.models.action_models import ExecuteMappingPathParams


class TestExecuteMappingPathParams:
    """Test ExecuteMappingPathParams model."""

    def test_valid_params_creation(self):
        """Test creating valid ExecuteMappingPathParams."""
        params = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            batch_size=100,
            min_confidence=0.8,
            include_deprecated=True,
            max_retries=3
        )
        
        assert params.identifier == "P12345"
        assert params.source_type == "uniprot"
        assert params.target_type == "ensembl"
        assert params.batch_size == 100
        assert params.min_confidence == 0.8
        assert params.include_deprecated is True
        assert params.max_retries == 3

    def test_minimal_params_creation(self):
        """Test creating ExecuteMappingPathParams with only required fields."""
        params = ExecuteMappingPathParams(
            identifier="BRCA2",
            source_type="hgnc",
            target_type="uniprot"
        )
        
        assert params.identifier == "BRCA2"
        assert params.source_type == "hgnc"
        assert params.target_type == "uniprot"
        # Test default values
        assert params.batch_size == 50  # Expected default
        assert params.min_confidence == 0.0  # Expected default
        assert params.include_deprecated is False  # Expected default
        assert params.max_retries == 3  # Expected default

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValueError, match="identifier"):
            ExecuteMappingPathParams(
                source_type="uniprot",
                target_type="ensembl"
            )
        
        with pytest.raises(ValueError, match="source_type"):
            ExecuteMappingPathParams(
                identifier="P12345",
                target_type="ensembl"
            )
        
        with pytest.raises(ValueError, match="target_type"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot"
            )

    def test_batch_size_validation(self):
        """Test batch_size must be greater than 0."""
        with pytest.raises(ValueError, match="batch_size"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                batch_size=0
            )
        
        with pytest.raises(ValueError, match="batch_size"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                batch_size=-10
            )

    def test_min_confidence_validation(self):
        """Test min_confidence must be between 0 and 1."""
        # Test below 0
        with pytest.raises(ValueError, match="min_confidence"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                min_confidence=-0.1
            )
        
        # Test above 1
        with pytest.raises(ValueError, match="min_confidence"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                min_confidence=1.1
            )
        
        # Test edge cases (should be valid)
        params_zero = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            min_confidence=0.0
        )
        assert params_zero.min_confidence == 0.0
        
        params_one = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            min_confidence=1.0
        )
        assert params_one.min_confidence == 1.0

    def test_type_validation(self):
        """Test that fields have correct types."""
        # Test invalid types for string fields
        with pytest.raises(ValueError):
            ExecuteMappingPathParams(
                identifier=12345,  # Should be string
                source_type="uniprot",
                target_type="ensembl"
            )
        
        with pytest.raises(ValueError):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type=123,  # Should be string
                target_type="ensembl"
            )
        
        # Test invalid types for numeric fields
        with pytest.raises(ValueError):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                batch_size="100"  # Should be int
            )
        
        with pytest.raises(ValueError):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                min_confidence="0.8"  # Should be float
            )
        
        # Test invalid type for boolean field
        with pytest.raises(ValueError):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                include_deprecated="yes"  # Should be bool
            )

    def test_max_retries_validation(self):
        """Test max_retries must be non-negative."""
        with pytest.raises(ValueError, match="max_retries"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="ensembl",
                max_retries=-1
            )
        
        # Test edge case (should be valid)
        params = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            max_retries=0
        )
        assert params.max_retries == 0

    def test_empty_identifier_handling(self):
        """Test that empty identifier is handled properly."""
        # Empty string should be invalid
        with pytest.raises(ValueError, match="identifier"):
            ExecuteMappingPathParams(
                identifier="",
                source_type="uniprot",
                target_type="ensembl"
            )
        
        # Whitespace-only should be invalid
        with pytest.raises(ValueError, match="identifier"):
            ExecuteMappingPathParams(
                identifier="   ",
                source_type="uniprot",
                target_type="ensembl"
            )

    def test_source_target_validation(self):
        """Test that source and target types cannot be the same."""
        with pytest.raises(ValueError, match="source_type.*target_type"):
            ExecuteMappingPathParams(
                identifier="P12345",
                source_type="uniprot",
                target_type="uniprot"
            )

    def test_model_export(self):
        """Test model export methods."""
        params = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            batch_size=100,
            min_confidence=0.8
        )
        
        # Test dict export
        params_dict = params.model_dump()
        assert params_dict["identifier"] == "P12345"
        assert params_dict["source_type"] == "uniprot"
        assert params_dict["target_type"] == "ensembl"
        assert params_dict["batch_size"] == 100
        assert params_dict["min_confidence"] == 0.8
        assert params_dict["include_deprecated"] is False
        assert params_dict["max_retries"] == 3
        
        # Test JSON export
        params_json = params.model_dump_json()
        assert isinstance(params_json, str)
        assert "P12345" in params_json
        assert "uniprot" in params_json
        assert "ensembl" in params_json

    def test_model_copy(self):
        """Test model copy with updates."""
        original = ExecuteMappingPathParams(
            identifier="P12345",
            source_type="uniprot",
            target_type="ensembl",
            batch_size=100
        )
        
        # Test copy with update
        updated = original.model_copy(update={"batch_size": 200, "min_confidence": 0.9})
        assert updated.identifier == "P12345"
        assert updated.batch_size == 200
        assert updated.min_confidence == 0.9
        
        # Ensure original is unchanged
        assert original.batch_size == 100
        assert original.min_confidence == 0.0