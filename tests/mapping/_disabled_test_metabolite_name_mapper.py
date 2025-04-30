"""Test suite for metabolite name mapping functionality."""

from pathlib import Path
import re
from unittest.mock import Mock, call, patch

import pandas as pd
import pytest
from requests_mock import Mocker

from biomapper.mapping.clients.chebi_client import ChEBIResult
from biomapper.mapping.metabolite.name import (
    MetaboliteClass,
    MetaboliteMapping,
    MetaboliteNameMapper,
    Classification
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

    # Set up UniChem mock response - Fix: Use get_compound_info_by_src_id instead
    mock_unichem.get_compound_info_by_src_id.return_value = {
        "chebi_ids": ["CHEBI:123"],
        "pubchem_ids": ["CID123"],
    }

    # Attach mocks to mapper instance
    mapper.refmet_client = mock_refmet
    mapper.unichem_client = mock_unichem
    mapper.chebi_client = mock_chebi

    result = mapper.map_single_name("glucose")

    assert isinstance(result, MetaboliteMapping)
    assert result.input_name == "glucose"
    assert result.compound_class == MetaboliteClass.SIMPLE
    assert result.refmet_id == "REFMET:0001"
    assert result.mapping_source == "RefMet"


def test_map_from_names(mapper: MetaboliteNameMapper) -> None:
    """Test mapping multiple metabolite names."""
    mock_callback = Mock()
    names = ["glucose", "cholesterol"]

    with patch.object(mapper, "map_single_name") as mock_map:
        # Create two different mappings to better test the functionality
        mock_map.side_effect = [
            MetaboliteMapping(
                input_name="glucose",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0001",
            ),
            MetaboliteMapping(
                input_name="cholesterol",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0002",
            ),
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
            MetaboliteMapping(
                input_name="glucose",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0001",
            ),
            MetaboliteMapping(
                input_name="cholesterol",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0002",
            ),
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
            MetaboliteMapping(
                input_name="glucose",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0001",
            ),
            MetaboliteMapping(
                input_name="cholesterol",
                compound_class=MetaboliteClass.SIMPLE,
                refmet_id="REFMET:0002",
            ),
        ]

        mapper.map_from_file(sample_csv, "compound_name", output_path)
        assert output_path.exists()
        result_df = pd.read_csv(output_path, sep="\t")
        assert "refmet_id" in result_df.columns


def test_no_refmet_match(mapper: MetaboliteNameMapper) -> None:
    """Test behavior when RefMet returns no match."""
    with patch.object(mapper.refmet_client, "search_by_name") as mock_search:
        mock_search.return_value = None

        result = mapper.map_single_name("unknown_metabolite")
        assert isinstance(result, MetaboliteMapping)
        assert result.refmet_id is None
        assert result.mapping_source is None


def test_refmet_success_with_unichem(
    mapper: MetaboliteNameMapper, requests_mock: Mocker
) -> None:
    """Test successful mapping through RefMet with UniChem enrichment."""
    # Mock RefMet response
    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=(
            "Input name\tRefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\t"
            "PubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
            "glucose\tRM0135901\tGlucose\tC6H12O6\t180.0634\tTEST123\t12345\t4167\t"
            "HMDB0000122\tC00031\n"
        ),
    )

    # Mock UniChem response
    requests_mock.get(
        f"{mapper.unichem_client.config.base_url}/compound/inchikey/TEST123",
        json={"chebi_ids": ["CHEBI:4167"], "pubchem_ids": ["12345"]},
    )

    result = mapper.map_single_name("glucose")
    assert result.input_name == "glucose"
    assert result.refmet_id == "REFMET:RM0135901"
    assert result.chebi_id == "CHEBI:4167"
    assert result.pubchem_id == "12345"
    assert result.mapping_source == "RefMet"


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
    with patch.object(mapper.refmet_client, "search_by_name") as mock_refmet:
        mock_refmet.return_value = None

        with patch.object(mapper.chebi_client, "search_by_name") as mock_chebi:
            mock_chebi.return_value = []

            result = mapper.map_single_name("unknown_compound")

            assert isinstance(result, MetaboliteMapping)
            assert result.input_name == "unknown_compound"
            assert result.refmet_id is None
            assert result.chebi_id is None
            assert result.mapping_source is None


def test_refmet_error_handling(mapper: MetaboliteNameMapper) -> None:
    """Test error handling when RefMet raises an exception."""
    with patch.object(mapper.refmet_client, "search_by_name") as mock_refmet:
        mock_refmet.side_effect = Exception("API Error")

        with patch.object(mapper.chebi_client, "search_by_name") as mock_chebi:
            mock_chebi.return_value = [
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


def test_map_single_name_with_refmet_edge_cases(
    mapper: MetaboliteNameMapper,
    requests_mock: Mocker,
) -> None:
    """Test mapping edge cases with RefMet."""
    # Mock RefMet response for HDL cholesterol
    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=(
            "Input name\tRefMet_ID\tStandardized name\tFormula\tExact mass\tINCHI_KEY\t"
            "PubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
            "HDL cholesterol\tRF123\tHDL-cholesterol\tC27H46O\t386.35\tABCD123\t12345\t"
            "67890\tHMDB123\tC12345\n"
        ),
    )

    # Mock UniChem response
    requests_mock.get(
        f"{mapper.unichem_client.config.base_url}/compound/inchikey/ABCD123",
        json={"chebi_ids": ["CHEBI:67890"], "pubchem_ids": ["12345"]},
    )

    result = mapper.map_single_name("HDL cholesterol")
    assert result.input_name == "HDL cholesterol"
    assert result.refmet_id == "REFMET:RF123"
    assert result.refmet_name == "HDL-cholesterol"
    assert result.inchikey == "ABCD123"
    assert result.chebi_id == "CHEBI:67890"
    assert result.mapping_source == "RefMet"


def test_map_single_name_with_failed_refmet(
    mapper: MetaboliteNameMapper,
    requests_mock: Mocker,
) -> None:
    """Test graceful handling of RefMet failures."""
    # Mock failed RefMet response
    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        status_code=500,
    )

    # Mock successful ChEBI response with ChEBIResult object
    with patch.object(
        mapper.chebi_client,
        "search_by_name",
        return_value=[
            ChEBIResult(
                chebi_id="CHEBI:789",
                name="Test Compound",
                inchikey="TEST123",
            )
        ],
    ):
        result = mapper.map_single_name("test-compound")
        assert result.input_name == "test-compound"
        assert result.refmet_id is None
        assert result.chebi_id == "CHEBI:789"
        assert result.mapping_source == "ChEBI"


def test_map_single_name_refmet_success(
    mapper: MetaboliteNameMapper,
    requests_mock: Mocker,
) -> None:
    """Test successful mapping through RefMet."""
    mock_response = (
        "Input name\tStandardized name\tFormula\tExact mass\tINCHI_KEY\tPubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
        "glucose\tGlucose\tC6H12O6\t180.0634\tWQZGKKKJIJFFOK-GASJEMHNSA-N\t5793\t4167\tHMDB0000122\tC00031\n"
    )

    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=mock_response,
    )

    result = mapper.map_single_name("glucose")
    assert result.input_name == "glucose"
    assert result.refmet_name == "Glucose"
    assert result.chebi_id == "CHEBI:4167"
    assert result.pubchem_id == "5793"
    assert result.inchikey == "WQZGKKKJIJFFOK-GASJEMHNSA-N"
    assert result.mapping_source == "RefMet"


def test_map_single_name_refmet_fallback_to_chebi(
    mapper: MetaboliteNameMapper,
    requests_mock: Mocker,
) -> None:
    """Test fallback to ChEBI when RefMet fails."""
    # Mock failed RefMet response
    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        status_code=500,
    )

    # Mock successful ChEBI response
    chebi_result = Mock()
    chebi_result.chebi_id = "CHEBI:4167"
    chebi_result.name = "glucose"
    with patch.object(
        mapper.chebi_client,
        "search_by_name",
        return_value=[chebi_result],
    ):
        result = mapper.map_single_name("glucose")
        assert result.input_name == "glucose"
        assert result.refmet_id is None
        assert result.chebi_id == "CHEBI:4167"
        assert result.chebi_name == "glucose"
        assert result.mapping_source == "ChEBI"


def test_map_single_name_invalid_refmet(
    mapper: MetaboliteNameMapper,
    requests_mock: Mocker,
) -> None:
    """Test handling of invalid RefMet results."""
    mock_response = (
        "Input name\tStandardized name\tFormula\tExact mass\tINCHI_KEY\tPubChem_CID\tChEBI_ID\tHMDB_ID\tKEGG_ID\n"
        "invalid\t-\t-\t-\t-\t-\t-\t-\t-\n"
    )

    requests_mock.post(
        f"{mapper.refmet_client.config.base_url}/name_to_refmet_new_minID.php",
        text=mock_response,
    )

    # Mock ChEBI fallback
    chebi_result = Mock()
    chebi_result.chebi_id = "CHEBI:4167"
    chebi_result.name = "glucose"
    with patch.object(
        mapper.chebi_client,
        "search_by_name",
        return_value=[chebi_result],
    ):
        result = mapper.map_single_name("invalid")
        assert result.refmet_id is None
        assert result.chebi_id == "CHEBI:4167"
        assert result.mapping_source == "ChEBI"


def test_classify_complex_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of various complex patterns."""
    test_cases = [
        (
            "Concentration of glucose in serum",
            MetaboliteClass.CONCENTRATION,
            "glucose",
            "serum",
        ),
        (
            "Ratio of omega-3 to total fatty acids",
            MetaboliteClass.RATIO,
            "omega-3",
            "total fatty acids",
        ),
        (
            "Total cholesterol in extremely large VLDL",
            MetaboliteClass.LIPOPROTEIN,
            "vldl cholesterol",
            None,
        ),
        ("Alanine/lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("HDL cholesterol", MetaboliteClass.LIPOPROTEIN, "hdl cholesterol", None),
        (
            "Glucose plus lactate",
            MetaboliteClass.COMPOSITE,
            "glucose plus lactate",
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_lipoprotein_extraction(mapper: MetaboliteNameMapper) -> None:
    """Test extraction of lipoprotein information."""
    test_cases = [
        ("HDL cholesterol", "HDL", None, "cholesterol"),
        ("extremely large VLDL", "VLDL", "extremely large", ""),
        ("small LDL particles", "LDL", "small", "particles"),
        ("IDL concentration", "IDL", None, "concentration"),
    ]

    for name, expected_class, expected_size, expected_remaining in test_cases:
        lipo_class, size, remaining = mapper.classifier._extract_lipoprotein_info(name)
        assert lipo_class == expected_class
        assert size == expected_size
        assert remaining.strip() == expected_remaining


def test_get_mapping_summary(mapper: MetaboliteNameMapper) -> None:
    """Test generation of mapping summary statistics."""
    mappings = [
        MetaboliteMapping(
            input_name="glucose",
            compound_class=MetaboliteClass.SIMPLE,
            refmet_id="REFMET:0001",
            chebi_id="CHEBI:17234",  # Add ChEBI ID
        ),
        MetaboliteMapping(
            input_name="HDL cholesterol",
            compound_class=MetaboliteClass.LIPOPROTEIN,
            refmet_id="REFMET:0002",
        ),
        MetaboliteMapping(
            input_name="unknown",
            compound_class=MetaboliteClass.SIMPLE,
        ),
    ]

    stats = mapper.get_mapping_summary(mappings)

    assert stats["total"] == 3
    assert stats["mapped_any"] == 2
    assert stats["mapped_refmet"] == 2
    assert stats["mapped_chebi"] == 1
    assert stats["percent_mapped"] == 66.7
    assert "simple" in stats["by_class"]
    assert "lipoprotein" in stats["by_class"]
    assert "RefMet" in stats["by_source"]
    assert len(stats["unmapped"]) == 1
    assert "unknown" in stats["unmapped"]


def test_print_mapping_report(
    mapper: MetaboliteNameMapper, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test printing of mapping report."""
    mappings = [
        MetaboliteMapping(
            input_name="glucose",
            compound_class=MetaboliteClass.SIMPLE,
            refmet_id="REFMET:0001",
            chebi_id="CHEBI:1234",  # Add ChEBI ID explicitly
            mapping_source="RefMet",
        ),
        MetaboliteMapping(
            input_name="HDL cholesterol",
            compound_class=MetaboliteClass.LIPOPROTEIN,
            refmet_id="REFMET:0002",
            mapping_source="RefMet",
        ),
    ]

    mapper.print_mapping_report(mappings)
    captured = capsys.readouterr()

    assert "Total metabolites processed: 2" in captured.out
    assert "Mapped to RefMet: 2" in captured.out
    assert "Mapped to ChEBI: 1" in captured.out


def test_map_single_name_with_classification(mapper: MetaboliteNameMapper) -> None:
    """Test mapping with metabolite classification."""
    with patch.object(mapper.refmet_client, "search_by_name") as mock_refmet:
        mock_refmet.return_value = {
            "refmet_id": "REFMET:0001",
            "name": "HDL Cholesterol",
            "inchikey": "TEST123",
        }

        result = mapper.map_single_name("Total HDL cholesterol")

        assert result.compound_class == MetaboliteClass.LIPOPROTEIN
        assert result.refmet_id == "REFMET:0001"
        assert result.primary_compound == "hdl cholesterol"
        assert result.mapping_source == "RefMet"


def test_complex_term_mapping(mapper: MetaboliteNameMapper) -> None:
    """Test mapping of complex metabolite terms."""
    test_cases = [
        (
            "Ratio of omega-3 to total fatty acids",
            MetaboliteClass.RATIO,
            "omega-3",
            "total fatty acids",
        ),
        (
            "Concentration of glucose in serum",
            MetaboliteClass.CONCENTRATION,
            "glucose",
            "serum",
        ),
        (
            "HDL cholesterol plus LDL cholesterol",
            MetaboliteClass.COMPOSITE,
            "hdl cholesterol plus ldl cholesterol",
            None,
        ),
    ]

    for name, expected_class, primary, secondary in test_cases:
        with patch.object(mapper.refmet_client, "search_by_name") as mock_refmet:
            mock_refmet.return_value = {
                "refmet_id": "REFMET:TEST",
                "name": primary,
            }

            result = mapper.map_single_name(name)
            assert result.compound_class == expected_class
            assert result.primary_compound == primary
            if secondary and result.secondary_compound:
                assert secondary in result.secondary_compound.lower()


def test_classify_ratio_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of different ratio patterns."""
    test_cases = [
        ("Alanine to Lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("Alanine/Lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("Ratio of HDL to LDL", MetaboliteClass.RATIO, "hdl", "ldl"),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert expected_primary in result.primary_compound.lower()
        if expected_secondary:
            assert result.secondary_compound is not None
            assert expected_secondary in result.secondary_compound.lower()


def test_classify_composite_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of composite measurements."""
    test_cases = [
        (
            "Total cholesterol minus HDL-C",
            MetaboliteClass.COMPOSITE,
            "total cholesterol minus hdl-c",  # Keep as single compound
            None,
        ),
        (
            "Glucose plus Lactate",
            MetaboliteClass.COMPOSITE,
            "glucose plus lactate",  # Keep as single compound
            None,
        ),
        (
            "HDL and LDL cholesterol",
            MetaboliteClass.COMPOSITE,
            "hdl and ldl cholesterol",  # Keep as single compound
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_pattern_matching_edge_cases(mapper: MetaboliteNameMapper) -> None:
    """Test pattern matching with edge cases."""
    test_cases = [
        ("", (None, None)),  # Empty string
        ("Simple metabolite", (None, None)),  # No pattern match
        ("X to Y ratio", ("x", "y")),  # Basic ratio
        ("Ratio of A to B", ("a", "b")),  # Standard ratio format
        (
            "Ratio of HDL to LDL",
            ("hdl", "ldl"),
        ),  # Ratio takes precedence over lipoprotein
        ("Concentration of Z in blood", ("z", "blood")),  # Standard concentration
        ("HDL cholesterol", (None, None)),  # Should be handled by lipoprotein logic
    ]

    for name, expected in test_cases:
        # Ensure name is str
        name_str = str(name)
        # Get patterns directly from the classifier
        ratio_patterns = [
            re.compile(r"ratio\s+of\s+(.+?)\s+to\s+(.+)", re.IGNORECASE),
            re.compile(r"(.+?)/(.+?)\s+ratio", re.IGNORECASE),
            re.compile(r"(.+?)\s+to\s+(.+?)\s+ratio", re.IGNORECASE),
        ]
        concentration_patterns = [
            re.compile(r"concentration\s+of\s+(.+?)\s+in\s+(.+)", re.IGNORECASE),
            re.compile(r"(.+?)\s+in\s+(.+)", re.IGNORECASE),
        ]
        primary, secondary = mapper.classifier._try_match_patterns(
            name_str,
            ratio_patterns + concentration_patterns,
        )
        assert (primary, secondary) == expected, f"Failed for input: {name_str}"


def test_classification_order(mapper: MetaboliteNameMapper) -> None:
    """Test that classification patterns are checked in the correct order."""
    test_cases = [
        # Ratio should take precedence over lipoprotein
        (
            "Ratio of HDL to LDL",
            MetaboliteClass.RATIO,
            "hdl",
            "ldl",
        ),
        # Concentration should take precedence over lipoprotein
        (
            "Concentration of HDL in blood",
            MetaboliteClass.CONCENTRATION,
            "hdl",
            "blood",
        ),
        # Composite should take precedence over lipoprotein
        (
            "HDL plus LDL",
            MetaboliteClass.COMPOSITE,
            "hdl plus ldl",
            None,
        ),
        # Lipoprotein only if no other patterns match
        (
            "HDL cholesterol",
            MetaboliteClass.LIPOPROTEIN,
            "hdl cholesterol",
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_case_and_total_prefix_handling(mapper: MetaboliteNameMapper) -> None:
    """Test case normalization and handling of 'Total' prefix."""
    test_cases = [
        (
            "TOTAL HDL CHOLESTEROL",
            MetaboliteClass.LIPOPROTEIN,
            "hdl cholesterol",
        ),
        (
            "Total Glucose",
            MetaboliteClass.SIMPLE,
            "glucose",
        ),
        (
            "TOTAL Ratio of HDL to LDL",
            MetaboliteClass.RATIO,
            "hdl",
            "ldl",
        ),
    ]

    for test_case in test_cases:
        name = str(test_case[0])  # Ensure name is str
        expected_class = test_case[1]
        expected_primary = test_case[2]
        expected_secondary = test_case[3] if len(test_case) > 3 else None

        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        if expected_secondary is not None:
            assert result.secondary_compound == expected_secondary
        else:
            assert result.secondary_compound is None

def test_classify_complex_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of various complex patterns."""
    test_cases = [
        (
            "Concentration of glucose in serum",
            MetaboliteClass.CONCENTRATION,
            "glucose",
            "serum",
        ),
        (
            "Ratio of omega-3 to total fatty acids",
            MetaboliteClass.RATIO,
            "omega-3",
            "total fatty acids",
        ),
        (
            "Total cholesterol in extremely large VLDL",
            MetaboliteClass.LIPOPROTEIN,
            "vldl cholesterol",
            None,
        ),
        ("Alanine/lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("HDL cholesterol", MetaboliteClass.LIPOPROTEIN, "hdl cholesterol", None),
        (
            "Glucose plus lactate",
            MetaboliteClass.COMPOSITE,
            "glucose plus lactate",
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_lipoprotein_extraction(mapper: MetaboliteNameMapper) -> None:
    """Test extraction of lipoprotein information."""
    test_cases = [
        ("HDL cholesterol", "HDL", None, "cholesterol"),
        ("extremely large VLDL", "VLDL", "extremely large", ""),
        ("small LDL particles", "LDL", "small", "particles"),
        ("IDL concentration", "IDL", None, "concentration"),
    ]

    for name, expected_class, expected_size, expected_remaining in test_cases:
        lipo_class, size, remaining = mapper.classifier._extract_lipoprotein_info(name)
        assert lipo_class == expected_class
        assert size == expected_size
        assert remaining.strip() == expected_remaining


def test_get_mapping_summary(mapper: MetaboliteNameMapper) -> None:
    """Test generation of mapping summary."""
    mappings = [
        MetaboliteMapping(
            input_name="glucose",
            compound_class=MetaboliteClass.SIMPLE,
            refmet_id="REFMET:0001",
            mapping_source="RefMet",
        ),
        MetaboliteMapping(
            input_name="hdl/ldl",
            compound_class=MetaboliteClass.RATIO,
            primary_compound="hdl",
            secondary_compound="ldl",
            mapping_source="ChEBI",
        ),
    ]

    summary = mapper.get_mapping_summary(mappings)
    assert summary["total_terms"] == 2
    assert summary["mapped_any"] == 1
    assert summary["by_class"][MetaboliteClass.SIMPLE.value] == 1
    assert summary["by_class"][MetaboliteClass.RATIO.value] == 1


def test_print_mapping_report(
    mapper: MetaboliteNameMapper, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test printing of mapping report."""
    mappings = [
        MetaboliteMapping(
            input_name="glucose",
            compound_class=MetaboliteClass.SIMPLE,
            refmet_id="REFMET:0001",
            mapping_source="RefMet",
        ),
        MetaboliteMapping(
            input_name="HDL cholesterol",
            compound_class=MetaboliteClass.LIPOPROTEIN,
            refmet_id="REFMET:0002",
            mapping_source="RefMet",
        ),
    ]

    mapper.print_mapping_report(mappings)
    captured = capsys.readouterr()
    assert "Mapping Summary" in captured.out
    assert "Total terms processed: 2" in captured.out


def test_map_single_name_with_classification(mapper: MetaboliteNameMapper) -> None:
    """Test mapping with metabolite classification."""
    with patch.object(mapper.refmet_client, "search_by_name") as mock_refmet:
        mock_refmet.return_value = {
            "refmet_id": "REFMET:0001",
            "name": "HDL Cholesterol",
            "inchikey": "TEST123",
        }

        result = mapper.map_single_name("Total HDL cholesterol")
        assert result.compound_class == MetaboliteClass.LIPOPROTEIN
        assert result.mapping_source == "RefMet"


def test_complex_term_mapping(mapper: MetaboliteNameMapper) -> None:
    """Test mapping of complex terms."""
    test_cases = [
        ("HDL/LDL ratio", MetaboliteClass.RATIO),
        ("Glucose in serum", MetaboliteClass.CONCENTRATION),
        ("HDL cholesterol", MetaboliteClass.LIPOPROTEIN),
        ("Glucose plus lactate", MetaboliteClass.COMPOSITE),
    ]

    for name, expected_class in test_cases:
        result = mapper.map_single_name(name)
        assert result.compound_class == expected_class


def test_classify_ratio_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of different ratio patterns."""
    test_cases = [
        ("Alanine to Lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("Alanine/Lactate ratio", MetaboliteClass.RATIO, "alanine", "lactate"),
        ("Ratio of HDL to LDL", MetaboliteClass.RATIO, "hdl", "ldl"),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_classify_composite_patterns(mapper: MetaboliteNameMapper) -> None:
    """Test classification of composite measurements."""
    test_cases = [
        (
            "Total cholesterol minus HDL-C",
            MetaboliteClass.COMPOSITE,
            "total cholesterol minus hdl-c",  # Keep as single compound
            None,
        ),
        (
            "Glucose plus Lactate",
            MetaboliteClass.COMPOSITE,
            "glucose plus lactate",  # Keep as single compound
            None,
        ),
        (
            "HDL and LDL cholesterol",
            MetaboliteClass.COMPOSITE,
            "hdl and ldl cholesterol",  # Keep as single compound
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_pattern_matching_edge_cases(mapper: MetaboliteNameMapper) -> None:
    """Test edge cases in pattern matching."""
    test_cases = [
        ("", MetaboliteClass.SIMPLE),  # Empty string
        ("   ", MetaboliteClass.SIMPLE),  # Only whitespace
        ("Total", MetaboliteClass.SIMPLE),  # Just the word "Total"
        ("HDL/", MetaboliteClass.SIMPLE),  # Incomplete ratio
        ("in blood", MetaboliteClass.SIMPLE),  # Just matrix
    ]

    for name, expected_class in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class


def test_classification_order(mapper: MetaboliteNameMapper) -> None:
    """Test that classification patterns are checked in the correct order."""
    test_cases = [
        # Ratio should take precedence over lipoprotein
        (
            "Ratio of HDL to LDL",
            MetaboliteClass.RATIO,
            "hdl",
            "ldl",
        ),
        # Concentration should take precedence over lipoprotein
        (
            "Concentration of HDL in blood",
            MetaboliteClass.CONCENTRATION,
            "hdl",
            "blood",
        ),
        # Composite should take precedence over lipoprotein
        (
            "HDL plus LDL",
            MetaboliteClass.COMPOSITE,
            "hdl plus ldl",
            None,
        ),
        # Lipoprotein only if no other patterns match
        (
            "HDL cholesterol",
            MetaboliteClass.LIPOPROTEIN,
            "hdl cholesterol",
            None,
        ),
    ]

    for name, expected_class, expected_primary, expected_secondary in test_cases:
        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary


def test_case_and_total_prefix_handling(mapper: MetaboliteNameMapper) -> None:
    """Test case normalization and handling of 'Total' prefix."""
    test_cases = [
        (
            "TOTAL HDL CHOLESTEROL",
            MetaboliteClass.LIPOPROTEIN,
            "hdl cholesterol",
        ),
        (
            "Total Glucose",
            MetaboliteClass.SIMPLE,
            "glucose",
        ),
        (
            "TOTAL Ratio of HDL to LDL",
            MetaboliteClass.RATIO,
            "hdl",
            "ldl",
        ),
    ]

    for test_case in test_cases:
        name = str(test_case[0])  # Ensure name is str
        expected_class = test_case[1]
        expected_primary = test_case[2]
        expected_secondary = test_case[3] if len(test_case) > 3 else None

        result = mapper.classifier.classify(name)
        assert result.measurement_class == expected_class
        assert result.primary_compound == expected_primary
        assert result.secondary_compound == expected_secondary
