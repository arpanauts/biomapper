"""Base protocol and utilities for analyzing knowledge graph structures."""

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


class IdentifierConfidence(Enum):
    """Confidence level for identified ontology fields."""

    HIGH = "high"  # Very likely an ontology identifier (e.g., pattern match)
    MEDIUM = "medium"  # Possibly an ontology identifier (e.g., name suggests it)
    LOW = "low"  # Might be an ontology identifier (e.g., contains some pattern)


@dataclass
class NodeTypeMetadata:
    """Metadata about a node type in a knowledge graph."""

    name: str  # Name of the node type
    count: int = 0  # Approximate count of nodes
    properties: Dict[str, str] = field(default_factory=dict)  # Property name to type
    sample_values: Dict[str, List[Any]] = field(default_factory=dict)  # Sample values
    potential_identifiers: Dict[str, IdentifierConfidence] = field(
        default_factory=dict
    )  # Potential ontology IDs


@dataclass
class RelationshipMetadata:
    """Metadata about a relationship type in a knowledge graph."""

    name: str  # Name of the relationship type
    count: int = 0  # Approximate count of relationships
    source_node_types: Set[str] = field(default_factory=set)  # Source node types
    target_node_types: Set[str] = field(default_factory=set)  # Target node types
    properties: Dict[str, str] = field(default_factory=dict)  # Property name to type
    sample_sources: List[str] = field(default_factory=list)  # Sample source nodes
    sample_targets: List[str] = field(default_factory=list)  # Sample target nodes


@dataclass
class OntologyTypeMapping:
    """Mapping between graph schema and ontology types."""

    node_type: str  # Node type in the graph
    property_path: str  # Path to the property (e.g., 'properties.chebi')
    ontology_type: str  # Standard ontology type (e.g., 'chebi')
    confidence: float = 1.0  # Confidence in this mapping


@dataclass
class GraphSchemaMapping:
    """Schema mapping for a knowledge graph."""

    graph_name: str  # Name of the graph
    node_type_mappings: List[OntologyTypeMapping] = field(
        default_factory=list
    )  # Node mappings
    relationship_mappings: Dict[str, Dict[str, str]] = field(
        default_factory=dict
    )  # Relationship mappings


class KnowledgeGraphAnalyzer(abc.ABC):
    """Base analyzer protocol for knowledge graph introspection.

    This abstract base class defines the interface for all knowledge graph
    analyzers. Specific implementations should be created for different
    graph database technologies.
    """

    @abc.abstractmethod
    async def discover_node_types(self) -> Dict[str, NodeTypeMetadata]:
        """Discover node types and their properties.

        Returns:
            Dictionary mapping node type names to their metadata
        """
        pass

    @abc.abstractmethod
    async def discover_relationship_types(self) -> Dict[str, RelationshipMetadata]:
        """Discover relationship types between nodes.

        Returns:
            Dictionary mapping relationship type names to their metadata
        """
        pass

    @abc.abstractmethod
    async def identify_ontology_fields(
        self,
    ) -> Dict[str, List[Tuple[str, IdentifierConfidence]]]:
        """Identify fields that likely contain ontology identifiers.

        Returns:
            Dictionary mapping node type names to lists of (field_name, confidence) tuples
        """
        pass

    @abc.abstractmethod
    async def sample_node_data(
        self, node_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get sample data for a specific node type.

        Args:
            node_type: The node type to sample
            limit: Maximum number of samples to return

        Returns:
            List of node data dictionaries
        """
        pass

    @abc.abstractmethod
    async def sample_relationship_data(
        self, relationship_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get sample data for a specific relationship type.

        Args:
            relationship_type: The relationship type to sample
            limit: Maximum number of samples to return

        Returns:
            List of relationship data dictionaries
        """
        pass

    async def generate_schema_mapping(self, graph_name: str) -> GraphSchemaMapping:
        """Generate schema mapping configuration.

        This method uses the results of the other discovery methods to generate
        a complete schema mapping configuration.

        Args:
            graph_name: Name of the graph for the configuration

        Returns:
            Schema mapping configuration
        """
        node_types = await self.discover_node_types()
        ontology_fields = await self.identify_ontology_fields()

        # Create schema mapping
        mapping = GraphSchemaMapping(graph_name=graph_name)

        # Process each node type
        for node_type, fields in ontology_fields.items():
            for field_name, confidence in fields:
                # Try to determine the ontology type from the field name
                ontology_type = self._infer_ontology_type(field_name)

                # Create mapping entry
                mapping.node_type_mappings.append(
                    OntologyTypeMapping(
                        node_type=node_type,
                        property_path=field_name,
                        ontology_type=ontology_type,
                        confidence=self._confidence_to_float(confidence),
                    )
                )

        return mapping

    def _infer_ontology_type(self, field_name: str) -> str:
        """Infer ontology type from field name.

        This is a simple heuristic method that can be overridden by specific implementations.

        Args:
            field_name: The field name to analyze

        Returns:
            Inferred ontology type
        """
        # Extract the last part of the field path
        parts = field_name.split(".")
        name = parts[-1].lower()

        # Common ontology types
        if "chebi" in name:
            return "chebi"
        elif "hmdb" in name:
            return "hmdb"
        elif "pubchem" in name:
            return "pubchem"
        elif "inchi" in name and "key" in name:
            return "inchikey"
        elif "inchi" in name:
            return "inchi"
        elif "smiles" in name:
            return "smiles"
        elif "kegg" in name:
            return "kegg"
        elif "uniprot" in name:
            return "uniprot"
        elif "ensembl" in name:
            return "ensembl"
        elif "symbol" in name and ("gene" in name or "protein" in name):
            return "gene_symbol"
        elif "mondo" in name:
            return "mondo"
        elif "doid" in name:
            return "doid"
        elif "mesh" in name:
            return "mesh"

        # If we can't determine, use the field name itself
        return name

    def _confidence_to_float(self, confidence: IdentifierConfidence) -> float:
        """Convert confidence enum to float value.

        Args:
            confidence: Confidence enum value

        Returns:
            Float representation (0.0 to 1.0)
        """
        if confidence == IdentifierConfidence.HIGH:
            return 1.0
        elif confidence == IdentifierConfidence.MEDIUM:
            return 0.7
        else:  # LOW
            return 0.4
