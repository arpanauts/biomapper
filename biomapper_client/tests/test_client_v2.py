"""Tests for enhanced Biomapper client."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from biomapper_client.client_v2 import BiomapperClient
from biomapper_client.exceptions import (
    ApiError,
    JobNotFoundError,
    NetworkError,
    StrategyNotFoundError,
    TimeoutError,
)
from biomapper_client.models import (
    ExecutionContext,
    ExecutionOptions,
    Job,
    JobStatus,
    JobStatusEnum,
    ProgressEvent,
    ProgressEventType,
    StrategyResult,
)


@pytest.fixture
def client():
    """Create a test client."""
    return BiomapperClient(base_url="http://test.example.com", api_key="test-key")


@pytest.fixture
def mock_response():
    """Create a mock response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"status": "success"}
    response.raise_for_status = Mock()
    return response


class TestBiomapperClient:
    """Test BiomapperClient class."""

    def test_init(self):
        """Test client initialization."""
        client = BiomapperClient(
            base_url="http://example.com",
            api_key="test-key",
            timeout=600,
            auto_retry=False,
        )
        assert client.base_url == "http://example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 600
        assert client.auto_retry is False

    def test_init_with_env_var(self):
        """Test client initialization with environment variable."""
        with patch.dict("os.environ", {"BIOMAPPER_API_KEY": "env-key"}):
            client = BiomapperClient()
            assert client.api_key == "env-key"

    @pytest.mark.asyncio
    async def test_context_manager_async(self, client):
        """Test async context manager."""
        async with client as c:
            assert c._client is not None
            assert isinstance(c._client, httpx.AsyncClient)
        assert client._client is None

    def test_context_manager_sync(self, client):
        """Test sync context manager."""
        with client as c:
            assert c._sync_client is not None
            assert isinstance(c._sync_client, httpx.Client)
        assert client._sync_client is None

    @pytest.mark.asyncio
    async def test_execute_strategy_with_name(self, client):
        """Test executing strategy by name."""
        # Mock _get_client to return a mock client directly
        with patch.object(client, "_get_client") as mock_get_client:
            # Create a mock client (not AsyncMock to avoid auto-async attributes)
            mock_client = Mock()
            
            # Create mock response with proper synchronous methods
            mock_response = Mock()
            # Make json() return the dict directly (not a Mock)
            mock_response.json = lambda: {
                "job_id": "job-123",
                "status": "running",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
            # Make raise_for_status() a no-op function
            mock_response.raise_for_status = lambda: None
            
            # Create an AsyncMock for post that returns the response
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.post = mock_post
            
            # Make _get_client return the mock client
            mock_get_client.return_value = mock_client

            job = await client.execute_strategy("test_strategy", parameters={"param": "value"})

            assert isinstance(job, Job)
            assert job.id == "job-123"
            assert job.status == JobStatusEnum.RUNNING
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_strategy_with_yaml_file(self, client, tmp_path):
        """Test executing strategy from YAML file."""
        # Create temporary YAML file
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text("name: test\nactions: []")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            mock_response = Mock()
            mock_response.json = lambda: {
                "job_id": "job-456",
                "status": "running",
            }
            mock_response.raise_for_status = lambda: None
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.post = mock_post

            job = await client.execute_strategy(yaml_file)

            assert job.id == "job-456"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_strategy_not_found(self, client):
        """Test executing non-existent strategy."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            error_response = httpx.Response(
                status_code=404,
                request=httpx.Request("POST", "http://test"),
            )
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Not found",
                request=error_response.request,
                response=error_response,
            )

            with pytest.raises(StrategyNotFoundError):
                await client.execute_strategy("nonexistent")

    @pytest.mark.asyncio
    async def test_wait_for_job_success(self, client):
        """Test waiting for successful job completion."""
        with patch.object(client, "get_job_status") as mock_get_status:
            with patch.object(client, "get_job_results") as mock_get_results:
                # First call: running, second call: completed
                mock_get_status.side_effect = [
                    JobStatus(
                        job_id="job-123",
                        status=JobStatusEnum.RUNNING,
                        progress=50.0,
                        updated_at="2024-01-01T00:00:00",
                    ),
                    JobStatus(
                        job_id="job-123",
                        status=JobStatusEnum.COMPLETED,
                        progress=100.0,
                        updated_at="2024-01-01T00:01:00",
                    ),
                ]

                mock_get_results.return_value = {"data": "result"}

                result = await client.wait_for_job("job-123", poll_interval=0.1)

                assert isinstance(result, StrategyResult)
                assert result.success is True
                assert result.job_id == "job-123"
                assert result.result_data == {"data": "result"}

    @pytest.mark.asyncio
    async def test_wait_for_job_failure(self, client):
        """Test waiting for failed job."""
        with patch.object(client, "get_job_status") as mock_get_status:
            mock_get_status.return_value = JobStatus(
                job_id="job-123",
                status=JobStatusEnum.FAILED,
                progress=0.0,
                message="Error occurred",
                updated_at="2024-01-01T00:00:00",
            )

            result = await client.wait_for_job("job-123", poll_interval=0.1)

            assert result.success is False
            assert result.error == "Error occurred"

    @pytest.mark.asyncio
    async def test_wait_for_job_timeout(self, client):
        """Test job timeout."""
        with patch.object(client, "get_job_status") as mock_get_status:
            mock_get_status.return_value = JobStatus(
                job_id="job-123",
                status=JobStatusEnum.RUNNING,
                progress=50.0,
                updated_at="2024-01-01T00:00:00",
            )

            with pytest.raises(TimeoutError):
                await client.wait_for_job("job-123", timeout=0.1, poll_interval=0.05)

    def test_run_sync(self, client):
        """Test synchronous run method."""
        with patch.object(client, "_async_run", new_callable=AsyncMock) as mock_async_run:
            mock_result = StrategyResult(
                success=True,
                job_id="job-123",
                execution_time_seconds=10.0,
            )
            mock_async_run.return_value = mock_result

            result = client.run("test_strategy", parameters={"param": "value"})

            assert result == mock_result
            mock_async_run.assert_called_once_with(
                "test_strategy",
                {"param": "value"},
                None,
                True,
                False,
            )

    def test_run_with_progress(self, client):
        """Test run with progress tracking."""
        with patch.object(client, "_async_run_with_progress", new_callable=AsyncMock) as mock_run:
            mock_result = StrategyResult(
                success=True,
                job_id="job-123",
                execution_time_seconds=10.0,
            )
            mock_run.return_value = mock_result

            callback = Mock()
            result = client.run_with_progress(
                "test_strategy",
                progress_callback=callback,
                use_tqdm=False,
            )

            assert result == mock_result
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_progress(self, client):
        """Test progress streaming."""
        # Make get_job_status an AsyncMock that returns values
        mock_get_status = AsyncMock()
        mock_get_status.side_effect = [
            JobStatus(
                job_id="job-123",
                status=JobStatusEnum.RUNNING,
                progress=25.0,
                message="Step 1",
                updated_at="2024-01-01T00:00:00",
            ),
            JobStatus(
                job_id="job-123",
                status=JobStatusEnum.RUNNING,
                progress=50.0,
                message="Step 2",
                updated_at="2024-01-01T00:00:01",
            ),
            JobStatus(
                job_id="job-123",
                status=JobStatusEnum.COMPLETED,
                progress=100.0,
                message="Done",
                updated_at="2024-01-01T00:00:02",
            ),
        ]
        
        with patch.object(client, "get_job_status", mock_get_status):
            events = []
            async for event in client.stream_progress("job-123"):
                events.append(event)

            assert len(events) == 3
            assert events[0].percentage == 25.0
            assert events[1].percentage == 50.0
            assert events[2].percentage == 100.0

    @pytest.mark.asyncio
    async def test_get_job_status(self, client):
        """Test getting job status."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            mock_response = Mock()
            mock_response.json = lambda: {
                "job_id": "job-123",
                "status": "running",
                "progress": 75.0,
                "updated_at": "2024-01-01T00:00:00",
            }
            mock_response.raise_for_status = lambda: None
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.get = mock_get

            status = await client.get_job_status("job-123")

            assert isinstance(status, JobStatus)
            assert status.job_id == "job-123"
            assert status.progress == 75.0

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            mock_response = Mock()
            mock_response.json = lambda: {"status": "healthy", "version": "1.0.0"}
            mock_response.raise_for_status = lambda: None
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.get = mock_get

            health = await client.health_check()

            assert health["status"] == "healthy"
            assert health["version"] == "1.0.0"

    def test_prepare_strategy_request_with_context(self, client):
        """Test preparing strategy request with ExecutionContext."""
        context = ExecutionContext()
        context.add_parameter("param1", "value1")
        context.add_file("input", "/path/to/file")
        context.enable_checkpoints()

        request = client._prepare_strategy_request(
            "test_strategy",
            parameters={"param2": "value2"},
            context=context,
        )

        assert request.strategy_name == "test_strategy"
        assert request.parameters["param1"] == "value1"
        assert request.parameters["param2"] == "value2"
        assert request.options.checkpoint_enabled is True
        assert request.context["files"]["input"] == "/path/to/file"

    def test_prepare_strategy_request_with_dict(self, client):
        """Test preparing strategy request with dict strategy."""
        strategy_dict = {
            "name": "custom",
            "actions": [],
        }

        request = client._prepare_strategy_request(
            strategy_dict,
            parameters={"param": "value"},
        )

        assert request.strategy_yaml == strategy_dict
        assert request.parameters["param"] == "value"

    def test_get_headers(self, client):
        """Test header generation."""
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"


class TestExecutionContext:
    """Test ExecutionContext helper class."""

    def test_add_parameter(self):
        """Test adding parameters."""
        context = ExecutionContext()
        context.add_parameter("key", "value")

        assert context.parameters["key"] == "value"

    def test_add_file(self):
        """Test adding files."""
        context = ExecutionContext()
        context.add_file("input", Path("/path/to/file"))

        assert context.files["input"] == "/path/to/file"

    def test_set_output_dir(self):
        """Test setting output directory."""
        context = ExecutionContext()
        context.set_output_dir("/output")

        assert context.options.output_dir == "/output"

    def test_enable_checkpoints(self):
        """Test enabling checkpoints."""
        context = ExecutionContext()
        context.enable_checkpoints()

        assert context.options.checkpoint_enabled is True

    def test_enable_debug(self):
        """Test enabling debug mode."""
        context = ExecutionContext()
        context.enable_debug()

        assert context.options.debug_mode is True

    def test_set_timeout(self):
        """Test setting timeout."""
        context = ExecutionContext()
        context.set_timeout(600)

        assert context.options.timeout_seconds == 600

    def test_to_request(self):
        """Test converting to request."""
        context = ExecutionContext()
        context.add_parameter("param", "value")
        context.add_file("input", "/file")

        request = context.to_request("test_strategy")

        assert request.strategy_name == "test_strategy"
        assert request.parameters["param"] == "value"
        assert request.context["files"]["input"] == "/file"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_network_error(self, client):
        """Test network error handling."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(NetworkError):
                await client.execute_strategy("test")

    @pytest.mark.asyncio
    async def test_api_error(self, client):
        """Test API error handling."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = Mock()
            # Make _get_client return an async context manager
            mock_get_client.return_value = mock_client

            error_response = httpx.Response(
                status_code=500,
                request=httpx.Request("POST", "http://test"),
                content=b"Internal Server Error",
            )
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=error_response.request,
                response=error_response,
            )

            with pytest.raises(ApiError) as exc_info:
                await client.execute_strategy("test")

            assert exc_info.value.status_code == 500