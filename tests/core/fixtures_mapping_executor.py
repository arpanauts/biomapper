"""Shared fixtures for mapping executor tests."""
import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool
from biomapper.db.models import Base as MetamapperBase


@pytest.fixture(scope="function")
async def async_metamapper_engine():
    """Provides an async SQLAlchemy engine for an in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", 
        echo=False,
        poolclass=StaticPool,  # Use StaticPool for in-memory databases
        connect_args={
            "check_same_thread": False,
            "timeout": 5.0
        }
    )
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(MetamapperBase.metadata.create_all)
        yield engine
    finally:
        # Ensure cleanup happens even on failure
        await engine.dispose()


@pytest.fixture
async def async_metamapper_session_factory(async_metamapper_engine):
    """Creates an async session factory for the in-memory metamapper DB."""
    factory = async_sessionmaker(
        bind=async_metamapper_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    yield factory