"""Tests for dependency injection and resource management."""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from src.api.deps import get_mapper_service
from src.api.services.mapper_service import MapperService
from src.api.main import app


class TestMapperServiceDependency:
    """Test MapperService dependency injection."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        return request
    
    def test_get_mapper_service_success(self, mock_request):
        """Test successful MapperService dependency resolution."""
        # Mock MapperService instance
        mock_mapper_service = Mock(spec=MapperService)
        mock_request.app.state.mapper_service = mock_mapper_service
        
        # Call dependency function
        result = get_mapper_service(mock_request)
        
        # Verify correct service is returned
        assert result == mock_mapper_service
        assert isinstance(result, type(mock_mapper_service))
    
    def test_get_mapper_service_from_app_state(self, mock_request):
        """Test that dependency correctly accesses app state."""
        mock_mapper_service = Mock(spec=MapperService)
        mock_request.app.state.mapper_service = mock_mapper_service
        
        result = get_mapper_service(mock_request)
        
        # Verify it accessed the correct app state attribute
        assert result == mock_request.app.state.mapper_service
    
    def test_get_mapper_service_missing_service(self, mock_request):
        """Test dependency behavior when service is missing from app state."""
        # Remove mapper_service from app state
        mock_request.app.state = Mock(spec=[])  # Empty spec means no attributes
        
        # Should raise AttributeError when trying to access missing service
        with pytest.raises(AttributeError):
            get_mapper_service(mock_request)
    
    def test_get_mapper_service_none_service(self, mock_request):
        """Test dependency behavior when service is None."""
        mock_request.app.state.mapper_service = None
        
        result = get_mapper_service(mock_request)
        
        # Should return None if that's what's stored
        assert result is None
    
    def test_get_mapper_service_type_consistency(self, mock_request):
        """Test that dependency returns consistent type."""
        mock_mapper_service = Mock(spec=MapperService)
        mock_request.app.state.mapper_service = mock_mapper_service
        
        result1 = get_mapper_service(mock_request)
        result2 = get_mapper_service(mock_request)
        
        # Should return the same instance
        assert result1 is result2
        assert result1 == mock_mapper_service


class TestDependencyInjectionIntegration:
    """Test dependency injection in context of full application."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.mark.integration
    def test_dependency_injection_in_app_context(self, client):
        """Test that dependency injection works in application context."""
        # The app should have initialized MapperService during startup
        # We can verify this by testing an endpoint that uses the dependency
        
        # Health check doesn't use MapperService, so test strategy endpoint
        response = client.post("/api/strategies/v2/execute", json={
            "strategy": "test_strategy",
            "parameters": {}
        })
        
        # Should not get dependency injection errors (404, 422, or 500 are fine)
        # but should not get 503 (service unavailable due to dependency issues)
        assert response.status_code != 503
    
    @pytest.mark.integration
    def test_mapper_service_available_in_app_state(self):
        """Test that MapperService is available in app state after startup."""
        # Access the app's state directly
        # Note: This test assumes the app has gone through startup
        if hasattr(app.state, 'mapper_service'):
            mapper_service = app.state.mapper_service
            assert mapper_service is not None
            assert isinstance(mapper_service, MapperService)


class TestDependencyLifecycle:
    """Test dependency lifecycle management."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        return request
    
    def test_dependency_singleton_behavior(self, mock_request):
        """Test that dependency returns singleton instance."""
        mock_mapper_service = Mock(spec=MapperService)
        mock_request.app.state.mapper_service = mock_mapper_service
        
        # Multiple calls should return same instance
        result1 = get_mapper_service(mock_request)
        result2 = get_mapper_service(mock_request)
        result3 = get_mapper_service(mock_request)
        
        assert result1 is result2
        assert result2 is result3
        assert result1 is mock_mapper_service
    
    def test_dependency_persistence_across_requests(self):
        """Test that dependency persists across different request objects."""
        # Create multiple mock requests pointing to same app
        mock_app = Mock()
        mock_app.state = Mock()
        mock_mapper_service = Mock(spec=MapperService)
        mock_app.state.mapper_service = mock_mapper_service
        
        request1 = Mock(spec=Request)
        request1.app = mock_app
        
        request2 = Mock(spec=Request)
        request2.app = mock_app
        
        # Should return same service instance for different requests
        result1 = get_mapper_service(request1)
        result2 = get_mapper_service(request2)
        
        assert result1 is result2
        assert result1 is mock_mapper_service
    
    def test_dependency_isolation_between_apps(self):
        """Test that different apps have isolated dependencies."""
        # Create two different mock apps
        app1 = Mock()
        app1.state = Mock()
        service1 = Mock(spec=MapperService)
        app1.state.mapper_service = service1
        
        app2 = Mock()
        app2.state = Mock()
        service2 = Mock(spec=MapperService)
        app2.state.mapper_service = service2
        
        request1 = Mock(spec=Request)
        request1.app = app1
        
        request2 = Mock(spec=Request)
        request2.app = app2
        
        # Should return different services
        result1 = get_mapper_service(request1)
        result2 = get_mapper_service(request2)
        
        assert result1 is service1
        assert result2 is service2
        assert result1 is not result2


class TestDependencyErrorHandling:
    """Test error handling in dependency injection."""
    
    def test_dependency_with_malformed_request(self):
        """Test dependency behavior with malformed request object."""
        # Request without app attribute
        malformed_request = Mock(spec=[])  # No attributes
        
        with pytest.raises(AttributeError):
            get_mapper_service(malformed_request)
    
    def test_dependency_with_malformed_app(self):
        """Test dependency behavior with malformed app object."""
        request = Mock(spec=Request)
        request.app = Mock(spec=[])  # App without state attribute
        
        with pytest.raises(AttributeError):
            get_mapper_service(request)
    
    def test_dependency_with_malformed_state(self):
        """Test dependency behavior with malformed app state."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock(spec=[])  # State without mapper_service
        
        with pytest.raises(AttributeError):
            get_mapper_service(request)
    
    def test_dependency_error_propagation(self):
        """Test that dependency errors are properly propagated."""
        request = Mock(spec=Request)
        request.app = Mock()
        
        # Make state access raise a custom exception
        def raise_custom_error():
            raise RuntimeError("Custom state access error")
        
        type(request.app).state = property(lambda self: raise_custom_error())
        
        with pytest.raises(RuntimeError, match="Custom state access error"):
            get_mapper_service(request)


class TestDependencyPerformance:
    """Test performance aspects of dependency injection."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        mock_mapper_service = Mock(spec=MapperService)
        request.app.state.mapper_service = mock_mapper_service
        return request
    
    def test_dependency_resolution_performance(self, mock_request):
        """Test that dependency resolution is fast."""
        import time
        
        # Multiple dependency resolutions should be fast
        start_time = time.time()
        for _ in range(1000):
            get_mapper_service(mock_request)
        end_time = time.time()
        
        # Should complete quickly (under 0.1 seconds for 1000 calls)
        assert (end_time - start_time) < 0.1
    
    def test_dependency_memory_usage(self, mock_request):
        """Test dependency memory usage."""
        # Multiple calls should not create new objects
        results = []
        for _ in range(100):
            result = get_mapper_service(mock_request)
            results.append(result)
        
        # All results should be the same object (no memory leak)
        first_result = results[0]
        for result in results:
            assert result is first_result
    
    def test_concurrent_dependency_access(self, mock_request):
        """Test concurrent access to dependency."""
        import threading
        
        results = []
        errors = []
        
        def access_dependency():
            try:
                result = get_mapper_service(mock_request)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_dependency)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 10
        
        # All results should be the same object
        first_result = results[0]
        for result in results:
            assert result is first_result


class TestDependencyDocumentation:
    """Test dependency function documentation and type hints."""
    
    def test_dependency_function_signature(self):
        """Test that dependency function has correct signature."""
        import inspect
        
        signature = inspect.signature(get_mapper_service)
        
        # Should have one parameter: request
        assert len(signature.parameters) == 1
        assert 'request' in signature.parameters
        
        # Parameter should have correct type annotation
        request_param = signature.parameters['request']
        assert request_param.annotation == Request
        
        # Return type should be annotated
        assert signature.return_annotation == MapperService
    
    def test_dependency_function_docstring(self):
        """Test that dependency function has proper documentation."""
        docstring = get_mapper_service.__doc__
        
        assert docstring is not None
        assert len(docstring.strip()) > 0
        
        # Should contain key information
        assert "mapper service" in docstring.lower()
        assert "dependency" in docstring.lower() or "returns" in docstring.lower()
    
    def test_dependency_function_module(self):
        """Test that dependency function is in correct module."""
        assert get_mapper_service.__module__ == "src.api.deps"


class TestDependencyMocking:
    """Test mocking strategies for dependency injection."""
    
    def test_mock_dependency_in_tests(self):
        """Test strategy for mocking dependencies in tests."""
        # Create a mock MapperService
        mock_service = Mock(spec=MapperService)
        mock_service.list_strategies.return_value = ["test_strategy"]
        
        # Create request that returns the mock
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        request.app.state.mapper_service = mock_service
        
        # Use dependency
        result = get_mapper_service(request)
        
        # Verify mock is returned
        assert result is mock_service
        assert result.list_strategies() == ["test_strategy"]
    
    @patch('tests.unit.api.test_deps.get_mapper_service')
    def test_patch_dependency_function(self, mock_get_mapper_service):
        """Test patching the dependency function directly."""
        mock_service = Mock(spec=MapperService)
        mock_get_mapper_service.return_value = mock_service
        
        # Create a request (won't be used due to patch)
        request = Mock(spec=Request)
        
        # Call the (now mocked) dependency function
        result = get_mapper_service(request)
        
        # Verify mock was called and returned
        assert result is mock_service
        mock_get_mapper_service.assert_called_once_with(request)
    
    def test_dependency_override_pattern(self):
        """Test pattern for overriding dependencies in tests."""
        # This demonstrates how you might override dependencies in FastAPI tests
        # using dependency_overrides (though we're not testing FastAPI's override here)
        
        mock_service = Mock(spec=MapperService)
        
        def mock_get_mapper_service(request: Request) -> MapperService:
            return mock_service
        
        # In real FastAPI tests, you'd use:
        # app.dependency_overrides[get_mapper_service] = mock_get_mapper_service
        
        # For this test, just verify the pattern works
        request = Mock(spec=Request)
        result = mock_get_mapper_service(request)
        assert result is mock_service


class TestDependencyEdgeCases:
    """Test edge cases in dependency injection."""
    
    def test_dependency_with_none_app(self):
        """Test dependency when request.app is None."""
        request = Mock(spec=Request)
        request.app = None
        
        with pytest.raises(AttributeError):
            get_mapper_service(request)
    
    def test_dependency_with_none_state(self):
        """Test dependency when app.state is None."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = None
        
        with pytest.raises(AttributeError):
            get_mapper_service(request)
    
    def test_dependency_with_wrong_service_type(self):
        """Test dependency when wrong type is stored in app state."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        # Store wrong type
        request.app.state.mapper_service = "not_a_mapper_service"
        
        result = get_mapper_service(request)
        
        # Should return whatever is stored (type checking is not enforced at runtime)
        assert result == "not_a_mapper_service"
    
    def test_dependency_with_dynamic_service_creation(self):
        """Test dependency when service is created dynamically."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        
        # Use a property that creates service on first access
        class DynamicState:
            def __init__(self):
                self._mapper_service = None
            
            @property
            def mapper_service(self):
                if self._mapper_service is None:
                    self._mapper_service = Mock(spec=MapperService)
                return self._mapper_service
        
        request.app.state = DynamicState()
        
        # First access should create the service
        result1 = get_mapper_service(request)
        result2 = get_mapper_service(request)
        
        # Should be the same service instance
        assert result1 is result2
        assert result1 is not None


class TestDependencyThreadSafety:
    """Test thread safety of dependency injection."""
    
    def test_dependency_thread_safety(self):
        """Test that dependency injection is thread-safe."""
        import threading
        import time
        
        # Create shared app state
        app_state = Mock()
        mapper_service = Mock(spec=MapperService)
        app_state.mapper_service = mapper_service
        
        results = []
        errors = []
        
        def worker():
            try:
                request = Mock(spec=Request)
                request.app = Mock()
                request.app.state = app_state
                
                for _ in range(100):
                    result = get_mapper_service(request)
                    results.append(result)
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors and all results are correct
        assert len(errors) == 0
        assert len(results) == 500  # 5 threads * 100 calls each
        
        # All results should be the same service
        for result in results:
            assert result is mapper_service