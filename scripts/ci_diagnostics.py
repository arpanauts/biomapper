#!/usr/bin/env python3
"""
CI Diagnostics Script - Run this to check for common CI issues before pushing.

Usage:
    python scripts/ci_diagnostics.py
"""

import ast
import re
import sys
from pathlib import Path
from typing import List


def check_sqlalchemy_models() -> List[str]:
    """Check for BigInteger autoincrement issues in SQLAlchemy models."""
    issues = []
    models_dir = Path("biomapper-api/app/models")

    if not models_dir.exists():
        return issues

    for py_file in models_dir.glob("*.py"):
        content = py_file.read_text()

        # Look for BigInteger with autoincrement
        if "BigInteger" in content and "autoincrement=True" in content:
            # Parse the file to find specific issues
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                if "BigInteger" in line and "autoincrement" in line:
                    issues.append(
                        f"{py_file}:{i} - BigInteger with autoincrement "
                        "(SQLite needs Integer for autoincrement)"
                    )

    return issues


def check_mock_patches() -> List[str]:
    """Check for incorrect mock patches in tests."""
    issues = []
    test_patterns = [
        (
            r'@patch\(["\']biomapper_client\.progress\.tqdm',
            "Should patch 'tqdm.tqdm' not 'biomapper_client.progress.tqdm'",
        ),
        (
            r'@patch\(["\']biomapper_client\.progress\.Progress',
            "Should patch 'rich.progress.Progress' not 'biomapper_client.progress.Progress'",
        ),
        (
            r'@patch\(["\']biomapper_client\.progress\.(Label|HBox|IntProgress)',
            "Should patch 'ipywidgets.{name}' not 'biomapper_client.progress.{name}'",
        ),
    ]

    # Find all test files
    for test_file in Path(".").rglob("test_*.py"):
        if "/.venv/" in str(test_file) or "/venv/" in str(test_file):
            continue

        content = test_file.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern, message in test_patterns:
                if re.search(pattern, line):
                    issues.append(f"{test_file}:{i} - {message}")

    return issues


def check_async_mocking_issues() -> List[str]:
    """Check for async mocking and validation issues in tests."""
    issues = []

    # Patterns to detect async mocking problems
    async_patterns = [
        (r"MagicMock\(\).*await", "Use AsyncMock for async methods, not MagicMock"),
        (r"Mock\(\).*await", "Use AsyncMock for async methods, not Mock"),
        (
            r"return_value\s*=\s*Mock\(\).*async\s+def",
            "Mock return_value should be AsyncMock for async methods",
        ),
    ]

    # Find all test files
    for test_file in Path(".").rglob("test_*.py"):
        if "/.venv/" in str(test_file) or "/venv/" in str(test_file):
            continue

        content = test_file.read_text()
        lines = content.split("\n")

        # Check for missing ProgressEventType import
        if (
            "ProgressEventType" in content
            and "from biomapper_client.models" not in content
        ):
            issues.append(
                f"{test_file} - Uses ProgressEventType but missing import: "
                "from biomapper_client.models import ProgressEventType"
            )

        # Check for StrategyExecutionContext validation issues
        if "StrategyExecutionContext" in content:
            # Look for test creation without required fields
            # Need to handle multiline constructor calls
            constructor_matches = []
            for i, line in enumerate(lines):
                if "StrategyExecutionContext(" in line:
                    # Find the end of the constructor call
                    paren_count = line.count("(") - line.count(")")
                    j = i
                    constructor_block = line

                    while paren_count > 0 and j < len(lines) - 1:
                        j += 1
                        next_line = lines[j]
                        constructor_block += "\n" + next_line
                        paren_count += next_line.count("(") - next_line.count(")")

                    constructor_matches.append((i + 1, constructor_block))

            for line_num, constructor_block in constructor_matches:
                # Check if required fields are missing
                required_fields = [
                    "initial_identifier",
                    "current_identifier",
                    "ontology_type",
                ]
                missing_fields = [
                    field for field in required_fields if field not in constructor_block
                ]

                if (
                    missing_fields and "**" not in constructor_block
                ):  # Skip if using **kwargs
                    issues.append(
                        f"{test_file}:{line_num} - StrategyExecutionContext missing required fields: "
                        f"{', '.join(missing_fields)}"
                    )

        # Check for async mocking patterns
        for i, line in enumerate(lines, 1):
            for pattern, message in async_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"{test_file}:{i} - {message}")

    return issues


def check_test_isolation() -> List[str]:
    """Check for test isolation issues that can cause CI failures."""
    issues = []

    for test_file in Path(".").rglob("test_*.py"):
        if "/.venv/" in str(test_file) or "/venv/" in str(test_file):
            continue

        content = test_file.read_text()

        # Check for global state modifications without cleanup
        global_patterns = [
            (
                r"ACTION_REGISTRY\.clear\(\)",
                "Should restore ACTION_REGISTRY after clearing",
            ),
            (
                r"os\.environ\[",
                "Should use pytest monkeypatch for environment variables",
            ),
            (r"chdir\(", "Should restore working directory after changing"),
        ]

        for pattern, message in global_patterns:
            if re.search(pattern, content):
                # Check if there's cleanup
                if "restore" not in content and "monkeypatch" not in content:
                    issues.append(f"{test_file} - {message}")

    return issues


def check_import_style() -> List[str]:
    """Check for imports that happen inside methods (affects patching)."""
    info = []

    for py_file in Path(".").rglob("*.py"):
        if any(
            skip in str(py_file) for skip in [".venv", "venv", "__pycache__", ".git"]
        ):
            continue

        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for imports inside functions
                    for child in ast.walk(node):
                        if isinstance(child, (ast.Import, ast.ImportFrom)):
                            if hasattr(child, "lineno"):
                                module = (
                                    child.module
                                    if hasattr(child, "module")
                                    else "module"
                                )
                                info.append(
                                    f"{py_file}:{child.lineno} - Import '{module}' "
                                    f"inside method '{node.name}' (affects mock patching)"
                                )
        except:
            pass  # Skip files that can't be parsed

    return info[:10]  # Limit to first 10 to avoid spam


def check_database_cleanup() -> List[str]:
    """Check if tests properly clean up database files."""
    issues = []

    # Look for test files that might create databases
    for test_file in Path(".").rglob("test_*.py"):
        if "/.venv/" in str(test_file) or "/venv/" in str(test_file):
            continue

        content = test_file.read_text()

        # Check if file creates a database but doesn't clean up
        if ".db" in content or "create_engine" in content:
            if (
                "rm -f" not in content
                and "unlink()" not in content
                and "@pytest.fixture" not in content
            ):
                issues.append(
                    f"{test_file} - Creates database but may not clean up "
                    "(can cause test pollution)"
                )

    return issues


def check_environment_variables() -> List[str]:
    """Check for proper environment variable handling in tests."""
    issues = []
    required_test_env = ["LANGFUSE_ENABLED=false"]

    conftest_files = list(Path(".").rglob("conftest.py"))

    for env_var in required_test_env:
        key = env_var.split("=")[0]
        found = False

        for conftest in conftest_files:
            if key in conftest.read_text():
                found = True
                break

        if not found:
            issues.append(f"Missing test environment setup: {env_var}")

    return issues


def main():
    """Run all diagnostics."""
    print("🔍 Running CI Diagnostics...\n")

    all_issues = []

    # Run checks
    checks = [
        ("SQLAlchemy Models", check_sqlalchemy_models),
        ("Mock Patches", check_mock_patches),
        ("Async Mocking Issues", check_async_mocking_issues),
        ("Test Isolation", check_test_isolation),
        ("Database Cleanup", check_database_cleanup),
        ("Environment Variables", check_environment_variables),
    ]

    for name, check_func in checks:
        print(f"Checking {name}...")
        issues = check_func()
        if issues:
            print(f"  ⚠️  Found {len(issues)} issue(s):")
            for issue in issues[:5]:  # Show first 5
                print(f"    - {issue}")
            if len(issues) > 5:
                print(f"    ... and {len(issues) - 5} more")
            all_issues.extend(issues)
        else:
            print("  ✅ No issues found")
        print()

    # Optional: Show import style info
    if "--verbose" in sys.argv:
        print("ℹ️  Import Style Information (affects mock patching):")
        import_info = check_import_style()
        for info in import_info:
            print(f"  - {info}")
        print()

    # Summary
    if all_issues:
        print(f"❌ Found {len(all_issues)} total issue(s) that may cause CI failures")
        print("\n💡 Run with --verbose for more details about import patterns")
        return 1
    else:
        print("✅ No common CI issues detected!")
        print("\n💡 Run with --verbose for more details about import patterns")
        return 0


if __name__ == "__main__":
    sys.exit(main())
