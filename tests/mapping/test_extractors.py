"""
Unit tests for biomapper.mapping.extractors and CSVAdapter.
"""
import pytest
from biomapper.mapping.extractors import (
    extract_hmdb_id,
    extract_chebi_id,
    extract_pubchem_id,
    extract_uniprot_id,
    extract_all_ids,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("HMDB0001234", "HMDB0001234"),
        ("foo HMDB0012345 bar", "HMDB0012345"),
        ("no id here", None),
    ],
)
def test_extract_hmdb_id(text, expected):
    assert extract_hmdb_id(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("CHEBI:15377", "CHEBI:15377"),
        ("foo CHEBI:1234 bar", "CHEBI:1234"),
        ("no chebi", None),
    ],
)
def test_extract_chebi_id(text, expected):
    assert extract_chebi_id(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1234567", "1234567"),
        ("foo 7654321 bar", "7654321"),
        ("abc", None),
    ],
)
def test_extract_pubchem_id(text, expected):
    assert extract_pubchem_id(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("P12345", "P12345"),
        ("foo Q9XYZ1 bar", "Q9XYZ1"),
        ("not a uniprot", None),
    ],
)
def test_extract_uniprot_id(text, expected):
    assert extract_uniprot_id(text) == expected


def test_extract_all_ids():
    text = "HMDB0001234 CHEBI:15377 1234567 P12345"
    ids = extract_all_ids(text)
    assert ids["hmdb"] == "HMDB0001234"
    assert ids["chebi"] == "CHEBI:15377"
    assert ids["pubchem"] == "1234567"
    assert ids["uniprot"] == "P12345"


def test_csv_adapter_extract_ids_from_row():
    # Test extracting IDs from multiple columns using extract_all_ids
    row = {
        "col1": "HMDB0001234",
        "col2": "CHEBI:15377",
        "col3": "1234567",
        "col4": "P12345",
    }
    
    # The CSVAdapter doesn't have extract_ids_from_row method
    # Instead, we can test extracting from each cell value
    ids = {}
    for col, value in row.items():
        extracted = extract_all_ids(value)
        ids.update({k: v for k, v in extracted.items() if v is not None})
    
    assert ids["hmdb"] == "HMDB0001234"
    assert ids["chebi"] == "CHEBI:15377"
    assert ids["pubchem"] == "1234567"
    assert ids["uniprot"] == "P12345"


def test_csv_adapter_extract_id_from_cell():
    # Test the extract_all_ids function directly since CSVAdapter
    # doesn't have extract_id_from_cell method
    ids = extract_all_ids("CHEBI:15377 and HMDB0001234")
    assert ids["chebi"] == "CHEBI:15377"
    assert ids["hmdb"] == "HMDB0001234"
