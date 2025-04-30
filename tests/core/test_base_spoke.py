"""Tests for SPOKE base classes."""
import pytest
from pydantic import ValidationError
from typing import Dict, Any, List

from biomapper.core.base_spoke import (
    SPOKEConfig,
    SPOKEEntity,
    SPOKERelation,
    AQLQuery,
    SPOKEMappingResult,
    BaseSPOKEMapper,
    SPOKEError,
)


class MockSPOKEMapper(BaseSPOKEMapper):
    """Test implementation of BaseSPOKEMapper."""

    async def map_to_spoke(
        self, entities: List[str], entity_type: str = None
    ) -> SPOKEMappingResult:
        mapped = [
            SPOKEEntity(
                input_id=str(entity),
                spoke_id=f"SPOKE:{entity}",
                node_type="Compound",
                node_label=f"Test {entity}",
                properties={},
                confidence=1.0,
            )
            for entity in entities[:2]  # Map first 2 entities
        ]
        return SPOKEMappingResult(
            mapped_entities=mapped,
            unmapped_entities=entities[2:],
            mapping_sources={"test"},
        )

    async def analyze_pathways(self, entities: List[SPOKEEntity]) -> Dict[str, Any]:
        return {
            "pathways": ["Test Pathway"],
            "enrichment_scores": {"Test Pathway": 0.8},
        }


@pytest.fixture
def spoke_config() -> SPOKEConfig:
    """Fixture for test SPOKE configuration."""
    return SPOKEConfig(
        base_url="https://test.spoke.db", timeout=30, max_retries=3, backoff_factor=0.5
    )


@pytest.fixture
def spoke_entity_data() -> Dict[str, Any]:
    """Fixture for valid SPOKE entity data."""
    return {
        "input_id": "TEST:123",
        "spoke_id": "SPOKE:456",
        "node_type": "Compound",
        "node_label": "Test Compound",
        "properties": {"formula": "C6H12O6"},
        "confidence": 0.95,
        "source": "direct",
    }


@pytest.fixture
def spoke_relation_data() -> Dict[str, Any]:
    """Fixture for valid SPOKE relation data."""
    return {
        "source_id": "SPOKE:123",
        "target_id": "SPOKE:456",
        "relation_type": "PARTICIPATES_IN",
        "properties": {"score": 0.8},
        "confidence": 0.9,
    }


@pytest.fixture
def aql_query_data() -> Dict[str, Any]:
    """Fixture for valid AQL query data."""
    return {
        "query_text": "FOR c IN Compound RETURN c",
        "parameters": {"limit": 10},
        "expected_node_types": ["Compound"],
        "metadata": {"purpose": "test"},
    }


class TestSPOKEConfig:
    """Tests for SPOKEConfig."""

    def test_valid_config(self, spoke_config):
        """Test valid configuration creation."""
        assert spoke_config.base_url == "https://test.spoke.db"
        assert spoke_config.timeout == 30
        assert spoke_config.max_retries == 3
        assert spoke_config.backoff_factor == 0.5

    def test_invalid_timeout(self):
        """Test validation of timeout value."""
        with pytest.raises(ValidationError) as exc:
            SPOKEConfig(base_url="https://test.db", timeout=-1)
        assert "timeout" in str(exc.value)

    def test_invalid_retries(self):
        """Test validation of max_retries value."""
        with pytest.raises(ValidationError) as exc:
            SPOKEConfig(base_url="https://test.db", max_retries=-1)
        assert "max_retries" in str(exc.value)

    def test_config_immutable(self, spoke_config):
        """Test that config is immutable."""
        with pytest.raises(Exception):
            spoke_config.timeout = 60


class TestSPOKEEntity:
    """Tests for SPOKEEntity."""

    def test_valid_entity(self, spoke_entity_data):
        """Test valid entity creation."""
        entity = SPOKEEntity(**spoke_entity_data)
        assert entity.input_id == "TEST:123"
        assert entity.spoke_id == "SPOKE:456"
        assert entity.confidence == 0.95
        assert entity.source == "direct"

    def test_invalid_confidence(self, spoke_entity_data):
        """Test confidence score validation."""
        spoke_entity_data["confidence"] = 1.5
        with pytest.raises(ValidationError) as exc:
            SPOKEEntity(**spoke_entity_data)
        assert "confidence" in str(exc.value)

    def test_invalid_node_type(self, spoke_entity_data):
        """Test node type validation."""
        spoke_entity_data["node_type"] = "InvalidType"
        with pytest.raises(ValidationError) as exc:
            SPOKEEntity(**spoke_entity_data)
        assert "node_type" in str(exc.value)

    def test_default_values(self):
        """Test entity default values."""
        entity = SPOKEEntity(
            input_id="test", spoke_id="test", node_type="Compound", node_label="test"
        )
        assert entity.confidence == 1.0
        assert entity.properties == {}
        assert entity.source == "direct"


class TestSPOKERelation:
    """Tests for SPOKERelation."""

    def test_valid_relation(self, spoke_relation_data):
        """Test valid relation creation."""
        relation = SPOKERelation(**spoke_relation_data)
        assert relation.source_id == "SPOKE:123"
        assert relation.target_id == "SPOKE:456"
        assert relation.relation_type == "PARTICIPATES_IN"
        assert relation.confidence == 0.9

    def test_empty_properties(self, spoke_relation_data):
        """Test relation with empty properties."""
        spoke_relation_data["properties"] = {}
        relation = SPOKERelation(**spoke_relation_data)
        assert relation.properties == {}

    def test_default_confidence(self):
        """Test default confidence value."""
        relation = SPOKERelation(
            source_id="test", target_id="test", relation_type="test"
        )
        assert relation.confidence == 1.0


class TestAQLQuery:
    """Tests for AQLQuery."""

    def test_valid_query(self, aql_query_data):
        """Test valid query creation."""
        query = AQLQuery(**aql_query_data)
        assert query.query_text == "FOR c IN Compound RETURN c"
        assert query.parameters["limit"] == 10
        assert query.expected_node_types == ["Compound"]

    def test_empty_parameters(self):
        """Test query with empty parameters."""
        query = AQLQuery(query_text="FOR c IN Compound RETURN c")
        assert query.parameters == {}
        assert query.expected_node_types == []
        assert query.metadata == {}


class TestSPOKEMappingResult:
    """Tests for SPOKEMappingResult."""

    def test_valid_result(self, spoke_entity_data):
        """Test valid result creation."""
        entity = SPOKEEntity(**spoke_entity_data)
        result = SPOKEMappingResult(
            mapped_entities=[entity],
            unmapped_entities=["TEST:789"],
            mapping_sources={"direct", "inferred"},
        )
        assert len(result.mapped_entities) == 1
        assert len(result.unmapped_entities) == 1
        assert result.mapping_sources == {"direct", "inferred"}

    def test_mapping_rate(self):
        """Test mapping rate calculation."""
        result = SPOKEMappingResult(
            mapped_entities=[
                SPOKEEntity(
                    input_id="test1",
                    spoke_id="test1",
                    node_type="Compound",
                    node_label="test1",
                )
            ],
            unmapped_entities=["test2"],
            mapping_sources={"test"},
        )
        assert result.mapping_rate == 0.5

    def test_empty_result(self):
        """Test empty result."""
        result = SPOKEMappingResult()
        assert result.mapped_entities == []
        assert result.unmapped_entities == []
        assert result.mapping_sources == set()
        assert result.mapping_rate == 0.0


class TestBaseSPOKEMapper:
    """Tests for BaseSPOKEMapper."""

    @pytest.mark.asyncio
    async def test_mock_mapper(self):
        """Test mock implementation of BaseSPOKEMapper."""
        mapper = MockSPOKEMapper()
        entities = ["TEST1", "TEST2", "TEST3"]
        result = await mapper.map_to_spoke(entities)

        assert isinstance(result, SPOKEMappingResult)
        assert len(result.mapped_entities) == 2
        assert len(result.unmapped_entities) == 1
        assert all(isinstance(e, SPOKEEntity) for e in result.mapped_entities)
        assert result.mapping_sources == {"test"}

    @pytest.mark.asyncio
    async def test_pathway_analysis(self):
        """Test pathway analysis."""
        mapper = MockSPOKEMapper()
        entities = [
            SPOKEEntity(
                input_id="test",
                spoke_id="test",
                node_type="Compound",
                node_label="test",
            )
        ]
        result = await mapper.analyze_pathways(entities)

        assert "pathways" in result
        assert "enrichment_scores" in result
        assert result["pathways"] == ["Test Pathway"]


def test_spoke_error():
    """Test SPOKEError exception."""
    with pytest.raises(SPOKEError) as exc:
        raise SPOKEError("Test error")
    assert str(exc.value) == "Test error"
