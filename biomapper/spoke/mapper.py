"""Base classes for mapping entities to SPOKE nodes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic

from .client import SPOKEDBClient


class SPOKENodeType(str, Enum):
    """SPOKE node types."""
    COMPOUND = "Compound"
    METABOLITE = "Metabolite"
    DRUG = "Drug"
    PROTEIN = "Protein"
    DISEASE = "Disease"
    PATHWAY = "Pathway"
    GENE = "Gene"


@dataclass
class SPOKEMappingResult:
    """Result of mapping an entity to a SPOKE node."""
    input_value: str
    spoke_id: Optional[str] = None
    node_type: Optional[SPOKENodeType] = None
    properties: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, List[str]]] = None
    confidence_score: float = 0.0

    def __post_init__(self) -> None:
        """Initialize default dictionaries."""
        if self.properties is None:
            self.properties = {}
        if self.metadata is None:
            self.metadata = {}
        if self.relationships is None:
            self.relationships = {}


T = TypeVar("T")


class SPOKEMapper(Generic[T], ABC):
    """Base class for mapping entities to SPOKE nodes."""

    def __init__(self, client: SPOKEDBClient, default_node_type: SPOKENodeType) -> None:
        """Initialize mapper with SPOKE client and default node type."""
        self.client = client
        self.default_node_type = default_node_type
        self._cache: Dict[str, SPOKEMappingResult] = {}

    @abstractmethod
    async def standardize(self, input_value: str, **kwargs: Any) -> T:
        """Standardize input value before SPOKE mapping."""
        pass

    @abstractmethod
    async def _get_spoke_query_params(self, std_result: T) -> List[Dict[str, Any]]:
        """Get SPOKE query parameters from standardized result."""
        pass

    async def map_entity(
        self,
        input_value: str,
        node_type: Optional[SPOKENodeType] = None,
        **kwargs: Any
    ) -> SPOKEMappingResult:
        """Map an entity to its SPOKE representation."""
        try:
            # First standardize the input
            std_result = await self.standardize(input_value, **kwargs)

            # Get query parameters
            query_params_list = await self._get_spoke_query_params(std_result)

            # Try each set of parameters in priority order
            failed_attempts = []
            for params in query_params_list:
                found = await self._find_spoke_node(
                    params,
                    node_type or self.default_node_type,
                    original_input=input_value,
                )
                if found:
                    return found
                failed_attempts.append(str(params))

            # If no mapping was found
            return SPOKEMappingResult(
                input_value=input_value,
                metadata={"failed_attempts": failed_attempts},
                confidence_score=0.0,
            )

        except Exception as e:
            # If there's any error in the entire mapping flow
            return SPOKEMappingResult(
                input_value=input_value,
                metadata={"error": str(e)},
                confidence_score=0.0,
            )

    async def _find_spoke_node(
        self,
        query_params: Dict[str, Any],
        node_type: SPOKENodeType,
        original_input: str = "",  # Default value to maintain compatibility with tests
    ) -> Optional[SPOKEMappingResult]:
        """Find a SPOKE node using the provided parameters."""
        # Use node_type.value to get the actual collection name
        collection_name = node_type.value if isinstance(node_type, SPOKENodeType) else str(node_type)
        
        query = f"""
        FOR node in {collection_name}
            FILTER {self._build_filter_conditions(query_params)}
            LET rels = (
                FOR rel in OUTBOUND node._id GRAPH 'spoke'
                RETURN {{
                    type: rel._type,
                    target: rel._to
                }}
            )
            RETURN {{
                id: node._id,
                type: node._type,
                properties: node,
                relationships: rels,
                metadata: {{
                    match_type: 'direct',
                    query_params: @params
                }}
            }}
        """

        try:
            # Execute query with keyword args for better test inspection
            result = await self.client.execute_query(
                query=query,
                bind_vars={"params": query_params}
            )
        except Exception as e:
            # Re-raise so map_entity can catch and store error
            raise e

        if result and isinstance(result, list) and len(result) > 0:
            # Take the first matched node
            node_data = result[0]

            # Convert relationships list to dictionary by type
            relationship_dict: Dict[str, List[str]] = {}
            for rel in node_data.get("relationships", []):
                rel_type = rel.get("type")
                rel_target = rel.get("target")
                if rel_type and rel_target:
                    if rel_type not in relationship_dict:
                        relationship_dict[rel_type] = []
                    relationship_dict[rel_type].append(rel_target)

            # Use original_input if provided, otherwise fallback to str(query_params)
            input_val = original_input if original_input else str(query_params)

            return SPOKEMappingResult(
                input_value=input_val,
                spoke_id=node_data["id"],
                node_type=node_data["type"],
                properties=node_data["properties"],
                relationships=relationship_dict,
                metadata=node_data["metadata"],
                confidence_score=self._calculate_confidence(node_data),
            )

        return None

    def _build_filter_conditions(self, params: Dict[str, Any]) -> str:
        """Build ArangoDB filter conditions from parameters."""
        conditions = []
        for key, value in params.items():
            conditions.append(f"node.{key} == {repr(value)}")
        return " OR ".join(conditions) if conditions else "true"

    def _calculate_confidence(self, node_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the mapping."""
        base_score = 0.8
        metadata = node_data.get("metadata", {})
        if metadata.get("match_type") == "direct":
            base_score += 0.1

        # Add relationship score (0.01 per relationship, capped at 0.1)
        relationships = node_data.get("relationships", [])
        rel_score = min(0.1, len(relationships) * 0.01)
        
        return min(1.0, base_score + rel_score)

    async def map_batch(
        self,
        input_values: List[str],
        node_type: Optional[SPOKENodeType] = None,
        **kwargs: Any
    ) -> List[SPOKEMappingResult]:
        """Map a batch of entities to SPOKE nodes."""
        results = []
        for value in input_values:
            result = await self.map_entity(value, node_type, **kwargs)
            results.append(result)
        return results
