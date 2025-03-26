"""Database session management and connection utilities."""

import os
from pathlib import Path
import logging
from typing import Any, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

# SQLite pragmas for performance optimization
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Set SQLite pragmas for performance optimization."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balanced durability and performance
    cursor.execute("PRAGMA foreign_keys=ON")  # Enforce foreign key constraints
    cursor.execute("PRAGMA cache_size=-64000")  # Use ~64MB of memory for caching
    cursor.close()


class DatabaseManager:
    """Database connection manager for the mapping cache."""

    def __init__(
        self, 
        db_url: Optional[str] = None,
        data_dir: Optional[str] = None,
        echo: bool = False
    ) -> None:
        """Initialize the database manager.
        
        Args:
            db_url: SQLAlchemy database URL
            data_dir: Directory for storing database files
            echo: Whether to echo SQL statements
        """
        if not db_url:
            # Default to a SQLite database in the user's home directory
            if not data_dir:
                data_dir = os.environ.get(
                    "BIOMAPPER_DATA_DIR", 
                    os.path.join(str(Path.home()), ".biomapper", "data")
                )
            
            # Create directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)
            
            # Construct SQLite URL
            db_path = os.path.join(data_dir, "mapping_cache.db")
            db_url = f"sqlite:///{db_path}"
            logger.info(f"Using SQLite database at {db_path}")
        
        # Create engine with specified URL
        self.engine = create_engine(db_url, echo=echo)
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.db_url = db_url
    
    def create_session(self) -> Session:
        """Create a new database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionFactory()
    
    def init_db(self, drop_all: bool = False) -> None:
        """Initialize the database schema.
        
        Args:
            drop_all: Whether to drop all tables before creation
        """
        if drop_all:
            logger.warning("Dropping all tables from the database")
            Base.metadata.drop_all(self.engine)
        
        logger.info("Creating database tables")
        Base.metadata.create_all(self.engine)
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()


# Default database manager
_default_manager: Optional[DatabaseManager] = None


def get_db_manager(
    db_url: Optional[str] = None,
    data_dir: Optional[str] = None,
    echo: bool = False
) -> DatabaseManager:
    """Get the default database manager instance.
    
    Args:
        db_url: SQLAlchemy database URL
        data_dir: Directory for storing database files
        echo: Whether to echo SQL statements
        
    Returns:
        Database manager instance
    """
    global _default_manager
    
    if _default_manager is None:
        _default_manager = DatabaseManager(db_url, data_dir, echo)
    
    return _default_manager


def get_session() -> Session:
    """Get a new database session using the default manager.
    
    Returns:
        SQLAlchemy session
    """
    return get_db_manager().create_session()
