"""Test utilities for cache database setup."""

from biomapper.db.cache_models import Base as CacheBase

async def init_cache_tables_async(engine):
    """Initialize cache database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(CacheBase.metadata.create_all)

def init_cache_tables_sync(engine):
    """Initialize cache database tables synchronously."""
    CacheBase.metadata.create_all(engine)