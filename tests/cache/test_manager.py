"""Tests for the mapping cache manager."""

import datetime
import os
import tempfile
import unittest
from pathlib import Path

from biomapper.cache.manager import CacheManager
from biomapper.db.models import CacheStats, EntityTypeConfig
from biomapper.db.cache_models import EntityMapping, MappingMetadata
from biomapper.db.session import DatabaseManager
from tests.utils.test_db_manager import TestDatabaseManager


class CacheManagerTest(unittest.TestCase):
    """Test suite for the CacheManager class."""

    def setUp(self):
        """Set up test database."""
        # Create temporary directory for test database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_cache.db")
        self.db_url = f"sqlite:///{self.db_path}"

        # Initialize database with test manager that creates cache tables
        self.db_manager = TestDatabaseManager(db_url=self.db_url, echo=False)
        self.db_manager.init_db(drop_all=True)

        # Create cache manager
        self.cache_manager = CacheManager(
            default_ttl_days=30,
            confidence_threshold=0.7,
            enable_stats=True,
        )

        # Override database connection to use test database
        # This is a bit of a hack since we're accessing a protected member
        self.original_session_scope = self.cache_manager._session_scope

        from contextlib import contextmanager
        from sqlalchemy.exc import SQLAlchemyError

        @contextmanager
        def test_session_scope():
            """Create test session context manager."""
            session = self.db_manager.create_session()
            try:
                yield session
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                raise
            finally:
                session.close()

        self.cache_manager._session_scope = test_session_scope

    def tearDown(self):
        """Clean up temporary files."""
        # Close database connection
        self.db_manager.close()

        # Remove temporary directory
        self.temp_dir.cleanup()

        # Restore original session scope
        self.cache_manager._session_scope = self.original_session_scope

    def test_add_mapping(self):
        """Test adding a mapping to the cache."""
        # Add mapping
        result = self.cache_manager.add_mapping(
            source_id="HMDB0000001",
            source_type="hmdb",
            target_id="CHEBI:16236",
            target_type="chebi",
            confidence=0.95,
            mapping_source="test",
        )

        # Check result
        self.assertEqual(result["source_id"], "HMDB0000001")
        self.assertEqual(result["target_id"], "CHEBI:16236")
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["mapping_source"], "test")
        self.assertFalse(result["is_derived"])

        # Check bidirectional mapping was created
        session = self.db_manager.create_session()
        mappings = session.query(EntityMapping).all()
        session.close()

        self.assertEqual(len(mappings), 2)

        # Check forward mapping
        forward = next(m for m in mappings if m.source_type == "hmdb")
        self.assertEqual(forward.source_id, "HMDB0000001")
        self.assertEqual(forward.target_id, "CHEBI:16236")

        # Check reverse mapping
        reverse = next(m for m in mappings if m.source_type == "chebi")
        self.assertEqual(reverse.source_id, "CHEBI:16236")
        self.assertEqual(reverse.target_id, "HMDB0000001")

    def test_add_mapping_with_metadata(self):
        """Test adding a mapping with metadata."""
        # Add mapping
        result = self.cache_manager.add_mapping(
            source_id="HMDB0000002",
            source_type="hmdb",
            target_id="PUBCHEM.COMPOUND:5793",
            target_type="pubchem.compound",
            confidence=0.9,
            mapping_source="test",
            metadata={
                "compound_name": "Glucose",
                "molecular_weight": "180.16",
                "formula": "C6H12O6",
            },
        )

        # Check result
        self.assertEqual(result["source_id"], "HMDB0000002")
        self.assertEqual(result["metadata"]["compound_name"], "Glucose")

        # Check metadata was stored
        session = self.db_manager.create_session()
        mapping = (
            session.query(EntityMapping)
            .filter(EntityMapping.source_id == "HMDB0000002")
            .first()
        )

        metadata = (
            session.query(MappingMetadata)
            .filter(MappingMetadata.mapping_id == mapping.id)
            .all()
        )

        session.close()

        self.assertEqual(len(metadata), 3)
        metadata_dict = {m.key: m.value for m in metadata}
        self.assertEqual(metadata_dict["compound_name"], "Glucose")
        self.assertEqual(metadata_dict["molecular_weight"], "180.16")
        self.assertEqual(metadata_dict["formula"], "C6H12O6")

    def test_lookup(self):
        """Test looking up mappings."""
        # Add mappings
        self.cache_manager.add_mapping(
            source_id="CHEBI:17234",
            source_type="chebi",
            target_id="PUBCHEM.COMPOUND:5793",
            target_type="pubchem.compound",
            confidence=0.95,
            mapping_source="api",
        )

        self.cache_manager.add_mapping(
            source_id="CHEBI:17234",
            source_type="chebi",
            target_id="HMDB0000001",
            target_type="hmdb",
            confidence=0.85,
            mapping_source="api",
        )

        # Look up mappings
        results = self.cache_manager.lookup(
            source_id="CHEBI:17234",
            source_type="chebi",
        )

        # Check results
        self.assertEqual(len(results), 2)

        # Check stats were updated
        session = self.db_manager.create_session()
        stats = session.query(CacheStats).first()
        session.close()

        self.assertIsNotNone(stats)
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 0)

    def test_bidirectional_lookup(self):
        """Test bidirectional lookup."""
        # Add mapping
        self.cache_manager.add_mapping(
            source_id="HMDB0000001",
            source_type="hmdb",
            target_id="CHEBI:16236",
            target_type="chebi",
            confidence=0.95,
            mapping_source="test",
        )

        # Look up forward
        forward = self.cache_manager.lookup(
            source_id="HMDB0000001",
            source_type="hmdb",
        )

        # Look up reverse
        reverse = self.cache_manager.lookup(
            source_id="CHEBI:16236",
            source_type="chebi",
        )

        # Check results
        self.assertEqual(len(forward), 1)
        self.assertEqual(len(reverse), 1)
        self.assertEqual(forward[0]["target_id"], "CHEBI:16236")
        self.assertEqual(reverse[0]["target_id"], "HMDB0000001")

        # Test bidirectional lookup
        bi_results = self.cache_manager.bidirectional_lookup(
            entity_id="HMDB0000001",
            entity_type="hmdb",
        )

        self.assertEqual(len(bi_results), 2)

    def test_cache_stats(self):
        """Test cache statistics."""
        # Create some activity
        self.cache_manager.lookup(
            source_id="missing",
            source_type="test",
        )

        self.cache_manager.add_mapping(
            source_id="HMDB0000001",
            source_type="hmdb",
            target_id="CHEBI:16236",
            target_type="chebi",
            confidence=0.95,
            mapping_source="test",
        )

        self.cache_manager.lookup(
            source_id="HMDB0000001",
            source_type="hmdb",
        )

        # Get stats
        stats = self.cache_manager.get_cache_stats()

        # Check stats
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["hits"], 1)
        self.assertEqual(stats[0]["misses"], 1)
        self.assertEqual(stats[0]["hit_ratio"], 0.5)

    def test_delete_expired_mappings(self):
        """Test deleting expired mappings."""
        # Add mapping with short TTL
        session = self.db_manager.create_session()

        mapping = EntityMapping(
            source_id="test1",
            source_type="test",
            target_id="test2",
            target_type="test",
            confidence=1.0,
            mapping_source="test",
            last_updated=datetime.datetime.utcnow(),
            # Set expiration in the past
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
        )

        session.add(mapping)
        session.commit()
        session.close()

        # Delete expired mappings
        deleted = self.cache_manager.delete_expired_mappings()

        # Check result
        self.assertEqual(deleted, 1)

        # Verify mapping was deleted
        session = self.db_manager.create_session()
        count = session.query(EntityMapping).count()
        session.close()

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
