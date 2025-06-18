"""Test database manager that handles both metamapper and cache tables."""

import logging
from typing import Optional

from biomapper.db.session import DatabaseManager
from biomapper.db.models import Base as MetamapperBase
from biomapper.db.cache_models import Base as CacheBase

logger = logging.getLogger(__name__)


class TestDatabaseManager(DatabaseManager):
    """Extended DatabaseManager for tests that creates both metamapper and cache tables."""
    
    def init_db(self, drop_all: bool = False) -> None:
        """Initialize both metamapper and cache database schemas.
        
        Args:
            drop_all: Whether to drop all tables before creation
        """
        if drop_all:
            logger.warning("Dropping all tables from the database")
            MetamapperBase.metadata.drop_all(self.engine)
            CacheBase.metadata.drop_all(self.engine)
        
        logger.info("Creating database tables")
        # Create metamapper tables
        MetamapperBase.metadata.create_all(self.engine)
        # Create cache tables (including entity_mappings)
        CacheBase.metadata.create_all(self.engine)
        logger.info("Created both metamapper and cache tables")
    
    async def init_db_async(self, drop_all: bool = False) -> None:
        """Initialize both metamapper and cache database schemas asynchronously.
        
        Args:
            drop_all: Whether to drop all tables before creation
        """
        logger.info(f"Initializing database schemas asynchronously (drop_all={drop_all})")
        async with self.async_engine.begin() as conn:
            if drop_all:
                logger.warning("Dropping all tables from the database")
                await conn.run_sync(MetamapperBase.metadata.drop_all)
                await conn.run_sync(CacheBase.metadata.drop_all)
            
            logger.info("Creating database tables")
            # Create metamapper tables
            await conn.run_sync(MetamapperBase.metadata.create_all)
            # Create cache tables (including entity_mappings)
            await conn.run_sync(CacheBase.metadata.create_all)
        
        logger.info("Asynchronous database schema initialization completed")