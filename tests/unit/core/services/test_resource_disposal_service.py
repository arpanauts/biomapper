"""
Unit tests for ResourceDisposalService.

Tests the resource cleanup and disposal functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from biomapper.core.services.resource_disposal_service import ResourceDisposalService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.engine_components.client_manager import ClientManager


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    mock = Mock(spec=SessionManager)
    
    # Create mock engines
    mock.async_metamapper_engine = Mock()
    mock.async_metamapper_engine.dispose = AsyncMock()
    
    mock.async_cache_engine = Mock()
    mock.async_cache_engine.dispose = AsyncMock()
    
    return mock


@pytest.fixture
def mock_client_manager():
    """Create a mock ClientManager."""
    mock = Mock(spec=ClientManager)
    mock.clear_cache = Mock()
    return mock


@pytest.fixture
def disposal_service(mock_session_manager, mock_client_manager):
    """Create a ResourceDisposalService instance."""
    return ResourceDisposalService(
        session_manager=mock_session_manager,
        client_manager=mock_client_manager
    )


class TestResourceDisposalService:
    """Test cases for ResourceDisposalService."""
    
    def test_initialization(self, disposal_service, mock_session_manager, mock_client_manager):
        """Test service initialization."""
        assert disposal_service.session_manager == mock_session_manager
        assert disposal_service.client_manager == mock_client_manager
        assert disposal_service.is_disposed is False
    
    async def test_dispose_all(self, disposal_service, mock_session_manager, mock_client_manager):
        """Test disposing all resources."""
        await disposal_service.dispose_all()
        
        # Verify engines were disposed
        mock_session_manager.async_metamapper_engine.dispose.assert_called_once()
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        
        # Verify client cache was cleared
        mock_client_manager.clear_cache.assert_called_once()
        
        # Verify disposed state
        assert disposal_service.is_disposed is True
    
    async def test_dispose_all_idempotent(self, disposal_service):
        """Test that dispose_all is idempotent."""
        await disposal_service.dispose_all()
        assert disposal_service.is_disposed is True
        
        # Reset mocks
        disposal_service.session_manager.async_metamapper_engine.dispose.reset_mock()
        disposal_service.session_manager.async_cache_engine.dispose.reset_mock()
        disposal_service.client_manager.clear_cache.reset_mock()
        
        # Call again
        await disposal_service.dispose_all()
        
        # Should not call disposal methods again
        disposal_service.session_manager.async_metamapper_engine.dispose.assert_not_called()
        disposal_service.session_manager.async_cache_engine.dispose.assert_not_called()
        disposal_service.client_manager.clear_cache.assert_not_called()
    
    async def test_dispose_metamapper_engine(self, disposal_service, mock_session_manager):
        """Test disposing only metamapper engine."""
        await disposal_service.dispose_metamapper_engine()
        
        mock_session_manager.async_metamapper_engine.dispose.assert_called_once()
        mock_session_manager.async_cache_engine.dispose.assert_not_called()
    
    async def test_dispose_cache_engine(self, disposal_service, mock_session_manager):
        """Test disposing only cache engine."""
        await disposal_service.dispose_cache_engine()
        
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        mock_session_manager.async_metamapper_engine.dispose.assert_not_called()
    
    def test_clear_client_cache(self, disposal_service, mock_client_manager):
        """Test clearing client cache."""
        disposal_service.clear_client_cache()
        
        mock_client_manager.clear_cache.assert_called_once()
    
    async def test_dispose_all_without_client_manager(self, mock_session_manager):
        """Test disposal without client manager."""
        service = ResourceDisposalService(
            session_manager=mock_session_manager,
            client_manager=None
        )
        
        await service.dispose_all()
        
        # Engines should still be disposed
        mock_session_manager.async_metamapper_engine.dispose.assert_called_once()
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        
        assert service.is_disposed is True
    
    async def test_dispose_all_without_engines(self):
        """Test disposal when engines don't exist."""
        mock_session = Mock(spec=SessionManager)
        # No engines attached
        
        service = ResourceDisposalService(
            session_manager=mock_session,
            client_manager=None
        )
        
        # Should not raise error
        await service.dispose_all()
        assert service.is_disposed is True
    
    async def test_dispose_all_with_errors(self, disposal_service, mock_session_manager):
        """Test disposal with errors in some operations."""
        # Make metamapper disposal fail
        mock_session_manager.async_metamapper_engine.dispose.side_effect = Exception("Metamapper error")
        
        # Should still dispose other resources
        await disposal_service.dispose_all()
        
        # Cache engine and client cache should still be cleaned
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        disposal_service.client_manager.clear_cache.assert_called_once()
    
    async def test_dispose_on_error(self, disposal_service, mock_session_manager, mock_client_manager):
        """Test emergency disposal on error."""
        error = RuntimeError("Critical error occurred")
        
        await disposal_service.dispose_on_error(error)
        
        # Should dispose all resources
        mock_session_manager.async_metamapper_engine.dispose.assert_called_once()
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        mock_client_manager.clear_cache.assert_called_once()
        
        assert disposal_service.is_disposed is True
    
    async def test_dispose_on_error_with_disposal_failure(self, disposal_service, mock_session_manager):
        """Test emergency disposal when disposal itself fails."""
        error = RuntimeError("Critical error")
        mock_session_manager.async_metamapper_engine.dispose.side_effect = Exception("Disposal failed")
        
        # Should not raise error
        await disposal_service.dispose_on_error(error)
    
    def test_get_resource_status(self, disposal_service):
        """Test getting resource status."""
        status = disposal_service.get_resource_status()
        
        assert status == {
            'metamapper_engine': True,
            'cache_engine': True,
            'client_manager': True,
            'is_disposed': False
        }
        
        # After disposal
        disposal_service._is_disposed = True
        status = disposal_service.get_resource_status()
        assert status['is_disposed'] is True
    
    def test_get_resource_status_partial(self):
        """Test resource status with partial resources."""
        mock_session = Mock(spec=SessionManager)
        mock_session.async_metamapper_engine = Mock()
        # No cache engine
        
        service = ResourceDisposalService(
            session_manager=mock_session,
            client_manager=None
        )
        
        status = service.get_resource_status()
        assert status == {
            'metamapper_engine': True,
            'cache_engine': False,
            'client_manager': False,
            'is_disposed': False
        }
    
    async def test_verify_disposal(self, disposal_service):
        """Test verifying disposal."""
        # Before disposal
        assert await disposal_service.verify_disposal() is False
        
        # After disposal
        await disposal_service.dispose_all()
        
        # Remove engines to simulate proper disposal
        disposal_service.session_manager.async_metamapper_engine = None
        disposal_service.session_manager.async_cache_engine = None
        disposal_service.client_manager = None
        
        assert await disposal_service.verify_disposal() is True
    
    async def test_verify_disposal_incomplete(self, disposal_service):
        """Test verifying incomplete disposal."""
        disposal_service._is_disposed = True
        
        # But resources still exist
        assert await disposal_service.verify_disposal() is False
    
    async def test_context_manager(self, mock_session_manager, mock_client_manager):
        """Test using service as async context manager."""
        async with ResourceDisposalService(
            session_manager=mock_session_manager,
            client_manager=mock_client_manager
        ) as service:
            assert service.is_disposed is False
        
        # Should be disposed after exit
        mock_session_manager.async_metamapper_engine.dispose.assert_called_once()
        mock_session_manager.async_cache_engine.dispose.assert_called_once()
        mock_client_manager.clear_cache.assert_called_once()
    
    def test_clear_client_cache_without_manager(self, mock_session_manager):
        """Test clearing client cache when no manager exists."""
        service = ResourceDisposalService(
            session_manager=mock_session_manager,
            client_manager=None
        )
        
        # Should not raise error
        service.clear_client_cache()
    
    async def test_dispose_metamapper_engine_not_exists(self, mock_session_manager):
        """Test disposing metamapper engine when it doesn't exist."""
        mock_session_manager.async_metamapper_engine = None
        
        service = ResourceDisposalService(session_manager=mock_session_manager)
        
        # Should not raise error
        await service.dispose_metamapper_engine()
    
    async def test_dispose_cache_engine_not_exists(self, mock_session_manager):
        """Test disposing cache engine when it doesn't exist."""
        mock_session_manager.async_cache_engine = None
        
        service = ResourceDisposalService(session_manager=mock_session_manager)
        
        # Should not raise error
        await service.dispose_cache_engine()
    
    async def test_dispose_with_slow_engines(self, disposal_service, mock_session_manager):
        """Test disposal with engines that take time to dispose."""
        # Simulate slow disposal
        async def slow_dispose():
            await asyncio.sleep(0.1)
        
        mock_session_manager.async_metamapper_engine.dispose = slow_dispose
        mock_session_manager.async_cache_engine.dispose = slow_dispose
        
        # Should complete without timeout
        await disposal_service.dispose_all()
        assert disposal_service.is_disposed is True
    
    async def test_dispose_on_error_with_context(self, disposal_service):
        """Test emergency disposal with various error types."""
        # Test with different error types
        errors = [
            RuntimeError("Runtime error"),
            ValueError("Value error"),
            Exception("Generic error"),
            KeyboardInterrupt("User interrupt")
        ]
        
        for error in errors:
            disposal_service._is_disposed = False  # Reset state
            await disposal_service.dispose_on_error(error)
            # Should handle all error types gracefully
    
    def test_get_resource_status_after_partial_disposal(self, disposal_service):
        """Test resource status after partial disposal."""
        # Remove only one engine
        disposal_service.session_manager.async_metamapper_engine = None
        
        status = disposal_service.get_resource_status()
        assert status['metamapper_engine'] is False
        assert status['cache_engine'] is True
        assert status['client_manager'] is True
        assert status['is_disposed'] is False
    
    async def test_concurrent_disposal_calls(self, disposal_service):
        """Test multiple concurrent disposal calls."""
        # Create multiple disposal tasks
        tasks = [disposal_service.dispose_all() for _ in range(5)]
        
        # All should complete without error
        await asyncio.gather(*tasks)
        
        # The first call should trigger disposal, others should be skipped
        # Due to concurrent execution, we may see 1-5 calls depending on timing
        assert disposal_service.session_manager.async_metamapper_engine.dispose.call_count >= 1
        assert disposal_service.session_manager.async_cache_engine.dispose.call_count >= 1
        assert disposal_service.is_disposed is True
    
    async def test_dispose_specific_engines_sequence(self, disposal_service, mock_session_manager):
        """Test disposing engines in specific sequence."""
        # Dispose engines individually
        await disposal_service.dispose_metamapper_engine()
        assert mock_session_manager.async_metamapper_engine.dispose.call_count == 1
        assert mock_session_manager.async_cache_engine.dispose.call_count == 0
        
        await disposal_service.dispose_cache_engine()
        assert mock_session_manager.async_cache_engine.dispose.call_count == 1
        
        # Clear client cache
        disposal_service.clear_client_cache()
        assert disposal_service.client_manager.clear_cache.call_count == 1
        
        # Full dispose will dispose engines again since individual disposal
        # doesn't set the global _is_disposed flag
        await disposal_service.dispose_all()
        assert mock_session_manager.async_metamapper_engine.dispose.call_count == 2
        assert mock_session_manager.async_cache_engine.dispose.call_count == 2
        
        # But subsequent calls should be idempotent
        await disposal_service.dispose_all()
        assert mock_session_manager.async_metamapper_engine.dispose.call_count == 2
        assert mock_session_manager.async_cache_engine.dispose.call_count == 2
    
    async def test_context_manager_with_error(self, mock_session_manager, mock_client_manager):
        """Test context manager behavior when error occurs."""
        service = None
        error_raised = False
        
        try:
            async with ResourceDisposalService(
                session_manager=mock_session_manager,
                client_manager=mock_client_manager
            ) as svc:
                service = svc
                # Simulate error in context
                raise ValueError("Test error in context")
        except ValueError:
            error_raised = True
        
        # Should still dispose resources even with error
        assert error_raised
        assert mock_session_manager.async_metamapper_engine.dispose.call_count == 1
        assert mock_session_manager.async_cache_engine.dispose.call_count == 1
    
    async def test_verify_disposal_with_partial_cleanup(self, disposal_service):
        """Test disposal verification with partial cleanup."""
        await disposal_service.dispose_all()
        
        # Simulate partial cleanup - engine removed but client_manager still exists
        disposal_service.session_manager.async_metamapper_engine = None
        disposal_service.session_manager.async_cache_engine = None
        # Keep client_manager
        
        # Should not verify as complete
        assert await disposal_service.verify_disposal() is False
    
    def test_resource_status_with_no_session_manager(self):
        """Test resource status when session manager is None."""
        service = ResourceDisposalService(
            session_manager=None,
            client_manager=Mock()
        )
        
        status = service.get_resource_status()
        assert status == {
            'metamapper_engine': False,
            'cache_engine': False,
            'client_manager': True,
            'is_disposed': False
        }