from typing import Dict, List, Optional
from pydantic import BaseModel

class KnownIssue(BaseModel):
    """Document a known edge case"""
    
    identifier: str
    issue_type: str
    description: str
    affected_datasets: List[str]
    workaround: Optional[str] = None
    investigation_status: str  # 'open', 'investigating', 'won't fix', 'resolved'
    first_observed: str
    last_verified: str
    example_command: Optional[str] = None
    related_files: List[str] = []
    resolution: Optional[str] = None

class KnownIssuesRegistry:
    """Registry of known edge cases and issues"""
    
    ISSUES = {
        'Q6EMK4_no_match': KnownIssue(
            identifier='Q6EMK4',
            issue_type='matching_failure',
            description='Q6EMK4 from Arivale shows as source_only despite being in KG2c xrefs',
            affected_datasets=['arivale_proteomics', 'kg2c_proteins'],
            workaround='Manual mapping: Q6EMK4 -> NCBIGene:114990 (OTUD5)',
            investigation_status='open',
            first_observed='2024-12-14',
            last_verified='2024-12-14',
            example_command='grep Q6EMK4 /tmp/biomapper_results/protein_mapping_results.csv',
            related_files=[
                'biomapper/core/strategy_actions/merge_with_uniprot_resolution.py',
                'investigate_Q6EMK4.py',
                'Q6EMK4_BUG_REPORT.md',
                'Q6EMK4_INVESTIGATION_SUMMARY.md',
                'Q6EMK4_RESOLUTION.md'
            ],
            resolution=None
        ),
        # Add more known issues here as they are discovered
    }
    
    @classmethod
    def check_identifier(cls, identifier: str) -> Optional[KnownIssue]:
        """Check if identifier has known issues"""
        for issue in cls.ISSUES.values():
            if identifier == issue.identifier:
                return issue
        return None
    
    @classmethod
    def get_workaround(cls, identifier: str) -> Optional[str]:
        """Get workaround for known issue"""
        issue = cls.check_identifier(identifier)
        return issue.workaround if issue else None
    
    @classmethod
    def get_all_open_issues(cls) -> List[KnownIssue]:
        """Get all open issues"""
        return [issue for issue in cls.ISSUES.values() 
                if issue.investigation_status == 'open']
    
    @classmethod
    def add_issue(cls, key: str, issue: KnownIssue):
        """Add a new known issue to the registry"""
        cls.ISSUES[key] = issue
    
    @classmethod
    def update_status(cls, identifier: str, status: str, resolution: Optional[str] = None):
        """Update issue status"""
        for key, issue in cls.ISSUES.items():
            if issue.identifier == identifier:
                issue.investigation_status = status
                if resolution:
                    issue.resolution = resolution
                return True
        return False