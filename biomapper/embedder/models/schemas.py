"""Data schemas for the Biomapper Embedder module."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class EmbedderItem(BaseModel):
    """Standardized format for data to be embedded."""
    
    id: str = Field(..., description="Unique identifier for the item")
    type: str = Field(..., description="Data type (e.g., pubchem_compound, pubmed_article)")
    primary_text: str = Field(..., description="Main content for embedding generation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata fields")
    source: str = Field(..., description="Source of the data")


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""
    
    id: str = Field(..., description="ID of the embedded item")
    embedding: List[float] = Field(..., description="Embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the item")


class SearchResult(BaseModel):
    """Result from vector search."""
    
    id: str = Field(..., description="ID of the retrieved item")
    similarity: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the item")
