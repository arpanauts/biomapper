"""Test suite for protein metadata comparison functionality."""

import os
from pathlib import Path
from unittest.mock import Mock
from typing import Any, Protocol, TYPE_CHECKING

import pandas as pd
import pytest
from pytest_mock import MockerFixture
import numpy as np

from biomapper.core.protein_metadata_comparison import (
    ComparisonResult,
    ProteinMetadataComparison,
    ValidationResult,
    clean_uniprot_id,
)


if TYPE_CHECKING:
    from pandas import Series

    SeriesType = Series[Any]
else:
    SeriesType = pd.Series


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


@pytest.fixture
def sample_comparison_result() -> ComparisonResult:
    """Create sample comparison result for testing."""
    return ComparisonResult(
        shared_proteins={"P12345", "Q67890"},
        unique_to_first={"A11111"},
        unique_to_second={"B22222"},
        mappings_first={"P12345": {"GeneCards": ["GC1234"]}},
        mappings_second={"Q67890": {"RefSeq_Protein": ["NP_001234"]}},
    )


@pytest.fixture
def test_output_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test outputs."""
    return tmp_path / "test_output"


def test_initialization() -> None:
    """Test comparison tool initialization."""
    comparer = ProteinMetadataComparison()
    assert comparer.mapper is not None


def test_clean_uniprot_id_valid() -> None:
    """Test cleaning valid UniProt IDs."""
    test_cases = [
        ("P12345", "P12345", True),
        ("p12345", "P12345", True),
        ("Q9UNM6", "Q9UNM6", True),
        (" P12345 ", "P12345", True),  # Test whitespace handling
    ]

    for input_id, expected_clean, expected_valid in test_cases:
        clean_id, is_valid = clean_uniprot_id(input_id)
        assert clean_id == expected_clean
        assert is_valid == expected_valid


@pytest.mark.parametrize("input_id", [None, pd.NA, np.nan])
def test_clean_uniprot_id_invalid_input(input_id: Any) -> None:
    if input_id is None or pd.isna(input_id):
        clean_id, is_valid = clean_uniprot_id(str(input_id))
    else:
        clean_id, is_valid = clean_uniprot_id(input_id)
    assert not is_valid


@pytest.mark.parametrize(
    "protein_id,expected",
    [
        ("P12345", True),
        ("Q98765", True),
        ("INVALID", False),
        ("12345P", False),
        ("", False),
        ("P1234", False),
        ("P123456", False),
    ],
)
def test_uniprot_id_validation(
    comparer: ProteinMetadataComparison, protein_id: str, expected: bool
) -> None:
    """Test UniProt ID validation with various inputs."""
    cleaned_id, is_valid = clean_uniprot_id(protein_id)
    assert is_valid == expected


def test_validate_protein_ids(mock_mapper: Mock) -> None:
    """Test protein ID validation functionality."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    # Create test data
    test_data = pd.Series(["P12345", "invalid", "Q9UNM6", ""])

    # Validate IDs
    result = comparer.validate_protein_ids(test_data, "test_source")

    assert isinstance(result, ValidationResult)
    assert len(result.valid_ids) == 2
    assert "P12345" in result.valid_ids
    assert "Q9UNM6" in result.valid_ids
    assert len(result.invalid_records["id"]) == 2


def test_compare_datasets(comparer: ProteinMetadataComparison) -> None:
    """Test basic dataset comparison functionality."""
    first_set = {"P12345", "P67890"}
    second_set = {"P12345", "Q11111"}

    result = comparer.compare_datasets(first_set, second_set)

    assert isinstance(result, ComparisonResult)
    assert result.shared_proteins == {"P12345"}
    assert result.unique_to_first == {"P67890"}
    assert result.unique_to_second == {"Q11111"}
    assert "P12345" in result.mappings_first
    assert "P12345" in result.mappings_second


def test_compare_datasets_with_categories(comparer: ProteinMetadataComparison) -> None:
    """Test dataset comparison with specific categories."""
    first_set = {"P12345"}
    second_set = {"P12345"}
    categories = ["Disease"]

    # Configure mock mapper
    mapper = comparer.mapper
    assert isinstance(mapper, Mock)  # Type narrowing
    mapper.map_id.return_value = {
        "results": [{"from": "P12345", "to": {"id": "MIM:123456"}}]
    }

    result = comparer.compare_datasets(first_set, second_set, map_categories=categories)

    assert "P12345" in result.mappings_first
    assert "MIM" in result.mappings_first["P12345"]
    mapper.map_id.assert_called_with("P12345", "MIM")


def test_create_comparison_dataframe(
    mock_mapper: Mock, sample_comparison_result: ComparisonResult
) -> None:
    """Test creation of comparison DataFrames."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    invalid_first = {
        "id": ["invalid1"],
        "reason": ["Invalid format"],
        "original_value": ["invalid1"],
        "source": ["first"],
    }

    invalid_second = {
        "id": ["invalid2"],
        "reason": ["Invalid format"],
        "original_value": ["invalid2"],
        "source": ["second"],
    }

    results_df, invalid_df = comparer.create_comparison_dataframe(
        sample_comparison_result, invalid_first, invalid_second
    )

    assert isinstance(results_df, pd.DataFrame)
    assert isinstance(invalid_df, pd.DataFrame)
    assert len(results_df) == 4  # 2 shared + 1 unique first + 1 unique second
    assert len(invalid_df) == 2  # 1 invalid from each dataset


def test_generate_report(
    mock_mapper: Mock,
    sample_comparison_result: ComparisonResult,
    test_output_dir: Path,
) -> None:
    """Test report generation functionality."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    results_df = pd.DataFrame(
        {
            "uniprot_id": ["P12345", "Q67890"],
            "status": ["shared", "shared"],
            "source": ["both", "both"],
        }
    )

    invalid_df = pd.DataFrame(
        {
            "uniprot_id": ["invalid1", "invalid2"],
            "source": ["first", "second"],
            "reason": ["Invalid format", "Invalid format"],
            "original_value": ["invalid1", "invalid2"],
        }
    )

    comparer.generate_report(
        sample_comparison_result,
        results_df,
        invalid_df,
        str(test_output_dir),
    )

    report_files = list(test_output_dir.glob("protein_comparison_report_*.txt"))
    assert len(report_files) == 1

    report_content = report_files[0].read_text()
    assert "Protein Dataset Comparison Report" in report_content
    assert "Data Validation Summary" in report_content
    assert "Comparison Statistics" in report_content


def test_save_results(
    mock_mapper: Mock,
    test_output_dir: Path,
) -> None:
    """Test saving results to CSV files."""
    comparer = ProteinMetadataComparison(mapper=mock_mapper)

    results_df = pd.DataFrame(
        {
            "uniprot_id": ["P12345", "Q67890"],
            "status": ["shared", "shared"],
        }
    )

    invalid_df = pd.DataFrame(
        {
            "uniprot_id": ["invalid1"],
            "reason": ["Invalid format"],
        }
    )

    results_path, invalid_path = comparer.save_results(
        results_df,
        invalid_df,
        str(test_output_dir),
    )

    assert os.path.exists(results_path)
    assert os.path.exists(invalid_path)

    saved_results = pd.read_csv(results_path)
    saved_invalid = pd.read_csv(invalid_path)

    assert len(saved_results) == 2
    assert len(saved_invalid) == 1


def test_empty_datasets(comparer: ProteinMetadataComparison) -> None:
    """Test comparison of empty datasets."""
    result = comparer.compare_datasets(set(), set())

    assert len(result.shared_proteins) == 0
    assert len(result.unique_to_first) == 0
    assert len(result.unique_to_second) == 0
    assert len(result.mappings_first) == 0
    assert len(result.mappings_second) == 0


def test_completely_different_datasets(comparer: ProteinMetadataComparison) -> None:
    """Test comparison of datasets with no overlap."""
    first_set = {"P12345", "P67890"}
    second_set = {"Q11111", "Q22222"}

    result = comparer.compare_datasets(first_set, second_set)

    assert len(result.shared_proteins) == 0
    assert result.unique_to_first == first_set
    assert result.unique_to_second == second_set


def test_identical_datasets(comparer: ProteinMetadataComparison) -> None:
    """Test comparison of identical datasets."""
    proteins = {"P12345", "P67890"}
    result = comparer.compare_datasets(proteins, proteins)

    assert result.shared_proteins == proteins
    assert len(result.unique_to_first) == 0
    assert len(result.unique_to_second) == 0


def test_mappings_structure(comparer: ProteinMetadataComparison) -> None:
    """Test structure of generated mappings."""
    proteins = {"P12345"}
    result = comparer._generate_mappings(proteins)

    assert isinstance(result, dict)
    assert all(isinstance(v, dict) for v in result.values())
    assert all(
        isinstance(v, list) for mapping in result.values() for v in mapping.values()
    )


def test_generate_mappings_with_progress(mocker: MockerFixture) -> None:
    """Test concurrent mapping progress tracking."""
    mock_mapper = mocker.Mock()
    available_mappings = {"Protein/Gene": ["test_db"]}

    # Core mocks
    mock_mapper.get_available_mappings.return_value = available_mappings
    mock_mapper.map_id.return_value = {
        "results": [{"from": "P12345", "to": {"id": "TEST123"}}]
    }

    # Make the mock properly iterable
    mock_mapper.CORE_MAPPINGS = available_mappings
    type(mock_mapper).__iter__ = Mock(return_value=iter(available_mappings))
    type(mock_mapper).__getitem__ = Mock(side_effect=available_mappings.__getitem__)

    comparer = ProteinMetadataComparison(mapper=mock_mapper)
    result = comparer._generate_mappings({"P12345", "Q67890"})
    assert "P12345" in result


def test_mapping_with_errors(comparer: ProteinMetadataComparison) -> None:
    """Test mapping behavior when errors occur."""
    mapper = comparer.mapper
    assert isinstance(mapper, Mock)  # Type narrowing

    # Reset all mock configurations
    mapper.reset_mock()

    # Configure mock to raise exception for all mapping attempts
    mapper.map_id.side_effect = Exception("Mapping failed")

    # Configure available mappings to ensure the test uses the mock
    mapper.get_available_mappings.return_value = {
        "Disease": ["MIM"],
        "Protein/Gene": ["GeneCards", "RefSeq_Protein", "Ensembl"],
    }

    result = comparer._generate_mappings({"P12345"})
    assert len(result) == 0


def test_mapping_with_different_response_formats(
    comparer: ProteinMetadataComparison,
) -> None:
    """Test mapping with various response formats."""
    mapper = comparer.mapper
    assert isinstance(mapper, Mock)  # Type narrowing

    # Set up mock responses for different formats
    mapper.map_id.return_value = {
        "results": [
            {"from": "P12345", "to": "direct_id"},
            {"from": "P12345", "to": {"id": "nested_id"}},
        ]
    }

    # Configure mock mappings
    available_mappings = {"Disease": ["test_db"]}
    mapper.get_available_mappings.return_value = available_mappings
    mapper.CORE_MAPPINGS = available_mappings

    result = comparer._generate_mappings({"P12345"})
    assert "P12345" in result
    assert "test_db" in result["P12345"]
    assert any(id in result["P12345"]["test_db"] for id in ["direct_id", "nested_id"])


def test_concurrent_mapping(comparer: ProteinMetadataComparison) -> None:
    """Test concurrent mapping of multiple proteins."""
    large_protein_set = {f"P{i:05d}" for i in range(1, 201)}  # 200 proteins
    result = comparer._generate_mappings(large_protein_set)
    assert len(result) > 0


def test_report_generation_empty_results(
    comparer: ProteinMetadataComparison, test_output_dir: Path
) -> None:
    """Test report generation with empty results."""
    empty_results = pd.DataFrame(columns=["uniprot_id", "status", "source"])
    empty_invalid = pd.DataFrame(
        columns=["uniprot_id", "source", "reason", "original_value"]
    )

    comparer.generate_report(
        ComparisonResult(set(), set(), set(), {}, {}),
        empty_results,
        empty_invalid,
        str(test_output_dir),
    )

    report_files = list(test_output_dir.glob("protein_comparison_report_*.txt"))
    assert len(report_files) == 1

    report_content = report_files[0].read_text()
    assert "Total shared proteins: 0" in report_content


def test_invalid_uniprot_format(comparer: ProteinMetadataComparison) -> None:
    """Test handling of invalid UniProt format in comparison."""
    with pytest.raises(ValueError, match="Invalid UniProt ID format detected"):
        comparer.compare_datasets({"invalid_id"}, {"P12345"})


@pytest.mark.parametrize(
    "protein_id,expected_clean,expected_valid",
    [
        # Existing cases
        ("P12345", "P12345", True),
        ("p12345", "P12345", True),
        ("Q9UNM6", "Q9UNM6", True),
        (" P12345 ", "P12345", True),
        # New cases to cover lines 82-84
        (pd.NA, "<NA>", False),  # Tests pd.isna(protein_id) - line 82
        ("", "", False),  # Tests bool(cleaned_id) - line 83
        ("ABC123", "ABC123", False),  # Tests regex match - line 84
    ],
)
def test_clean_uniprot_id_comprehensive(
    protein_id: Any, expected_clean: str, expected_valid: bool
) -> None:
    """Test clean_uniprot_id with comprehensive test cases covering all validation paths."""
    if isinstance(protein_id, pd._libs.missing.NAType):
        clean_id, is_valid = clean_uniprot_id(str(protein_id))
    else:
        clean_id, is_valid = clean_uniprot_id(protein_id)
    assert clean_id == expected_clean
    assert is_valid == expected_valid


def test_series_type_definition() -> None:
    """Test SeriesType definition for runtime scenario."""
    test_series = pd.Series(["P12345", "Q67890"])
    comparer = ProteinMetadataComparison()
    result = comparer.validate_protein_ids(test_series, "test")
    assert isinstance(result, ValidationResult)


def test_series_type_annotation() -> None:
    """Test that SeriesType annotations work correctly."""
    series: SeriesType = pd.Series(["P12345"])
    assert isinstance(series, pd.Series)

    def process_series(data: SeriesType) -> None:
        assert isinstance(data, pd.Series)

    process_series(series)


def test_series_type_runtime_behavior() -> None:
    """Test SeriesType behavior at runtime."""
    # This will use the runtime SeriesType (pd.Series)
    test_series = pd.Series(["P12345", "Q67890"])

    # Verify we can use it with validate_protein_ids
    comparer = ProteinMetadataComparison()
    result = comparer.validate_protein_ids(test_series, "test")

    # Verify the result
    assert isinstance(result, ValidationResult)
    assert "P12345" in result.valid_ids
    assert "Q67890" in result.valid_ids

    # Verify runtime type
    assert SeriesType == pd.Series


def test_series_type_definitions() -> None:
    """Test both runtime and type checking SeriesType definitions."""
    # Create a test series
    test_series: SeriesType = pd.Series(["P12345", "Q67890"])

    # Runtime assertions
    assert isinstance(test_series, pd.Series)

    # Use the series in a way that exercises both type paths
    def accept_series(s: SeriesType) -> None:
        assert isinstance(s, pd.Series)

    accept_series(test_series)

    # Verify runtime type
    if not TYPE_CHECKING:
        assert SeriesType == pd.Series
