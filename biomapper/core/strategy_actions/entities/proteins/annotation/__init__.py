"""Protein annotation strategy actions."""

from .extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction,
    ExtractUniProtFromXrefsParams,
    ExtractUniProtFromXrefsResult,
)

__all__ = [
    "ProteinExtractUniProtFromXrefsAction",
    "ExtractUniProtFromXrefsParams",
    "ExtractUniProtFromXrefsResult",
]
