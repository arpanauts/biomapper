"""Tests for ArangoDB base classes."""

import pytest
from typing import Any, Dict, List, Optional, Set, Tuple

from biomapper.mapping.arango.base_arango import (
    BaseArango,
    ArangoNode,
    ArangoEdge,
    ArangoQuery,
    ArangoResult,
)


class MockArango(BaseArango):
    """Mock implementation of BaseArango for testing."""

    def __init__(self) -> None:
        """Initialize mock data."""
        self.nodes: Dict[str, ArangoNode] = {
            "compound1": ArangoNode(
                id="compound1",
                type="Compound",
                name="Glucose",
                properties={"hmdb_id": "HMDB0000122"},
            ),
            "compound2": ArangoNode(
                id="compound2",
                type="Compound",
                name="ATP",
                properties={"hmdb_id": "HMDB0000538"},
            ),
            "protein1": ArangoNode(
                id="protein1",
                type="Protein",
                name="Hexokinase",
                properties={"uniprot_id": "P19367"},
            ),
        }

        self.edges: List[ArangoEdge] = [
            ArangoEdge(
                source_id="compound1",
                target_id="protein1",
                type="INTERACTS_WITH",
                properties={"score": 0.9},
            ),
            ArangoEdge(
                source_id="compound2",
                target_id="protein1",
                type="INTERACTS_WITH",
                properties={"score": 0.8},
            ),
        ]

        self.is_connected = False

    async def connect(self) -> None:
        """Mock connection."""
        self.is_connected = True

    async def close(self) -> None:
        """Mock close connection."""
        self.is_connected = False

    async def get_node(self, node_id: str) -> Optional[ArangoNode]:
        """Mock get node."""
        return self.nodes.get(node_id)

    async def get_node_by_property(
        self, node_type: str, property_name: str, property_value: Any
    ) -> Optional[ArangoNode]:
        """Mock get node by property."""
        for node in self.nodes.values():
            if (
                node.type == node_type
                and node.properties.get(property_name) == property_value
            ):
                return node
        return None

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None,
    ) -> List[Tuple[ArangoEdge, ArangoNode]]:
        """Mock get neighbors."""
        results = []
        for edge in self.edges:
            # Check if this edge connects to our node
            if edge.source_id == node_id:
                target_node = self.nodes.get(edge.target_id)
            elif edge.target_id == node_id:
                target_node = self.nodes.get(edge.source_id)
            else:
                continue

            # Apply filters
            if edge_types and edge.type not in edge_types:
                continue
            if node_types and target_node and target_node.type not in node_types:
                continue

            if target_node:
                results.append((edge, target_node))

        return results

    async def find_paths(
        self,
        query: ArangoQuery,
    ) -> ArangoResult:
        """Mock find paths."""
        # For testing, just return a simple path if it exists
        paths = []
        nodes = []
        edges = []

        # Find start and end nodes
        start_nodes = [
            n for n in self.nodes.values() if n.type == query.start_node_type
        ]
        end_nodes = [n for n in self.nodes.values() if n.type == query.end_node_type]

        # Look for direct connections
        for start_node in start_nodes:
            for end_node in end_nodes:
                for edge in self.edges:
                    if (
                        edge.source_id == start_node.id
                        and edge.target_id == end_node.id
                        or edge.target_id == start_node.id
                        and edge.source_id == end_node.id
                    ):
                        paths.append([start_node.id, end_node.id])
                        nodes.extend([start_node, end_node])
                        edges.append(edge)
                        break

        return ArangoResult(
            nodes=nodes,
            edges=edges,
            paths=paths,
        )

    async def get_node_types(self) -> Set[str]:
        """Mock get node types."""
        return {"Compound", "Protein"}

    async def get_edge_types(self) -> Set[str]:
        """Mock get edge types."""
        return {"INTERACTS_WITH"}


@pytest.fixture
async def mock_arango():
    """Fixture for MockArango instance."""
    arango = MockArango()
    await arango.connect()
    return arango


@pytest.mark.asyncio
async def test_connection():
    """Test connection management."""
    arango = MockArango()
    assert not arango.is_connected

    await arango.connect()
    assert arango.is_connected

    await arango.close()
    assert not arango.is_connected


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    async with MockArango() as arango:
        assert arango.is_connected
    assert not arango.is_connected


@pytest.mark.asyncio
async def test_get_node(mock_arango: MockArango):
    """Test getting nodes by ID."""
    arango = await mock_arango
    node = await arango.get_node("compound1")
    assert node is not None
    assert node.name == "Glucose"
    assert node.type == "Compound"

    node = await arango.get_node("nonexistent")
    assert node is None


@pytest.mark.asyncio
async def test_get_node_by_property(mock_arango: MockArango):
    """Test getting nodes by property."""
    arango = await mock_arango
    node = await arango.get_node_by_property("Compound", "hmdb_id", "HMDB0000122")
    assert node is not None
    assert node.name == "Glucose"

    node = await arango.get_node_by_property("Compound", "hmdb_id", "nonexistent")
    assert node is None


@pytest.mark.asyncio
async def test_get_neighbors(mock_arango: MockArango):
    """Test getting node neighbors."""
    arango = await mock_arango
    # Get all neighbors
    neighbors = await arango.get_neighbors("compound1")
    assert len(neighbors) == 1
    edge, node = neighbors[0]
    assert edge.type == "INTERACTS_WITH"
    assert node.type == "Protein"
    assert node.name == "Hexokinase"

    # Filter by edge type
    neighbors = await arango.get_neighbors("compound1", edge_types=["WRONG_TYPE"])
    assert len(neighbors) == 0

    # Filter by node type
    neighbors = await arango.get_neighbors("compound1", node_types=["Protein"])
    assert len(neighbors) == 1


@pytest.mark.asyncio
async def test_find_paths(mock_arango: MockArango):
    """Test finding paths between nodes."""
    arango = await mock_arango
    query = ArangoQuery(
        start_node_type="Compound", end_node_type="Protein", max_path_length=1
    )
    result = await arango.find_paths(query)

    assert len(result.paths) == 2  # Two compounds connect to protein
    assert len(result.nodes) == 4  # Two compounds and one protein
    assert len(result.edges) == 2  # Two interaction edges


@pytest.mark.asyncio
async def test_get_types(mock_arango: MockArango):
    """Test getting available node and edge types."""
    arango = await mock_arango
    node_types = await arango.get_node_types()
    assert node_types == {"Compound", "Protein"}

    edge_types = await arango.get_edge_types()
    assert edge_types == {"INTERACTS_WITH"}
