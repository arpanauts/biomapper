#!/usr/bin/env python3
"""
Analyze Qdrant dependencies across biomapper strategies and actions.
"""

import os
import re
from pathlib import Path
import yaml
from typing import Dict, List, Any

def analyze_qdrant_dependencies():
    """Analyze how Qdrant is used across biomapper strategies."""
    
    qdrant_usage = {
        'strategies_affected': [],
        'actions_using_qdrant': [],
        'vector_operations': [],
        'collection_requirements': [],
        'performance_requirements': {}
    }
    
    base_dir = Path("/home/ubuntu/biomapper")
    
    # Scan strategy files for Qdrant references
    strategy_dir = base_dir / "configs" / "strategies"
    print(f"Scanning strategy directory: {strategy_dir}")
    
    if strategy_dir.exists():
        for strategy_file in strategy_dir.rglob("*.yaml"):
            try:
                with open(strategy_file, 'r') as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)
                
                # Check for Qdrant-related parameters
                if 'qdrant' in content.lower() or 'vector' in content.lower():
                    qdrant_usage['strategies_affected'].append({
                        'file': str(strategy_file),
                        'strategy_name': yaml_content.get('name', 'unknown'),
                        'qdrant_references': extract_qdrant_references(content)
                    })
            except Exception as e:
                print(f"Error analyzing {strategy_file}: {e}")
    
    # Scan action files for Qdrant imports and usage
    actions_dir = base_dir / "biomapper" / "core" / "strategy_actions"
    print(f"Scanning actions directory: {actions_dir}")
    
    if actions_dir.exists():
        for action_file in actions_dir.rglob("*.py"):
            try:
                with open(action_file, 'r') as f:
                    content = f.read()
                
                if 'qdrant' in content.lower():
                    qdrant_usage['actions_using_qdrant'].append({
                        'file': str(action_file),
                        'imports': extract_imports(content, 'qdrant'),
                        'usage_patterns': extract_qdrant_operations(content)
                    })
            except Exception as e:
                print(f"Error analyzing {action_file}: {e}")
    
    return qdrant_usage

def extract_qdrant_references(content: str) -> List[str]:
    """Extract Qdrant-related references from YAML content."""
    references = []
    
    # Common patterns
    patterns = [
        r'qdrant[_\w]*',
        r'vector[_\w]*',
        r'embedding[_\w]*',
        r'similarity[_\w]*',
        r'collection[_\w]*'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        references.extend(matches)
    
    return list(set(references))

def extract_imports(content: str, package_name: str) -> List[str]:
    """Extract import statements for a specific package."""
    import_patterns = [
        rf'from {package_name}[_\w\.]* import .*',
        rf'import {package_name}[_\w\.]*',
    ]
    
    imports = []
    for pattern in import_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        imports.extend(matches)
    
    return imports

def extract_qdrant_operations(content: str) -> List[str]:
    """Extract specific Qdrant operations from Python code."""
    operations = []
    
    # Look for common Qdrant operations
    operation_patterns = [
        r'client\.search\(',
        r'client\.upsert\(',
        r'client\.create_collection\(',
        r'client\.delete_collection\(',
        r'qdrant_client\.\w+\(',
        r'vector_store\.\w+\(',
        r'embeddings\.\w+\('
    ]
    
    for pattern in operation_patterns:
        matches = re.findall(pattern, content)
        operations.extend(matches)
    
    return operations

def generate_qdrant_dependency_report(usage_data: Dict) -> str:
    """Generate comprehensive Qdrant dependency report."""
    
    report = """# Qdrant Dependency Analysis Report

## Summary
- **Strategies Affected**: {num_strategies}
- **Actions Using Qdrant**: {num_actions}
- **Critical Impact**: {impact_level}

## Detailed Findings

### Affected Strategies
""".format(
        num_strategies=len(usage_data['strategies_affected']),
        num_actions=len(usage_data['actions_using_qdrant']),
        impact_level="HIGH" if len(usage_data['strategies_affected']) > 5 else "MEDIUM"
    )
    
    for strategy in usage_data['strategies_affected']:
        report += f"""
#### {strategy['strategy_name']}
- **File**: `{strategy['file']}`
- **Qdrant References**: {', '.join(strategy['qdrant_references'])}
"""
    
    report += """
### Actions Using Qdrant
"""
    
    for action in usage_data['actions_using_qdrant']:
        report += f"""
#### {Path(action['file']).stem}
- **File**: `{action['file']}`
- **Imports**: {action['imports']}
- **Operations**: {action['usage_patterns']}
"""
    
    return report

if __name__ == "__main__":
    print("Starting Qdrant dependency analysis...")
    usage_data = analyze_qdrant_dependencies()
    report = generate_qdrant_dependency_report(usage_data)
    
    with open('/tmp/qdrant_dependency_report.md', 'w') as f:
        f.write(report)
    
    print("Qdrant dependency analysis complete. Report saved to /tmp/qdrant_dependency_report.md")
    print(f"Found {len(usage_data['strategies_affected'])} affected strategies and {len(usage_data['actions_using_qdrant'])} actions using Qdrant")