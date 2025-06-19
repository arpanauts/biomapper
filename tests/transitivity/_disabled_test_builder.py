"""Tests for the transitivity builder module."""

import os
import tempfile
import unittest

from biomapper.cache.manager import CacheManager
from biomapper.transitivity.builder import TransitivityBuilder
from biomapper.db.session import DatabaseManager


class TransitivityBuilderTest(unittest.TestCase):
    """Test suite for the TransitivityBuilder class."""

    def setUp(self):
        """Set up test database."""
        # Create temporary directory for test database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_transitivity.db")
        self.db_url = f"sqlite:///{self.db_path}"

        # Initialize database
        self.db_manager = DatabaseManager(db_url=self.db_url, echo=False)
        self.db_manager.init_db(drop_all=True)

        # Create cache manager
        self.cache_manager = CacheManager(
            default_ttl_days=30,
            confidence_threshold=0.5,
            enable_stats=True,
        )

        # Override database connection to use test database
        self.original_session_scope = self.cache_manager._session_scope

        def test_session_scope():
            """Create test session context manager."""
            return self.db_manager.create_session()

        self.cache_manager._session_scope = test_session_scope

        # Create transitivity builder
        self.builder = TransitivityBuilder(
            cache_manager=self.cache_manager,
            min_confidence=0.5,
            max_chain_length=3,
            confidence_decay=0.9,
        )

    def tearDown(self):
        """Clean up temporary files."""
        # Close database connection
        self.db_manager.close()

        # Remove temporary directory
        self.temp_dir.cleanup()

        # Restore original session scope
        self.cache_manager._session_scope = self.original_session_scope

    def test_build_transitive_mappings(self):
        """Test building transitive mappings."""
        # Add initial mappings to form a transitive chain
        # HMDB -> ChEBI -> PubChem
        self.cache_manager.add_mapping(
            source_id="HMDB0000001",
            source_type="hmdb",
            target_id="CHEBI:16236",
            target_type="chebi",
            confidence=0.95,
            mapping_source="api",
        )

        self.cache_manager.add_mapping(
            source_id="CHEBI:16236",
            source_type="chebi",
            target_id="PUBCHEM.COMPOUND:5793",
            target_type="pubchem.compound",
            confidence=0.9,
            mapping_source="api",
        )

        # Build transitive mappings
        created = self.builder.build_transitive_mappings()

        # Check that one new mapping was created
        self.assertEqual(created, 1)

        # Look up the new transitive mapping
        results = self.cache_manager.lookup(
            source_id="HMDB0000001",
            source_type="hmdb",
            target_type="pubchem.compound",
        )

        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target_id"], "PUBCHEM.COMPOUND:5793")
        self.assertTrue(results[0]["is_derived"])
        self.assertEqual(results[0]["mapping_source"], "derived")

        # Check confidence decay
        expected_confidence = 0.95 * 0.9 * 0.9  # Original confidences * decay
        self.assertAlmostEqual(results[0]["confidence"], expected_confidence, places=5)

        # Check bidirectional mapping was created
        reverse_results = self.cache_manager.lookup(
            source_id="PUBCHEM.COMPOUND:5793",
            source_type="pubchem.compound",
            target_type="hmdb",
        )

        self.assertEqual(len(reverse_results), 1)
        self.assertEqual(reverse_results[0]["target_id"], "HMDB0000001")
        self.assertTrue(reverse_results[0]["is_derived"])

    def test_extended_transitive_mappings(self):
        """Test building extended transitive mappings (length > 2)."""
        # Add initial mappings to form a longer transitive chain
        # HMDB -> ChEBI -> PubChem -> KEGG
        self.cache_manager.add_mapping(
            source_id="HMDB0000002",
            source_type="hmdb",
            target_id="CHEBI:17234",
            target_type="chebi",
            confidence=0.9,
            mapping_source="api",
        )

        self.cache_manager.add_mapping(
            source_id="CHEBI:17234",
            source_type="chebi",
            target_id="PUBCHEM.COMPOUND:5793",
            target_type="pubchem.compound",
            confidence=0.9,
            mapping_source="api",
        )

        self.cache_manager.add_mapping(
            source_id="PUBCHEM.COMPOUND:5793",
            source_type="pubchem.compound",
            target_id="KEGG:C00031",
            target_type="kegg",
            confidence=0.9,
            mapping_source="api",
        )

        # Build standard transitive mappings first
        self.builder.build_transitive_mappings()

        # Build extended transitive mappings
        created = self.builder.build_extended_transitive_mappings()

        # Check that at least one new mapping was created
        self.assertGreaterEqual(created, 1)

        # Look up the new long-chain transitive mapping (HMDB -> KEGG)
        results = self.cache_manager.lookup(
            source_id="HMDB0000002",
            source_type="hmdb",
            target_type="kegg",
        )

        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target_id"], "KEGG:C00031")
        self.assertTrue(results[0]["is_derived"])

        # Verify the confidence decay over the longer chain
        expected_confidence = (
            0.9 * 0.9 * 0.9 * (0.9**2)
        )  # Original confidences * decay^2
        self.assertLess(
            results[0]["confidence"], 0.9
        )  # Should be lower than direct mappings

    def test_confidence_threshold(self):
        """Test confidence threshold prevents low-confidence derivations."""
        # Create a chain but with low confidence
        self.cache_manager.add_mapping(
            source_id="HMDB0000003",
            source_type="hmdb",
            target_id="CHEBI:12345",
            target_type="chebi",
            confidence=0.6,  # Higher than threshold
            mapping_source="api",
        )

        self.cache_manager.add_mapping(
            source_id="CHEBI:12345",
            source_type="chebi",
            target_id="PUBCHEM.COMPOUND:12345",
            target_type="pubchem.compound",
            confidence=0.3,  # Lower than threshold
            mapping_source="api",
        )

        # Set higher threshold for this test
        self.builder.min_confidence = 0.5

        # Build transitive mappings
        created = self.builder.build_transitive_mappings()

        # Check that no new mapping was created due to confidence threshold
        self.assertEqual(created, 0)

        # Look up to verify no mapping exists
        results = self.cache_manager.lookup(
            source_id="HMDB0000003",
            source_type="hmdb",
            target_type="pubchem.compound",
            min_confidence=0.0,  # Set low to ensure we'd see it if it existed
        )

        # Check no results
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
