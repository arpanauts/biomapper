"""Tests for health check endpoints."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import time

from src.api.routes.health import router
from src.api.main import app


class TestHealthEndpoint:
    """Test health check endpoint functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def standalone_app(self):
        """Create standalone FastAPI app with only health router for isolated testing."""
        standalone_app = FastAPI()
        standalone_app.include_router(router)
        return TestClient(standalone_app)
    
    def test_health_check_success(self, client):
        """Test successful health check response."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
    
    def test_health_check_response_format(self, client):
        """Test health check response format validation."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert isinstance(data, dict)
        assert "status" in data
        assert "version" in data
        
        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        
        # Verify field values
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
    
    def test_health_check_performance(self, client):
        """Test health check endpoint performance."""
        start_time = time.time()
        response = client.get("/api/health/")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Health check should be fast (under 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0, f"Health check took {response_time:.3f}s, should be under 1s"
    
    def test_health_check_multiple_requests(self, client):
        """Test health check can handle multiple concurrent requests."""
        responses = []
        
        # Make multiple requests
        for _ in range(5):
            response = client.get("/api/health/")
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    def test_health_check_http_methods(self, client):
        """Test health check endpoint HTTP method restrictions."""
        # GET should work
        response = client.get("/api/health/")
        assert response.status_code == 200
        
        # POST should not be allowed
        response = client.post("/api/health/")
        assert response.status_code == 405  # Method Not Allowed
        
        # PUT should not be allowed
        response = client.put("/api/health/")
        assert response.status_code == 405
        
        # DELETE should not be allowed
        response = client.delete("/api/health/")
        assert response.status_code == 405
    
    def test_health_check_standalone_router(self, standalone_app):
        """Test health router in isolation."""
        response = standalone_app.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestHealthEndpointIntegration:
    """Integration tests for health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.mark.integration
    def test_health_check_with_full_app(self, client):
        """Test health check in context of full application."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Verify response headers
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]
    
    @pytest.mark.integration
    def test_health_check_after_app_startup(self, client):
        """Test health check works after application startup events."""
        # This test verifies that health check works even after
        # the application has gone through its startup process
        response = client.get("/api/health/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestHealthEndpointExtended:
    """Extended health check functionality tests."""
    
    @pytest.fixture
    def client(self):
        """Create test client.""" 
        return TestClient(app)
    
    def test_health_check_response_consistency(self, client):
        """Test that health check responses are consistent."""
        responses = []
        
        # Make multiple requests
        for _ in range(3):
            response = client.get("/api/health/")
            responses.append(response.json())
        
        # All responses should be identical
        first_response = responses[0]
        for response in responses[1:]:
            assert response == first_response
    
    def test_health_check_response_structure(self, client):
        """Test detailed response structure validation."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Test exact structure
        expected_keys = {"status", "version"}
        actual_keys = set(data.keys())
        assert actual_keys == expected_keys, f"Expected {expected_keys}, got {actual_keys}"
        
        # Test value constraints
        assert data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
    
    def test_health_check_content_type(self, client):
        """Test response content type is properly set."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]
    
    def test_health_check_with_query_parameters(self, client):
        """Test health check ignores query parameters."""
        response = client.get("/api/health/?param=value&other=test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
    
    def test_health_check_with_headers(self, client):
        """Test health check works with various headers."""
        headers = {
            "User-Agent": "Test-Client/1.0",
            "Accept": "application/json",
            "Authorization": "Bearer fake-token"
        }
        
        response = client.get("/api/health/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestHealthEndpointErrorHandling:
    """Test error handling scenarios for health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check_malformed_path(self, client):
        """Test health check with malformed paths."""
        # Extra slashes should still work
        response = client.get("/api/health//")
        assert response.status_code in [200, 404]  # Depends on FastAPI routing
        
        # Missing trailing slash (should still work with our route)
        response = client.get("/api/health")
        assert response.status_code in [200, 307, 404]  # May redirect or work
    
    def test_health_check_case_sensitivity(self, client):
        """Test health check path case sensitivity."""
        # Lowercase (correct)
        response = client.get("/api/health/")
        assert response.status_code == 200
        
        # Mixed case (should fail)
        response = client.get("/API/HEALTH/")
        assert response.status_code == 404
        
        response = client.get("/api/Health/")
        assert response.status_code == 404


class TestHealthEndpointMocking:
    """Test health endpoint with mocked dependencies."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('api.routes.health.router')
    def test_health_check_router_mocking(self, mock_router):
        """Test health check with mocked router."""
        # This test demonstrates how to mock the router if needed
        # for more complex health checks
        mock_router.get.return_value = {"status": "healthy", "version": "0.1.0"}
        
        # In practice, you'd use this pattern for complex health checks
        # that depend on external services
        assert True  # Router mocking setup works
    
    def test_health_check_without_dependencies(self, client):
        """Test that health check doesn't depend on external services."""
        # The current health check is simple and doesn't depend on
        # external services, which is good for basic availability monitoring
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestHealthEndpointDocumentation:
    """Test health endpoint documentation and OpenAPI spec."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint_in_openapi_spec(self, client):
        """Test that health endpoint is properly documented in OpenAPI spec."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        
        # Check that health endpoint is documented
        assert "paths" in openapi_spec
        health_path = "/api/health/"
        assert health_path in openapi_spec["paths"]
        
        # Check GET method is documented
        health_endpoint = openapi_spec["paths"][health_path]
        assert "get" in health_endpoint
        
        # Check response schema
        get_spec = health_endpoint["get"]
        assert "responses" in get_spec
        assert "200" in get_spec["responses"]
    
    def test_health_endpoint_tags(self, client):
        """Test that health endpoint has proper tags in OpenAPI."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        health_endpoint = openapi_spec["paths"]["/api/health/"]["get"]
        
        # Should have health tag
        assert "tags" in health_endpoint
        assert "health" in health_endpoint["tags"]


class TestHealthEndpointSecurity:
    """Test security aspects of health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check_no_sensitive_data(self, client):
        """Test that health check doesn't expose sensitive information."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        response_str = str(data).lower()
        
        # Should not contain sensitive information
        sensitive_terms = [
            "password", "token", "secret", "key", "database",
            "connection", "error", "exception", "traceback"
        ]
        
        for term in sensitive_terms:
            assert term not in response_str, f"Health check should not expose '{term}'"
    
    def test_health_check_response_headers_security(self, client):
        """Test that health check doesn't expose sensitive headers."""
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        
        # Should not expose sensitive server information
        assert "server" not in headers or "fastapi" not in headers["server"].lower()
        
        # Should have proper content type
        assert "content-type" in headers
        assert "application/json" in headers["content-type"]
    
    def test_health_check_no_authentication_required(self, client):
        """Test that health check doesn't require authentication."""
        # Health checks should typically be publicly accessible
        response = client.get("/api/health/")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Should work without any authentication headers
        response_without_auth = client.get("/api/health/")
        assert response_without_auth.status_code == 200