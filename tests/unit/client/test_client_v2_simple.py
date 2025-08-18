"""Simplified tests for client_v2.py - BiomapperClient."""

import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
from httpx import AsyncClient

from src.client.client_v2 import BiomapperClient
from src.client.exceptions import (
    FileUploadError, 
    JobNotFoundError,
    NetworkError,
    StrategyNotFoundError,
    ValidationError,
)
from src.client.models import (
    ExecutionContext,
    ExecutionOptions,
    Job,
    JobStatusEnum,
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


class TestBiomapperClientHelperMethods:
    """Test helper methods and utilities."""

    def test_prepare_strategy_request_with_name(self):
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

    def test_prepare_strategy_request_with_dict(self):
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
        context.add_file("data", "/path/to/data.csv")
        context.enable_checkpoints()
        
        request = client._prepare_strategy_request("test_strategy", context=context)
        
        assert request.strategy_name == "test_strategy"
        assert request.parameters["key1"] == "value1"
        assert request.options.checkpoint_enabled is True


class TestBiomapperClientMockedMethods:
    """Test client methods with mocked HTTP calls."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    @pytest.mark.asyncio
    async def test_execute_strategy_success(self, client):
        """Test successful strategy execution."""
        mock_response_data = {
            "job_id": "test-job-123",
            "status": "running",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:01:00Z"
        }
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            job = await client.execute_strategy("test_strategy")
            
            assert job.id == "test-job-123"
            assert job.status == JobStatusEnum.RUNNING
            assert job.strategy_name == "test_strategy"

    @pytest.mark.asyncio
    async def test_execute_strategy_not_found_error(self, client):
        """Test strategy execution with strategy not found."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Strategy not found"
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=mock_response
            )
            mock_get_client.return_value = mock_client
            
            with pytest.raises(StrategyNotFoundError):
                await client.execute_strategy("nonexistent_strategy")

    @pytest.mark.asyncio
    async def test_execute_strategy_validation_error(self, client):
        """Test strategy execution with validation error."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Invalid strategy parameters"
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "400 Bad Request", request=Mock(), response=mock_response
            )
            mock_get_client.return_value = mock_client
            
            with pytest.raises(ValidationError):
                await client.execute_strategy("test_strategy")

    @pytest.mark.asyncio
    async def test_execute_strategy_network_error(self, client):
        """Test strategy execution with network error."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            mock_get_client.return_value = mock_client
            
            with pytest.raises(NetworkError):
                await client.execute_strategy("test_strategy")

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
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_status
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            status = await client.get_job_status("test-job-123")
            
            assert status.job_id == "test-job-123"
            assert status.status == JobStatusEnum.RUNNING
            assert status.progress == 50.0
            assert status.current_action == "LOAD_DATA"
            assert status.message == "Loading data..."

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client):
        """Test job status retrieval with job not found."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Job not found"
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=mock_response
            )
            mock_get_client.return_value = mock_client
            
            with pytest.raises(JobNotFoundError):
                await client.get_job_status("nonexistent")

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test API health check."""
        mock_health = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600
        }
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_health
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            health = await client.health_check()
            
            assert health["status"] == "healthy"
            assert health["version"] == "1.0.0"
            assert health["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, client):
        """Test file upload with non-existent file."""
        with pytest.raises(FileUploadError) as exc_info:
            await client.upload_file("/nonexistent/file.csv")
        
        assert "File not found" in str(exc_info.value)


class TestBiomapperClientSynchronousMethods:
    """Test synchronous convenience methods."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BiomapperClient(base_url="http://test-api.example.com")

    def test_run_strategy_wait_false(self, client):
        """Test synchronous strategy execution without waiting."""
        mock_job_data = {
            "job_id": "test-job-123",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:01:00Z"
        }
        
        async def mock_execute_strategy(*args, **kwargs):
            return Job(
                id="test-job-123",
                status=JobStatusEnum.RUNNING,
                strategy_name="test_strategy",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        
        with patch.object(client, 'execute_strategy', side_effect=mock_execute_strategy):
            result = client.run("test_strategy", wait=False)
            
            assert isinstance(result, Job)
            assert result.id == "test-job-123"


class TestBiomapperClientEdgeCases:
    """Test edge cases and error conditions."""

    def test_large_parameters_handling(self):
        """Test handling of large parameter sets."""
        client = BiomapperClient()
        
        # Create large parameter set
        large_params = {f"param_{i}": f"value_{i}" for i in range(1000)}
        
        request = client._prepare_strategy_request("test_strategy", parameters=large_params)
        
        assert len(request.parameters) == 1000
        assert request.parameters["param_500"] == "value_500"

    def test_unicode_parameter_handling(self):
        """Test handling of Unicode parameters."""
        client = BiomapperClient()
        
        unicode_params = {
            "description": "Test with unicode: 你好 🌟 café",
            "path": "/data/файл.csv"
        }
        
        request = client._prepare_strategy_request("test_strategy", parameters=unicode_params)
        
        assert request.parameters["description"] == "Test with unicode: 你好 🌟 café"
        assert request.parameters["path"] == "/data/файл.csv"

    def test_nested_parameter_structure(self):
        """Test handling of nested parameter structures."""
        client = BiomapperClient()
        
        nested_params = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {
                        "username": "user",
                        "password": "pass"
                    }
                }
            },
            "features": ["feature1", "feature2", "feature3"]
        }
        
        request = client._prepare_strategy_request("test_strategy", parameters=nested_params)
        
        assert request.parameters["config"]["database"]["host"] == "localhost"
        assert request.parameters["features"] == ["feature1", "feature2", "feature3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])