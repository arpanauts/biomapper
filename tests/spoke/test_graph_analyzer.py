"""Tests for the ArangoDB graph analyzer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from biomapper.core.graph_analyzer import IdentifierConfidence, NodeTypeMetadata
from biomapper.spoke.graph_analyzer import ArangoDBGraphAnalyzer, SPOKEGraphAnalyzer
from biomapper.spoke.client import SPOKEConfig


@pytest.fixture
def mock_arango_client():
    """Mock ArangoClient."""
    with patch("biomapper.spoke.graph_analyzer.ArangoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.db.return_value = mock_db

        # Mock collections
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection

        # Mock AQL execution
        mock_cursor = MagicMock()
        mock_db.aql.execute.return_value = mock_cursor

        yield mock_db


@pytest.fixture
def mock_spoke_graph_analyzer():
    """Mock SPOKEGraphAnalyzer with test configuration."""
    config = SPOKEConfig(
        host="test_host",
        port=8529,
        username="test_user",
        password="test_password",
        database="test_db",
    )

    analyzer = SPOKEGraphAnalyzer(config=config, sample_size=2)

    # Mock connect to avoid actual connection
    analyzer.connect = AsyncMock()

    return analyzer


@pytest.mark.asyncio
async def test_discover_node_types_spoke_style(
    mock_arango_client, mock_spoke_graph_analyzer
):
    """Test discovering node types in a SPOKE-style database."""
    # Setup mock responses
    analyzer = mock_spoke_graph_analyzer
    mock_arango_client.collections.return_value = [
        {"name": "Nodes"},
        {"name": "Edges"},
    ]

    # Mock AQL execution for node types
    mock_arango_client.aql.execute.return_value.__iter__.return_value = [
        {"type": "Compound", "count": 100},
        {"type": "Gene", "count": 200},
    ]

    # Mock sample node data for each type
    compound_samples = [
        {
            "_id": "Nodes/123",
            "type": "Compound",
            "name": "Glucose",
            "properties": {
                "chebi": "CHEBI:17234",
                "hmdb": "HMDB0000122",
                "formula": "C6H12O6",
            },
        }
    ]

    gene_samples = [
        {
            "_id": "Nodes/456",
            "type": "Gene",
            "name": "BRCA1",
            "properties": {
                "ensembl": "ENSG00000012048",
                "symbol": "BRCA1",
                "description": "Breast cancer type 1",
            },
        }
    ]

    # Mock the sample_node_data method
    analyzer.sample_node_data = AsyncMock(
        side_effect=lambda node_type, limit=None: compound_samples
        if node_type == "Compound"
        else gene_samples
    )

    # Execute the method
    node_types = await analyzer.discover_node_types()

    # Verify results
    assert len(node_types) == 2
    assert "Compound" in node_types
    assert "Gene" in node_types

    # Check compound node type
    compound = node_types["Compound"]
    assert compound.name == "Compound"
    assert compound.count == 100
    assert "properties.chebi" in compound.properties
    assert "properties.hmdb" in compound.properties

    # Check gene node type
    gene = node_types["Gene"]
    assert gene.name == "Gene"
    assert gene.count == 200
    assert "properties.ensembl" in gene.properties
    assert "properties.symbol" in gene.properties


@pytest.mark.asyncio
async def test_discover_relationship_types(
    mock_arango_client, mock_spoke_graph_analyzer
):
    """Test discovering relationship types."""
    # Setup mock responses
    analyzer = mock_spoke_graph_analyzer
    mock_arango_client.collections.return_value = [
        {"name": "Nodes"},
        {"name": "Edges"},
    ]

    # Mock AQL execution for relationship types
    mock_arango_client.aql.execute.return_value.__iter__.side_effect = [
        # First call returns relationship types
        [
            {"label": "INTERACTS_WITH", "count": 150},
            {"label": "PARTICIPATES_IN", "count": 250},
        ],
        # Second call returns sample relationships for INTERACTS_WITH
        [
            {
                "_from": "Nodes/123",
                "_to": "Nodes/456",
                "label": "INTERACTS_WITH",
                "properties": {"score": 0.9},
            },
        ],
        # Third call returns sample relationships for PARTICIPATES_IN
        [
            {
                "_from": "Nodes/789",
                "_to": "Nodes/012",
                "label": "PARTICIPATES_IN",
                "properties": {"evidence": "experimental"},
            },
        ],
    ]

    # Mock the _get_node_type_for_id method
    analyzer._get_node_type_for_id = AsyncMock(
        side_effect=lambda node_id: "Compound"
        if node_id == "Nodes/123"
        else "Gene"
        if node_id == "Nodes/456"
        else "Protein"
        if node_id == "Nodes/789"
        else "Pathway"
    )

    # Execute the method
    relationship_types = await analyzer.discover_relationship_types()

    # Verify results
    assert len(relationship_types) == 2
    assert "INTERACTS_WITH" in relationship_types
    assert "PARTICIPATES_IN" in relationship_types

    # Check INTERACTS_WITH relationship
    interacts = relationship_types["INTERACTS_WITH"]
    assert interacts.name == "INTERACTS_WITH"
    assert interacts.count == 150
    assert "Compound" in interacts.source_node_types
    assert "Gene" in interacts.target_node_types
    assert "score" in interacts.properties

    # Check PARTICIPATES_IN relationship
    participates = relationship_types["PARTICIPATES_IN"]
    assert participates.name == "PARTICIPATES_IN"
    assert participates.count == 250
    assert "Protein" in participates.source_node_types
    assert "Pathway" in participates.target_node_types
    assert "evidence" in participates.properties


@pytest.mark.asyncio
async def test_identify_ontology_fields(mock_spoke_graph_analyzer):
    """Test identifying ontology fields."""
    # Setup mock responses
    analyzer = mock_spoke_graph_analyzer

    # Mock discover_node_types to return test data
    compound_metadata = NodeTypeMetadata(
        name="Compound",
        count=100,
        properties={
            "name": "str",
            "properties.chebi": "str",
            "properties.hmdb": "str",
            "properties.formula": "str",
            "identifier": "str",
        },
        sample_values={
            "name": ["Glucose", "Caffeine"],
            "properties.chebi": ["CHEBI:17234", "CHEBI:27732"],
            "properties.hmdb": ["HMDB0000122", "HMDB0001847"],
            "properties.formula": ["C6H12O6", "C8H10N4O2"],
            "identifier": ["C00031", "C07481"],
        },
    )

    gene_metadata = NodeTypeMetadata(
        name="Gene",
        count=200,
        properties={
            "name": "str",
            "properties.ensembl": "str",
            "properties.symbol": "str",
            "description": "str",
        },
        sample_values={
            "name": ["BRCA1", "TP53"],
            "properties.ensembl": ["ENSG00000012048", "ENSG00000141510"],
            "properties.symbol": ["BRCA1", "TP53"],
            "description": ["Breast cancer type 1", "Tumor protein 53"],
        },
    )

    analyzer.discover_node_types = AsyncMock(
        return_value={
            "Compound": compound_metadata,
            "Gene": gene_metadata,
        }
    )

    # Execute the method
    ontology_fields = await analyzer.identify_ontology_fields()

    # Verify results
    assert "Compound" in ontology_fields
    assert "Gene" in ontology_fields

    # Check compound ontology fields
    compound_fields = dict(ontology_fields["Compound"])
    assert "properties.chebi" in compound_fields
    assert "properties.hmdb" in compound_fields
    assert "identifier" in compound_fields

    # Check confidence levels
    assert compound_fields["properties.chebi"] == IdentifierConfidence.HIGH
    assert compound_fields["properties.hmdb"] == IdentifierConfidence.HIGH

    # Check gene ontology fields
    gene_fields = dict(ontology_fields["Gene"])
    assert "properties.ensembl" in gene_fields
    assert "properties.symbol" in gene_fields

    # Check confidence levels
    assert gene_fields["properties.ensembl"] == IdentifierConfidence.HIGH


@pytest.mark.asyncio
async def test_generate_schema_mapping(mock_spoke_graph_analyzer):
    """Test generating schema mapping configuration."""
    # Setup mock responses
    analyzer = mock_spoke_graph_analyzer

    # Mock discover_node_types and identify_ontology_fields
    analyzer.discover_node_types = AsyncMock(
        return_value={
            "Compound": NodeTypeMetadata(name="Compound"),
            "Gene": NodeTypeMetadata(name="Gene"),
        }
    )

    analyzer.identify_ontology_fields = AsyncMock(
        return_value={
            "Compound": [
                ("properties.chebi", IdentifierConfidence.HIGH),
                ("properties.hmdb", IdentifierConfidence.HIGH),
            ],
            "Gene": [
                ("properties.ensembl", IdentifierConfidence.HIGH),
                ("properties.symbol", IdentifierConfidence.MEDIUM),
            ],
        }
    )

    # Execute the method
    schema_mapping = await analyzer.generate_schema_mapping("test_graph")

    # Verify results
    assert schema_mapping.graph_name == "test_graph"
    assert len(schema_mapping.node_type_mappings) == 4

    # Check mappings
    mappings = {m.property_path: m for m in schema_mapping.node_type_mappings}

    assert "properties.chebi" in mappings
    assert mappings["properties.chebi"].node_type == "Compound"
    assert mappings["properties.chebi"].ontology_type == "chebi"
    assert mappings["properties.chebi"].confidence == 1.0

    assert "properties.hmdb" in mappings
    assert mappings["properties.hmdb"].node_type == "Compound"
    assert mappings["properties.hmdb"].ontology_type == "hmdb"

    assert "properties.ensembl" in mappings
    assert mappings["properties.ensembl"].node_type == "Gene"
    assert mappings["properties.ensembl"].ontology_type == "ensembl"

    assert "properties.symbol" in mappings
    assert mappings["properties.symbol"].node_type == "Gene"
    assert mappings["properties.symbol"].ontology_type == "symbol"
    assert mappings["properties.symbol"].confidence == 0.7


def test_spoke_graph_analyzer_init():
    """Test initializing SPOKEGraphAnalyzer with config."""
    config = SPOKEConfig(
        host="test_host",
        port=9999,
        username="test_user",
        password="test_password",
        database="test_db",
        use_ssl=True,
    )

    analyzer = SPOKEGraphAnalyzer(config=config, sample_size=10)

    assert analyzer.host == "test_host"
    assert analyzer.port == 9999
    assert analyzer.username == "test_user"
    assert analyzer.password == "test_password"
    assert analyzer.database == "test_db"
    assert analyzer.use_ssl is True
    assert analyzer.sample_size == 10
