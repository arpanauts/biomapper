"""Tests for known issues registry standards component."""

import pytest
import threading
import time

from pydantic import ValidationError
from src.core.standards.known_issues import KnownIssue, KnownIssuesRegistry


class TestKnownIssue:
    """Test KnownIssue model functionality."""
    
    @pytest.fixture
    def sample_known_issue(self):
        """Create sample known issue for testing."""
        return KnownIssue(
            identifier="Q6EMK4",
            issue_type="matching_failure",
            description="Q6EMK4 from Arivale shows as source_only despite being in KG2c xrefs",
            affected_datasets=["arivale_proteomics", "kg2c_proteins"],
            workaround="Manual mapping: Q6EMK4 -> NCBIGene:114990 (OTUD5)",
            investigation_status="open",
            first_observed="2024-12-14",
            last_verified="2024-12-14",
            example_command="grep Q6EMK4 /tmp/biomapper_results/protein_mapping_results.csv",
            related_files=[
                "biomapper/actions/merge_with_uniprot_resolution.py",
                "investigate_Q6EMK4.py"
            ],
            resolution=None
        )
    
    @pytest.fixture
    def biological_issue_data(self):
        """Create biological issue test data."""
        return {
            "protein_issues": [
                {
                    "identifier": "P99999",
                    "issue_type": "deprecated_accession",
                    "description": "Deprecated UniProt accession causing lookup failures",
                    "affected_datasets": ["uniprot_kb"],
                    "investigation_status": "resolved",
                    "resolution": "Use current accession P12345 instead"
                },
                {
                    "identifier": "OBSOLETE_PROTEIN",
                    "issue_type": "obsolete_entry",
                    "description": "Protein entry removed from database",
                    "affected_datasets": ["legacy_proteomics"],
                    "investigation_status": "won't fix"
                }
            ],
            "metabolite_issues": [
                {
                    "identifier": "HMDB9999999",
                    "issue_type": "invalid_format",
                    "description": "HMDB ID exceeds maximum allowed length",
                    "affected_datasets": ["user_metabolites"],
                    "investigation_status": "investigating"
                }
            ]
        }

    def test_known_issue_creation(self, sample_known_issue):
        """Test basic KnownIssue creation."""
        issue = sample_known_issue
        
        assert issue.identifier == "Q6EMK4"
        assert issue.issue_type == "matching_failure"
        assert issue.investigation_status == "open"
        assert "Arivale shows as source_only" in issue.description
        assert "Manual mapping" in issue.workaround
        assert len(issue.affected_datasets) == 2
        assert len(issue.related_files) == 2

    def test_known_issue_minimal_creation(self):
        """Test KnownIssue creation with minimal required fields."""
        minimal_issue = KnownIssue(
            identifier="TEST123",
            issue_type="test_issue",
            description="Test description",
            affected_datasets=["test_dataset"],
            investigation_status="open",
            first_observed="2024-01-01",
            last_verified="2024-01-01"
        )
        
        assert minimal_issue.identifier == "TEST123"
        assert minimal_issue.workaround is None
        assert minimal_issue.resolution is None
        assert minimal_issue.example_command is None
        assert len(minimal_issue.related_files) == 0

    def test_known_issue_validation_errors(self):
        """Test KnownIssue validation errors."""
        # Test missing required fields
        with pytest.raises(ValidationError):
            KnownIssue()  # Missing all required fields
        
        # Test with missing identifier
        with pytest.raises(ValidationError):
            KnownIssue(
                issue_type="test",
                description="test",
                affected_datasets=["test"],
                investigation_status="open",
                first_observed="2024-01-01",
                last_verified="2024-01-01"
            )

    def test_known_issue_field_types(self):
        """Test KnownIssue field type validation."""
        # Test with proper types
        issue = KnownIssue(
            identifier="TEST123",
            issue_type="validation_test",
            description="Testing field types",
            affected_datasets=["dataset1", "dataset2"],
            investigation_status="open",
            first_observed="2024-01-01",
            last_verified="2024-01-01",
            related_files=["file1.py", "file2.py"]
        )
        
        assert isinstance(issue.affected_datasets, list)
        assert isinstance(issue.related_files, list)
        assert all(isinstance(f, str) for f in issue.related_files)

    def test_known_issue_biological_patterns(self, biological_issue_data):
        """Test KnownIssue with biological data patterns."""
        # Test protein issue
        protein_issue_data = biological_issue_data["protein_issues"][0]
        protein_issue = KnownIssue(
            identifier=protein_issue_data["identifier"],
            issue_type=protein_issue_data["issue_type"],
            description=protein_issue_data["description"],
            affected_datasets=protein_issue_data["affected_datasets"],
            investigation_status=protein_issue_data["investigation_status"],
            first_observed="2024-01-01",
            last_verified="2024-01-15",
            resolution=protein_issue_data["resolution"]
        )
        
        assert protein_issue.identifier == "P99999"
        assert protein_issue.issue_type == "deprecated_accession"
        assert protein_issue.investigation_status == "resolved"
        assert "Use current accession P12345" in protein_issue.resolution
        
        # Test metabolite issue
        metabolite_issue_data = biological_issue_data["metabolite_issues"][0]
        metabolite_issue = KnownIssue(
            identifier=metabolite_issue_data["identifier"],
            issue_type=metabolite_issue_data["issue_type"],
            description=metabolite_issue_data["description"],
            affected_datasets=metabolite_issue_data["affected_datasets"],
            investigation_status=metabolite_issue_data["investigation_status"],
            first_observed="2024-01-01",
            last_verified="2024-01-15"
        )
        
        assert metabolite_issue.identifier == "HMDB9999999"
        assert metabolite_issue.issue_type == "invalid_format"
        assert metabolite_issue.investigation_status == "investigating"


class TestKnownIssuesRegistry:
    """Test KnownIssuesRegistry functionality."""
    
    @pytest.fixture
    def registry_backup(self):
        """Backup and restore registry state for testing."""
        original_issues = KnownIssuesRegistry.ISSUES.copy()
        yield
        KnownIssuesRegistry.ISSUES = original_issues

    def test_registry_check_identifier_existing(self, registry_backup):
        """Test checking existing identifier in registry."""
        # Check existing Q6EMK4 issue
        issue = KnownIssuesRegistry.check_identifier("Q6EMK4")
        
        assert issue is not None
        assert isinstance(issue, KnownIssue)
        assert issue.identifier == "Q6EMK4"
        assert issue.issue_type == "matching_failure"
        assert "Arivale shows as source_only" in issue.description

    def test_registry_check_identifier_nonexistent(self, registry_backup):
        """Test checking non-existent identifier."""
        issue = KnownIssuesRegistry.check_identifier("NONEXISTENT123")
        assert issue is None

    def test_registry_get_workaround_existing(self, registry_backup):
        """Test getting workaround for existing issue."""
        workaround = KnownIssuesRegistry.get_workaround("Q6EMK4")
        
        assert workaround is not None
        assert "Manual mapping" in workaround
        assert "NCBIGene:114990" in workaround
        assert "OTUD5" in workaround

    def test_registry_get_workaround_nonexistent(self, registry_backup):
        """Test getting workaround for non-existent issue."""
        workaround = KnownIssuesRegistry.get_workaround("NONEXISTENT123")
        assert workaround is None

    def test_registry_get_all_open_issues(self, registry_backup):
        """Test getting all open issues."""
        open_issues = KnownIssuesRegistry.get_all_open_issues()
        
        assert isinstance(open_issues, list)
        assert len(open_issues) >= 1  # At least Q6EMK4 should be open
        
        # Verify all returned issues are actually open
        for issue in open_issues:
            assert issue.investigation_status == "open"
        
        # Q6EMK4 should be in open issues
        q6emk4_issue = next((issue for issue in open_issues if issue.identifier == "Q6EMK4"), None)
        assert q6emk4_issue is not None

    def test_registry_add_issue(self, registry_backup):
        """Test adding new issue to registry."""
        new_issue = KnownIssue(
            identifier="TEST_PROTEIN_123",
            issue_type="test_issue",
            description="Test protein issue for unit testing",
            affected_datasets=["test_dataset"],
            workaround="Test workaround procedure",
            investigation_status="open",
            first_observed="2024-01-01",
            last_verified="2024-01-01"
        )
        
        # Add issue
        KnownIssuesRegistry.add_issue("test_protein_issue", new_issue)
        
        # Verify it was added
        retrieved_issue = KnownIssuesRegistry.check_identifier("TEST_PROTEIN_123")
        assert retrieved_issue is not None
        assert retrieved_issue.identifier == "TEST_PROTEIN_123"
        assert retrieved_issue.description == "Test protein issue for unit testing"

    def test_registry_update_status(self, registry_backup):
        """Test updating issue status."""
        # Add test issue first
        test_issue = KnownIssue(
            identifier="UPDATE_TEST_123",
            issue_type="test_issue",
            description="Test issue for status update",
            affected_datasets=["test_dataset"],
            investigation_status="open",
            first_observed="2024-01-01",
            last_verified="2024-01-01"
        )
        KnownIssuesRegistry.add_issue("update_test", test_issue)
        
        # Update status
        success = KnownIssuesRegistry.update_status(
            "UPDATE_TEST_123", 
            "resolved", 
            "Fixed by implementing new validation logic"
        )
        
        assert success is True
        
        # Verify update
        updated_issue = KnownIssuesRegistry.check_identifier("UPDATE_TEST_123")
        assert updated_issue.investigation_status == "resolved"
        assert updated_issue.resolution == "Fixed by implementing new validation logic"

    def test_registry_update_status_nonexistent(self, registry_backup):
        """Test updating status for non-existent issue."""
        success = KnownIssuesRegistry.update_status("NONEXISTENT", "resolved")
        assert success is False

    def test_registry_thread_safety(self, registry_backup):
        """Test KnownIssuesRegistry thread safety."""
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                # Each thread adds and checks issues
                test_issue = KnownIssue(
                    identifier=f"THREAD_TEST_{thread_id}",
                    issue_type="thread_test",
                    description=f"Test issue from thread {thread_id}",
                    affected_datasets=[f"thread_{thread_id}_dataset"],
                    investigation_status="open",
                    first_observed="2024-01-01",
                    last_verified="2024-01-01"
                )
                
                # Add issue
                KnownIssuesRegistry.add_issue(f"thread_test_{thread_id}", test_issue)
                
                # Check if it was added
                retrieved = KnownIssuesRegistry.check_identifier(f"THREAD_TEST_{thread_id}")
                results.append({
                    "thread_id": thread_id,
                    "added": retrieved is not None,
                    "identifier": retrieved.identifier if retrieved else None
                })
                
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify all threads successfully added their issues
        for result in results:
            assert result["added"] is True
            assert f"THREAD_TEST_{result['thread_id']}" == result["identifier"]

    def test_registry_performance(self, registry_backup):
        """Test KnownIssuesRegistry performance with many issues."""
        # Add many issues
        start_time = time.time()
        
        for i in range(1000):
            issue = KnownIssue(
                identifier=f"PERF_TEST_{i:04d}",
                issue_type="performance_test",
                description=f"Performance test issue {i}",
                affected_datasets=[f"perf_dataset_{i}"],
                investigation_status="open" if i % 2 == 0 else "resolved",
                first_observed="2024-01-01",
                last_verified="2024-01-01"
            )
            KnownIssuesRegistry.add_issue(f"perf_test_{i}", issue)
        
        addition_time = time.time() - start_time
        
        # Test lookup performance
        start_time = time.time()
        for i in range(100):
            KnownIssuesRegistry.check_identifier(f"PERF_TEST_{i:04d}")
        lookup_time = time.time() - start_time
        
        # Test getting all open issues performance
        start_time = time.time()
        open_issues = KnownIssuesRegistry.get_all_open_issues()
        filter_time = time.time() - start_time
        
        # Performance assertions
        assert addition_time < 1.0  # Adding 1000 issues should be fast
        assert lookup_time < 0.1    # 100 lookups should be very fast
        assert filter_time < 0.1    # Filtering should be fast
        assert len(open_issues) >= 500  # About half should be open


class TestBiologicalIssuePatterns:
    """Test with realistic biological issue patterns."""
    
    @pytest.fixture
    def registry_backup(self):
        """Backup and restore registry state for testing."""
        original_issues = KnownIssuesRegistry.ISSUES.copy()
        yield
        KnownIssuesRegistry.ISSUES = original_issues
    
    @pytest.fixture
    def protein_mapping_issues(self):
        """Realistic protein mapping issues."""
        return [
            KnownIssue(
                identifier="Q6EMK4",
                issue_type="matching_failure",
                description="Q6EMK4 from Arivale shows as source_only despite being in KG2c xrefs",
                affected_datasets=["arivale_proteomics", "kg2c_proteins"],
                workaround="Manual mapping: Q6EMK4 -> NCBIGene:114990 (OTUD5)",
                investigation_status="open",
                first_observed="2024-12-14",
                last_verified="2024-12-14"
            ),
            KnownIssue(
                identifier="P99999",
                issue_type="deprecated_accession",
                description="Deprecated UniProt accession causing lookup failures",
                affected_datasets=["uniprot_kb", "protein_atlas"],
                workaround="Use current accession P12345",
                investigation_status="resolved",
                first_observed="2024-11-01",
                last_verified="2024-12-01",
                resolution="Updated mapping tables with current accessions"
            ),
            KnownIssue(
                identifier="ISOFORM_P12345-2",
                issue_type="isoform_handling",
                description="Protein isoforms not properly matched to canonical sequences",
                affected_datasets=["ensembl_proteins", "uniprot_isoforms"],
                workaround="Strip isoform suffix before matching",
                investigation_status="investigating",
                first_observed="2024-10-15",
                last_verified="2024-12-10"
            )
        ]
    
    @pytest.fixture
    def metabolite_analysis_issues(self):
        """Realistic metabolite analysis issues."""
        return [
            KnownIssue(
                identifier="HMDB0000001",
                issue_type="semantic_matching_ambiguity",
                description="Multiple semantic matches with similar confidence scores",
                affected_datasets=["user_metabolites", "hmdb_reference"],
                workaround="Use chemical formula as tie-breaker",
                investigation_status="open",
                first_observed="2024-12-01",
                last_verified="2024-12-14"
            ),
            KnownIssue(
                identifier="GLUCOSE_VARIANT",
                issue_type="name_normalization",
                description="Various glucose spellings not recognized as equivalent",
                affected_datasets=["clinical_metabolites", "literature_extracts"],
                workaround="Add glucose synonyms to normalization dictionary",
                investigation_status="resolved",
                first_observed="2024-11-20",
                last_verified="2024-12-05",
                resolution="Extended synonym dictionary with 15 glucose variants"
            )
        ]

    def test_protein_issue_registry_integration(self, protein_mapping_issues, registry_backup):
        """Test protein mapping issues in registry."""
        # Add protein issues to registry
        for i, issue in enumerate(protein_mapping_issues):
            KnownIssuesRegistry.add_issue(f"protein_issue_{i}", issue)
        
        # Test Q6EMK4 edge case
        q6emk4_issue = KnownIssuesRegistry.check_identifier("Q6EMK4")
        assert q6emk4_issue is not None
        assert q6emk4_issue.issue_type == "matching_failure"
        assert "NCBIGene:114990" in q6emk4_issue.workaround
        
        # Test deprecated accession
        deprecated_issue = KnownIssuesRegistry.check_identifier("P99999")
        assert deprecated_issue is not None
        assert deprecated_issue.issue_type == "deprecated_accession"
        assert deprecated_issue.investigation_status == "resolved"
        
        # Test isoform handling
        isoform_issue = KnownIssuesRegistry.check_identifier("ISOFORM_P12345-2")
        assert isoform_issue is not None
        assert isoform_issue.issue_type == "isoform_handling"
        assert "Strip isoform suffix" in isoform_issue.workaround

    def test_metabolite_issue_registry_integration(self, metabolite_analysis_issues, registry_backup):
        """Test metabolite analysis issues in registry."""
        # Add metabolite issues to registry
        for i, issue in enumerate(metabolite_analysis_issues):
            KnownIssuesRegistry.add_issue(f"metabolite_issue_{i}", issue)
        
        # Test semantic matching ambiguity
        hmdb_issue = KnownIssuesRegistry.check_identifier("HMDB0000001")
        assert hmdb_issue is not None
        assert hmdb_issue.issue_type == "semantic_matching_ambiguity"
        assert "chemical formula" in hmdb_issue.workaround
        
        # Test name normalization
        glucose_issue = KnownIssuesRegistry.check_identifier("GLUCOSE_VARIANT")
        assert glucose_issue is not None
        assert glucose_issue.issue_type == "name_normalization"
        assert glucose_issue.investigation_status == "resolved"
        assert "15 glucose variants" in glucose_issue.resolution

    def test_issue_status_filtering(self, protein_mapping_issues, metabolite_analysis_issues, registry_backup):
        """Test filtering issues by status."""
        # Add all issues
        all_issues = protein_mapping_issues + metabolite_analysis_issues
        for i, issue in enumerate(all_issues):
            KnownIssuesRegistry.add_issue(f"all_issues_{i}", issue)
        
        # Get open issues
        open_issues = KnownIssuesRegistry.get_all_open_issues()
        open_identifiers = {issue.identifier for issue in open_issues}
        
        # Should include open issues
        assert "Q6EMK4" in open_identifiers
        assert "HMDB0000001" in open_identifiers
        
        # Should not include resolved issues
        assert "P99999" not in open_identifiers
        assert "GLUCOSE_VARIANT" not in open_identifiers

    def test_workaround_retrieval_patterns(self, protein_mapping_issues, metabolite_analysis_issues, registry_backup):
        """Test workaround retrieval for biological issues."""
        # Add issues
        all_issues = protein_mapping_issues + metabolite_analysis_issues
        for i, issue in enumerate(all_issues):
            KnownIssuesRegistry.add_issue(f"workaround_test_{i}", issue)
        
        # Test protein workarounds
        q6emk4_workaround = KnownIssuesRegistry.get_workaround("Q6EMK4")
        assert "Manual mapping" in q6emk4_workaround
        assert "NCBIGene:114990" in q6emk4_workaround
        
        deprecated_workaround = KnownIssuesRegistry.get_workaround("P99999")
        assert "current accession P12345" in deprecated_workaround
        
        # Test metabolite workarounds
        hmdb_workaround = KnownIssuesRegistry.get_workaround("HMDB0000001")
        assert "chemical formula" in hmdb_workaround
        
        glucose_workaround = KnownIssuesRegistry.get_workaround("GLUCOSE_VARIANT")
        assert "synonyms" in glucose_workaround

    def test_issue_lifecycle_management(self, registry_backup):
        """Test complete issue lifecycle management."""
        # Step 1: Create new issue
        new_issue = KnownIssue(
            identifier="LIFECYCLE_TEST_123",
            issue_type="test_lifecycle",
            description="Testing complete issue lifecycle",
            affected_datasets=["test_dataset"],
            investigation_status="open",
            first_observed="2024-01-01",
            last_verified="2024-01-01"
        )
        KnownIssuesRegistry.add_issue("lifecycle_test", new_issue)
        
        # Step 2: Verify issue is open
        open_issues = KnownIssuesRegistry.get_all_open_issues()
        lifecycle_issue = next((issue for issue in open_issues if issue.identifier == "LIFECYCLE_TEST_123"), None)
        assert lifecycle_issue is not None
        assert lifecycle_issue.investigation_status == "open"
        
        # Step 3: Update to investigating
        KnownIssuesRegistry.update_status("LIFECYCLE_TEST_123", "investigating")
        updated_issue = KnownIssuesRegistry.check_identifier("LIFECYCLE_TEST_123")
        assert updated_issue.investigation_status == "investigating"
        
        # Step 4: Resolve with solution
        KnownIssuesRegistry.update_status(
            "LIFECYCLE_TEST_123", 
            "resolved", 
            "Implemented fix in validation pipeline"
        )
        resolved_issue = KnownIssuesRegistry.check_identifier("LIFECYCLE_TEST_123")
        assert resolved_issue.investigation_status == "resolved"
        assert resolved_issue.resolution == "Implemented fix in validation pipeline"
        
        # Step 5: Verify no longer in open issues
        final_open_issues = KnownIssuesRegistry.get_all_open_issues()
        still_open = any(issue.identifier == "LIFECYCLE_TEST_123" for issue in final_open_issues)
        assert still_open is False

    def test_multi_dataset_impact_tracking(self, registry_backup):
        """Test tracking issues that affect multiple datasets."""
        multi_dataset_issue = KnownIssue(
            identifier="MULTI_DATASET_ISSUE",
            issue_type="cross_dataset_inconsistency",
            description="Identifier format inconsistency across multiple biological databases",
            affected_datasets=[
                "arivale_proteomics",
                "kg2c_proteins", 
                "uniprot_kb",
                "ensembl_proteins",
                "protein_atlas"
            ],
            workaround="Implement cross-database normalization layer",
            investigation_status="investigating",
            first_observed="2024-12-01",
            last_verified="2024-12-14",
            related_files=[
                "normalization/protein_id_normalizer.py",
                "mapping/cross_database_mapper.py",
                "validation/multi_dataset_validator.py"
            ]
        )
        
        KnownIssuesRegistry.add_issue("multi_dataset", multi_dataset_issue)
        
        # Verify multi-dataset issue tracking
        retrieved_issue = KnownIssuesRegistry.check_identifier("MULTI_DATASET_ISSUE")
        assert len(retrieved_issue.affected_datasets) == 5
        assert "arivale_proteomics" in retrieved_issue.affected_datasets
        assert "protein_atlas" in retrieved_issue.affected_datasets
        assert len(retrieved_issue.related_files) == 3
        assert "normalization layer" in retrieved_issue.workaround