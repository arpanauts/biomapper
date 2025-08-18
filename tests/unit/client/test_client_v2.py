"""Tests for client_v2.py - BiomapperClient."""

import asyncio
import os
import pytest
import respx
from unittest.mock import AsyncMock, Mock, patch

import httpx
from httpx import AsyncClient

from src.client.client_v2 import BiomapperClient
from src.client.exceptions import (
    ApiError,
    FileUploadError, 
    JobNotFoundError,
    NetworkError,
    StrategyNotFoundError,
    TimeoutError,
    ValidationError,
)
from src.client.models import (
    ExecutionContext,
    ExecutionOptions,
    Job,
    JobStatusEnum,
    StrategyResult,
)


class TestBiomapperClientInitialization:
    """Test BiomapperClient initialization and configuration."""

    def test_client_initialization_defaults(self):
        """Test client initialization with default parameters."""
        client = BiomapperClient()
        
        assert client.base_url == "http://localhost:8000"
        assert client.api_key is None
        assert client.timeout == 300
        assert client.auto_retry is True
        assert client.max_retries == 3
        assert client._client is None
        assert client._sync_client is None

    def test_client_initialization_custom_config(self):
        """Test client initialization with custom configuration."""
        client = BiomapperClient(
            base_url="https://api.biomapper.com",
            api_key="test-key-123",
            timeout=600,
            auto_retry=False,
            max_retries=5
        )
        
        assert client.base_url == "https://api.biomapper.com"
        assert client.api_key == "test-key-123"
        assert client.timeout == 600
        assert client.auto_retry is False
        assert client.max_retries == 5

    def test_client_initialization_api_key_from_env(self):
        """Test client initialization with API key from environment."""
        with patch.dict(os.environ, {"BIOMAPPER_API_KEY": "env-key-456"}):
            client = BiomapperClient()
            assert client.api_key == "env-key-456"

    def test_client_initialization_base_url_normalization(self):
        """Test base URL normalization (removes trailing slash)."""
        client = BiomapperClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_client_headers_without_api_key(self):
        """Test header generation without API key."""
        client = BiomapperClient()
        headers = client._get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers

    def test_client_headers_with_api_key(self):
        """Test header generation with API key."""
        client = BiomapperClient(api_key="test-key")
        headers = client._get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"


class TestBiomapperClientContextManager:
    """Test BiomapperClient context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager entry and exit."""
        client = BiomapperClient()
        
        async with client as ctx_client:
            assert ctx_client is client
            assert client._client is not None
            assert isinstance(client._client, AsyncClient)
            assert str(client._client.base_url) == "http://localhost:8000"
        
        # Client should be closed after exit
        assert client._client is None

    def test_sync_context_manager(self):
        """Test sync context manager entry and exit."""
        client = BiomapperClient()
        
        with client as ctx_client:
            assert ctx_client is client
            assert client._sync_client is not None
            assert isinstance(client._sync_client, httpx.Client)
            assert str(client._sync_client.base_url) == "http://localhost:8000"
        
        # Client should be closed after exit
        assert client._sync_client is None


class TestBiomapperClientStrategyExecution:
    """Test strategy execution functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.fixture
    def mock_job_response(self):
        """Mock job response data."""
        return {
            "job_id": "test-job-123",
            "status": "running",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:01:00Z"
        }

    @pytest.mark.asyncio
    async def test_execute_strategy_by_name_success(self, client, mock_job_response):
        """Test successful strategy execution by name."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_job_response
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            job = await client.execute_strategy("test_strategy")
            
            assert job.id == "test-job-123"
            assert job.status == JobStatusEnum.RUNNING
            assert job.strategy_name == "test_strategy"

    @pytest.mark.asyncio
    async def test_execute_strategy_with_parameters(self, client, mock_job_response):
        """Test strategy execution with parameters."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json=mock_job_response)
            
            parameters = {"threshold": 0.8, "output_dir": "/tmp"}
            
            async with client:
                job = await client.execute_strategy("test_strategy", parameters=parameters)
                
                assert job.id == "test-job-123"

    @pytest.mark.asyncio
    async def test_execute_strategy_with_yaml_dict(self, client, mock_job_response):
        """Test strategy execution with YAML dictionary."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json=mock_job_response)
            
            strategy_dict = {
                "name": "test_strategy",
                "steps": [{"action": {"type": "LOAD_DATA"}}]
            }
            
            async with client:
                job = await client.execute_strategy(strategy_dict)
                
                assert job.strategy_name == "custom"

    @pytest.mark.asyncio
    async def test_execute_strategy_not_found_error(self, client):
        """Test strategy execution with strategy not found."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(404, json={"detail": "Strategy not found"})
            
            async with client:
                with pytest.raises(StrategyNotFoundError) as exc_info:
                    await client.execute_strategy("nonexistent_strategy")
                
                assert "Strategy not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_strategy_validation_error(self, client):
        """Test strategy execution with validation error."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(400, json={"detail": "Invalid strategy parameters"})
            
            async with client:
                with pytest.raises(ValidationError) as exc_info:
                    await client.execute_strategy("test_strategy")
                
                assert "Invalid strategy" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_strategy_network_error(self, client):
        """Test strategy execution with network error."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).mock(side_effect=httpx.ConnectError("Connection failed"))
            
            async with client:
                with pytest.raises(NetworkError) as exc_info:
                    await client.execute_strategy("test_strategy")
                
                assert "Network error" in str(exc_info.value)


class TestBiomapperClientJobManagement:
    """Test job management functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.asyncio
    async def test_get_job_status_success(self, client):
        """Test successful job status retrieval."""
        mock_status = {
            "job_id": "test-job-123",
            "status": "running",
            "progress": 50.0,
            "current_action": "LOAD_DATA",
            "message": "Loading data...",
            "updated_at": "2023-01-01T00:01:00Z"
        }
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            ).respond(200, json=mock_status)
            
            async with client:
                status = await client.get_job_status("test-job-123")
                
                assert status.job_id == "test-job-123"
                assert status.status == JobStatusEnum.RUNNING
                assert status.progress == 50.0
                assert status.current_action == "LOAD_DATA"
                assert status.message == "Loading data..."

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client):
        """Test job status retrieval with job not found."""
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/nonexistent/status"
            ).respond(404, json={"detail": "Job not found"})
            
            async with client:
                with pytest.raises(JobNotFoundError) as exc_info:
                    await client.get_job_status("nonexistent")
                
                assert "Job not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_job_results_success(self, client):
        """Test successful job results retrieval."""
        mock_results = {
            "job_id": "test-job-123",
            "status": "completed",
            "results": {"mapped_count": 100, "unmapped_count": 5},
            "output_files": ["/tmp/results.csv"]
        }
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/results"
            ).respond(200, json=mock_results)
            
            async with client:
                results = await client.get_job_results("test-job-123")
                
                assert results["job_id"] == "test-job-123"
                assert results["results"]["mapped_count"] == 100
                assert "/tmp/results.csv" in results["output_files"]

    @pytest.mark.asyncio
    async def test_wait_for_job_completion_success(self, client):
        """Test waiting for job completion successfully."""
        async with respx.mock:
            # Mock multiple status calls showing progression
            status_route = respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            )
            status_route.side_effect = [
                httpx.Response(200, json={
                    "job_id": "test-job-123",
                    "status": "running",
                    "progress": 50.0,
                    "updated_at": "2023-01-01T00:01:00Z"
                }),
                httpx.Response(200, json={
                    "job_id": "test-job-123",
                    "status": "completed",
                    "progress": 100.0,
                    "updated_at": "2023-01-01T00:02:00Z"
                })
            ]
            
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/results"
            ).respond(200, json={"job_id": "test-job-123", "results": {"mapped_count": 100}})
            
            async with client:
                result = await client.wait_for_job("test-job-123", timeout=30, poll_interval=0.1)
                
                assert result.success is True
                assert result.job_id == "test-job-123"
                assert result.result_data["job_id"] == "test-job-123"

    @pytest.mark.asyncio
    async def test_wait_for_job_timeout(self, client):
        """Test waiting for job with timeout."""
        async with respx.mock:
            # Mock status calls that never complete
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            ).respond(200, json={
                "job_id": "test-job-123",
                "status": "running",
                "progress": 10.0,
                "updated_at": "2023-01-01T00:01:00Z"
            })
            
            async with client:
                with pytest.raises(TimeoutError) as exc_info:
                    await client.wait_for_job("test-job-123", timeout=0.1, poll_interval=0.05)
                
                assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_job_failure(self, client):
        """Test waiting for job that fails."""
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            ).respond(200, json={
                "job_id": "test-job-123",
                "status": "failed",
                "progress": 25.0,
                "message": "Processing error occurred",
                "updated_at": "2023-01-01T00:01:00Z"
            })
            
            async with client:
                result = await client.wait_for_job("test-job-123")
                
                assert result.success is False
                assert result.job_id == "test-job-123"
                assert "Processing error occurred" in result.error


class TestBiomapperClientProgressStreaming:
    """Test progress streaming functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.asyncio
    async def test_stream_progress_events(self, client):
        """Test streaming progress events."""
        async with respx.mock:
            # Mock progressive status updates
            status_responses = [
                {
                    "job_id": "test-job-123",
                    "status": "running",
                    "progress": 25.0,
                    "message": "Loading data...",
                    "updated_at": "2023-01-01T00:01:00Z"
                },
                {
                    "job_id": "test-job-123",
                    "status": "running",
                    "progress": 75.0,
                    "message": "Processing data...",
                    "updated_at": "2023-01-01T00:02:00Z"
                },
                {
                    "job_id": "test-job-123",
                    "status": "completed",
                    "progress": 100.0,
                    "message": "Completed",
                    "updated_at": "2023-01-01T00:03:00Z"
                }
            ]
            
            status_route = respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            )
            status_route.side_effect = [httpx.Response(200, json=resp) for resp in status_responses]
            
            async with client:
                events = []
                async for event in client.stream_progress("test-job-123"):
                    events.append(event)
                    if len(events) >= 2:  # Collect first 2 progress events
                        break
                
                assert len(events) == 2
                assert events[0].percentage == 25.0
                assert events[0].message == "Loading data..."
                assert events[1].percentage == 75.0
                assert events[1].message == "Processing data..."


class TestBiomapperClientFileOperations:
    """Test file operations functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary test file."""
        test_file = tmp_path / "test_data.csv"
        test_file.write_text("id,name\n1,protein1\n2,protein2\n")
        return test_file

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client, temp_file):
        """Test successful file upload."""
        mock_response = {
            "session_id": "session-123",
            "filename": "test_data.csv",
            "file_size": 100,
            "columns": ["id", "name"],
            "row_count": 2
        }
        
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/files/upload"
            ).respond(200, json=mock_response)
            
            async with client:
                response = await client.upload_file(temp_file)
                
                assert response.session_id == "session-123"
                assert response.filename == "test_data.csv"
                assert response.file_size == 100
                assert response.columns == ["id", "name"]
                assert response.row_count == 2

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, client):
        """Test file upload with non-existent file."""
        async with client:
            with pytest.raises(FileUploadError) as exc_info:
                await client.upload_file("/nonexistent/file.csv")
            
            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_file_columns(self, client):
        """Test getting file columns."""
        mock_response = {
            "session_id": "session-123",
            "columns": ["id", "name", "description"],
            "data_types": {"id": "int", "name": "str", "description": "str"},
            "sample_values": {
                "id": [1, 2, 3],
                "name": ["protein1", "protein2", "protein3"]
            }
        }
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/files/session-123/columns"
            ).respond(200, json=mock_response)
            
            async with client:
                response = await client.get_file_columns("session-123")
                
                assert response.session_id == "session-123"
                assert response.columns == ["id", "name", "description"]
                assert response.data_types["id"] == "int"

    @pytest.mark.asyncio
    async def test_preview_file(self, client):
        """Test file preview."""
        mock_response = {
            "session_id": "session-123",
            "columns": ["id", "name"],
            "data": [
                {"id": 1, "name": "protein1"},
                {"id": 2, "name": "protein2"}
            ],
            "total_rows": 100,
            "preview_rows": 2
        }
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/files/session-123/preview"
            ).respond(200, json=mock_response)
            
            async with client:
                response = await client.preview_file("session-123", rows=10)
                
                assert response.session_id == "session-123"
                assert len(response.data) == 2
                assert response.data[0]["name"] == "protein1"
                assert response.total_rows == 100
                assert response.preview_rows == 2


class TestBiomapperClientSynchronousMethods:
    """Test synchronous convenience methods."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    def test_run_strategy_synchronous(self, client):
        """Test synchronous strategy execution."""
        with respx.mock:
            # Mock strategy execution
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json={"job_id": "test-job-123"})
            
            # Mock status polling
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            ).respond(200, json={
                "job_id": "test-job-123",
                "status": "completed",
                "progress": 100.0,
                "updated_at": "2023-01-01T00:01:00Z"
            })
            
            # Mock results
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/results"
            ).respond(200, json={"job_id": "test-job-123", "results": {"mapped_count": 100}})
            
            result = client.run("test_strategy", wait=True)
            
            assert isinstance(result, StrategyResult)
            assert result.success is True
            assert result.job_id == "test-job-123"

    def test_run_strategy_without_wait(self, client):
        """Test synchronous strategy execution without waiting."""
        with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json={"job_id": "test-job-123"})
            
            result = client.run("test_strategy", wait=False)
            
            assert isinstance(result, Job)
            assert result.id == "test-job-123"


class TestBiomapperClientAPIInformation:
    """Test API information methods."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test API health check."""
        mock_health = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600
        }
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/"
            ).respond(200, json=mock_health)
            
            async with client:
                health = await client.health_check()
                
                assert health["status"] == "healthy"
                assert health["version"] == "1.0.0"
                assert health["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_list_endpoints(self, client):
        """Test listing API endpoints."""
        mock_endpoints = [
            {
                "path": "/api/strategies/execute",
                "method": "POST",
                "description": "Execute strategy",
                "parameters": [],
                "response_model": "Job"
            }
        ]
        
        async with respx.mock:
            respx.get(
                "http://test-api.example.com/api/endpoints"
            ).respond(200, json=mock_endpoints)
            
            async with client:
                endpoints = await client.list_endpoints()
                
                assert len(endpoints) == 1
                assert endpoints[0].path == "/api/strategies/execute"
                assert endpoints[0].method == "POST"


class TestBiomapperClientErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """Test handling of various API errors."""
        async with respx.mock:
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(500, json={"detail": "Internal server error"})
            
            async with client:
                with pytest.raises(ApiError) as exc_info:
                    await client.execute_strategy("test_strategy")
                
                assert exc_info.value.status_code == 500
                assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_timeout_error(self, client):
        """Test network timeout handling."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_get_client.return_value = mock_client
            
            with pytest.raises(NetworkError):
                await client.execute_strategy("test_strategy")


class TestBiomapperClientIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.integration
    def test_complete_strategy_execution_workflow(self, client):
        """Test complete strategy execution from start to finish."""
        with respx.mock:
            # Mock strategy submission
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json={"job_id": "test-job-123"})
            
            # Mock status polling with progression
            status_route = respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/status"
            )
            status_route.side_effect = [
                httpx.Response(200, json={
                    "job_id": "test-job-123",
                    "status": "running",
                    "progress": 50.0,
                    "current_action": "PROCESSING",
                    "updated_at": "2023-01-01T00:01:00Z"
                }),
                httpx.Response(200, json={
                    "job_id": "test-job-123",
                    "status": "completed",
                    "progress": 100.0,
                    "updated_at": "2023-01-01T00:02:00Z"
                })
            ]
            
            # Mock result retrieval
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-123/results"
            ).respond(200, json={
                "job_id": "test-job-123",
                "results": {"mapped_count": 100, "unmapped_count": 5},
                "output_files": ["/tmp/results.csv"]
            })
            
            # Execute complete workflow
            result = client.run("test_strategy", {"param": "value"})
            
            assert isinstance(result, StrategyResult)
            assert result.success is True
            assert result.job_id == "test-job-123"
            assert result.result_data["results"]["mapped_count"] == 100

    @pytest.mark.integration
    def test_file_upload_and_strategy_execution_workflow(self, client, tmp_path):
        """Test file upload followed by strategy execution."""
        with respx.mock:
            # Create test file
            test_file = tmp_path / "data.csv"
            test_file.write_text("id,name\n1,protein1\n2,protein2\n")
            
            # Mock file upload
            respx.post(
                "http://test-api.example.com/api/files/upload"
            ).respond(200, json={
                "session_id": "session-123",
                "filename": "data.csv",
                "file_size": 30,
                "columns": ["id", "name"]
            })
            
            # Mock strategy execution
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json={"job_id": "test-job-456"})
            
            # Mock completion
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-456/status"
            ).respond(200, json={
                "job_id": "test-job-456",
                "status": "completed",
                "progress": 100.0,
                "updated_at": "2023-01-01T00:01:00Z"
            })
            
            respx.get(
                "http://test-api.example.com/api/mapping/jobs/test-job-456/results"
            ).respond(200, json={"job_id": "test-job-456", "results": {"processed_file": "session-123"}})
            
            # Execute workflow with context manager to ensure proper cleanup
            with client:
                # This would be async in real usage, but using sync for integration test
                result = client.run("test_strategy", {"input_file": "session-123"})
                
                assert result.success is True
                assert result.job_id == "test-job-456"


class TestBiomapperClientParameterValidation:
    """Test parameter validation and edge cases."""

    def test_strategy_request_preparation_name(self):
        """Test strategy request preparation with strategy name."""
        client = BiomapperClient()
        
        request = client._prepare_strategy_request(
            "test_strategy",
            parameters={"param1": "value1"},
            options=ExecutionOptions(debug_mode=True)
        )
        
        assert request.strategy_name == "test_strategy"
        assert request.parameters == {"param1": "value1"}
        assert request.options.debug_mode is True

    def test_strategy_request_preparation_dict(self):
        """Test strategy request preparation with strategy dict."""
        client = BiomapperClient()
        
        strategy_dict = {"name": "test", "steps": []}
        request = client._prepare_strategy_request(strategy_dict)
        
        assert request.strategy_yaml == strategy_dict
        assert request.strategy_name is None

    def test_execution_context_to_request(self):
        """Test ExecutionContext conversion to request."""
        client = BiomapperClient()
        
        context = ExecutionContext()
        context.add_parameter("key1", "value1")
        context.add_file("data", "/path/to/file.csv")
        context.enable_checkpoints()
        
        request = client._prepare_strategy_request("test_strategy", context=context)
        
        assert request.strategy_name == "test_strategy"
        assert request.parameters["key1"] == "value1"
        assert request.options.checkpoint_enabled is True


# Performance tests (optional, can be run separately)
class TestBiomapperClientPerformance:
    """Performance-related tests."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests."""
        clients = [BiomapperClient(base_url="http://test-api.example.com") for _ in range(5)]
        
        async with respx.mock:
            # Mock a single route that returns any job ID
            respx.post(
                "http://test-api.example.com/api/strategies/v2/execute"
            ).respond(200, json={"job_id": "test-job"})
            
            # Execute strategies concurrently
            tasks = []
            for i, client in enumerate(clients):
                async with client:
                    task = asyncio.create_task(client.execute_strategy(f"strategy_{i}"))
                    tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests succeeded
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert result.id == "test-job"  # All should have the same job ID from mock

    @pytest.mark.performance
    def test_request_formation_performance(self):
        """Test request formation performance with large parameters."""
        client = BiomapperClient()
        
        # Create large parameter set
        large_params = {f"param_{i}": f"value_{i}" for i in range(1000)}
        
        import time
        start_time = time.time()
        
        request = client._prepare_strategy_request("test_strategy", parameters=large_params)
        
        end_time = time.time()
        
        # Should complete quickly (under 100ms for 1000 parameters)
        assert end_time - start_time < 0.1
        assert len(request.parameters) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])