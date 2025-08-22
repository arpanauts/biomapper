#!/usr/bin/env python3
"""
Analyze package usage in the BioMapper project.
Identifies potentially unused dependencies by checking imports across the codebase.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple
import json

def get_installed_packages() -> Dict[str, str]:
    """Get all installed packages from pyproject.toml."""
    packages = {}
    
    # Read pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Extract dependencies section
    import toml
    try:
        data = toml.load(pyproject_path)
        
        # Main dependencies
        if 'tool' in data and 'poetry' in data['tool']:
            deps = data['tool']['poetry'].get('dependencies', {})
            for pkg, version in deps.items():
                if pkg != 'python':  # Skip Python version spec
                    # Handle complex dependency specs
                    if isinstance(version, dict):
                        packages[pkg.lower()] = str(version)
                    else:
                        packages[pkg.lower()] = version
            
            # Dev dependencies
            if 'group' in data['tool']['poetry']:
                for group_name, group_data in data['tool']['poetry']['group'].items():
                    group_deps = group_data.get('dependencies', {})
                    for pkg, version in group_deps.items():
                        if isinstance(version, dict):
                            packages[pkg.lower()] = f"{version} (group: {group_name})"
                        else:
                            packages[pkg.lower()] = f"{version} (group: {group_name})"
            
            # Optional dependencies (extras)
            extras = data['tool']['poetry'].get('extras', {})
            for extra_name, extra_pkgs in extras.items():
                for pkg in extra_pkgs:
                    if pkg.lower() not in packages:
                        packages[pkg.lower()] = f"(extra: {extra_name})"
    except ImportError:
        print("Warning: toml not installed, parsing manually...")
        # Fallback to regex parsing
        deps_pattern = r'^\s*([a-zA-Z0-9_-]+)\s*=\s*["\']?([^"\'#\n]+)'
        for line in content.split('\n'):
            match = re.match(deps_pattern, line)
            if match and not line.strip().startswith('#'):
                pkg = match.group(1).lower()
                version = match.group(2).strip()
                if pkg != 'python':
                    packages[pkg] = version
    
    return packages

def get_import_names() -> Dict[str, Set[str]]:
    """Map package names to their import names."""
    # Common package name to import name mappings
    import_map = {
        'scikit-learn': {'sklearn'},
        'pillow': {'PIL'},
        'python-dotenv': {'dotenv'},
        'python-multipart': {'multipart'},
        'python-arango': {'arango'},
        'python-levenshtein': {'Levenshtein'},
        'google-api-python-client': {'googleapiclient', 'google_auth_httplib2', 'google_auth_oauthlib'},
        'google-auth-httplib2': {'httplib2'},
        'google-auth-oauthlib': {'google_auth_oauthlib'},
        'pytorch': {'torch'},
        'types-requests': set(),  # Type stubs, no runtime imports
        'pandas-stubs': set(),  # Type stubs
        'types-tqdm': set(),  # Type stubs
        'pytest-cov': {'pytest_cov'},
        'pytest-mock': {'pytest_mock'},
        'pytest-asyncio': {'pytest_asyncio'},
        'requests-mock': {'requests_mock'},
        'sphinx-rtd-theme': {'sphinx_rtd_theme'},
        'sphinx-autodoc-typehints': {'sphinx_autodoc_typehints'},
        'myst-parser': {'myst_parser'},
        'sphinxcontrib-mermaid': {'sphinxcontrib'},
        'libchebipy': {'libchebipy'},
        'dspy-ai': {'dspy'},
        'matplotlib-venn': {'matplotlib_venn'},
        'pydantic-settings': {'pydantic_settings'},
        'qdrant-client': {'qdrant_client'},
        'sentence-transformers': {'sentence_transformers'},
        'faiss-cpu': {'faiss'},
        'phenome-arivale': {'phenome_arivale', 'phenome'},
    }
    
    # For packages not in the map, use the package name itself
    return import_map

def find_imports_in_file(filepath: Path) -> Set[str]:
    """Extract all imports from a Python file."""
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except Exception as e:
        # Fallback to regex for files that can't be parsed
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find imports with regex
            import_patterns = [
                r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
            ]
            
            for line in content.split('\n'):
                line = line.strip()
                for pattern in import_patterns:
                    match = re.match(pattern, line)
                    if match:
                        imports.add(match.group(1))
        except:
            pass
    
    return imports

def find_all_imports(src_dirs: List[Path]) -> Set[str]:
    """Find all imports across the codebase."""
    all_imports = set()
    
    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
            
        for py_file in src_dir.rglob('*.py'):
            # Skip test files for initial analysis
            if 'test' not in str(py_file):
                imports = find_imports_in_file(py_file)
                all_imports.update(imports)
    
    return all_imports

def find_test_imports(test_dirs: List[Path]) -> Set[str]:
    """Find imports used only in tests."""
    test_imports = set()
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
            
        for py_file in test_dir.rglob('*.py'):
            imports = find_imports_in_file(py_file)
            test_imports.update(imports)
    
    return test_imports

def analyze_usage():
    """Main analysis function."""
    print("=" * 80)
    print("BioMapper Package Usage Analysis")
    print("=" * 80)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Define source directories
    src_dirs = [
        project_root / 'src',
    ]
    
    test_dirs = [
        project_root / 'tests',
    ]
    
    # Get all packages
    print("\n📦 Analyzing installed packages...")
    packages = get_installed_packages()
    print(f"Found {len(packages)} packages in pyproject.toml")
    
    # Get import mappings
    import_map = get_import_names()
    
    # Find all imports in source code
    print("\n🔍 Scanning source code for imports...")
    source_imports = find_all_imports(src_dirs)
    print(f"Found {len(source_imports)} unique imports in source code")
    
    # Find test imports
    print("\n🧪 Scanning test code for imports...")
    test_imports = find_test_imports(test_dirs)
    test_only_imports = test_imports - source_imports
    print(f"Found {len(test_only_imports)} imports used only in tests")
    
    # Analyze usage
    print("\n📊 Analyzing package usage...")
    
    used_packages = set()
    unused_packages = set()
    test_only_packages = set()
    type_stub_packages = set()
    
    for package, version in packages.items():
        # Get possible import names for this package
        if package in import_map:
            possible_imports = import_map[package]
        else:
            # Try common transformations
            possible_imports = {
                package,
                package.replace('-', '_'),
                package.replace('python-', ''),
                package.replace('-python', ''),
            }
        
        # Check if it's a type stub package
        if package.startswith('types-') or package.endswith('-stubs') or package.endswith('-types'):
            type_stub_packages.add(package)
            continue
        
        # Check if it's a build/dev tool
        if package in ['poetry-core', 'setuptools', 'wheel', 'pip', 'hatchling']:
            used_packages.add(package)  # Build tools are implicitly used
            continue
        
        # Check if used in source
        if any(imp in source_imports for imp in possible_imports):
            used_packages.add(package)
        # Check if used only in tests
        elif any(imp in test_only_imports for imp in possible_imports):
            test_only_packages.add(package)
        else:
            unused_packages.add(package)
    
    # Special handling for packages that are definitely used but hard to detect
    always_used = {
        'pytest', 'pytest-cov', 'pytest-mock', 'pytest-asyncio',  # Testing
        'mypy', 'ruff', 'vulture', 'autoflake',  # Linting/formatting
        'sphinx', 'sphinx-rtd-theme', 'sphinx-autodoc-typehints', 'myst-parser',  # Docs
        'jupyter', 'ipykernel',  # Development
        'uvicorn',  # Server runtime (used via CLI)
    }
    
    for pkg in always_used:
        if pkg in unused_packages:
            unused_packages.remove(pkg)
            used_packages.add(pkg)
    
    # Generate report
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    
    print(f"\n✅ Used Packages ({len(used_packages)}):")
    for pkg in sorted(used_packages):
        if pkg in packages:
            print(f"  • {pkg}: {packages[pkg]}")
    
    print(f"\n🧪 Test-Only Packages ({len(test_only_packages)}):")
    for pkg in sorted(test_only_packages):
        if pkg in packages:
            print(f"  • {pkg}: {packages[pkg]}")
    
    print(f"\n📝 Type Stub Packages ({len(type_stub_packages)}):")
    for pkg in sorted(type_stub_packages):
        if pkg in packages:
            print(f"  • {pkg}: {packages[pkg]}")
    
    print(f"\n⚠️  Potentially Unused Packages ({len(unused_packages)}):")
    for pkg in sorted(unused_packages):
        if pkg in packages:
            print(f"  • {pkg}: {packages[pkg]}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if unused_packages:
        print("\n🔍 Packages to investigate for removal:")
        for pkg in sorted(unused_packages):
            print(f"  • {pkg}")
            if pkg == 'venn':
                print("    Note: Might be used for Venn diagram visualizations")
            elif pkg == 'upsetplot':
                print("    Note: Might be used for upset plot visualizations")
            elif pkg == 'cloudpickle':
                print("    Note: Might be used for serialization")
            elif pkg == 'chardet':
                print("    Note: Might be used for encoding detection")
            elif pkg == 'odfpy':
                print("    Note: Might be used for OpenDocument format support")
            elif pkg == 'respx':
                print("    Note: Used for async HTTP mocking in tests")
            elif pkg == 'responses':
                print("    Note: Used for HTTP mocking in tests")
    
    print("\n💡 Next Steps:")
    print("1. Review 'Potentially Unused' packages - some might be used indirectly")
    print("2. Check if test-only packages can be moved to dev dependencies only")
    print("3. Verify type stub packages are still needed with current Python version")
    print("4. Run 'poetry check' after removing packages to ensure no conflicts")
    print("5. Run full test suite after any removals")
    
    # Save detailed report
    report_path = project_root / 'package_usage_report.json'
    report = {
        'total_packages': len(packages),
        'used_packages': sorted(list(used_packages)),
        'test_only_packages': sorted(list(test_only_packages)),
        'type_stub_packages': sorted(list(type_stub_packages)),
        'potentially_unused': sorted(list(unused_packages)),
        'source_imports': sorted(list(source_imports)),
        'test_only_imports': sorted(list(test_only_imports)),
    }
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")

if __name__ == "__main__":
    # Check if toml is available
    try:
        import toml
    except ImportError:
        print("Installing toml package for better parsing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "toml"], check=True)
        import toml
    
    analyze_usage()