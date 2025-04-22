"""
extractors.py

Utility functions for extracting and normalizing identifiers from endpoint values (e.g., MetabolitesCSV rows).
"""
import re
from typing import Optional, Dict

# Patterns for common metabolite/protein IDs
HMDB_PATTERN = re.compile(r"HMDB\d{5,7}")
CHEBI_PATTERN = re.compile(r"CHEBI:\d+")
PUBCHEM_PATTERN = re.compile(r"(?<!:)\b\d{5,}\b")  # PubChem CIDs: not after colon, 5+ digits
UNIPROT_PATTERN = re.compile(r"[OPQ][0-9][A-Z0-9]{3}[0-9]")  # Simplified UniProt


def extract_hmdb_id(text: str) -> Optional[str]:
    match = HMDB_PATTERN.search(text)
    return match.group(0) if match else None

def extract_chebi_id(text: str) -> Optional[str]:
    match = CHEBI_PATTERN.search(text)
    return match.group(0) if match else None

def extract_pubchem_id(text: str) -> Optional[str]:
    match = PUBCHEM_PATTERN.search(text)
    return match.group(0) if match else None

def extract_uniprot_id(text: str) -> Optional[str]:
    match = UNIPROT_PATTERN.search(text)
    return match.group(0) if match else None


SUPPORTED_ID_TYPES = ["hmdb", "chebi", "pubchem", "uniprot"]

def extract_all_ids(text: str) -> Dict[str, Optional[str]]:
    """Extracts all supported identifiers (HMDB, ChEBI, PubChem, UniProt)
    from a given text/cell."""
    return {
        "hmdb": extract_hmdb_id(text),
        "chebi": extract_chebi_id(text),
        "pubchem": extract_pubchem_id(text),
        "uniprot": extract_uniprot_id(text),
    }
