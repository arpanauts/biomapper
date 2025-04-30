"""Integration tests for ArangoStore."""

import pytest
from biomapper.mapping.arango.arango_store import ArangoStore
from biomapper.mapping.arango.base_arango import ArangoQuery


@pytest.fixture
async def arango():
    """Fixture for ArangoStore instance."""
    store = ArangoStore(
        username="root",
        password="ph",
        database="spoke_human",
        host="localhost",
        port=8529,
    )
    await store.connect()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_connection():
    """Test connection management."""
    store = ArangoStore()
    assert not store.is_connected

    await store.connect()
    assert store.is_connected
    assert store.db is not None

    await store.close()
    assert not store.is_connected
    assert store.db is None


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    async with ArangoStore() as store:
        assert store.is_connected
        assert store.db is not None
    assert not store.is_connected
    assert store.db is None


@pytest.mark.asyncio
async def test_get_node(arango: ArangoStore):
    """Test getting nodes by ID."""
    # Test with a known node ID
    node = await arango.get_node("your_test_node_id")
    assert node is not None
    assert node.type == "expected_type"
    assert node.name == "expected_name"

    # Test with nonexistent node
    node = await arango.get_node("nonexistent_id")
    assert node is None


@pytest.mark.asyncio
async def test_get_node_by_property(arango: ArangoStore):
    """Test getting nodes by property."""
    # Test with a known property
    node = await arango.get_node_by_property("Compound", "hmdb_id", "your_test_hmdb_id")
    assert node is not None
    assert node.type == "Compound"
    assert node.name == "expected_name"

    # Test with nonexistent property
    node = await arango.get_node_by_property("Compound", "hmdb_id", "nonexistent")
    assert node is None


@pytest.mark.asyncio
async def test_get_neighbors(arango: ArangoStore):
    """Test getting node neighbors."""
    # Get all neighbors
    neighbors = await arango.get_neighbors("your_test_node_id")
    assert len(neighbors) > 0
    edge, node = neighbors[0]
    assert edge.type == "expected_edge_type"
    assert node.type == "expected_node_type"

    # Filter by edge type
    neighbors = await arango.get_neighbors(
        "your_test_node_id", edge_types=["expected_edge_type"]
    )
    assert len(neighbors) > 0

    # Filter by node type
    neighbors = await arango.get_neighbors(
        "your_test_node_id", node_types=["expected_node_type"]
    )
    assert len(neighbors) > 0


@pytest.mark.asyncio
async def test_find_paths(arango: ArangoStore):
    """Test finding paths between nodes."""
    query = ArangoQuery(
        start_node_type="Compound", end_node_type="Protein", max_path_length=2
    )
    result = await arango.find_paths(query)

    assert len(result.paths) > 0
    assert len(result.nodes) > 0
    assert len(result.edges) > 0


@pytest.mark.asyncio
async def test_get_types(arango: ArangoStore):
    """Test getting available node and edge types."""
    node_types = await arango.get_node_types()
    assert "Compound" in node_types
    assert "Protein" in node_types

    edge_types = await arango.get_edge_types()
    assert len(edge_types) > 0  # At least one edge type should exist
