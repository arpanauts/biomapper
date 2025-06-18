"""Alembic migration environment script."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

# Import SQLAlchemy models for the mapping cache
from biomapper.db.cache_models import Base
# Import centralized settings
from biomapper.config import settings

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Target metadata for schema management
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    # Use the cache_db_url from settings
    url = settings.cache_db_url
    
    # Convert async SQLite URL to sync for Alembic
    if url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite+aiosqlite://", "sqlite:///")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Use the cache_db_url from settings
    database_url = settings.cache_db_url
    
    # Convert async SQLite URL to sync for Alembic
    if database_url.startswith("sqlite+aiosqlite://"):
        database_url = database_url.replace("sqlite+aiosqlite://", "sqlite:///")

    # Create the engine
    connectable = create_engine(database_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Enable batch mode for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
