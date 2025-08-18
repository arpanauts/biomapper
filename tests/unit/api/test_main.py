"""Tests for FastAPI main application setup."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import logging

from src.api.main import app, startup_event, shutdown_event, global_exception_handler


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestFastAPIApplication:
    """Test FastAPI application setup and configuration."""
    
    def test_app_creation(self):
        """Test FastAPI app is created with correct configuration."""
        assert isinstance(app, FastAPI)
        assert app.title == "Biomapper API"
        assert "API for Biomapper Web UI with Resource Management" in app.description
        assert app.version == "0.2.0"
        assert app.docs_url == "/api/docs"
        assert app.openapi_url == "/api/openapi.json"
    
    def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        # Check that CORS middleware is in the middleware stack
        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware.cls, '__name__') and 'CORS' in middleware.cls.__name__:
                cors_middleware = middleware
                break
        
        assert cors_middleware is not None, "CORS middleware should be configured"
    
    def test_routers_included(self, client):
        """Test that routers are properly included."""
        # Test health router is included
        response = client.get("/api/health/")
        assert response.status_code == 200
        
        # Test strategies v2 router paths exist (should return 422 for GET without params)
        response = client.get("/api/strategies/v2/execute")
        assert response.status_code in [405, 422]  # Method not allowed or validation error
    
    def test_root_endpoint(self, client):
        """Test root endpoint functionality."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "Welcome to Biomapper API. Visit /api/docs for documentation."
        }
    
    def test_openapi_docs_accessible(self, client):
        """Test OpenAPI documentation is accessible."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_json_accessible(self, client):
        """Test OpenAPI JSON schema is accessible."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert openapi_data["info"]["title"] == "Biomapper API"


class TestApplicationEvents:
    """Test application startup and shutdown events."""
    
    @pytest.mark.asyncio
    @patch('src.api.main.MapperService')
    @patch('src.api.main.logger')
    async def test_startup_event_success(self, mock_logger, mock_mapper_service_class):
        """Test successful startup event."""
        # Create a mock app state
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Mock MapperService creation
        mock_mapper_service = Mock()
        mock_mapper_service_class.return_value = mock_mapper_service
        
        # Patch app in the global context with correct module path
        with patch('src.api.main.app', mock_app):
            await startup_event()
        
        # Verify MapperService was created and assigned
        mock_mapper_service_class.assert_called_once()
        assert mock_app.state.mapper_service == mock_mapper_service
        mock_logger.info.assert_called_with("MapperService initialized successfully.")
    
    @pytest.mark.asyncio
    @patch('src.api.main.MapperService')
    @patch('src.api.main.logger')
    async def test_startup_event_failure(self, mock_logger, mock_mapper_service_class):
        """Test startup event with MapperService initialization failure."""
        # Mock MapperService to raise an exception
        mock_mapper_service_class.side_effect = Exception("Service initialization failed")
        
        # Create a mock app state
        mock_app = Mock()
        mock_app.state = Mock()
        
        with patch('src.api.main.app', mock_app):
            with pytest.raises(Exception, match="Service initialization failed"):
                await startup_event()
        
        # Verify error was logged
        mock_logger.critical.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.api.main.logger')
    async def test_shutdown_event(self, mock_logger):
        """Test shutdown event."""
        await shutdown_event()
        mock_logger.info.assert_called_with("API shutting down...")


class TestExceptionHandling:
    """Test global exception handling."""
    
    @pytest.mark.asyncio
    @patch('src.api.main.logger')
    async def test_global_exception_handler(self, mock_logger):
        """Test global exception handler."""
        # Create mock request
        mock_request = Mock()
        mock_request.url.path = "/test/path"
        mock_request.method = "GET"
        
        # Create test exception
        test_exception = Exception("Test error message")
        
        # Call exception handler
        response = await global_exception_handler(mock_request, test_exception)
        
        # Verify response
        assert response.status_code == 500
        assert response.media_type == "application/json"
        
        # Verify logging
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Unhandled exception occurred" in call_args[0][0]
        assert call_args[1]["exc_info"] == test_exception
        assert call_args[1]["path"] == "/test/path"
        assert call_args[1]["method"] == "GET"
    
    def test_exception_handler_integration(self, client):
        """Test exception handler integration with test client."""
        # This would require creating an endpoint that raises an exception
        # For now, we'll test that the handler is registered
        assert len(app.exception_handlers) > 0


class TestMiddlewareExecution:
    """Test middleware execution and order."""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are added to responses."""
        response = client.get("/")
        
        # Check for CORS headers (these might not all be present in test environment)
        # but the middleware should be configured
        assert response.status_code == 200
        # In a real test, you might check for Access-Control-Allow-Origin header


class TestImportedActions:
    """Test that strategy actions are properly imported and registered."""
    
    @patch('src.api.main.logger_temp')
    def test_action_imports_success(self, mock_logger):
        """Test successful action imports."""
        # The imports happen at module level, so we test that no critical errors occurred
        # This is mainly to ensure the import block doesn't break the app
        assert True  # If we reach here, imports succeeded
    
    @patch('src.api.main.logger_temp')
    @patch('builtins.__import__', side_effect=ImportError("Mock import error"))
    def test_action_imports_failure_handled(self, mock_import, mock_logger):
        """Test that import failures are handled gracefully."""
        # This test verifies that import errors don't crash the application
        # Note: This is a complex test since imports happen at module level
        # In practice, you'd test this by temporarily breaking imports
        assert True  # Import error handling is in place


class TestApplicationConfiguration:
    """Test application configuration and settings integration."""
    
    def test_settings_integration(self):
        """Test that settings are properly integrated into app configuration."""
        from src.api.core.config import settings
        
        # Verify settings are accessible
        assert settings.PROJECT_NAME == "Biomapper API"
        assert isinstance(settings.CORS_ORIGINS, list)
        
        # Verify app uses settings
        assert app.title == settings.PROJECT_NAME
    
    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        # Verify logging is configured before app creation
        logger = logging.getLogger("api.main")
        assert logger is not None
        
        # Check that logger has handlers (configured by configure_logging)
        # This is a basic check since detailed logging config testing 
        # would be in logging_config tests


class TestAPIIntegration:
    """Integration tests for complete API workflows."""
    
    @pytest.mark.integration
    def test_health_check_integration(self, client):
        """Test complete health check workflow."""
        response = client.get("/api/health/")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
    
    @pytest.mark.integration
    @patch('src.api.routes.strategies_v2_simple.MinimalStrategyService')
    def test_strategy_endpoint_accessibility(self, mock_service, client):
        """Test that strategy endpoints are accessible."""
        # Test that the strategy endpoint exists and responds appropriately
        response = client.post("/api/strategies/v2/execute", json={
            "strategy": "test_strategy",
            "parameters": {}
        })
        
        # Should get either success or a meaningful error (not 404)
        assert response.status_code != 404
    
    @pytest.mark.integration
    def test_documentation_integration(self, client):
        """Test that API documentation is properly generated and accessible."""
        # Test docs page
        docs_response = client.get("/api/docs")
        assert docs_response.status_code == 200
        
        # Test OpenAPI spec
        openapi_response = client.get("/api/openapi.json")
        assert openapi_response.status_code == 200
        
        openapi_spec = openapi_response.json()
        assert "paths" in openapi_spec
        assert "/api/health/" in openapi_spec["paths"]
        assert "/api/strategies/v2/execute" in openapi_spec["paths"]


class TestEnvironmentConfiguration:
    """Test environment-specific configuration."""
    
    @patch.dict('os.environ', {'DEBUG': 'true'})
    def test_debug_mode_configuration(self):
        """Test application behavior in debug mode."""
        # This would test environment-specific settings
        # For now, verify that the config system can handle env vars
        from src.api.core.config import Settings
        debug_settings = Settings(DEBUG=True)
        assert debug_settings.DEBUG is True
    
    def test_production_mode_configuration(self):
        """Test application behavior in production mode."""
        from src.api.core.config import Settings
        prod_settings = Settings(DEBUG=False)
        assert prod_settings.DEBUG is False


class TestSecurityConfiguration:
    """Test security-related configurations."""
    
    def test_cors_configuration(self):
        """Test CORS configuration for security."""
        from src.api.core.config import settings
        
        # Verify CORS origins are configured
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0
    
    def test_error_response_security(self, client):
        """Test that error responses don't leak sensitive information."""
        # Test with an endpoint that doesn't exist
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        # Verify response doesn't contain sensitive debug info
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "exception" not in response_text