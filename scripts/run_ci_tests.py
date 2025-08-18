#!/usr/bin/env python3
"""
Script to run tests in CI mode without external dependencies.

This script runs tests excluding those that require:
- External services (Qdrant, external APIs)
- Network access
- API server running locally

Usage:
    python scripts/run_ci_tests.py
    python scripts/run_ci_tests.py --with-performance
    python scripts/run_ci_tests.py --unit-only
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Exit code: {e.returncode}")
        if e.stdout:
            print(f"   STDOUT:\n{e.stdout}")
        if e.stderr:
            print(f"   STDERR:\n{e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run CI tests without external dependencies")
    parser.add_argument("--with-performance", action="store_true", 
                       help="Include performance tests")
    parser.add_argument("--unit-only", action="store_true",
                       help="Run only unit tests")
    parser.add_argument("--coverage", action="store_true", default=True,
                       help="Include coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Base pytest command
    pytest_cmd = ["poetry", "run", "pytest"]
    
    # CI markers to exclude
    exclude_markers = [
        "not requires_external_services",
        "not requires_api", 
        "not requires_qdrant",
        "not requires_network"
    ]
    
    if not args.with_performance:
        exclude_markers.append("not slow")
        exclude_markers.append("not performance")
    
    if args.unit_only:
        pytest_cmd.extend(["tests/unit/"])
    
    # Add marker exclusions
    pytest_cmd.extend(["-m", " and ".join(exclude_markers)])
    
    # Add coverage if requested
    if args.coverage:
        pytest_cmd.extend([
            "--cov=biomapper",
            "--cov=biomapper_client", 
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add verbosity
    if args.verbose:
        pytest_cmd.append("-v")
    else:
        pytest_cmd.append("-q")
    
    # Other useful flags for CI
    pytest_cmd.extend([
        "--tb=short",
        "--strict-markers",
        "-ra"  # Show all except passed
    ])
    
    print("🧪 Running biomapper CI tests")
    print(f"   Performance tests: {'✅' if args.with_performance else '❌'}")
    print(f"   Unit tests only: {'✅' if args.unit_only else '❌'}")
    print(f"   Coverage: {'✅' if args.coverage else '❌'}")
    
    success = run_command(pytest_cmd, "Running CI test suite")
    
    if success:
        print("\n🎉 All CI tests passed!")
        
        if args.coverage:
            print("\n📊 Coverage report generated in htmlcov/")
            
        print("\n✅ Tests are ready for CI/CD deployment")
    else:
        print("\n💥 Some tests failed")
        print("\n🔍 Check the output above for details")
        sys.exit(1)


if __name__ == "__main__":
    main()