"""Tests for SPOKE mapper base classes."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock
from typing import Any, Dict, List, Optional

from biomapper.spoke.client import SPOKEDBClient
from biomapper.spoke.mapper import SPOKEMapper, SPOKEMappingResult, SPOKENodeType


class TestMapper(SPOKEMapper[Dict[str, Any]]):
    """Test implementation of SPOKEMapper."""

    async def standardize(self, input_value: str, **kwargs: Any) -> Dict[str, Any]:
        """Test standardization that just returns input as dict."""
        return {"value": input_value, "original": input_value}

    async def _get_spoke_query_params(
        self, std_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Test query params that just uses standardized value."""
        # Return multiple query attempts in priority order
        return [
            {"name": std_result["value"]},  # Exact name match
            {"synonym": std_result["value"]},  # Synonym match
        ]


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock SPOKE client."""
    client = AsyncMock(spec=SPOKEDBClient)
    # Ensure execute_query returns empty list by default
    client.execute_query.return_value = []
    return client


@pytest_asyncio.fixture
async def mapper(mock_client: AsyncMock) -> TestMapper:
    """Create a test mapper instance."""
    return TestMapper(mock_client, SPOKENodeType.COMPOUND)


def test_mapping_result_initialization() -> None:
    """Test SPOKEMappingResult initialization."""
    # Test with minimal args
    result = SPOKEMappingResult(input_value="test")
    assert result.input_value == "test"
    assert result.spoke_id is None
    assert result.node_type is None
    assert result.properties == {}
    assert result.metadata == {}
    assert result.relationships == {}
    assert result.confidence_score == 0.0

    # Test with all args
    result = SPOKEMappingResult(
        input_value="test",
        spoke_id="spoke/123",
        node_type=SPOKENodeType.COMPOUND,
        properties={"name": "test"},
        metadata={"source": "test"},
        relationships={"SIMILAR_TO": ["spoke/456"]},
        confidence_score=0.9,
    )
    assert result.input_value == "test"
    assert result.spoke_id == "spoke/123"
    assert result.node_type == SPOKENodeType.COMPOUND
    assert result.properties == {"name": "test"}
    assert result.metadata == {"source": "test"}
    assert result.relationships == {"SIMILAR_TO": ["spoke/456"]}
    assert result.confidence_score == 0.9


def test_mapping_result_post_init() -> None:
    """Test SPOKEMappingResult post initialization handling of None values."""
    # Test that None values are converted to empty dicts
    result = SPOKEMappingResult(
        input_value="test", properties=None, metadata=None, relationships=None
    )
    assert result.properties == {}
    assert result.metadata == {}
    assert result.relationships == {}


@pytest.mark.asyncio
async def test_map_entity_success(mapper: TestMapper, mock_client: AsyncMock) -> None:
    """Test successful entity mapping."""
    # Mock successful query result
    mock_client.execute_query.return_value = [
        {
            "id": "spoke/123",
            "type": "Compound",
            "properties": {"name": "test"},
            "relationships": [{"type": "SIMILAR_TO", "target": "spoke/456"}],
            "metadata": {"match_type": "direct"},
        }
    ]

    # Test value
    test_input = "test_compound"
    result = await mapper.map_entity(test_input)

    # Verify result
    assert result.input_value == test_input
    assert result.spoke_id == "spoke/123"
    assert result.node_type == SPOKENodeType.COMPOUND
    assert result.properties == {"name": "test"}
    assert result.metadata["match_type"] == "direct"
    assert "SIMILAR_TO" in result.relationships
    assert result.confidence_score > 0

    # Verify query was called
    mock_client.execute_query.assert_called_once()


@pytest.mark.asyncio
async def test_map_entity_not_found(mapper: TestMapper, mock_client: AsyncMock) -> None:
    """Test entity mapping when node not found."""
    # Mock empty query result
    mock_client.execute_query.return_value = []

    result = await mapper.map_entity("test")
    assert result.input_value == "test"
    assert result.spoke_id is None
    assert result.node_type is None
    assert "failed_attempts" in result.metadata
    assert len(result.metadata["failed_attempts"]) == 2  # Both query attempts failed
    assert result.confidence_score == 0


@pytest.mark.asyncio
async def test_map_entity_error(mapper: TestMapper, mock_client: AsyncMock) -> None:
    """Test entity mapping with query error."""
    # Mock query error
    mock_client.execute_query.side_effect = Exception("Test error")

    result = await mapper.map_entity("test")
    assert result.input_value == "test"
    assert result.spoke_id is None
    assert result.node_type is None
    assert "error" in result.metadata
    assert "Test error" in result.metadata["error"]
    assert result.confidence_score == 0


@pytest.mark.asyncio
async def test_map_batch(mapper: TestMapper, mock_client: AsyncMock) -> None:
    """Test batch mapping of multiple entities."""

    # Mock different responses for different inputs
    async def mock_execute_query(
        query: str, bind_vars: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if "test1" in str(bind_vars):
            return [
                {
                    "id": "spoke/1",
                    "type": "Compound",
                    "properties": {"name": "test1"},
                    "relationships": [],
                    "metadata": {"match_type": "direct"},
                }
            ]
        elif "test2" in str(bind_vars):
            return []  # Not found
        else:
            raise Exception("Test error")  # Error for test3

    mock_client.execute_query.side_effect = mock_execute_query

    # Map multiple entities
    results = await mapper.map_batch(["test1", "test2", "test3"])

    # Verify results
    assert len(results) == 3

    # First entity found
    assert results[0].spoke_id == "spoke/1"
    assert results[0].node_type == SPOKENodeType.COMPOUND

    # Second entity not found
    assert results[1].spoke_id is None
    assert "failed_attempts" in results[1].metadata

    # Third entity errored
    assert results[2].spoke_id is None
    assert "error" in results[2].metadata


@pytest.mark.asyncio
async def test_find_spoke_node_query(
    mapper: TestMapper, mock_client: AsyncMock
) -> None:
    """Test SPOKE node query construction."""
    # Set up test parameters
    query_params = {"name": "test", "id": "123"}
    node_type = SPOKENodeType.COMPOUND

    # Call method
    await mapper._find_spoke_node(query_params, node_type)

    # Verify query structure
    mock_client.execute_query.assert_called_once()
    call_kwargs = mock_client.execute_query.call_args.kwargs

    # Check query includes key elements
    query = call_kwargs["query"]
    assert "FOR node in Compound" in query
    assert "FILTER" in query
    assert "OUTBOUND node._id GRAPH 'spoke'" in query

    # Check bind vars
    bind_vars = call_kwargs["bind_vars"]
    assert bind_vars == {"params": query_params}


@pytest.mark.asyncio
async def test_find_spoke_node_success(
    mapper: TestMapper, mock_client: AsyncMock
) -> None:
    """Test successful SPOKE node finding."""
    # Mock successful response
    mock_client.execute_query.return_value = [
        {
            "id": "spoke/123",
            "type": "Compound",
            "properties": {"name": "test"},
            "relationships": [{"type": "SIMILAR_TO", "target": "spoke/456"}],
            "metadata": {"match_type": "direct"},
        }
    ]

    result = await mapper._find_spoke_node({"name": "test"}, SPOKENodeType.COMPOUND)

    assert result is not None
    assert result.spoke_id == "spoke/123"
    assert result.node_type == SPOKENodeType.COMPOUND
    assert result.properties == {"name": "test"}
    assert "SIMILAR_TO" in result.relationships


@pytest.mark.asyncio
async def test_find_spoke_node_with_relationships(
    mapper: TestMapper, mock_client: AsyncMock
) -> None:
    """Test SPOKE node finding with relationship processing."""
    # Mock response with multiple relationships
    mock_client.execute_query.return_value = [
        {
            "id": "spoke/123",
            "type": "Compound",
            "properties": {"name": "test"},
            "relationships": [
                {"type": "SIMILAR_TO", "target": "spoke/456"},
                {"type": "SIMILAR_TO", "target": "spoke/789"},
                {"type": "PART_OF", "target": "spoke/999"},
            ],
            "metadata": {"match_type": "direct"},
        }
    ]

    result = await mapper._find_spoke_node({"name": "test"}, SPOKENodeType.COMPOUND)

    assert result is not None
    # Check relationship grouping
    assert len(result.relationships["SIMILAR_TO"]) == 2
    assert len(result.relationships["PART_OF"]) == 1
    assert "spoke/456" in result.relationships["SIMILAR_TO"]
    assert "spoke/789" in result.relationships["SIMILAR_TO"]
    assert "spoke/999" in result.relationships["PART_OF"]
