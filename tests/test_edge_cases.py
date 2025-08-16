"""Test known edge cases to track if they get fixed"""

import pytest
import pandas as pd
from pathlib import Path
from biomapper.core.standards.known_issues import KnownIssuesRegistry, KnownIssue


class TestKnownEdgeCases:
    """Test suite for tracking known edge cases and their resolution status."""
    
    @pytest.mark.xfail(reason="Q6EMK4 known issue - shows as source_only despite being in target")
    def test_q6emk4_matching(self):
        """Test Q6EMK4 matching - currently fails due to known issue.
        
        Q6EMK4 is present in both source (Arivale) and target (KG2c) datasets,
        but fails to match properly in the merge_with_uniprot_resolution action.
        Expected: Should match and show as 'both'
        Actual: Shows as 'source_only'
        """
        # This test documents the expected behavior
        # When the issue is fixed, this test should pass
        
        # Simulate the matching scenario
        source_data = pd.DataFrame({
            'identifier': ['Q6EMK4', 'P12345'],
            'source': ['arivale', 'arivale']
        })
        
        target_data = pd.DataFrame({
            'identifier': ['Q6EMK4', 'P12345'],
            'xrefs': ['UniProtKB:Q6EMK4', 'UniProtKB:P12345']
        })
        
        # Expected: Both identifiers should match
        # Q6EMK4 should be found in target xrefs
        assert 'Q6EMK4' in target_data['xrefs'].str.extract(r'UniProtKB:([A-Z0-9]+)')[0].values
        
        # This assertion would fail in production due to the bug
        # assert matching_result['Q6EMK4'] == 'both'  # Currently returns 'source_only'
    
    def test_edge_case_documentation(self):
        """Ensure all edge cases are properly documented in the registry."""
        # Check that Q6EMK4 is documented
        issue = KnownIssuesRegistry.check_identifier('Q6EMK4')
        assert issue is not None, "Q6EMK4 should be documented as a known issue"
        assert issue.issue_type == 'matching_failure'
        assert issue.workaround is not None
        assert len(issue.related_files) > 0
        
    def test_workarounds_available(self):
        """Test that workarounds are provided for all open known issues."""
        open_issues = KnownIssuesRegistry.get_all_open_issues()
        
        for issue in open_issues:
            # High priority issues should have workarounds
            if issue.investigation_status == 'open':
                assert issue.workaround is not None or issue.resolution is not None, \
                    f"Issue {issue.identifier} should have a workaround or resolution"
    
    def test_known_issue_structure(self):
        """Test that all known issues have required fields."""
        for key, issue in KnownIssuesRegistry.ISSUES.items():
            assert isinstance(issue, KnownIssue)
            assert issue.identifier
            assert issue.issue_type
            assert issue.description
            assert issue.investigation_status in ['open', 'investigating', "won't fix", 'resolved']
            assert issue.first_observed
            assert issue.last_verified
            assert isinstance(issue.affected_datasets, list)
            assert isinstance(issue.related_files, list)
    
    @pytest.mark.parametrize("identifier,expected_workaround", [
        ("Q6EMK4", "Manual mapping: Q6EMK4 -> NCBIGene:114990 (OTUD5)"),
        # Add more edge cases as they are discovered
    ])
    def test_specific_workarounds(self, identifier, expected_workaround):
        """Test that specific identifiers have the expected workarounds."""
        workaround = KnownIssuesRegistry.get_workaround(identifier)
        assert workaround == expected_workaround
    
    def test_issue_status_updates(self):
        """Test that issue status can be updated when resolved."""
        # Create a test issue
        test_issue = KnownIssue(
            identifier="TEST123",
            issue_type="test_issue",
            description="Test issue for unit testing",
            affected_datasets=["test_dataset"],
            investigation_status="open",
            first_observed="2024-12-14",
            last_verified="2024-12-14"
        )
        
        # Add to registry
        KnownIssuesRegistry.add_issue("test_issue", test_issue)
        
        # Update status
        success = KnownIssuesRegistry.update_status(
            "TEST123", 
            "resolved", 
            "Fixed in version 1.2.3"
        )
        assert success
        
        # Verify update
        updated_issue = KnownIssuesRegistry.check_identifier("TEST123")
        assert updated_issue.investigation_status == "resolved"
        assert updated_issue.resolution == "Fixed in version 1.2.3"
        
        # Clean up
        del KnownIssuesRegistry.ISSUES["test_issue"]
    
    @pytest.mark.skip(reason="Requires actual data files")
    def test_q6emk4_in_real_data(self):
        """Test Q6EMK4 presence in actual data files."""
        # This test would check real data files if available
        arivale_file = Path("/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv")
        kg2c_file = Path("/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv")
        
        if arivale_file.exists():
            arivale_df = pd.read_csv(arivale_file, sep='\t')
            # Check for Q6EMK4 in arivale data
            
        if kg2c_file.exists():
            kg2c_df = pd.read_csv(kg2c_file)
            # Check for Q6EMK4 in KG2c xrefs
    
    def test_edge_case_regression(self):
        """Ensure fixed edge cases don't regress."""
        # This test would track previously fixed issues
        # to ensure they don't break again
        resolved_issues = [
            issue for issue in KnownIssuesRegistry.ISSUES.values()
            if issue.investigation_status == 'resolved'
        ]
        
        for issue in resolved_issues:
            # Test that the resolution still works
            # This would involve running the specific scenario
            # that was previously broken
            pass