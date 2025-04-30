"""Tests for SPOKE database client."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
import aiohttp
from typing import AsyncGenerator

from biomapper.spoke.client import SPOKEDBClient, SPOKEConfig, SPOKEError


@pytest.fixture
def config() -> SPOKEConfig:
    """Create a test configuration."""
    return SPOKEConfig(
        host="test.spoke.db",
        port=8529,
        username="test",
        password="test",
        database="test_db",
        use_ssl=True,
        timeout=30,
    )


@pytest.fixture
def mock_response() -> AsyncMock:
    """Create a mock response."""
    response = AsyncMock()
    response.status = 200
    response.json.return_value = {"result": [{"test": "data"}]}
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_session(mock_response: AsyncMock) -> AsyncMock:
    """Create a mock aiohttp session."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    # This mock is used in `async with session.post(...)`
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = mock_response
    session.post.return_value = async_cm
    return session


@pytest_asyncio.fixture
async def client_with_session(
    config: SPOKEConfig, mock_session: AsyncMock
) -> AsyncGenerator[SPOKEDBClient, None]:
    """Create a test client with pre-configured session."""
    client = SPOKEDBClient(config)
    client._session = mock_session  # Bypass connect() entirely
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_initialization(config: SPOKEConfig) -> None:
    """Test client initialization."""
    client = SPOKEDBClient(config)
    assert client.base_url == f"https://{config.host}:{config.port}"


@pytest.mark.asyncio
async def test_base_url(config: SPOKEConfig) -> None:
    """Test base URL construction."""
    config.use_ssl = False
    client = SPOKEDBClient(config)
    assert client.base_url == f"http://{config.host}:{config.port}"


@pytest.mark.asyncio
async def test_connect_success(config: SPOKEConfig, mock_session: AsyncMock) -> None:
    """Test successful connection."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = SPOKEDBClient(config)
        await client.connect()
        assert client._session is mock_session


@pytest.mark.asyncio
async def test_connect_failure(config: SPOKEConfig, mock_session: AsyncMock) -> None:
    """Test connection failure."""
    mock_session.post.side_effect = aiohttp.ClientError("boom")
    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = SPOKEDBClient(config)
        with pytest.raises(SPOKEError, match="Failed to connect"):
            await client.connect()


@pytest.mark.asyncio
async def test_disconnect(config: SPOKEConfig, mock_session: AsyncMock) -> None:
    """Test disconnection."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = SPOKEDBClient(config)
        await client.connect()
        await client.disconnect()
        assert client._session is None
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_query_success(client_with_session: SPOKEDBClient) -> None:
    """Test successful query execution."""
    result = await client_with_session.execute_query("RETURN 1")
    assert result == [{"test": "data"}]


@pytest.mark.asyncio
async def test_execute_query_with_bind_vars(client_with_session: SPOKEDBClient) -> None:
    """Test query execution with bind variables."""
    result = await client_with_session.execute_query(
        "FOR doc IN test FILTER doc.id == @id RETURN doc",
        {"id": "test_id"},
    )
    assert result == [{"test": "data"}]


@pytest.mark.asyncio
async def test_execute_query_failure(
    client_with_session: SPOKEDBClient, mock_session: AsyncMock
) -> None:
    """Test query execution failure."""
    mock_session.post.side_effect = aiohttp.ClientError("boom")
    with pytest.raises(SPOKEError, match="Query execution failed"):
        await client_with_session.execute_query("RETURN 1")


@pytest.mark.asyncio
async def test_get_node_by_id(
    client_with_session: SPOKEDBClient, mock_session: AsyncMock
) -> None:
    """Test fetching node by ID."""
    expected_result = {"_id": "test/123", "name": "test"}
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": [expected_result]})
    mock_response.raise_for_status = Mock()

    mock_session.post.return_value = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client_with_session.get_node_by_id("test/123", "test")
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_nodes_by_property(
    client_with_session: SPOKEDBClient, mock_session: AsyncMock
) -> None:
    """Test fetching nodes by property."""
    expected_results = [
        {"_id": "test/1", "name": "test1"},
        {"_id": "test/2", "name": "test2"},
    ]
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": expected_results})
    mock_response.raise_for_status = Mock()

    mock_session.post.return_value = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    results = await client_with_session.get_nodes_by_property(
        "test", "name", "test", limit=2
    )
    assert results == expected_results


@pytest.mark.asyncio
async def test_context_manager(config: SPOKEConfig, mock_session: AsyncMock) -> None:
    """Test client as context manager."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        async with SPOKEDBClient(config) as client:
            assert client._session is not None
            result = await client.execute_query("RETURN 1")
            assert result == [{"test": "data"}]
        # On exit
        assert client._session is None
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_query_success(
    client_with_session: SPOKEDBClient,
    mock_session: AsyncMock,
    mock_response: AsyncMock,
) -> None:
    """Test successful query execution."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await client_with_session.execute_query("RETURN 1")
        assert result == [{"test": "data"}]


@pytest.mark.asyncio
async def test_execute_query_with_bind_vars(
    client_with_session: SPOKEDBClient, mock_session: AsyncMock
) -> None:
    """Test query execution with bind variables."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        await client_with_session.execute_query(
            "FOR doc IN test FILTER doc.id == @id RETURN doc",
            {"id": "test_id"},
        )

        # Verify bind vars were passed correctly
        call_kwargs = mock_session.post.call_args[1]
        assert "json" in call_kwargs
        assert "bindVars" in call_kwargs["json"]
        assert call_kwargs["json"]["bindVars"] == {"id": "test_id"}


@pytest.mark.asyncio
async def test_execute_query_failure(
    client_with_session: SPOKEDBClient, mock_session: AsyncMock
) -> None:
    """Test query execution failure."""
    mock_session.post.side_effect = aiohttp.ClientError("boom")
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(SPOKEError, match="Query execution failed"):
            await client_with_session.execute_query("RETURN 1")
