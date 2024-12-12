"""Test suite for metabolite name mapping functionality."""

from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd
import pytest

from biomapper.mapping.chebi_client import ChEBIResult
from biomapper.mapping.metabolite_name_mapper import (
    MetaboliteMapping,
    MetaboliteNameMapper,
)


@pytest.fixture
def mapper() -> MetaboliteNameMapper:
    """Create a MetaboliteNameMapper instance."""
    return MetaboliteNameMapper()


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a sample CSV file for testing."""
    df = pd.DataFrame(
        {
            "compound_name": ["glucose", "cholesterol"],
            "other_col": ["value1", "value2"],
        }
    )
    path = tmp_path / "test.csv"
    df.to_csv(path, index=False)
    return path


def test_map_single_name(mapper: MetaboliteNameMapper) -> None:
    """Test mapping a single metabolite name."""
    # Create fresh mocks for each client
    mock_refmet = Mock()
    mock_unichem = Mock()
    mock_chebi = Mock()

    # Set up RefMet mock response
    mock_refmet.search_by_name.return_value = {
        "refmet_id": "REFMET:0001",
        "name": "Glucose",
        "inchikey": "TEST123",
    }

    # Set up UniChem mock response
    mock_unichem.get_compound_info_by_inchikey.return_value = {
        "chebi_ids": ["CHEBI:123"],
        "pubchem_ids": ["CID123"],
    }

    # Attach mocks to mapper instance
    mapper.refmet_client = mock_refmet
    mapper.unichem_client = mock_unichem
    mapper.chebi_client = mock_chebi

    result = mapper.map_single_name("glucose")

    assert isinstance(result, MetaboliteMapping)
    assert result.refmet_id == "REFMET:0001"
    assert result.chebi_id == "CHEBI:123"
    assert result.mapping_source == "RefMet"


def test_map_from_names(mapper: MetaboliteNameMapper) -> None:
    """Test mapping multiple metabolite names."""
    mock_callback = Mock()
    names = ["glucose", "cholesterol"]

    with patch.object(mapper, "map_single_name") as mock_map:
        # Create two different mappings to better test the functionality
        mock_map.side_effect = [
            MetaboliteMapping(input_name="glucose", refmet_id="REFMET:0001"),
            MetaboliteMapping(input_name="cholesterol", refmet_id="REFMET:0002"),
        ]

        results = mapper.map_from_names(names, progress_callback=mock_callback)

        # Test return type and length
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(result, MetaboliteMapping) for result in results)

        # Test individual mappings
        assert results[0].input_name == "glucose"
        assert results[0].refmet_id == "REFMET:0001"
        assert results[1].input_name == "cholesterol"
        assert results[1].refmet_id == "REFMET:0002"

        # Test progress callback
        assert mock_callback.call_count == 2
        mock_callback.assert_has_calls([call(1, 2), call(2, 2)])


def test_map_from_file(mapper: MetaboliteNameMapper, sample_csv: Path) -> None:
    """Test mapping metabolites from a file."""
    with patch.object(mapper, "map_from_names") as mock_map:
        mock_map.return_value = [
            MetaboliteMapping(input_name="glucose", refmet_id="REFMET:0001"),
            MetaboliteMapping(input_name="cholesterol", refmet_id="REFMET:0002"),
        ]

        result_df = mapper.map_from_file(sample_csv, "compound_name")
        assert isinstance(result_df, pd.DataFrame)
        assert "refmet_id" in result_df.columns
        assert len(result_df) == 2


def test_map_from_file_invalid_column(
    mapper: MetaboliteNameMapper, sample_csv: Path
) -> None:
    """Test handling of invalid column name."""
    with pytest.raises(ValueError):
        mapper.map_from_file(sample_csv, "invalid_column")


def test_map_from_file_with_output(
    mapper: MetaboliteNameMapper, sample_csv: Path, tmp_path: Path
) -> None:
    """Test mapping from file with output save."""
    output_path = tmp_path / "results.tsv"

    with patch.object(mapper, "map_from_names") as mock_map:
        mock_map.return_value = [
            MetaboliteMapping(input_name="glucose", refmet_id="REFMET:0001"),
            MetaboliteMapping(input_name="cholesterol", refmet_id="REFMET:0002"),
        ]

        mapper.map_from_file(sample_csv, "compound_name", output_path)
        assert output_path.exists()
        result_df = pd.read_csv(output_path, sep="\t")
        assert "refmet_id" in result_df.columns


def test_no_refmet_match(mapper: MetaboliteNameMapper) -> None:
    """Test behavior when RefMet returns no match."""
    with patch("biomapper.mapping.metabolite_name_mapper.RefMetClient") as mock_refmet:
        mock_refmet.return_value.search_by_name.return_value = None

        result = mapper.map_single_name("unknown_metabolite")
        assert isinstance(result, MetaboliteMapping)
        assert result.refmet_id is None
        assert result.mapping_source is None


def test_refmet_success_with_unichem(mapper: MetaboliteNameMapper) -> None:
    """Test successful mapping through RefMet with UniChem enrichment."""
    # Create fresh mocks
    mock_refmet = Mock()
    mock_unichem = Mock()
    mock_chebi = Mock()

    # Set up RefMet mock response
    mock_refmet.search_by_name.return_value = {
        "refmet_id": "REFMET:0001",
        "name": "Glucose",
        "inchikey": "TEST123",
    }

    # Set up UniChem mock response
    mock_unichem.get_compound_info_by_inchikey.return_value = {
        "chebi_ids": ["CHEBI:123"],
        "pubchem_ids": ["CID123"],
    }

    # Attach mocks to mapper instance
    mapper.refmet_client = mock_refmet
    mapper.unichem_client = mock_unichem
    mapper.chebi_client = mock_chebi

    result = mapper.map_single_name("glucose")

    assert isinstance(result, MetaboliteMapping)
    assert result.refmet_id == "REFMET:0001"
    assert result.refmet_name == "Glucose"
    assert result.chebi_id == "CHEBI:123"
    assert result.pubchem_id == "CID123"
    assert result.inchikey == "TEST123"
    assert result.mapping_source == "RefMet"

    # Verify ChEBI client wasn't called since RefMet succeeded
    mock_chebi.search_by_name.assert_not_called()


def test_refmet_fails_chebi_success(mapper: MetaboliteNameMapper) -> None:
    """Test fallback to ChEBI when RefMet fails."""
    # Create fresh mocks
    mock_refmet = Mock()
    mock_chebi = Mock()

    # Set up RefMet to return None (no match)
    mock_refmet.search_by_name.return_value = None

    # Set up ChEBI mock response
    mock_chebi.search_by_name.return_value = [
        ChEBIResult(
            chebi_id="CHEBI:17234",
            name="glucose",
            inchikey="WQZGKKKJIJFFOK-GASJEMHNSA-N",
        )
    ]

    # Attach mocks to mapper instance
    mapper.refmet_client = mock_refmet
    mapper.chebi_client = mock_chebi

    result = mapper.map_single_name("glucose")

    assert isinstance(result, MetaboliteMapping)
    assert result.refmet_id is None
    assert result.chebi_id == "CHEBI:17234"
    assert result.chebi_name == "glucose"
    assert result.inchikey == "WQZGKKKJIJFFOK-GASJEMHNSA-N"
    assert result.mapping_source == "ChEBI"


def test_both_services_fail(mapper: MetaboliteNameMapper) -> None:
    """Test behavior when both RefMet and ChEBI fail to find matches."""
    with patch("biomapper.mapping.metabolite_name_mapper.RefMetClient") as mock_refmet:
        mock_refmet.return_value.search_by_name.return_value = None

        with patch(
            "biomapper.mapping.metabolite_name_mapper.ChEBIClient"
        ) as mock_chebi:
            mock_chebi.return_value.search_by_name.return_value = []

            result = mapper.map_single_name("unknown_compound")

            assert isinstance(result, MetaboliteMapping)
            assert result.input_name == "unknown_compound"
            assert result.refmet_id is None
            assert result.chebi_id is None
            assert result.mapping_source is None


def test_refmet_error_handling(mapper: MetaboliteNameMapper) -> None:
    """Test error handling when RefMet raises an exception."""
    with patch("biomapper.mapping.metabolite_name_mapper.RefMetClient") as mock_refmet:
        mock_refmet.return_value.search_by_name.side_effect = Exception("API Error")

        with patch(
            "biomapper.mapping.metabolite_name_mapper.ChEBIClient"
        ) as mock_chebi:
            mock_chebi.return_value.search_by_name.return_value = [
                ChEBIResult(
                    chebi_id="CHEBI:17234",
                    name="glucose",
                    inchikey="WQZGKKKJIJFFOK-GASJEMHNSA-N",
                )
            ]

            result = mapper.map_single_name("glucose")

            # Should fall back to ChEBI successfully
            assert isinstance(result, MetaboliteMapping)
            assert result.chebi_id == "CHEBI:17234"
            assert result.mapping_source == "ChEBI"


def test_all_services_error(mapper: MetaboliteNameMapper) -> None:
    """Test behavior when all services raise exceptions."""
    # Create fresh mocks
    mock_refmet = Mock()
    mock_chebi = Mock()

    # Set up both services to raise exceptions
    mock_refmet.search_by_name.side_effect = Exception("RefMet Error")
    mock_chebi.search_by_name.side_effect = Exception("ChEBI Error")

    # Attach mocks to mapper instance
    mapper.refmet_client = mock_refmet
    mapper.chebi_client = mock_chebi

    result = mapper.map_single_name("glucose")

    assert isinstance(result, MetaboliteMapping)
    assert result.input_name == "glucose"
    assert result.refmet_id is None
    assert result.chebi_id is None
    assert result.mapping_source is None
