"""Database session management and connection utilities."""

import os
from pathlib import Path
import logging
from typing import Any, Optional, AsyncGenerator
import asyncio

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine

from .models import Base

# Configure logging
logger = logging.getLogger(__name__)


# SQLite pragmas for performance optimization
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Set SQLite pragmas for performance optimization."""
    cursor = dbapi_connection.cursor()
    cursor.execute(
        "PRAGMA journal_mode=WAL"
    )  # Write-Ahead Logging for better concurrency
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
        echo: bool = False,
    ) -> None:
        """Initialize the database manager.

        Args:
            db_url: SQLAlchemy database URL
            data_dir: Directory for storing database files
            echo: Whether to echo SQL statements
        """
        if not db_url:
            # Check if a specific database path is provided
            db_path = os.environ.get("BIOMAPPER_DB_PATH")

            if db_path:
                db_url = f"sqlite:///{db_path}"
                logger.info(f"Using environment-specified SQLite database at {db_path}")
            else:
                # Default to a SQLite database in the user's home directory
                if not data_dir:
                    data_dir = os.environ.get(
                        "BIOMAPPER_DATA_DIR",
                        os.path.join(str(Path.home()), ".biomapper", "data"),
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

        # Create async engine (for sqlite, just use the same URL but with aiosqlite)
        async_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        self.async_engine = create_async_engine(async_url, echo=echo)
        # In SQLAlchemy 1.4, we don't have async_sessionmaker, so we'll create a custom async session
        self._async_session_factory = sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    def create_session(self) -> Session:
        """Create a new database session.

        Returns:
            SQLAlchemy session
        """
        return self.SessionFactory()

    async def create_async_session(self) -> AsyncSession:
        """Create a new async database session.

        Returns:
            SQLAlchemy async session
        """
        return self._async_session_factory()

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
        self.async_engine.dispose()


# Default database manager
_default_manager: Optional[DatabaseManager] = None


def get_db_manager(
    db_url: Optional[str] = None, data_dir: Optional[str] = None, echo: bool = False
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

    # If BIOMAPPER_DB_PATH is set, always use that
    db_path = os.environ.get("BIOMAPPER_DB_PATH")
    if db_path and os.path.exists(db_path) and not db_url:
        db_url = f"sqlite:///{db_path}"
        logger.info(f"Using explicitly specified database path: {db_path}")

    if _default_manager is None:
        _default_manager = DatabaseManager(db_url, data_dir, echo)
    # If DB path changed, recreate the manager
    elif db_path and _default_manager.db_url != f"sqlite:///{db_path}":
        logger.info(
            f"Database path changed, recreating manager. Old: {_default_manager.db_url}, New: sqlite:///{db_path}"
        )
        _default_manager.close()
        _default_manager = DatabaseManager(db_url, data_dir, echo)

    return _default_manager


def init_db_manager():
    """Create and initialize a new database manager explicitly using the current database path."""
    global _default_manager

    # Clear the existing manager
    if _default_manager is not None:
        _default_manager.close()
        _default_manager = None

    # Get the current database path from environment
    db_path = os.environ.get("BIOMAPPER_DB_PATH")

    if db_path and os.path.exists(db_path):
        logger.info(f"Reinitializing database manager with path: {db_path}")
        _default_manager = DatabaseManager(f"sqlite:///{db_path}", echo=True)
    else:
        logger.error(
            f"Cannot initialize DB manager: {db_path} does not exist or is not set"
        )

    return _default_manager


def get_session() -> Session:
    """Get a new database session using the default manager.

    Returns:
        SQLAlchemy session
    """
    return get_db_manager().create_session()


async def get_async_session() -> AsyncSession:
    """Get a new async database session using the default manager.

    Returns:
        SQLAlchemy async session
    """
    return await get_db_manager().create_async_session()


# Async engine for direct use
async_engine = get_db_manager().async_engine


# Function to create async session
async def async_session_maker() -> AsyncSession:
    """Create a new async session.

    Returns:
        SQLAlchemy async session
    """
    return await get_async_session()
