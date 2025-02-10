"""Base classes for SPOKE database integration."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field, validator


class SPOKEConfig(BaseModel):
    """Configuration for SPOKE database client."""
    
    base_url: str = Field(
        "https://spoke.rbvi.ucsf.edu/api/v1",
        description="SPOKE API base URL"
    )
    timeout: int = Field(30, description="Request timeout in seconds", gt=0)
    max_retries: int = Field(3, description="Maximum number of retry attempts", ge=0)
    backoff_factor: float = Field(0.5, description="Backoff factor for retries")
    
    class Config:
        """Pydantic config."""
        frozen = True


class SPOKEEntity(BaseModel):
    """SPOKE entity representation."""
    
    input_id: str = Field(..., description="Original input identifier")
    spoke_id: str = Field(..., description="SPOKE node identifier")
    node_type: str = Field(..., description="SPOKE node type (e.g., Compound)")
    node_label: str = Field(..., description="Human-readable label")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Mapping confidence score"
    )
    source: str = Field(
        default="direct",
        description="Source of the mapping (direct/inferred)"
    )

    @validator("node_type")
    def validate_node_type(cls, v: str) -> str:
        """Validate node type is a known SPOKE type."""
        valid_types = {
            "Compound", "Gene", "Protein", "Disease",
            "Pathway", "Anatomy", "Symptom"
        }
        if v not in valid_types:
            raise ValueError(f"Invalid node type: {v}. Must be one of {valid_types}")
        return v


class SPOKERelation(BaseModel):
    """SPOKE relationship representation."""
    
    source_id: str = Field(..., description="Source node SPOKE ID")
    target_id: str = Field(..., description="Target node SPOKE ID")
    relation_type: str = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship properties"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relationship confidence score"
    )


class AQLQuery(BaseModel):
    """Arango Query Language (AQL) query representation."""
    
    query_text: str = Field(..., description="AQL query string")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Query parameters"
    )
    expected_node_types: List[str] = Field(
        default_factory=list,
        description="Expected node types in results"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional query metadata"
    )


class SPOKEMappingResult(BaseModel):
    """Results of SPOKE mapping operation."""
    
    mapped_entities: List[SPOKEEntity] = Field(
        default_factory=list,
        description="Successfully mapped entities"
    )
    unmapped_entities: List[str] = Field(
        default_factory=list,
        description="Entities that couldn't be mapped"
    )
    mapping_sources: Set[str] = Field(
        default_factory=set,
        description="Sources used for mapping"
    )
    
    @property
    def mapping_rate(self) -> float:
        """Calculate the mapping success rate."""
        total = len(self.mapped_entities) + len(self.unmapped_entities)
        return len(self.mapped_entities) / total if total > 0 else 0.0


class BaseSPOKEMapper(ABC):
    """Base class for mapping entities to SPOKE nodes."""
    
    def __init__(self, config: Optional[SPOKEConfig] = None) -> None:
        """Initialize the mapper.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or SPOKEConfig()
    
    @abstractmethod
    async def map_to_spoke(
        self,
        entities: List[str],
        entity_type: Optional[str] = None
    ) -> SPOKEMappingResult:
        """Map entities to SPOKE nodes.
        
        Args:
            entities: List of entity identifiers
            entity_type: Optional entity type hint
            
        Returns:
            Mapping results including mapped and unmapped entities
            
        Raises:
            SPOKEError: If mapping operation fails
        """
        pass

    @abstractmethod
    async def analyze_pathways(
        self,
        entities: List[SPOKEEntity]
    ) -> Dict[str, Any]:
        """Analyze pathways for mapped entities.
        
        Args:
            entities: List of SPOKE entities to analyze
            
        Returns:
            Dictionary containing pathway analysis results
            
        Raises:
            SPOKEError: If pathway analysis fails
        """
        pass


class BaseAQLGenerator(ABC):
    """Base class for generating SPOKE AQL queries."""
    
    def __init__(self, config: Optional[SPOKEConfig] = None) -> None:
        """Initialize the query generator.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or SPOKEConfig()
    
    @abstractmethod
    async def generate_query(
        self,
        entities: List[SPOKEEntity],
        query_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> AQLQuery:
        """Generate an AQL query for the given entities.
        
        Args:
            entities: List of SPOKE entities to query
            query_type: Type of query to generate
            parameters: Optional additional query parameters
            
        Returns:
            Generated AQL query
            
        Raises:
            ValueError: If query_type is invalid
            SPOKEError: If query generation fails
        """
        pass


class SPOKEError(Exception):
    """Base exception for SPOKE-related errors."""
    pass
