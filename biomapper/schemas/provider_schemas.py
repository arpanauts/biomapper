"""Provider-specific schemas for biomapper."""

from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported ontology providers."""

    CHEBI = "chebi"
    UNICHEM = "unichem"
    REFMET = "refmet"


class ChEBIEntry(BaseModel):
    """ChEBI compound entry schema."""

    chebi_id: str = Field(..., description="ChEBI identifier")
    name: str = Field(..., description="Primary name")
    definition: Optional[str] = Field(None, description="Compound definition")
    formula: Optional[str] = Field(None, description="Chemical formula")
    charge: Optional[int] = Field(None, description="Formal charge")
    mass: Optional[float] = Field(None, description="Monoisotopic mass")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    xrefs: Dict[str, List[str]] = Field(
        default_factory=dict, description="Cross-references to other databases"
    )


class UniChemEntry(BaseModel):
    """UniChem compound entry schema."""

    unichem_id: str = Field(..., description="UniChem identifier")
    name: str = Field(..., description="Primary name")
    source_id: str = Field(..., description="Source database identifier")
    source_name: str = Field(..., description="Source database name")
    xrefs: Dict[str, List[str]] = Field(
        default_factory=dict, description="Cross-references to other databases"
    )


class RefMetEntry(BaseModel):
    """RefMet metabolite entry schema."""

    refmet_id: str = Field(..., description="RefMet identifier")
    name: str = Field(..., description="Primary name")
    systematic_name: Optional[str] = Field(None, description="Systematic chemical name")
    formula: Optional[str] = Field(None, description="Chemical formula")
    super_class: Optional[str] = Field(None, description="Chemical superclass")
    main_class: Optional[str] = Field(None, description="Chemical main class")
    sub_class: Optional[str] = Field(None, description="Chemical subclass")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    xrefs: Dict[str, List[str]] = Field(
        default_factory=dict, description="Cross-references to other databases"
    )


class ProviderConfig(BaseModel):
    """Configuration for a provider."""

    name: ProviderType
    base_url: Optional[str] = Field(None, description="Base URL for API access")
    api_key: Optional[str] = Field(None, description="API key if required")
    data_path: Optional[str] = Field(None, description="Path to local data file")
    chunk_size: int = Field(1000, description="Size of text chunks for retrieval")
    overlap: int = Field(100, description="Overlap between chunks")
    embedding_model: Optional[str] = Field(
        None, description="Model to use for embeddings"
    )
    additional_config: Dict[str, Any] = Field(
        default_factory=dict, description="Additional provider-specific configuration"
    )
