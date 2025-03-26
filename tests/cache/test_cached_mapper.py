"""Tests for the cached mapper module."""

import asyncio
import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional

from biomapper.cache.manager import CacheManager
from biomapper.cache.mapper import CachedMapper
from biomapper.core.base_mapper import BaseMapper, MappingResult
from biomapper.db.session import DatabaseManager
from biomapper.schemas.domain_schema import DomainDocument


class TestDocument(DomainDocument):
    """Test document implementation."""
    
    def __init__(self, id: str = "", type: str = "test") -> None:
        """Initialize test document."""
        self.id = id
        self.type = type
        self.name = ""


class MockMapper(BaseMapper[TestDocument]):
    """Mock mapper for testing."""
    
    def __init__(self, delay: float = 0.0) -> None:
        """Initialize mock mapper.
        
        Args:
            delay: Simulated API delay in seconds
        """
        self.calls = []
        self.delay = delay
    
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Mock implementation that returns a fixed mapping.
        
        Args:
            text: Text to map
            context: Optional mapping context
            
        Returns:
            Mapping result
        """
        if context is None:
            context = {}
        
        self.calls.append((text, context))
        
        # Simulate API delay
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        # Create entity with ID based on input
        entity = TestDocument(id=f"TEST:{text}", type="test")
        entity.name = f"Test {text}"
        
        return MappingResult(
            input_text=text,
            mapped_entity=entity,
            confidence=0.9,
            source="mock_api",
            metadata={"source_text": text}
        )
    
    async def batch_map(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[MappingResult]:
        """Mock batch mapping.
        
        Args:
            texts: Texts to map
            context: Optional mapping context
            
        Returns:
            List of mapping results
        """
        if context is None:
            context = {}
        
        results = []
        for text in texts:
            results.append(await self.map_entity(text, context))
        
        return results


class CachedMapperTest(unittest.TestCase):
    """Test suite for the CachedMapper class."""

    def setUp(self):
        """Set up test database."""
        # Create temporary directory for test database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_mapper_cache.db")
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Initialize database
        self.db_manager = DatabaseManager(db_url=self.db_url, echo=False)
        self.db_manager.init_db(drop_all=True)
        
        # Create cache manager
        self.cache_manager = CacheManager(
            default_ttl_days=30,
            confidence_threshold=0.7,
            enable_stats=True,
        )
        
        # Override database connection to use test database
        self.original_session_scope = self.cache_manager._session_scope
        
        def test_session_scope():
            """Create test session context manager."""
            return self.db_manager.create_session()
        
        self.cache_manager._session_scope = test_session_scope
        
        # Create mock mapper
        self.mock_mapper = MockMapper(delay=0.1)
        
        # Create cached mapper
        self.mapper = CachedMapper(
            base_mapper=self.mock_mapper,
            document_class=TestDocument,
            source_type="test_input",
            target_type="test",
            cache_manager=self.cache_manager,
            ttl_days=30,
            min_confidence=0.7,
            track_api_usage=True,
            use_derived_mappings=True,
        )

    def tearDown(self):
        """Clean up temporary files."""
        # Close database connection
        self.db_manager.close()
        
        # Remove temporary directory
        self.temp_dir.cleanup()
        
        # Restore original session scope
        self.cache_manager._session_scope = self.original_session_scope

    def test_map_entity_cache_miss(self):
        """Test mapping with cache miss."""
        # Run mapping
        result = asyncio.run(self.mapper.map_entity("test_entity1"))
        
        # Check result
        self.assertEqual(result.input_text, "test_entity1")
        self.assertIsNotNone(result.mapped_entity)
        self.assertEqual(result.mapped_entity.id, "TEST:test_entity1")
        self.assertEqual(result.source, "mock_api")
        self.assertFalse(result.metadata.get("cache_hit", False))
        
        # Check that the mock mapper was called
        self.assertEqual(len(self.mock_mapper.calls), 1)
        self.assertEqual(self.mock_mapper.calls[0][0], "test_entity1")

    def test_map_entity_cache_hit(self):
        """Test mapping with cache hit."""
        # First mapping (cache miss)
        result1 = asyncio.run(self.mapper.map_entity("test_entity2"))
        
        # Second mapping of same entity (should be cache hit)
        result2 = asyncio.run(self.mapper.map_entity("test_entity2"))
        
        # Check results
        self.assertEqual(result1.input_text, "test_entity2")
        self.assertEqual(result2.input_text, "test_entity2")
        self.assertFalse(result1.metadata.get("cache_hit", False))
        self.assertTrue(result2.metadata.get("cache_hit", True))
        
        # Check that the mock mapper was called only once
        self.assertEqual(len(self.mock_mapper.calls), 1)

    def test_batch_map_mixed_hits(self):
        """Test batch mapping with mixed cache hits and misses."""
        # First set of mappings (all cache misses)
        batch1 = asyncio.run(
            self.mapper.batch_map(["entity1", "entity2", "entity3"])
        )
        
        # Reset mock calls
        self.mock_mapper.calls = []
        
        # Second set with some duplicates
        batch2 = asyncio.run(
            self.mapper.batch_map(["entity2", "entity3", "entity4"])
        )
        
        # Check results
        self.assertEqual(len(batch1), 3)
        self.assertEqual(len(batch2), 3)
        
        # First batch should all be misses
        for result in batch1:
            self.assertFalse(result.metadata.get("cache_hit", False))
        
        # Second batch should have 2 hits and 1 miss
        hits = sum(1 for r in batch2 if r.metadata.get("cache_hit", False))
        misses = sum(1 for r in batch2 if not r.metadata.get("cache_hit", False))
        self.assertEqual(hits, 2)
        self.assertEqual(misses, 1)
        
        # Check that the mock mapper was called only for the misses
        self.assertEqual(len(self.mock_mapper.calls), 1)
        self.assertEqual(self.mock_mapper.calls[0][0], "entity4")

    def test_skip_cache(self):
        """Test skipping the cache."""
        # First mapping (cache miss)
        result1 = asyncio.run(self.mapper.map_entity("test_entity3"))
        
        # Reset mock calls
        self.mock_mapper.calls = []
        
        # Second mapping with skip_cache=True
        result2 = asyncio.run(
            self.mapper.map_entity("test_entity3", {"skip_cache": True})
        )
        
        # Check that the mock mapper was called again despite cache hit
        self.assertEqual(len(self.mock_mapper.calls), 1)
        self.assertEqual(self.mock_mapper.calls[0][0], "test_entity3")
        self.assertFalse(result2.metadata.get("cache_hit", False))


if __name__ == "__main__":
    unittest.main()
