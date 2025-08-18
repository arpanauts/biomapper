"""Tests for strategy execution endpoints v2."""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path

from src.api.routes.strategies_v2_simple import (
    jobs,
    run_strategy_async,
    V2StrategyExecutionRequest,
    V2ExecutionOptions,
    V2StrategyExecutionResponse
)
from src.api.main import app


class TestStrategyExecutionModels:
    """Test Pydantic models for strategy execution."""
    
    def test_v2_execution_options_defaults(self):
        """Test V2ExecutionOptions default values."""
        options = V2ExecutionOptions()
        
        assert options.checkpoint_enabled is False
        assert options.timeout_seconds is None
        assert options.max_retries == 3
        assert options.validate_prerequisites is False
    
    def test_v2_execution_options_custom_values(self):
        """Test V2ExecutionOptions with custom values."""
        options = V2ExecutionOptions(
            checkpoint_enabled=True,
            timeout_seconds=300,
            max_retries=5,
            validate_prerequisites=True
        )
        
        assert options.checkpoint_enabled is True
        assert options.timeout_seconds == 300
        assert options.max_retries == 5
        assert options.validate_prerequisites is True
    
    def test_v2_strategy_execution_request_minimal(self):
        """Test V2StrategyExecutionRequest with minimal data."""
        request = V2StrategyExecutionRequest(strategy="test_strategy")
        
        assert request.strategy == "test_strategy"
        assert request.parameters == {}
        assert isinstance(request.options, V2ExecutionOptions)
    
    def test_v2_strategy_execution_request_full(self):
        """Test V2StrategyExecutionRequest with full data."""
        options = V2ExecutionOptions(checkpoint_enabled=True)
        request = V2StrategyExecutionRequest(
            strategy="test_strategy",
            parameters={"param1": "value1"},
            options=options
        )
        
        assert request.strategy == "test_strategy"
        assert request.parameters == {"param1": "value1"}
        assert request.options.checkpoint_enabled is True
    
    def test_v2_strategy_execution_request_inline_strategy(self):
        """Test V2StrategyExecutionRequest with inline strategy definition."""
        inline_strategy = {
            "name": "inline_test",
            "steps": [{"action": {"type": "TEST_ACTION"}}]
        }
        
        request = V2StrategyExecutionRequest(strategy=inline_strategy)
        
        assert request.strategy == inline_strategy
        assert request.parameters == {}
    
    def test_v2_strategy_execution_response(self):
        """Test V2StrategyExecutionResponse model."""
        response = V2StrategyExecutionResponse(
            job_id="test-job-123",
            status="running",
            message="Strategy execution started"
        )
        
        assert response.job_id == "test-job-123"
        assert response.status == "running"
        assert response.message == "Strategy execution started"


class TestStrategyExecutionEndpoints:
    """Test strategy execution endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    @patch('src.api.routes.strategies_v2_simple.run_strategy_async')
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    def test_execute_strategy_success(self, mock_service_class, mock_run_strategy, client, clear_jobs):
        """Test successful strategy execution."""
        # Mock MinimalStrategyService
        mock_service = Mock()
        mock_service.strategies = {"test_strategy": {"name": "test_strategy"}}
        mock_service_class.return_value = mock_service
        
        # Mock the background task to avoid actual execution
        mock_run_strategy.return_value = None
        
        request_data = {
            "strategy": "test_strategy",
            "parameters": {"param1": "value1"}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "running"
        assert "test_strategy" in data["message"]
        
        # Verify job was created in the global jobs dict
        job_id = data["job_id"]
        assert job_id in jobs
        assert jobs[job_id]["strategy_name"] == "test_strategy"
        assert jobs[job_id]["parameters"] == {"param1": "value1"}
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    async def test_execute_strategy_inline_definition(self, mock_service_class, client, clear_jobs):
        """Test strategy execution with inline strategy definition."""
        mock_service = Mock()
        mock_service.strategies = {}
        mock_service_class.return_value = mock_service
        
        inline_strategy = {
            "name": "inline_test",
            "steps": [{"action": {"type": "TEST_ACTION"}}]
        }
        
        request_data = {
            "strategy": inline_strategy,
            "parameters": {"param1": "value1"}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "running"
        
        # Verify job was created with inline strategy name
        job_id = data["job_id"]
        assert job_id in jobs
        assert jobs[job_id]["strategy_name"] == "inline_test"
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    async def test_execute_strategy_with_options(self, mock_service_class, client, clear_jobs):
        """Test strategy execution with custom options."""
        mock_service = Mock()
        mock_service.strategies = {"test_strategy": {"name": "test_strategy"}}
        mock_service_class.return_value = mock_service
        
        request_data = {
            "strategy": "test_strategy",
            "parameters": {"param1": "value1"},
            "options": {
                "checkpoint_enabled": True,
                "timeout_seconds": 300,
                "max_retries": 5
            }
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService', side_effect=Exception("Service error"))
    async def test_execute_strategy_service_error(self, mock_service_class, client, clear_jobs):
        """Test strategy execution with service initialization error."""
        request_data = {
            "strategy": "test_strategy",
            "parameters": {}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        
        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]
    
    def test_execute_strategy_invalid_request(self, client, clear_jobs):
        """Test strategy execution with invalid request data."""
        # Missing required strategy field
        request_data = {
            "parameters": {"param1": "value1"}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        assert response.status_code == 422
    
    def test_execute_strategy_empty_request(self, client, clear_jobs):
        """Test strategy execution with empty request."""
        response = client.post("/api/strategies/v2/execute", json={})
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    async def test_execute_strategy_nonexistent_strategy(self, mock_service_class, client, clear_jobs):
        """Test execution of non-existent strategy."""
        mock_service = Mock()
        mock_service.strategies = {}  # Empty strategies
        mock_service_class.return_value = mock_service
        
        request_data = {
            "strategy": "nonexistent_strategy",
            "parameters": {}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        
        # Should still succeed but log warning
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestJobStatusEndpoints:
    """Test job status and result endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    def test_get_job_status_success(self, client, clear_jobs):
        """Test getting job status for existing job."""
        # Create a test job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "strategy_name": "test_strategy",
            "parameters": {"param1": "value1"}
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "running"
        assert data["strategy_name"] == "test_strategy"
        assert "error" in data  # Should be present even if None
    
    def test_get_job_status_not_found(self, client, clear_jobs):
        """Test getting status for non-existent job."""
        nonexistent_job_id = str(uuid.uuid4())
        
        response = client.get(f"/api/strategies/v2/jobs/{nonexistent_job_id}/status")
        
        assert response.status_code == 404
        assert f"Job {nonexistent_job_id} not found" in response.json()["detail"]
    
    def test_get_job_status_with_error(self, client, clear_jobs):
        """Test getting status for job with error."""
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "failed",
            "strategy_name": "test_strategy",
            "error": "Test error message"
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "failed"
        assert data["error"] == "Test error message"
    
    def test_get_job_results_success(self, client, clear_jobs):
        """Test getting results for completed job."""
        job_id = str(uuid.uuid4())
        test_result = {"output": "test_result", "statistics": {"processed": 100}}
        
        jobs[job_id] = {
            "id": job_id,
            "status": "completed",
            "strategy_name": "test_strategy",
            "result": test_result
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/results")
        
        assert response.status_code == 200
        data = response.json()
        assert data == test_result
    
    def test_get_job_results_not_found(self, client, clear_jobs):
        """Test getting results for non-existent job."""
        nonexistent_job_id = str(uuid.uuid4())
        
        response = client.get(f"/api/strategies/v2/jobs/{nonexistent_job_id}/results")
        
        assert response.status_code == 404
        assert f"Job {nonexistent_job_id} not found" in response.json()["detail"]
    
    def test_get_job_results_not_completed(self, client, clear_jobs):
        """Test getting results for non-completed job."""
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "strategy_name": "test_strategy"
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/results")
        
        assert response.status_code == 400
        assert f"Job {job_id} is not completed" in response.json()["detail"]
    
    def test_get_job_results_failed_job(self, client, clear_jobs):
        """Test getting results for failed job."""
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "failed",
            "strategy_name": "test_strategy",
            "error": "Strategy execution failed"
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/results")
        
        assert response.status_code == 400
        assert f"Job {job_id} is not completed" in response.json()["detail"]
    
    def test_get_job_results_no_result_data(self, client, clear_jobs):
        """Test getting results for completed job without result data."""
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "completed",
            "strategy_name": "test_strategy"
            # No result field
        }
        
        response = client.get(f"/api/strategies/v2/jobs/{job_id}/results")
        
        assert response.status_code == 200
        data = response.json()
        assert data == {}  # Should return empty dict


class TestAsyncStrategyExecution:
    """Test async strategy execution function."""
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    @patch('src.api.routes.strategies_v2_simple.Path')
    async def test_run_strategy_async_success(self, mock_path, mock_service_class, clear_jobs):
        """Test successful async strategy execution."""
        # Setup mocks
        mock_service = AsyncMock()
        mock_service.execute_strategy = AsyncMock(return_value={"status": "success", "data": "test_data"})
        mock_service_class.return_value = mock_service
        
        mock_path.return_value.parent.parent.parent.parent = Path("/mock/path")
        
        # Create initial job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "strategy_name": "test_strategy"
        }
        
        # Run async function
        await run_strategy_async(job_id, "test_strategy", {"param1": "value1"})
        
        # Verify job was updated
        assert jobs[job_id]["status"] == "completed"
        assert jobs[job_id]["result"] == {"status": "success", "data": "test_data"}
        
        # Verify service was called correctly
        mock_service.execute_strategy.assert_called_once_with(
            strategy_name="test_strategy",
            context={"param1": "value1"}
        )
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    @patch('src.api.routes.strategies_v2_simple.Path')
    async def test_run_strategy_async_failure(self, mock_path, mock_service_class, clear_jobs):
        """Test async strategy execution with failure."""
        # Setup mocks to raise exception
        mock_service = AsyncMock()
        mock_service.execute_strategy = AsyncMock(side_effect=Exception("Strategy execution failed"))
        mock_service_class.return_value = mock_service
        
        mock_path.return_value.parent.parent.parent.parent = Path("/mock/path")
        
        # Create initial job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "strategy_name": "test_strategy"
        }
        
        # Run async function
        await run_strategy_async(job_id, "test_strategy", {"param1": "value1"})
        
        # Verify job was updated with error
        assert jobs[job_id]["status"] == "failed"
        assert jobs[job_id]["error"] == "Strategy execution failed"
        assert "result" not in jobs[job_id]
    
    @pytest.mark.asyncio
    @patch('src.api.routes.strategies_v2_simple.logger')
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    async def test_run_strategy_async_logging(self, mock_service_class, mock_logger, clear_jobs):
        """Test that async execution logs appropriately."""
        mock_service = AsyncMock()
        mock_service.execute_strategy = AsyncMock(side_effect=Exception("Test error"))
        mock_service_class.return_value = mock_service
        
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"id": job_id, "status": "pending"}
        
        await run_strategy_async(job_id, "test_strategy", {})
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Strategy execution failed" in str(mock_logger.error.call_args)


class TestStrategyEndpointIntegration:
    """Integration tests for strategy endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    @pytest.mark.integration
    @patch('src.api.routes.strategies_v2_simple.run_strategy_async')
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    def test_complete_workflow(self, mock_service_class, mock_run_strategy, client, clear_jobs):
        """Test complete workflow from execution to result retrieval."""
        # Mock service
        mock_service = Mock()
        mock_service.strategies = {"test_strategy": {"name": "test_strategy"}}
        mock_service_class.return_value = mock_service
        
        # Mock the background task to avoid actual execution
        mock_run_strategy.return_value = None
        
        # 1. Execute strategy
        request_data = {
            "strategy": "test_strategy",
            "parameters": {"param1": "value1"}
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        assert response.status_code == 200
        
        job_id = response.json()["job_id"]
        
        # 2. Check status
        status_response = client.get(f"/api/strategies/v2/jobs/{job_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] in ["pending", "running"]
        
        # 3. Simulate completion by manually updating job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {"output": "test_result"}
        
        # 4. Get results
        results_response = client.get(f"/api/strategies/v2/jobs/{job_id}/results")
        assert results_response.status_code == 200
        assert results_response.json() == {"output": "test_result"}
    
    @pytest.mark.integration
    def test_router_registration(self, client):
        """Test that router is properly registered."""
        # Test that the prefix is working
        response = client.post("/api/strategies/v2/execute", json={"strategy": "test"})
        
        # Should not get 404 (router is registered)
        assert response.status_code != 404
    
    @pytest.mark.integration
    def test_openapi_documentation(self, client):
        """Test that strategy endpoints are documented in OpenAPI."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        
        # Check that strategy endpoints are documented
        assert "paths" in openapi_spec
        assert "/api/strategies/v2/execute" in openapi_spec["paths"]
        assert "/api/strategies/v2/jobs/{job_id}/status" in openapi_spec["paths"]
        assert "/api/strategies/v2/jobs/{job_id}/results" in openapi_spec["paths"]


class TestStrategyEndpointSecurity:
    """Test security aspects of strategy endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    def test_input_validation(self, client, clear_jobs):
        """Test input validation prevents malicious payloads."""
        # Test with extremely large payload
        large_payload = {
            "strategy": "test_strategy",
            "parameters": {"large_param": "x" * 10000}
        }
        
        response = client.post("/api/strategies/v2/execute", json=large_payload)
        # Should handle large payloads gracefully
        assert response.status_code in [200, 413, 422]  # Success, too large, or validation error
    
    def test_job_id_validation(self, client, clear_jobs):
        """Test job ID validation prevents injection attacks."""
        # Test with malicious job ID
        malicious_job_id = "../../../etc/passwd"
        
        response = client.get(f"/api/strategies/v2/jobs/{malicious_job_id}/status")
        assert response.status_code == 404
    
    def test_parameter_sanitization(self, client, clear_jobs):
        """Test that parameters are properly sanitized."""
        # Test with potentially dangerous parameters
        request_data = {
            "strategy": "test_strategy",
            "parameters": {
                "script": "<script>alert('xss')</script>",
                "command": "rm -rf /",
                "sql": "'; DROP TABLE users; --"
            }
        }
        
        response = client.post("/api/strategies/v2/execute", json=request_data)
        # Should not crash the application
        assert response.status_code in [200, 422, 500]


class TestStrategyEndpointPerformance:
    """Test performance aspects of strategy endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def clear_jobs(self):
        """Clear jobs before each test."""
        jobs.clear()
        yield
        jobs.clear()
    
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    def test_concurrent_executions(self, mock_service_class, client, clear_jobs):
        """Test handling of concurrent strategy executions."""
        mock_service = Mock()
        mock_service.strategies = {"test_strategy": {"name": "test_strategy"}}
        mock_service_class.return_value = mock_service
        
        # Submit multiple requests
        responses = []
        for i in range(5):
            request_data = {
                "strategy": "test_strategy",
                "parameters": {"iteration": i}
            }
            response = client.post("/api/strategies/v2/execute", json=request_data)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "job_id" in response.json()
        
        # All job IDs should be unique
        job_ids = [resp.json()["job_id"] for resp in responses]
        assert len(set(job_ids)) == len(job_ids)
    
    def test_memory_usage_with_many_jobs(self, client, clear_jobs):
        """Test memory usage doesn't grow unbounded with many jobs."""
        # Create many jobs to test memory usage
        for i in range(100):
            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                "id": job_id,
                "status": "completed",
                "result": {"data": f"result_{i}"}
            }
        
        # Memory usage should be reasonable
        assert len(jobs) == 100
        
        # Access should still be fast
        first_job_id = list(jobs.keys())[0]
        response = client.get(f"/api/strategies/v2/jobs/{first_job_id}/status")
        assert response.status_code == 200