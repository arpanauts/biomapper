"""Integration tests for ArangoStore."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from biomapper.mapping.arango.arango_store import ArangoStore
from biomapper.mapping.arango.base_arango import ArangoQuery, ArangoNode, ArangoEdge


@pytest.fixture
async def arango():
    """Fixture for ArangoStore instance with mocked connection."""
    store = ArangoStore(
        username="root",
        password="ph",
        database="spoke_human",
        host="localhost",
        port=8529,
    )
    
    # Mock the connection and database
    with patch('biomapper.mapping.arango.arango_store.Connection') as mock_conn:
        mock_db = MagicMock()
        mock_conn.return_value.__getitem__.return_value = mock_db
        mock_conn.return_value.hasDatabase.return_value = True
        mock_db.hasCollection.return_value = True
        
        # Set up mock documents
        mock_doc = MagicMock()
        mock_doc.__getitem__.side_effect = lambda k: {
            "_key": "test_node_id",
            "type": "Compound",
            "name": "Test Compound",
            "hmdb_id": "HMDB0000122"
        }.get(k)
        mock_doc.items.return_value = [
            ("_key", "test_node_id"),
            ("type", "Compound"),
            ("name", "Test Compound"),
            ("hmdb_id", "HMDB0000122")
        ]
        
        mock_db.__getitem__.return_value.__getitem__.return_value = mock_doc
        
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
    # Mock the database's node collection
    mock_nodes = MagicMock()
    arango.db.__getitem__.return_value = mock_nodes
    
    # Test with existing node
    mock_doc = MagicMock()
    mock_doc.__getitem__.side_effect = lambda k: {
        "_key": "test_node_id",
        "type": "Compound",
        "name": "Test Compound"
    }.get(k)
    mock_doc.items.return_value = [
        ("_key", "test_node_id"),
        ("type", "Compound"),
        ("name", "Test Compound")
    ]
    mock_nodes.__getitem__.return_value = mock_doc
    
    node = await arango.get_node("test_node_id")
    assert node is not None
    assert node.type == "Compound"
    assert node.name == "Test Compound"
    
    # Test with nonexistent node - simulate DocumentNotFoundError
    from pyArango.theExceptions import DocumentNotFoundError
    mock_nodes.__getitem__.side_effect = DocumentNotFoundError
    
    node = await arango.get_node("nonexistent_id")
    assert node is None


@pytest.mark.asyncio
async def test_get_node_by_property(arango: ArangoStore):
    """Test getting nodes by property."""
    # Mock the AQL query execution
    mock_cursor = MagicMock()
    
    # Test with existing property
    mock_doc = MagicMock()
    mock_doc.__getitem__.side_effect = lambda k: {
        "_key": "compound_1",
        "type": "Compound",
        "name": "Test Compound",
        "hmdb_id": "HMDB0000122"
    }.get(k)
    mock_doc.items.return_value = [
        ("_key", "compound_1"),
        ("type", "Compound"),
        ("name", "Test Compound"),
        ("hmdb_id", "HMDB0000122")
    ]
    mock_cursor.__iter__.return_value = iter([mock_doc])
    arango.db.AQLQuery.return_value = mock_cursor
    
    node = await arango.get_node_by_property("Compound", "hmdb_id", "HMDB0000122")
    assert node is not None
    assert node.type == "Compound"
    assert node.name == "Test Compound"
    
    # Test with nonexistent property - empty result
    mock_cursor.__iter__.return_value = iter([])
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
