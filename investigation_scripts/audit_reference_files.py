#!/usr/bin/env python3
"""
Audit missing reference data files across biomapper strategies and actions.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
import re

class ReferenceFileAuditor:
    """Audit reference files required by biomapper strategies and actions."""
    
    def __init__(self, base_dir: str = "/home/ubuntu/biomapper"):
        self.base_dir = Path(base_dir)
        self.required_files = set()
        self.existing_files = set()
        self.missing_files = set()
        
    def audit_all_dependencies(self) -> Dict[str, Any]:
        """Audit all reference file dependencies."""
        
        results = {
            'strategy_dependencies': self.audit_strategy_files(),
            'action_dependencies': self.audit_action_files(),
            'existing_files': self.scan_existing_files(),
            'missing_files': [],
            'recommendations': []
        }
        
        # Combine all required files
        all_required = set()
        for deps in results['strategy_dependencies'].values():
            all_required.update(deps.get('reference_files', []))
        
        for deps in results['action_dependencies'].values():
            all_required.update(deps.get('reference_files', []))
        
        # Find missing files
        results['missing_files'] = self.find_missing_files(all_required, results['existing_files'])
        
        # Generate recommendations
        results['recommendations'] = self.generate_recommendations(results['missing_files'])
        
        return results
    
    def audit_strategy_files(self) -> Dict[str, Any]:
        """Audit reference files mentioned in strategy configurations."""
        
        strategy_deps = {}
        strategy_dir = self.base_dir / "configs" / "strategies"
        
        if not strategy_dir.exists():
            return strategy_deps
        
        for strategy_file in strategy_dir.rglob("*.yaml"):
            try:
                with open(strategy_file, 'r') as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)
                
                if yaml_content is None:
                    continue
                
                deps = self.extract_strategy_dependencies(yaml_content, content)
                if deps['reference_files'] or deps['data_files']:
                    strategy_deps[str(strategy_file)] = deps
                    
            except Exception as e:
                strategy_deps[str(strategy_file)] = {
                    'error': str(e),
                    'reference_files': [],
                    'data_files': []
                }
        
        return strategy_deps
    
    def audit_action_files(self) -> Dict[str, Any]:
        """Audit reference files mentioned in action implementations."""
        
        action_deps = {}
        actions_dir = self.base_dir / "biomapper" / "core" / "strategy_actions"
        
        if not actions_dir.exists():
            return action_deps
        
        for action_file in actions_dir.rglob("*.py"):
            try:
                with open(action_file, 'r') as f:
                    content = f.read()
                
                deps = self.extract_action_dependencies(content)
                if deps['reference_files'] or deps['data_files']:
                    action_deps[str(action_file)] = deps
                    
            except Exception as e:
                action_deps[str(action_file)] = {
                    'error': str(e),
                    'reference_files': [],
                    'data_files': []
                }
        
        return action_deps
    
    def extract_strategy_dependencies(self, yaml_content: Dict, raw_content: str) -> Dict[str, List[str]]:
        """Extract file dependencies from strategy YAML."""
        
        deps = {
            'reference_files': [],
            'data_files': []
        }
        
        # Common reference file patterns in strategies
        reference_patterns = [
            r'ontology[_\w]*\.(?:json|yaml|csv|tsv)',
            r'mapping[_\w]*\.(?:json|yaml|csv|tsv)',
            r'reference[_\w]*\.(?:json|yaml|csv|tsv)',
            r'nightingale[_\w]*\.(?:json|yaml|csv|tsv)',
            r'MAPPING_ONTOLOGIES[/\w\-\.]*',
            r'uniprot[_\w]*\.(?:json|yaml|csv|tsv)',
            r'chebi[_\w]*\.(?:json|yaml|csv|tsv)',
        ]
        
        # Data file patterns
        data_patterns = [
            r'[\w\-/]*\.csv',
            r'[\w\-/]*\.tsv',
            r'[\w\-/]*\.json',
            r'[\w\-/]*\.yaml',
        ]
        
        # Extract from raw content using patterns
        for pattern in reference_patterns:
            matches = re.findall(pattern, raw_content, re.IGNORECASE)
            deps['reference_files'].extend(matches)
        
        # Look for specific reference mentions
        if 'nightingale' in raw_content.lower():
            deps['reference_files'].append('nightingale_nmr_reference.json')
        
        if 'ontologies' in raw_content.lower():
            deps['reference_files'].append('MAPPING_ONTOLOGIES/')
        
        # Extract from parameters and action params
        parameters = yaml_content.get('parameters', {})
        for key, value in parameters.items():
            if isinstance(value, str) and any(ref in value.lower() for ref in ['ontology', 'reference', 'mapping']):
                deps['reference_files'].append(value)
        
        # Extract from action parameters
        for step in yaml_content.get('steps', []):
            action_params = step.get('action', {}).get('params', {})
            for param_name, param_value in action_params.items():
                if isinstance(param_value, str):
                    if any(ref in param_name.lower() for ref in ['reference', 'ontology', 'mapping']):
                        deps['reference_files'].append(param_value)
                    elif param_value.endswith(('.json', '.yaml', '.csv', '.tsv')):
                        deps['data_files'].append(param_value)
        
        return deps
    
    def extract_action_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Extract file dependencies from Python action code."""
        
        deps = {
            'reference_files': [],
            'data_files': []
        }
        
        # Look for file path patterns in Python code
        file_patterns = [
            r'["\']([^"\']*\.(?:json|yaml|csv|tsv))["\']',
            r'["\']([^"\']*ontolog[^"\']*)["\']',
            r'["\']([^"\']*reference[^"\']*)["\']',
            r'["\']([^"\']*mapping[^"\']*)["\']',
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if any(ref in match.lower() for ref in ['ontology', 'reference', 'mapping']):
                    deps['reference_files'].append(match)
                else:
                    deps['data_files'].append(match)
        
        # Look for specific imports and references
        if 'nightingale' in content.lower():
            deps['reference_files'].append('nightingale_nmr_reference')
        
        if 'chebi' in content.lower():
            deps['reference_files'].append('chebi_ontology')
        
        if 'uniprot' in content.lower():
            deps['reference_files'].append('uniprot_mappings')
        
        return deps
    
    def scan_existing_files(self) -> List[str]:
        """Scan for existing reference and data files."""
        
        existing_files = []
        
        # Common directories to scan
        scan_dirs = [
            self.base_dir / "data",
            self.base_dir / "configs" / "data",
            Path("/procedure/data/local_data"),
            Path("/procedure/data/MAPPING_ONTOLOGIES"),
            Path("/tmp/biomapper/data"),
        ]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for file_path in scan_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix in ['.json', '.yaml', '.csv', '.tsv', '.txt']:
                        existing_files.append(str(file_path))
        
        return existing_files
    
    def find_missing_files(self, required_files: Set[str], existing_files: List[str]) -> List[Dict[str, Any]]:
        """Find files that are required but missing."""
        
        missing = []
        existing_basenames = {Path(f).name for f in existing_files}
        existing_paths = set(existing_files)
        
        for required_file in required_files:
            if not required_file:
                continue
                
            required_path = Path(required_file)
            
            # Check exact path match
            if required_file in existing_paths:
                continue
            
            # Check basename match
            if required_path.name in existing_basenames:
                continue
            
            # Check if it's a directory
            if required_file.endswith('/') and any(required_file in existing for existing in existing_files):
                continue
            
            missing.append({
                'file': required_file,
                'basename': required_path.name,
                'type': self.classify_file_type(required_file),
                'severity': self.assess_severity(required_file)
            })
        
        return missing
    
    def classify_file_type(self, file_path: str) -> str:
        """Classify the type of reference file."""
        
        file_lower = file_path.lower()
        
        if 'ontology' in file_lower:
            return 'ontology'
        elif 'mapping' in file_lower:
            return 'mapping'
        elif 'reference' in file_lower:
            return 'reference'
        elif 'nightingale' in file_lower:
            return 'nmr_reference'
        elif file_path.endswith('.json'):
            return 'json_data'
        elif file_path.endswith(('.csv', '.tsv')):
            return 'tabular_data'
        else:
            return 'unknown'
    
    def assess_severity(self, file_path: str) -> str:
        """Assess the severity of a missing file."""
        
        file_lower = file_path.lower()
        
        # Critical files that strategies depend on
        if any(critical in file_lower for critical in ['ontology', 'mapping', 'reference']):
            return 'CRITICAL'
        elif 'nightingale' in file_lower:
            return 'HIGH'
        elif file_path.endswith('.json'):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def generate_recommendations(self, missing_files: List[Dict]) -> List[Dict[str, Any]]:
        """Generate recommendations for missing files."""
        
        recommendations = []
        
        # Group by type and severity
        by_type = {}
        for missing in missing_files:
            file_type = missing['type']
            if file_type not in by_type:
                by_type[file_type] = []
            by_type[file_type].append(missing)
        
        for file_type, files in by_type.items():
            if file_type == 'ontology':
                recommendations.append({
                    'type': 'ontology',
                    'priority': 'CRITICAL',
                    'title': 'Missing Ontology Files',
                    'description': f"Found {len(files)} missing ontology files",
                    'actions': [
                        'Download required ontology files from official sources',
                        'Create MAPPING_ONTOLOGIES directory structure',
                        'Verify ontology file formats match expected schemas',
                        'Update file paths in strategies to match actual locations'
                    ],
                    'files': [f['file'] for f in files]
                })
            
            elif file_type == 'nmr_reference':
                recommendations.append({
                    'type': 'nmr_reference',
                    'priority': 'HIGH',
                    'title': 'Missing NMR Reference Files',
                    'description': f"Found {len(files)} missing Nightingale NMR reference files",
                    'actions': [
                        'Download Nightingale NMR reference data',
                        'Verify NMR reference file format compatibility',
                        'Update NMR matching action configurations',
                        'Test NMR matching functionality'
                    ],
                    'files': [f['file'] for f in files]
                })
            
            elif file_type == 'mapping':
                recommendations.append({
                    'type': 'mapping',
                    'priority': 'HIGH',
                    'title': 'Missing Mapping Files',
                    'description': f"Found {len(files)} missing mapping files",
                    'actions': [
                        'Generate or download required mapping files',
                        'Verify mapping file schemas and formats',
                        'Test mapping functionality with sample data',
                        'Update mapping action configurations'
                    ],
                    'files': [f['file'] for f in files]
                })
        
        return recommendations

def generate_reference_audit_report(audit_results: Dict[str, Any]) -> str:
    """Generate comprehensive reference file audit report."""
    
    total_missing = len(audit_results['missing_files'])
    total_existing = len(audit_results['existing_files'])
    
    report = f"""# Reference Data Files Audit Report

## Summary
- **Existing Files Found**: {total_existing}
- **Missing Files Identified**: {total_missing}
- **Strategies Analyzed**: {len(audit_results['strategy_dependencies'])}
- **Actions Analyzed**: {len(audit_results['action_dependencies'])}

## Missing Files by Severity
"""
    
    # Count by severity
    severity_counts = {}
    for missing in audit_results['missing_files']:
        severity = missing['severity']
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = severity_counts.get(severity, 0)
        if count > 0:
            report += f"- **{severity}**: {count} files\n"
    
    report += "\n## Detailed Missing Files\n"
    
    for missing in audit_results['missing_files'][:20]:  # Show first 20
        report += f"""
### {missing['file']} ({missing['severity']})
- **Type**: {missing['type']}
- **Basename**: {missing['basename']}
"""
    
    if len(audit_results['missing_files']) > 20:
        report += f"\n... and {len(audit_results['missing_files']) - 20} more missing files.\n"
    
    report += "\n## Recommendations\n"
    
    for recommendation in audit_results['recommendations']:
        report += f"""
### {recommendation['title']} ({recommendation['priority']} Priority)
{recommendation['description']}

**Actions Required:**
"""
        for action in recommendation['actions']:
            report += f"1. {action}\n"
        
        report += f"\n**Affected Files**: {len(recommendation['files'])}\n"
        for file_path in recommendation['files'][:5]:
            report += f"- `{file_path}`\n"
        if len(recommendation['files']) > 5:
            report += f"- ... and {len(recommendation['files']) - 5} more\n"
    
    report += """
## Data Directory Structure Recommendations

```
/procedure/data/local_data/
├── MAPPING_ONTOLOGIES/
│   ├── chebi_ontology.json
│   ├── uniprot_mappings.csv
│   └── gene_ontology.json
├── nightingale_nmr_reference.json
├── reference_datasets/
└── cached_mappings/
```

## Implementation Steps

1. **Create Directory Structure**
   ```bash
   mkdir -p /procedure/data/local_data/MAPPING_ONTOLOGIES
   mkdir -p /procedure/data/local_data/reference_datasets
   mkdir -p /procedure/data/local_data/cached_mappings
   ```

2. **Download Critical Reference Files**
   - Obtain ontology files from official sources
   - Download Nightingale NMR reference data
   - Generate mapping files for identifier conversions

3. **Update Configuration**
   - Set BIOMAPPER_DATA_DIR environment variable
   - Update strategy files to use correct paths
   - Test file accessibility from actions

4. **Validation**
   - Run integration tests to verify file accessibility
   - Check file formats match expected schemas
   - Validate data integrity and completeness
"""
    
    return report

def main():
    """Main function to run reference file audit."""
    
    print("Starting reference file audit...")
    
    auditor = ReferenceFileAuditor()
    results = auditor.audit_all_dependencies()
    
    report = generate_reference_audit_report(results)
    
    with open('/tmp/reference_audit_report.md', 'w') as f:
        f.write(report)
    
    print(f"Reference file audit complete.")
    print(f"Found {len(results['existing_files'])} existing files")
    print(f"Identified {len(results['missing_files'])} missing files")
    print(f"Generated {len(results['recommendations'])} recommendations")
    print("Report saved to /tmp/reference_audit_report.md")

if __name__ == "__main__":
    main()