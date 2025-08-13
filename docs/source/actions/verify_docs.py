#!/usr/bin/env python3
"""Verify documentation completeness for BioMapper actions."""

import re
from pathlib import Path

# Parse index.rst to find referenced actions
index_file = Path("index.rst")
referenced_actions = set()

if index_file.exists():
    content = index_file.read_text()
    # Find actions in toctree directives
    for line in content.splitlines():
        line = line.strip()
        # Skip toctree directives and captions
        if line and not line.startswith(":") and not line.startswith(".."):
            # Check if it looks like an action reference (lowercase with underscores)
            if re.match(r'^[a-z_]+$', line):
                referenced_actions.add(line)

# Find existing RST documentation files  
existing_docs = set()
for rst_file in Path(".").glob("*.rst"):
    if rst_file.name != "index.rst":
        existing_docs.add(rst_file.stem)

# Find missing documentation
missing_docs = referenced_actions - existing_docs

# Find documented but not referenced
orphaned_docs = existing_docs - referenced_actions

print("=== Documentation Status Report ===\n")

print(f"Total actions referenced in index.rst: {len(referenced_actions)}")
print(f"Total documentation files found: {len(existing_docs)}")

if missing_docs:
    print(f"\n❌ MISSING DOCUMENTATION FILES ({len(missing_docs)}):")
    for action in sorted(missing_docs):
        print(f"  - {action}.rst")
else:
    print("\n✅ All referenced actions have documentation")

if orphaned_docs:
    print(f"\n⚠️  ORPHANED DOCUMENTATION ({len(orphaned_docs)}):")
    print("   (Files exist but not referenced in index.rst)")
    for action in sorted(orphaned_docs):
        print(f"  - {action}.rst")

# Check for actions in code that aren't documented
print("\n=== Checking Actions in Code ===\n")

# Path to actions directory
actions_dir = Path("../../../biomapper/core/strategy_actions")

registered_actions = set()
if actions_dir.exists():
    for py_file in actions_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            content = py_file.read_text()
            # Find @register_action decorators
            matches = re.findall(r'@register_action\("([^"]+)"\)', content)
            registered_actions.update(matches)

print(f"Total registered actions found in code: {len(registered_actions)}")

# Map action names to documentation names (convert to lowercase)
action_to_doc = {}
for action in registered_actions:
    doc_name = action.lower().replace("_v2", "")
    action_to_doc[action] = doc_name

# Find undocumented actions
undocumented_actions = []
for action, doc_name in sorted(action_to_doc.items()):
    if doc_name not in referenced_actions and doc_name not in existing_docs:
        undocumented_actions.append(action)

if undocumented_actions:
    print(f"\n❌ UNDOCUMENTED ACTIONS IN CODE ({len(undocumented_actions)}):")
    for action in undocumented_actions:
        print(f"  - {action}")
else:
    print("\n✅ All code actions appear to be documented")

print("\n=== Summary ===")
print(f"Documentation coverage: {len(existing_docs)}/{len(referenced_actions)} referenced actions")
print(f"Code coverage: {len(registered_actions) - len(undocumented_actions)}/{len(registered_actions)} actions")