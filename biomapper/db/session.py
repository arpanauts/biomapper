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

# Import settings
from biomapper.config import settings

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
        echo: bool = False,
    ) -> None:
        """Initialize the database manager.

        Args:
            db_url: SQLAlchemy database URL. If None, uses settings.cache_db_url.
            echo: Whether to echo SQL statements
        """
        if not db_url:
            db_url = settings.cache_db_url
            logger.info(f"Using cache database URL from settings: {db_url}")
        else:
            logger.info(f"Using provided cache database URL: {db_url}")

        # Ensure the directory exists if it's a file-based DB
        if db_url.startswith("sqlite"):
            db_path_str = db_url.split("///")[1]
            # If it's a relative path, resolve it relative to the current working directory
            if not os.path.isabs(db_path_str):
                db_path = Path.cwd() / db_path_str
                logger.info(f"Resolved relative database path: {db_path_str} -> {db_path}")
            else:
                db_path = Path(db_path_str)
            
            # Check if the path exists and is a directory (common error case)
            if db_path.exists() and db_path.is_dir():
                logger.error(f"Database path {db_path} exists but is a directory, not a file!")
                raise ValueError(f"Database path {db_path} is a directory, not a file. Please remove it.")
            
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {db_path.parent.absolute()}")

        # Create engine with specified URL
        # For sync SQLite, remove the async driver prefix if present
        sync_url = db_url
        if db_url.startswith("sqlite+aiosqlite"):
            sync_url = db_url.replace("sqlite+aiosqlite", "sqlite")
        elif not db_url.startswith("sqlite"):
             # Assuming other DB types have compatible sync/async URLs or use different handling
             pass

        self.engine = create_engine(sync_url, echo=echo)
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.db_url = db_url # Store the original (potentially async) URL

        # Create async engine (ensure it has async prefix)
        async_url = db_url
        if db_url.startswith("sqlite:///"):
            async_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        self.async_engine = create_async_engine(async_url, echo=echo)
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

    async def init_db_async(self, drop_all: bool = False) -> None:
        """Initialize the database schema asynchronously.

        Args:
            drop_all: Whether to drop all tables before creation
        """
        logger.info(f"Initializing database schema asynchronously (drop_all={drop_all}) using async_engine.")
        async with self.async_engine.begin() as conn:
            if drop_all:
                logger.warning("Dropping all tables from the database via async_engine.")
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Creating database tables via async_engine.")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Asynchronous database schema initialization completed.")

    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
        self.async_engine.dispose()


# Default database manager
_default_manager: Optional[DatabaseManager] = None


def get_db_manager(
    db_url: Optional[str] = None,
    echo: bool = False,
) -> DatabaseManager:
    """Get the default database manager instance.

    Uses settings.cache_db_url by default.

    Args:
        db_url: SQLAlchemy database URL (overrides settings.cache_db_url if provided)
        echo: Whether to echo SQL statements

    Returns:
        Database manager instance
    """
    global _default_manager

    # Determine the target URL: use provided db_url or fallback to settings
    target_db_url = db_url if db_url is not None else settings.cache_db_url

    # Initialize or re-initialize if needed
    if _default_manager is None:
        logger.info("Initializing default DatabaseManager.")
        _default_manager = DatabaseManager(db_url=target_db_url, echo=echo)
    elif _default_manager.db_url != target_db_url:
        logger.warning(
            f"Target cache DB URL changed, recreating manager. "
            f"Old: {_default_manager.db_url}, New: {target_db_url}"
        )
        _default_manager.close()
        _default_manager = DatabaseManager(db_url=target_db_url, echo=echo)
    # Ensure echo setting is updated if manager exists but echo differs
    elif _default_manager.engine.echo != echo:
         logger.info(f"Updating echo setting for existing manager to {echo}")
         # Recreate engine with new echo setting (simplest way)
         _default_manager.close()
         _default_manager = DatabaseManager(db_url=target_db_url, echo=echo)

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


# Function to create async session
async def async_session_maker() -> AsyncSession:
    """Create a new async session.

    Returns:
        SQLAlchemy async session
    """
    # Ensure the manager uses the latest settings
    manager = get_db_manager(echo=settings.log_level.upper() == "DEBUG")
    return await manager.create_async_session()
