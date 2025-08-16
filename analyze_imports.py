#!/usr/bin/env python3
"""Analyze import dependencies in the biomapper project."""

import ast
import os
from pathlib import Path
from collections import defaultdict
import json

def extract_imports(file_path):
    """Extract all imports from a Python file."""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except Exception as e:
        pass  # Skip files with syntax errors
    
    return imports

def categorize_import(import_name):
    """Categorize import as internal or external."""
    internal_prefixes = ['biomapper', 'app', 'tests']
    for prefix in internal_prefixes:
        if import_name.startswith(prefix):
            return 'internal'
    return 'external'

def analyze_project():
    """Analyze all Python files in the project."""
    project_root = Path('/home/ubuntu/biomapper')
    
    # Skip these directories
    skip_dirs = {'.git', '__pycache__', '.venv', 'venv', '.cache', '.ruff_cache'}
    
    file_imports = {}
    import_counts = defaultdict(int)
    internal_deps = defaultdict(set)
    external_deps = defaultdict(set)
    
    for py_file in project_root.rglob('*.py'):
        # Skip files in skip directories
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
        
        rel_path = py_file.relative_to(project_root)
        imports = extract_imports(py_file)
        file_imports[str(rel_path)] = imports
        
        for imp in imports:
            import_counts[imp] += 1
            if categorize_import(imp) == 'internal':
                internal_deps[str(rel_path)].add(imp)
            else:
                external_deps[str(rel_path)].add(imp)
    
    # Find orphaned modules (no incoming internal imports)
    all_modules = set()
    imported_modules = set()
    
    for file_path in file_imports.keys():
        module_name = file_path.replace('/', '.').replace('.py', '')
        all_modules.add(module_name)
        
        for imp in internal_deps.get(file_path, []):
            imported_modules.add(imp)
    
    orphaned = []
    for module in all_modules:
        # Check if this module is imported anywhere
        is_imported = False
        for imp in imported_modules:
            if module.startswith(imp) or imp.startswith(module):
                is_imported = True
                break
        if not is_imported and not module.startswith('tests') and not module.endswith('__main__'):
            orphaned.append(module)
    
    # Top imported modules
    top_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Files with most dependencies
    files_by_deps = sorted(
        [(f, len(internal_deps[f]) + len(external_deps[f])) for f in file_imports.keys()],
        key=lambda x: x[1],
        reverse=True
    )[:20]
    
    return {
        'total_files': len(file_imports),
        'top_imports': top_imports,
        'files_with_most_deps': files_by_deps,
        'orphaned_modules': orphaned[:20],
        'unique_external_deps': len(set(imp for deps in external_deps.values() for imp in deps)),
        'unique_internal_deps': len(set(imp for deps in internal_deps.values() for imp in deps))
    }

if __name__ == '__main__':
    results = analyze_project()
    print(json.dumps(results, indent=2))