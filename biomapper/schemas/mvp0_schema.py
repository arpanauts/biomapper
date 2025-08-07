from typing import List, Optional
from pydantic import BaseModel


class QdrantSearchResultItem(BaseModel):
    """Represents a single search result item from Qdrant."""

    cid: int
    score: float


class PubChemAnnotation(BaseModel):
    """Holds detailed annotations for a PubChem CID."""

    cid: int
    title: Optional[str] = None  # Preferred Term
    iupac_name: Optional[str] = None
    molecular_formula: Optional[str] = None
    canonical_smiles: Optional[str] = None
    inchi_key: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[List[str]] = None
    parent_cid: Optional[int] = None  # CanonicalizedCompound (Parent CID)
    # Add other relevant fields as needed based on PubChem API responses


class LLMCandidateInfo(BaseModel):
    """Information about a candidate CID presented to the LLM."""

    cid: int
    qdrant_score: float
    annotations: PubChemAnnotation


class FinalMappingOutput(BaseModel):
    """The final structured output for a single biochemical name mapping."""

    original_biochemical_name: str
    mapped_pubchem_cid: Optional[int] = None
    qdrant_score_of_selected: Optional[float] = None
    llm_confidence: Optional[str] = None  # e.g., "High", "Medium", "Low"
    llm_rationale: Optional[str] = None
    candidates_considered: List[LLMCandidateInfo] = []
    error_message: Optional[
        str
    ] = None  # To capture any errors during processing for this specific name
