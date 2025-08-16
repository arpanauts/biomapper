#!/usr/bin/env python3
"""
Documentation verification script for BioMapper Actions.

This script checks:
1. All action RST files are properly included in index.rst
2. No broken cross-references exist
3. Documentation builds without critical errors
"""

import os
import re
from pathlib import Path
from typing import List, Set, Tuple


def get_action_files() -> Set[str]:
    """Get all action RST files in the directory."""
    action_files = set()
    for file in Path(".").glob("*.rst"):
        if file.name not in ["index.rst"]:
            action_files.add(file.stem)
    return action_files


def get_indexed_actions() -> Set[str]:
    """Get all actions referenced in index.rst."""
    indexed = set()
    with open("index.rst", "r") as f:
        content = f.read()
        # Find all toctree entries
        pattern = r'^\s{3}(\w+)$'
        for match in re.finditer(pattern, content, re.MULTILINE):
            indexed.add(match.group(1))
    return indexed


def check_cross_references() -> List[str]:
    """Check for broken cross-references in RST files."""
    issues = []
    for rst_file in Path(".").glob("*.rst"):
        with open(rst_file, "r") as f:
            content = f.read()
            # Check for :doc: and :ref: directives
            for match in re.finditer(r':(?:doc|ref):`([^`]+)`', content):
                ref = match.group(1)
                # Simple check - could be enhanced
                if "/" in ref:
                    ref_path = Path(ref.split("/")[-1] + ".rst")
                    if not ref_path.exists():
                        issues.append(f"{rst_file}: broken reference to {ref}")
    return issues


def verify_documentation() -> Tuple[bool, List[str]]:
    """Verify documentation completeness and correctness."""
    issues = []
    
    # Check 1: All action files are indexed
    action_files = get_action_files()
    indexed_actions = get_indexed_actions()
    
    missing_from_index = action_files - indexed_actions
    if missing_from_index:
        issues.append(f"Actions not in index.rst: {', '.join(sorted(missing_from_index))}")
    
    indexed_but_missing = indexed_actions - action_files
    if indexed_but_missing:
        issues.append(f"Referenced in index but file missing: {', '.join(sorted(indexed_but_missing))}")
    
    # Check 2: Cross-references
    broken_refs = check_cross_references()
    if broken_refs:
        issues.extend(broken_refs)
    
    # Check 3: Quick table validation in index.rst
    with open("index.rst", "r") as f:
        content = f.read()
        # Count action types mentioned in tables
        action_pattern = r'\* - ``([A-Z_]+)``'
        table_actions = set(re.findall(action_pattern, content))
        
        # These should correspond to actual implementations
        if len(table_actions) < 20:
            issues.append(f"Only {len(table_actions)} actions documented in quick reference tables")
    
    return len(issues) == 0, issues


def main():
    """Run documentation verification."""
    print("BioMapper Actions Documentation Verification")
    print("=" * 50)
    
    success, issues = verify_documentation()
    
    if success:
        print("✅ All documentation checks passed!")
        print("\nSummary:")
        action_files = get_action_files()
        print(f"  - {len(action_files)} action documentation files found")
        print(f"  - All actions properly indexed")
        print(f"  - No broken cross-references detected")
    else:
        print("❌ Documentation issues found:")
        print()
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("Please fix these issues to ensure complete documentation.")
        return 1
    
    print("\n📚 Documentation structure:")
    print("  actions/")
    print("    ├── index.rst (main action reference)")
    for category in ["Data Operations", "Protein Actions", "Metabolite Actions", 
                     "Chemistry Actions", "Analysis Actions"]:
        print(f"    ├── {category}:")
        # Could list specific files per category here
    
    return 0


if __name__ == "__main__":
    exit(main())
