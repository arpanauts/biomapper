"""Test suite for protein metadata comparison functionality."""

from unittest.mock import Mock
from typing import Any, Protocol, Iterator
import pytest

from biomapper.core.protein_metadata_comparison import (
    ProteinMetadataComparison,
)


# Define SeriesType as a Protocol for testing
class SeriesType(Protocol):
    """Protocol for pandas Series."""

    def __len__(self) -> int:
        ...

    def __iter__(self) -> Iterator[Any]:
        ...

    def __getitem__(self, key: Any) -> Any:
        ...


# Define a protocol for the mapper interface
class ProteinMapper(Protocol):
    def map_protein(self, protein_id: str, source: str) -> dict[str, Any]:
        ...

    def validate_protein_ids(self, protein_ids: SeriesType, source_name: str) -> Any:
        ...

    def assert_called_with(self, *args: Any, **kwargs: Any) -> None:
        ...


@pytest.fixture
def mock_mapper() -> Mock:
    """Create a mock UniprotFocusedMapper."""
    mapper = Mock()

    available_mappings = {
        "Disease": ["MIM"],
        "Protein/Gene": ["GeneCards", "RefSeq_Protein", "Ensembl"],
    }

    # Core mocks
    mapper.get_available_mappings.return_value = available_mappings
    mapper.map_id.return_value = {
        "results": [{"from": "P12345", "to": {"id": "TEST123"}}]
    }

    # Make the mock properly iterable
    mapper.CORE_MAPPINGS = (
        available_mappings  # Add as attribute to support direct access
    )
    type(mapper).__iter__ = Mock(return_value=iter(available_mappings))
    type(mapper).__getitem__ = Mock(side_effect=available_mappings.__getitem__)

    return mapper


@pytest.fixture
def comparer(mock_mapper: Mock) -> ProteinMetadataComparison:
    """Create a ProteinMetadataComparison instance with mock mapper."""
    return ProteinMetadataComparison(mapper=mock_mapper)


def test_process_protein_with_invalid_to_id(mock_mapper: Mock) -> None:
    """Test processing a protein when 'to' ID is invalid or unexpected type."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    # Override the map_id return value for this specific test
    mock_mapper.map_id.return_value = {"results": [{"from": "P12345", "to": None}]}

    # Process a single protein
    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 0


def test_process_protein_with_missing_to_field(mock_mapper: Mock) -> None:
    """Test processing a protein when 'to' field is missing."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    # Override the map_id return value for this specific test
    mock_mapper.map_id.return_value = {
        "results": [{"from": "P12345"}]  # Missing 'to' field
    }

    # Process a single protein
    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 0


def test_process_protein_with_empty_results(mock_mapper: Mock) -> None:
    """Test processing a protein when results are empty."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    # Override the map_id return value for this specific test
    mock_mapper.map_id.return_value = {"results": []}

    # Process a single protein
    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 0


def test_process_chunk_with_mixed_results(mock_mapper: Mock) -> None:
    """Test processing a chunk of proteins with mixed results."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    def map_id_side_effect(protein_id: str, target_db: str) -> dict[str, Any]:
        if protein_id == "P12345":
            return {"results": [{"from": protein_id, "to": {"id": "TEST123"}}]}
        else:
            return {"results": [{"from": protein_id, "to": None}]}

    mock_mapper.map_id.side_effect = map_id_side_effect

    # Process multiple proteins
    result = comparer._generate_mappings({"P12345", "Q67890"})
    assert len(result) == 1
    assert "P12345" in result


def test_process_chunk_with_errors(mock_mapper: Mock) -> None:
    """Test processing a chunk when errors occur."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    def map_id_side_effect(protein_id: str, target_db: str) -> dict[str, Any]:
        if protein_id == "P12345":
            raise Exception("Test error")
        return {"results": [{"from": protein_id, "to": {"id": "TEST123"}}]}

    mock_mapper.map_id.side_effect = map_id_side_effect

    # Process multiple proteins
    result = comparer._generate_mappings({"P12345", "Q67890"})
    assert len(result) == 1
    assert "Q67890" in result


def test_process_chunk_with_invalid_response(mock_mapper: Mock) -> None:
    """Test processing a chunk when response format is invalid."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    # Override the map_id return value for this specific test
    mock_mapper.map_id.return_value = {"invalid_format": True}

    # Process a single protein
    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 0


def test_process_chunk_mapping_error(mock_mapper: Mock) -> None:
    """Test error handling in process_chunk function when mappings update fails."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    def map_id_side_effect(protein_id: str, target_db: str) -> dict[str, Any]:
        if target_db == "MIM":
            return {
                "results": [
                    {"from": protein_id, "to": {"id": "MIM123"}},
                ]
            }
        elif target_db == "GeneCards":
            return {
                "results": [
                    {"from": protein_id, "to": {"id": "GC123"}},
                ]
            }
        else:
            raise Exception(f"Test error for {target_db}")

    mock_mapper.map_id.side_effect = map_id_side_effect

    # Process protein - should handle errors gracefully
    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 1
    assert "P12345" in result
    assert "MIM" in result["P12345"]
    assert "GeneCards" in result["P12345"]


def test_process_chunk_causes_exception(mock_mapper: Mock) -> None:
    """Test that the except block in process_chunk is covered by causing an exception."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    def map_id_side_effect(protein_id: str, target_db: str) -> dict[str, Any]:
        if protein_id == "P12345":
            if target_db == "MIM":
                return {
                    "results": [
                        {"from": protein_id, "to": {"id": "MIM123"}},
                    ]
                }
            else:
                raise Exception("Test error")
        return {"results": []}

    mock_mapper.map_id.side_effect = map_id_side_effect

    # Process protein - should handle errors gracefully
    result = comparer._generate_mappings({"P12345", "Q67890"})
    assert len(result) == 1
    assert "P12345" in result
    assert "MIM" in result["P12345"]


def test_process_chunk_error_handling(mock_mapper: Mock) -> None:
    """Test error handling in process_chunk function."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    def map_id_side_effect(protein_id: str, target_db: str) -> dict[str, Any]:
        if protein_id == "P12345":
            if target_db == "MIM":
                return {
                    "results": [
                        {"from": protein_id, "to": {"id": "MIM123"}},
                    ]
                }
            elif target_db == "GeneCards":
                return {
                    "results": [
                        {"from": protein_id, "to": None},  # Invalid mapping
                    ]
                }
            else:
                raise Exception("Test error")
        return {"results": []}

    mock_mapper.map_id.side_effect = map_id_side_effect

    # Process protein - should handle errors gracefully
    result = comparer._generate_mappings({"P12345", "Q67890"})
    assert len(result) == 1
    assert "P12345" in result
    assert "MIM" in result["P12345"]
    assert "GeneCards" not in result["P12345"]  # Invalid mapping should be skipped
