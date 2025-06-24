"""Integration tests for ArangoStore."""

import pytest
from unittest.mock import MagicMock, patch
from biomapper.mapping.arango.arango_store import ArangoStore
from biomapper.mapping.arango.base_arango import ArangoQuery


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
    with patch('biomapper.mapping.arango.arango_store.Connection') as mock_conn:
        # Set up mock connection
        mock_db = MagicMock()
        mock_conn.return_value.__getitem__.return_value = mock_db
        mock_conn.return_value.hasDatabase.return_value = True
        mock_db.hasCollection.return_value = True
        
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
    with patch('biomapper.mapping.arango.arango_store.Connection') as mock_conn:
        # Set up mock connection
        mock_db = MagicMock()
        mock_conn.return_value.__getitem__.return_value = mock_db
        mock_conn.return_value.hasDatabase.return_value = True
        mock_db.hasCollection.return_value = True
        
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
    mock_doc.get.side_effect = lambda k, default=None: {
        "name": "Test Compound"
    }.get(k, default)
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
    mock_nodes.__getitem__.side_effect = DocumentNotFoundError("Document not found")
    
    node = await arango.get_node("nonexistent_id")
    assert node is None


@pytest.mark.asyncio
async def test_get_node_by_property(arango: ArangoStore):
    """Test getting nodes by property."""
    # Mock the AQL query execution
    mock_cursor = MagicMock()
    
    # Test with existing property - cursor should return a dict, not a mock
    mock_doc_dict = {
        "_key": "compound_1",
        "type": "Compound", 
        "name": "Test Compound",
        "hmdb_id": "HMDB0000122"
    }
    mock_cursor.__getitem__.return_value = mock_doc_dict
    mock_cursor.__bool__.return_value = True  # cursor evaluates to True
    arango.db.AQLQuery.return_value = mock_cursor
    
    node = await arango.get_node_by_property("Compound", "hmdb_id", "HMDB0000122")
    assert node is not None
    assert node.type == "Compound"
    assert node.name == "Test Compound"
    
    # Test with nonexistent property - empty result
    mock_empty_cursor = MagicMock()
    mock_empty_cursor.__bool__.return_value = False  # cursor evaluates to False for empty result
    arango.db.AQLQuery.return_value = mock_empty_cursor
    node = await arango.get_node_by_property("Compound", "hmdb_id", "nonexistent")
    assert node is None


@pytest.mark.asyncio
async def test_get_neighbors(arango: ArangoStore):
    """Test getting node neighbors."""
    # Mock the AQL query execution for neighbors
    mock_cursor = MagicMock()
    
    # Mock neighbor query result
    mock_result = {
        "edge": {
            "_from": "Nodes/test_node_id",
            "_to": "Nodes/neighbor_id",
            "type": "INTERACTS_WITH",
            "_key": "edge_1",
            "_id": "Edges/edge_1",
            "_rev": "123"
        },
        "neighbor": {
            "_key": "neighbor_id",
            "type": "Protein",
            "name": "Test Protein",
            "_id": "Nodes/neighbor_id",
            "_rev": "456"
        }
    }
    
    mock_cursor.__iter__.return_value = iter([mock_result])
    arango.db.AQLQuery.return_value = mock_cursor
    
    # Get all neighbors
    neighbors = await arango.get_neighbors("test_node_id")
    assert len(neighbors) > 0
    edge, node = neighbors[0]
    assert edge.type == "INTERACTS_WITH"
    assert node.type == "Protein"

    # Filter by edge type
    mock_cursor.__iter__.return_value = iter([mock_result])  # Reset the iterator
    neighbors = await arango.get_neighbors(
        "test_node_id", edge_types=["INTERACTS_WITH"]
    )
    assert len(neighbors) > 0

    # Filter by node type
    mock_cursor.__iter__.return_value = iter([mock_result])  # Reset the iterator
    neighbors = await arango.get_neighbors(
        "test_node_id", node_types=["Protein"]
    )
    assert len(neighbors) > 0


@pytest.mark.asyncio
async def test_find_paths(arango: ArangoStore):
    """Test finding paths between nodes."""
    # Mock the AQL query execution for paths
    mock_cursor = MagicMock()
    
    # Mock path query result
    mock_path_result = {
        "vertices": [
            {
                "_key": "compound_1",
                "type": "Compound",
                "name": "Test Compound",
                "_id": "Nodes/compound_1",
                "_rev": "123"
            },
            {
                "_key": "protein_1", 
                "type": "Protein",
                "name": "Test Protein",
                "_id": "Nodes/protein_1",
                "_rev": "456"
            }
        ],
        "edges": [
            {
                "_from": "Nodes/compound_1",
                "_to": "Nodes/protein_1",
                "type": "BINDS_TO",
                "_key": "edge_1",
                "_id": "Edges/edge_1",
                "_rev": "789"
            }
        ]
    }
    
    mock_cursor.__iter__.return_value = iter([mock_path_result])
    arango.db.AQLQuery.return_value = mock_cursor
    
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
    # Mock node types query
    mock_node_cursor = MagicMock()
    mock_node_cursor.__getitem__.return_value = ["Compound", "Protein", "Disease"]
    arango.db.AQLQuery.return_value = mock_node_cursor
    
    node_types = await arango.get_node_types()
    assert "Compound" in node_types
    assert "Protein" in node_types

    # Mock edge types query
    mock_edge_cursor = MagicMock()
    mock_edge_cursor.__getitem__.return_value = ["INTERACTS_WITH", "BINDS_TO", "CAUSES"]
    arango.db.AQLQuery.return_value = mock_edge_cursor
    
    edge_types = await arango.get_edge_types()
    assert len(edge_types) > 0  # At least one edge type should exist
