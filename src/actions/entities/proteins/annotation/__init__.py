"""Protein annotation strategy actions."""

from .extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction,
    ExtractUniProtFromXrefsParams,
    ExtractUniProtFromXrefsResult,
)

# Import to trigger registration
from . import normalize_accessions
from . import historical_resolution

__all__ = [
    "ProteinExtractUniProtFromXrefsAction",
    "ExtractUniProtFromXrefsParams",
    "ExtractUniProtFromXrefsResult",
]
