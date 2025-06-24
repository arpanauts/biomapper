"""Tests for cache-related functionality."""
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.exc import SQLAlchemyError
from biomapper.core.engine_components.cache_manager import CacheManager
from biomapper.core.exceptions import CacheRetrievalError, CacheError, CacheStorageError


@pytest.mark.asyncio
async def test_check_cache_sqlalchemy_error():
    """Test that cache operations handle SQLAlchemy errors properly through CacheManager."""
    # Create a mock cache sessionmaker
    mock_cache_sessionmaker = MagicMock()
    mock_cache_session = AsyncMock()
    
    # Configure the session to raise SQLAlchemyError
    mock_cache_session.execute.side_effect = SQLAlchemyError("Test database error")
    
    # Configure the sessionmaker to return our mock session
    mock_cache_sessionmaker.return_value.__aenter__ = AsyncMock(return_value=mock_cache_session)
    mock_cache_sessionmaker.return_value.__aexit__ = AsyncMock(return_value=False)
    
    # Create CacheManager instance
    logger = logging.getLogger(__name__)
    cache_manager = CacheManager(cache_sessionmaker=mock_cache_sessionmaker, logger=logger)
    
    # Test that cache lookup handles SQLAlchemy errors
    with pytest.raises(CacheRetrievalError) as exc_info:
        await cache_manager.check_cache(["ID1"], "ONT1", "ONT2")
    
    # Verify the error is properly wrapped
    assert isinstance(exc_info.value, CacheRetrievalError)
    assert "cache" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_check_cache_unexpected_error(caplog):
    """Test that cache operations handle unexpected errors properly through CacheManager."""
    # Create a mock cache sessionmaker
    mock_cache_sessionmaker = MagicMock()
    mock_cache_session = AsyncMock()
    
    # Configure the session to raise TypeError (unexpected error)
    mock_cache_session.execute.side_effect = TypeError("Unexpected test error")
    
    # Configure the sessionmaker to return our mock session
    mock_cache_sessionmaker.return_value.__aenter__ = AsyncMock(return_value=mock_cache_session)
    mock_cache_sessionmaker.return_value.__aexit__ = AsyncMock(return_value=False)
    
    # Create CacheManager instance
    logger = logging.getLogger(__name__)
    cache_manager = CacheManager(cache_sessionmaker=mock_cache_sessionmaker, logger=logger)
    
    # Set up logging capture at error level
    caplog.set_level(logging.ERROR)
    
    # Test that cache lookup handles unexpected errors
    with pytest.raises(CacheError) as exc_info:
        await cache_manager.check_cache(["ID1"], "ONT1", "ONT2")
    
    # Verify the error is properly wrapped
    assert isinstance(exc_info.value, CacheError)
    assert "error" in str(exc_info.value).lower() or "cache" in str(exc_info.value).lower()
    
    # Check log contains error message
    assert "error" in caplog.text.lower() or "unexpected" in caplog.text.lower()


@pytest.mark.asyncio
async def test_cache_results_db_error_during_commit():
    """Test cache storage handles commit failures properly through CacheManager."""
    from sqlalchemy.exc import OperationalError
    from unittest.mock import patch
    
    # Create a mock cache sessionmaker and session
    mock_cache_sessionmaker = MagicMock()
    mock_cache_session = AsyncMock()

    # Configure the session operations
    mock_cache_session.add_all = MagicMock()
    # Correctly instantiate OperationalError with None for params, which is safer.
    mock_cache_session.commit = AsyncMock(
        side_effect=OperationalError("Commit failed", None, None)
    )
    mock_cache_session.rollback = AsyncMock()

    # Configure the sessionmaker to return a robust mock async context manager
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_cache_session
    mock_session_context.__aexit__.return_value = False  # Ensure exceptions propagate
    mock_cache_sessionmaker.return_value = mock_session_context
    
    # Create CacheManager instance
    logger = logging.getLogger(__name__)
    cache_manager = CacheManager(cache_sessionmaker=mock_cache_sessionmaker, logger=logger)
    
    # Create mock results
    results = {"TestID": {"target_identifiers": ["TestTarget"], "confidence_score": 0.9}}
    
    # Create a mock path object
    mock_path = MagicMock()
    mock_path.id = 123
    mock_path.name = "TestPath"
    mock_path.steps = []
    
    # Mock the create_path_execution_log to avoid the nested session issue
    mock_log = MagicMock()
    mock_log.id = 1
    mock_log.status = MagicMock()
    mock_log.end_time = None
    
    with patch.object(cache_manager, 'create_path_execution_log', return_value=mock_log) as mock_create_log:
        mock_create_log.return_value = mock_log
        
        # Test that cache storage handles commit failures
        with pytest.raises(CacheStorageError):
            await cache_manager.store_mapping_results(
                results, mock_path, "SourceOnt", "TargetOnt"
            )
    
    # Verify add_all was called but commit raised exception
    mock_cache_session.add_all.assert_called_once()
    mock_cache_session.commit.assert_called_once()