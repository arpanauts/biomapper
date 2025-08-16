#!/usr/bin/env python3
"""Run three-level tests for biomapper components.

This script provides a convenient way to run tests at different levels:
- Level 1: Unit tests with minimal data (fast, isolated)
- Level 2: Integration tests with sample data (moderate, realistic)
- Level 3: Production subset tests (comprehensive, real data)

Usage:
    python scripts/run_three_level_tests.py [component] [--level N] [--verbose]
    
Examples:
    # Run all tests for protein actions
    python scripts/run_three_level_tests.py proteins
    
    # Run only level 1 (unit) tests
    python scripts/run_three_level_tests.py proteins --level 1
    
    # Run level 2 tests with verbose output
    python scripts/run_three_level_tests.py metabolites --level 2 --verbose
    
    # Run performance benchmarks
    python scripts/run_three_level_tests.py all --performance
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple
import json


class TestRunner:
    """Manages three-level test execution."""
    
    # Test level configurations
    LEVELS = {
        1: {
            'name': 'Unit',
            'marker': 'level1',
            'timeout': 60,
            'description': 'Fast unit tests with minimal synthetic data'
        },
        2: {
            'name': 'Integration', 
            'marker': 'level2',
            'timeout': 300,
            'description': 'Integration tests with sample data'
        },
        3: {
            'name': 'Production',
            'marker': 'level3',
            'timeout': 600,
            'description': 'Smoke tests with production data subset'
        }
    }
    
    # Component mappings
    COMPONENTS = {
        'proteins': 'tests/unit/core/strategy_actions/entities/proteins/',
        'metabolites': 'tests/unit/core/strategy_actions/entities/metabolites/',
        'chemistry': 'tests/unit/core/strategy_actions/entities/chemistry/',
        'algorithms': 'tests/unit/core/strategy_actions/algorithms/',
        'utils': 'tests/unit/core/strategy_actions/utils/',
        'io': 'tests/unit/core/strategy_actions/io/',
        'reports': 'tests/unit/core/strategy_actions/reports/',
        'all': 'tests/'
    }
    
    def __init__(self, verbose: bool = False):
        """Initialize test runner.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.results = []
    
    def run_tests(self, 
                 component: str,
                 level: Optional[int] = None,
                 performance: bool = False,
                 coverage: bool = False) -> int:
        """Run tests for specified component and level.
        
        Args:
            component: Component to test
            level: Specific level (1, 2, or 3) or None for all
            performance: Run performance benchmarks
            coverage: Generate coverage report
            
        Returns:
            Exit code (0 for success)
        """
        if component not in self.COMPONENTS:
            print(f"Error: Unknown component '{component}'")
            print(f"Available components: {', '.join(self.COMPONENTS.keys())}")
            return 1
        
        test_path = self.COMPONENTS[component]
        
        if level is not None:
            # Run specific level
            return self._run_level(component, level, test_path, performance, coverage)
        else:
            # Run all levels
            print(f"\n{'='*60}")
            print(f"Running all test levels for: {component}")
            print(f"{'='*60}\n")
            
            all_passed = True
            for lvl in [1, 2, 3]:
                result = self._run_level(component, lvl, test_path, performance, coverage)
                if result != 0:
                    all_passed = False
                    if lvl < 3:  # Don't stop on Level 3 failures (production data might not exist)
                        print(f"\n⚠️  Level {lvl} failed, skipping remaining levels")
                        break
            
            # Generate summary report
            self._generate_summary()
            
            return 0 if all_passed else 1
    
    def _run_level(self,
                  component: str,
                  level: int,
                  test_path: str,
                  performance: bool,
                  coverage: bool) -> int:
        """Run tests for a specific level.
        
        Args:
            component: Component name
            level: Test level (1, 2, or 3)
            test_path: Path to test directory
            performance: Include performance tests
            coverage: Generate coverage report
            
        Returns:
            Exit code
        """
        level_config = self.LEVELS[level]
        
        print(f"\n{'-'*60}")
        print(f"Level {level}: {level_config['name']} Tests")
        print(f"Description: {level_config['description']}")
        print(f"{'-'*60}\n")
        
        # Build pytest command
        cmd = ['poetry', 'run', 'pytest']
        
        # Add test path
        cmd.append(test_path)
        
        # Filter by level marker
        cmd.extend(['-k', f'test_{level_config["marker"]}_'])
        
        # Add performance tests if requested
        if performance:
            cmd[3] = cmd[3].replace('_', '_|test_performance_')
        
        # Add coverage if requested
        if coverage:
            cmd.extend([
                '--cov=biomapper',
                '--cov-report=term-missing',
                '--cov-report=html'
            ])
        
        # Add verbosity
        if self.verbose:
            cmd.append('-xvs')
        else:
            cmd.append('-q')
        
        # Add timeout
        cmd.extend(['--timeout', str(level_config['timeout'])])
        
        # Add JSON report for parsing
        report_file = f'test_report_level{level}.json'
        cmd.extend(['--json-report', '--json-report-file', report_file])
        
        # Run tests
        print(f"Running: {' '.join(cmd)}\n")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=not self.verbose)
        duration = time.time() - start_time
        
        # Parse results
        passed, failed, skipped = self._parse_results(report_file)
        
        # Store results
        self.results.append({
            'component': component,
            'level': level,
            'level_name': level_config['name'],
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'duration': duration,
            'exit_code': result.returncode
        })
        
        # Print summary
        if result.returncode == 0:
            print(f"\n✅ Level {level} PASSED ({passed} tests in {duration:.2f}s)")
        else:
            print(f"\n❌ Level {level} FAILED ({failed} failures out of {passed + failed} tests)")
            if not self.verbose and result.stderr:
                print("\nError output:")
                print(result.stderr.decode('utf-8'))
        
        if skipped > 0:
            print(f"   ⚠️  {skipped} tests skipped")
        
        return result.returncode
    
    def _parse_results(self, report_file: str) -> Tuple[int, int, int]:
        """Parse test results from JSON report.
        
        Args:
            report_file: Path to JSON report file
            
        Returns:
            Tuple of (passed, failed, skipped) counts
        """
        try:
            if Path(report_file).exists():
                with open(report_file) as f:
                    data = json.load(f)
                    summary = data.get('summary', {})
                    return (
                        summary.get('passed', 0),
                        summary.get('failed', 0),
                        summary.get('skipped', 0)
                    )
        except Exception:
            pass
        
        return (0, 0, 0)
    
    def _generate_summary(self):
        """Generate and print test summary report."""
        if not self.results:
            return
        
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}\n")
        
        # Overall statistics
        total_passed = sum(r['passed'] for r in self.results)
        total_failed = sum(r['failed'] for r in self.results)
        total_skipped = sum(r['skipped'] for r in self.results)
        total_duration = sum(r['duration'] for r in self.results)
        
        print(f"Total Tests Run: {total_passed + total_failed}")
        print(f"  ✅ Passed: {total_passed}")
        print(f"  ❌ Failed: {total_failed}")
        print(f"  ⚠️  Skipped: {total_skipped}")
        print(f"  ⏱️  Duration: {total_duration:.2f}s\n")
        
        # Level breakdown
        print("Level Breakdown:")
        for result in self.results:
            status = "✅" if result['exit_code'] == 0 else "❌"
            print(f"  {status} Level {result['level']} ({result['level_name']}): "
                  f"{result['passed']} passed, {result['failed']} failed, "
                  f"{result['skipped']} skipped ({result['duration']:.2f}s)")
        
        # Performance analysis
        if total_passed > 0:
            print(f"\nPerformance Metrics:")
            print(f"  Average test time: {total_duration / (total_passed + total_failed):.3f}s")
            
            for level in [1, 2, 3]:
                level_results = [r for r in self.results if r['level'] == level]
                if level_results:
                    level_tests = sum(r['passed'] + r['failed'] for r in level_results)
                    level_time = sum(r['duration'] for r in level_results)
                    if level_tests > 0:
                        print(f"  Level {level} avg: {level_time / level_tests:.3f}s per test")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run three-level tests for biomapper components',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'component',
        choices=list(TestRunner.COMPONENTS.keys()),
        help='Component to test'
    )
    
    parser.add_argument(
        '--level',
        type=int,
        choices=[1, 2, 3],
        help='Specific test level to run (1=unit, 2=integration, 3=production)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--performance', '-p',
        action='store_true',
        help='Include performance benchmarks'
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--list-components',
        action='store_true',
        help='List available components and exit'
    )
    
    args = parser.parse_args()
    
    if args.list_components:
        print("Available components:")
        for name, path in TestRunner.COMPONENTS.items():
            print(f"  {name:15} -> {path}")
        return 0
    
    # Run tests
    runner = TestRunner(verbose=args.verbose)
    return runner.run_tests(
        args.component,
        level=args.level,
        performance=args.performance,
        coverage=args.coverage
    )


if __name__ == '__main__':
    sys.exit(main())