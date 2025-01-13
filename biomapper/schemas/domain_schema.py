from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class DomainType(str, Enum):
    """Supported entity domains."""
    COMPOUND = "compound"
    DISEASE = "disease"
    MEDICATION = "medication"

class DomainDocument(BaseModel):
    """Base schema for all domain documents."""
    domain_type: DomainType = Field(description="Type of domain this document belongs to")
    
    def to_search_text(self) -> str:
        """Convert document to searchable text for embedding.
        
        Must be implemented by subclasses.
        """
        raise NotImplementedError
