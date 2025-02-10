from typing import List, Optional, Dict, Any
from pydantic import Field, model_validator
from .domain_schema import DomainDocument, DomainType


class MetaboliteDocument(DomainDocument):
    """Metabolite document optimized for name matching."""

    hmdb_id: str = Field(description="Primary HMDB identifier")
    name: str = Field(description="Primary name of the metabolite")
    synonyms: List[str] = Field(
        default_factory=list, description="Alternative names and synonyms"
    )
    description: Optional[str] = Field(
        default=None,
        description="Full text description containing potential informal names",
    )

    def to_search_text(self) -> str:
        """Convert document to searchable text for embedding."""
        parts = [self.name, " ".join(self.synonyms)]
        if self.description:
            # Add first sentence of description which often contains alternative names
            first_sentence = self.description.split(".")[0] if self.description else ""
            parts.append(first_sentence)
        return " ".join(parts)

    @model_validator(mode="before")
    def set_domain_type(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Set the domain type for all instances."""
        values["domain_type"] = DomainType.COMPOUND
        return values
