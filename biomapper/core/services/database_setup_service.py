"""
DatabaseSetupService for handling database schema initialization.

This service is responsible for creating database tables and ensuring proper
schema setup, providing a clean separation between application runtime and 
database management/setup tasks.
"""

import logging
from typing import Any

from ..exceptions import BiomapperError, ErrorCode


class DatabaseSetupService:
    """Service responsible for database schema initialization and setup.
    
    This service handles the creation of database tables and schema validation,
    ensuring that the required database structure is in place before the
    application begins its core operations.
    
    Responsibilities:
    - Connect to databases using provided engines
    - Check if required tables already exist
    - Create all tables defined in SQLAlchemy Base metadata objects
    - Handle database setup errors gracefully
    """
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the DatabaseSetupService.
        
        Args:
            logger: Logger instance for database setup operations
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def initialize_tables(self, engine: Any, base_metadata: Any) -> None:
        """Initialize database tables if they don't exist.
        
        This method checks if the required tables exist in the database and
        creates them if they don't. It uses a representative table check to
        determine if the schema is already initialized.
        
        Args:
            engine: SQLAlchemy async engine to use for database operations
            base_metadata: The metadata object containing table definitions
            
        Raises:
            BiomapperError: If database initialization fails
        """
        try:
            # Check if the tables already exist
            async with engine.connect() as conn:
                # Check if mapping_sessions table exists as a representative
                has_tables = await conn.run_sync(
                    lambda sync_conn: sync_conn.dialect.has_table(
                        sync_conn, "mapping_sessions"
                    )
                )
                
                if has_tables:
                    self.logger.info(
                        f"Tables already exist in database {engine.url}, skipping initialization."
                    )
                    return
                
                # Tables don't exist, create them
                self.logger.info(
                    f"Tables don't exist in database {engine.url}, creating them..."
                )
            
            # Create tables
            async with engine.begin() as conn:
                await conn.run_sync(base_metadata.create_all)
            
            self.logger.info(
                f"Database tables for {engine.url} initialized successfully."
            )
            
        except Exception as e:
            self.logger.error(
                f"Error initializing database tables for {engine.url}: {str(e)}", 
                exc_info=True
            )
            raise BiomapperError(
                f"Failed to initialize database tables: {str(e)}",
                error_code=ErrorCode.DATABASE_INITIALIZATION_ERROR,
                details={"engine_url": str(engine.url)}
            ) from e
