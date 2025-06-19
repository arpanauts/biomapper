"""Unit tests for SessionManager module."""
import logging
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.engine_components.session_manager import SessionManager


class TestSessionManager:
    """Test cases for the SessionManager class."""
    
    @patch('biomapper.core.engine_components.session_manager.sessionmaker')
    @patch('biomapper.core.engine_components.session_manager.create_async_engine')
    def test_initialization(self, mock_create_engine, mock_sessionmaker):
        """Test SessionManager initialization."""
        # Arrange
        metamapper_url = "sqlite:///test_metamapper.db"
        cache_url = "sqlite:///test_cache.db"
        echo_sql = True
        
        # Create mock engines
        mock_meta_engine = Mock()
        mock_cache_engine = Mock()
        mock_create_engine.side_effect = [mock_meta_engine, mock_cache_engine]
        
        # Create mock session factories
        mock_meta_factory = Mock()
        mock_cache_factory = Mock()
        mock_sessionmaker.side_effect = [mock_meta_factory, mock_cache_factory]
        
        # Act
        with patch.object(SessionManager, '_ensure_db_directories'):
            manager = SessionManager(
                metamapper_db_url=metamapper_url,
                mapping_cache_db_url=cache_url,
                echo_sql=echo_sql
            )
        
        # Assert
        assert manager.metamapper_db_url == metamapper_url
        assert manager.mapping_cache_db_url == cache_url
        assert manager.echo_sql == echo_sql
        
        # Verify create_async_engine was called twice with correct async URLs
        expected_calls = [
            call("sqlite+aiosqlite:///test_metamapper.db", echo=True),
            call("sqlite+aiosqlite:///test_cache.db", echo=True)
        ]
        mock_create_engine.assert_has_calls(expected_calls)
        
        # Verify sessionmaker was called twice with correct parameters
        expected_session_calls = [
            call(mock_meta_engine, class_=AsyncSession, expire_on_commit=False),
            call(mock_cache_engine, class_=AsyncSession, expire_on_commit=False)
        ]
        mock_sessionmaker.assert_has_calls(expected_session_calls)
        
        # Verify the engines and factories are set correctly
        assert manager.async_metamapper_engine == mock_meta_engine
        assert manager.async_cache_engine == mock_cache_engine
        assert manager.MetamapperSessionFactory == mock_meta_factory
        assert manager.CacheSessionFactory == mock_cache_factory
    
    def test_get_async_url_sqlite(self):
        """Test _get_async_url with SQLite URL."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        sqlite_url = "sqlite:///test.db"
        
        # Act
        result = manager._get_async_url(sqlite_url)
        
        # Assert
        assert result == "sqlite+aiosqlite:///test.db"
    
    def test_get_async_url_non_sqlite(self):
        """Test _get_async_url with non-SQLite URL."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        postgres_url = "postgresql+asyncpg://user:pass@localhost/db"
        
        # Act
        result = manager._get_async_url(postgres_url)
        
        # Assert
        assert result == postgres_url
    
    @patch('biomapper.core.engine_components.session_manager.Path')
    def test_ensure_db_directories_sqlite(self, mock_path_class):
        """Test _ensure_db_directories with SQLite URLs."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        manager.metamapper_db_url = "sqlite:///path/to/metamapper.db"
        manager.mapping_cache_db_url = "sqlite:///path/to/cache.db"
        manager.logger = Mock()
        
        # Create mock Path instances
        mock_meta_path = Mock()
        mock_cache_path = Mock()
        mock_meta_parent = Mock()
        mock_cache_parent = Mock()
        
        mock_meta_path.parent = mock_meta_parent
        mock_cache_path.parent = mock_cache_parent
        
        # Set up Path class to return our mocks
        mock_path_class.side_effect = [mock_meta_path, mock_cache_path]
        
        # Act
        manager._ensure_db_directories()
        
        # Assert
        # Verify Path was created for each SQLite URL
        mock_path_class.assert_any_call("path/to/metamapper.db")
        mock_path_class.assert_any_call("path/to/cache.db")
        
        # Verify mkdir was called on each parent directory
        mock_meta_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_cache_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('biomapper.core.engine_components.session_manager.Path')
    def test_ensure_db_directories_non_sqlite(self, mock_path_class):
        """Test _ensure_db_directories with non-SQLite URLs."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        manager.metamapper_db_url = "postgresql://localhost/db"
        manager.mapping_cache_db_url = "mysql://localhost/cache"
        manager.logger = Mock()
        
        # Act
        manager._ensure_db_directories()
        
        # Assert
        # Path should not be called for non-SQLite URLs
        mock_path_class.assert_not_called()
    
    @patch('biomapper.core.engine_components.session_manager.sessionmaker')
    @patch('biomapper.core.engine_components.session_manager.create_async_engine')
    def test_get_async_metamapper_session(self, mock_create_engine, mock_sessionmaker):
        """Test get_async_metamapper_session method."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)
        mock_factory = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_factory
        
        with patch.object(SessionManager, '_ensure_db_directories'):
            manager = SessionManager(
                metamapper_db_url="sqlite:///test.db",
                mapping_cache_db_url="sqlite:///cache.db"
            )
            manager.MetamapperSessionFactory = mock_factory
        
        # Act
        result = manager.get_async_metamapper_session()
        
        # Assert
        assert result == mock_session
        mock_factory.assert_called_once_with()
    
    @patch('biomapper.core.engine_components.session_manager.sessionmaker')
    @patch('biomapper.core.engine_components.session_manager.create_async_engine')
    def test_get_async_cache_session(self, mock_create_engine, mock_sessionmaker):
        """Test get_async_cache_session method."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)
        mock_factory = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_factory
        
        with patch.object(SessionManager, '_ensure_db_directories'):
            manager = SessionManager(
                metamapper_db_url="sqlite:///test.db",
                mapping_cache_db_url="sqlite:///cache.db"
            )
            manager.CacheSessionFactory = mock_factory
        
        # Act
        result = manager.get_async_cache_session()
        
        # Assert
        assert result == mock_session
        mock_factory.assert_called_once_with()
    
    @patch('biomapper.core.engine_components.session_manager.sessionmaker')
    @patch('biomapper.core.engine_components.session_manager.create_async_engine')
    def test_async_metamapper_session_property(self, mock_create_engine, mock_sessionmaker):
        """Test async_metamapper_session compatibility property."""
        # Arrange
        mock_factory = Mock()
        mock_sessionmaker.return_value = mock_factory
        
        with patch.object(SessionManager, '_ensure_db_directories'):
            manager = SessionManager(
                metamapper_db_url="sqlite:///test.db",
                mapping_cache_db_url="sqlite:///cache.db"
            )
            manager.MetamapperSessionFactory = mock_factory
        
        # Act
        result = manager.async_metamapper_session
        
        # Assert
        assert result == mock_factory
    
    @patch('biomapper.core.engine_components.session_manager.sessionmaker')
    @patch('biomapper.core.engine_components.session_manager.create_async_engine')
    def test_async_cache_session_property(self, mock_create_engine, mock_sessionmaker):
        """Test async_cache_session compatibility property."""
        # Arrange
        mock_factory = Mock()
        mock_sessionmaker.return_value = mock_factory
        
        with patch.object(SessionManager, '_ensure_db_directories'):
            manager = SessionManager(
                metamapper_db_url="sqlite:///test.db",
                mapping_cache_db_url="sqlite:///cache.db"
            )
            manager.CacheSessionFactory = mock_factory
        
        # Act
        result = manager.async_cache_session
        
        # Assert
        assert result == mock_factory
    
    @patch('biomapper.core.engine_components.session_manager.Path')
    def test_ensure_db_directories_error_handling(self, mock_path_class):
        """Test _ensure_db_directories error handling."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        manager.metamapper_db_url = "sqlite:///test.db"
        manager.mapping_cache_db_url = "sqlite:///cache.db"
        manager.logger = Mock()
        
        # Make Path raise an exception
        mock_path_class.side_effect = Exception("Test error")
        
        # Act
        manager._ensure_db_directories()
        
        # Assert
        # Verify error was logged
        assert manager.logger.error.call_count == 2
        error_calls = manager.logger.error.call_args_list
        # Check that the error messages contain the DB URLs
        assert "sqlite:///test.db" in str(error_calls[0])
        assert "sqlite:///cache.db" in str(error_calls[1])
    
    @patch('biomapper.core.engine_components.session_manager.Path')
    def test_ensure_db_directories_malformed_url(self, mock_path_class):
        """Test _ensure_db_directories with malformed SQLite URL."""
        # Arrange
        manager = SessionManager.__new__(SessionManager)
        manager.metamapper_db_url = "sqlite:test.db"  # Missing ///
        manager.mapping_cache_db_url = "sqlite:///cache.db"
        manager.logger = Mock()
        
        # Act
        manager._ensure_db_directories()
        
        # Assert
        # Verify error was logged for malformed URL
        assert manager.logger.error.call_count >= 1
        # Check that at least one error message is about parsing the malformed URL
        error_calls = [str(call) for call in manager.logger.error.call_args_list]
        assert any("Could not parse file path from SQLite URL: sqlite:test.db" in call for call in error_calls)