"""Session management module for handling database connections and sessions."""
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


class SessionManager:
    """Manages database sessions and connections for biomapper.
    
    This class centralizes all database session creation and management logic,
    providing a clean interface for obtaining database sessions while keeping
    the database connection details encapsulated.
    """
    
    def __init__(
        self,
        metamapper_db_url: str,
        mapping_cache_db_url: str,
        echo_sql: bool = False
    ):
        """Initialize the SessionManager with database configurations.
        
        Args:
            metamapper_db_url: URL for the metamapper database
            mapping_cache_db_url: URL for the mapping cache database
            echo_sql: Whether to echo SQL statements for debugging
        """
        self.logger = logging.getLogger(__name__)
        self.metamapper_db_url = metamapper_db_url
        self.mapping_cache_db_url = mapping_cache_db_url
        self.echo_sql = echo_sql
        
        # Log database URLs being used
        self.logger.info(f"SessionManager using Metamapper DB URL: {self.metamapper_db_url}")
        self.logger.info(f"SessionManager using Mapping Cache DB URL: {self.mapping_cache_db_url}")
        
        # Ensure directories for file-based DBs exist
        self._ensure_db_directories()
        
        # Setup SQLAlchemy engines and sessions for Metamapper
        meta_async_url = self._get_async_url(self.metamapper_db_url)
        self.async_metamapper_engine = create_async_engine(meta_async_url, echo=self.echo_sql)
        self.MetamapperSessionFactory = sessionmaker(
            self.async_metamapper_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Setup SQLAlchemy engines and sessions for Mapping Cache
        cache_async_url = self._get_async_url(self.mapping_cache_db_url)
        self.async_cache_engine = create_async_engine(cache_async_url, echo=self.echo_sql)
        self.CacheSessionFactory = sessionmaker(
            self.async_cache_engine, class_=AsyncSession, expire_on_commit=False
        )
    
    def _get_async_url(self, db_url: str) -> str:
        """Convert SQLite URL to async-compatible URL if needed.
        
        Args:
            db_url: The database URL to convert
            
        Returns:
            The async-compatible database URL
        """
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return db_url
    
    def _ensure_db_directories(self):
        """Ensure directories exist for file-based databases."""
        for db_url in [self.metamapper_db_url, self.mapping_cache_db_url]:
            if db_url.startswith("sqlite"):
                try:
                    # Extract path after '///'
                    db_path_str = db_url.split(":///", 1)[1]
                    db_path = Path(db_path_str)
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Ensured directory exists: {db_path.parent}")
                except IndexError:
                    self.logger.error(f"Could not parse file path from SQLite URL: {db_url}")
                except Exception as e:
                    self.logger.error(f"Error ensuring directory for {db_url}: {e}")
    
    def get_async_metamapper_session(self) -> AsyncSession:
        """Get an async session for the metamapper database.
        
        Returns:
            An AsyncSession instance for the metamapper database
        """
        return self.MetamapperSessionFactory()
    
    def get_async_cache_session(self) -> AsyncSession:
        """Get an async session for the cache database.
        
        Returns:
            An AsyncSession instance for the cache database
        """
        return self.CacheSessionFactory()
    
    # Convenience properties for backward compatibility
    @property
    def async_metamapper_session(self):
        """Property for backward compatibility with existing code."""
        return self.MetamapperSessionFactory
    
    @property
    def async_cache_session(self):
        """Property for backward compatibility with existing code."""
        return self.CacheSessionFactory