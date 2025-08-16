#!/usr/bin/env python3
"""Audit biomapper codebase for algorithmic complexity issues."""

import sys
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.standards.complexity_checker import ComplexityChecker, ComplexityIssue


class ComplexityAuditor:
    """Audits codebase for algorithmic complexity issues."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.checker = ComplexityChecker()
        self.issues: List[ComplexityIssue] = []
        self.stats = {
            'files_scanned': 0,
            'total_issues': 0,
            'critical_issues': 0,
            'high_issues': 0,
            'medium_issues': 0,
            'low_issues': 0,
            'files_with_issues': []
        }
        
    def audit_all_actions(self) -> Dict[str, Any]:
        """Scan all action files for complexity issues."""
        actions_path = self.base_path / "biomapper" / "core" / "strategy_actions"
        
        # Find all Python files
        python_files = list(actions_path.rglob("*.py"))
        
        print(f"Scanning {len(python_files)} Python files for complexity issues...")
        
        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue
                
            self.stats['files_scanned'] += 1
            file_issues = self.checker.analyze_file(file_path)
            
            if file_issues:
                self.issues.extend(file_issues)
                self.stats['files_with_issues'].append(str(file_path.relative_to(self.base_path)))
                
                for issue in file_issues:
                    self.stats['total_issues'] += 1
                    if issue.severity == 'critical':
                        self.stats['critical_issues'] += 1
                    elif issue.severity == 'high':
                        self.stats['high_issues'] += 1
                    elif issue.severity == 'medium':
                        self.stats['medium_issues'] += 1
                    else:
                        self.stats['low_issues'] += 1
                        
        return self.stats
    
    def find_iterrows_usage(self) -> List[Dict[str, Any]]:
        """Find all DataFrame.iterrows() usage."""
        import subprocess
        
        cmd = ['grep', '-r', '--include=*.py', '.iterrows()', 
               str(self.base_path / "biomapper" / "core" / "strategy_actions")]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            lines = result.stdout.strip().split('\n') if result.stdout else []
            
            iterrows_usage = []
            for line in lines:
                if line and "__pycache__" not in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        file_path = parts[0]
                        code_line = parts[1]
                        iterrows_usage.append({
                            'file': file_path.replace(str(self.base_path) + '/', ''),
                            'code': code_line.strip()
                        })
                        
            return iterrows_usage
        except Exception as e:
            print(f"Error finding iterrows usage: {e}")
            return []
    
    def find_nested_loops(self) -> List[Dict[str, Any]]:
        """Find nested for loops that might be O(n*m)."""
        import subprocess
        
        # First find files with multiple for loops
        cmd = ['grep', '-r', '--include=*.py', '-l', 'for .* in', 
               str(self.base_path / "biomapper" / "core" / "strategy_actions")]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            files = result.stdout.strip().split('\n') if result.stdout else []
            
            nested_loops = []
            for file_path in files:
                if file_path and "__pycache__" not in file_path:
                    # Check each file for nested loops
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines):
                        if 'for ' in line and ' in ' in line:
                            # Check next few lines for another for loop
                            indent_level = len(line) - len(line.lstrip())
                            for j in range(i+1, min(i+10, len(lines))):
                                next_line = lines[j]
                                next_indent = len(next_line) - len(next_line.lstrip())
                                if 'for ' in next_line and ' in ' in next_line and next_indent > indent_level:
                                    nested_loops.append({
                                        'file': file_path.replace(str(self.base_path) + '/', ''),
                                        'line': i + 1,
                                        'outer_loop': line.strip(),
                                        'inner_loop': next_line.strip()
                                    })
                                    break
                                    
            return nested_loops
        except Exception as e:
            print(f"Error finding nested loops: {e}")
            return []
    
    def generate_report(self) -> str:
        """Generate a detailed audit report."""
        report = []
        report.append("=" * 80)
        report.append("ALGORITHMIC COMPLEXITY AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Base Path: {self.base_path}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Files Scanned: {self.stats['files_scanned']}")
        report.append(f"Total Issues Found: {self.stats['total_issues']}")
        report.append(f"  - Critical: {self.stats['critical_issues']}")
        report.append(f"  - High: {self.stats['high_issues']}")
        report.append(f"  - Medium: {self.stats['medium_issues']}")
        report.append(f"  - Low: {self.stats['low_issues']}")
        report.append("")
        
        # Critical issues detail
        if self.stats['critical_issues'] > 0:
            report.append("CRITICAL ISSUES (Must Fix)")
            report.append("-" * 40)
            for issue in self.issues:
                if issue.severity == 'critical':
                    report.append(f"\nFile: {issue.file_path}")
                    report.append(f"Function: {issue.function_name}")
                    report.append(f"Line: {issue.line_number}")
                    report.append(f"Type: {issue.issue_type}")
                    report.append(f"Description: {issue.description}")
                    report.append(f"Complexity: {issue.estimated_complexity}")
                    report.append(f"Fix: {issue.suggested_fix}")
            report.append("")
        
        # High priority issues
        if self.stats['high_issues'] > 0:
            report.append("HIGH PRIORITY ISSUES")
            report.append("-" * 40)
            for issue in self.issues:
                if issue.severity == 'high':
                    report.append(f"\nFile: {issue.file_path}")
                    report.append(f"Function: {issue.function_name}")
                    report.append(f"Line: {issue.line_number}")
                    report.append(f"Type: {issue.issue_type}")
                    report.append(f"Description: {issue.description}")
                    report.append(f"Fix: {issue.suggested_fix}")
            report.append("")
        
        # DataFrame.iterrows() usage
        iterrows_usage = self.find_iterrows_usage()
        if iterrows_usage:
            report.append("DATAFRAME.ITERROWS() USAGE")
            report.append("-" * 40)
            report.append("Consider replacing with vectorized operations:")
            for usage in iterrows_usage[:10]:  # Show first 10
                report.append(f"\n{usage['file']}")
                report.append(f"  {usage['code']}")
            if len(iterrows_usage) > 10:
                report.append(f"\n... and {len(iterrows_usage) - 10} more occurrences")
            report.append("")
        
        # Nested loops
        nested_loops = self.find_nested_loops()
        if nested_loops:
            report.append("POTENTIAL NESTED LOOP ISSUES")
            report.append("-" * 40)
            for loop in nested_loops[:10]:  # Show first 10
                report.append(f"\n{loop['file']} (line {loop['line']})")
                report.append(f"  Outer: {loop['outer_loop']}")
                report.append(f"  Inner: {loop['inner_loop']}")
            if len(nested_loops) > 10:
                report.append(f"\n... and {len(nested_loops) - 10} more potential issues")
            report.append("")
        
        # Files with issues
        if self.stats['files_with_issues']:
            report.append("FILES WITH COMPLEXITY ISSUES")
            report.append("-" * 40)
            for file_path in sorted(set(self.stats['files_with_issues'])):
                report.append(f"  - {file_path}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        if self.stats['critical_issues'] > 0:
            report.append("1. URGENT: Fix all critical issues immediately")
            report.append("   These are causing severe performance degradation")
        if self.stats['high_issues'] > 0:
            report.append("2. HIGH: Address high priority issues this sprint")
        report.append("3. Replace DataFrame.iterrows() with vectorized operations")
        report.append("4. Use EfficientMatcher utilities for all matching operations")
        report.append("5. Add performance tests to prevent regressions")
        report.append("")
        
        return "\n".join(report)
    
    def save_report(self, output_path: Path):
        """Save audit report to file."""
        report = self.generate_report()
        output_path.write_text(report)
        
        # Also save JSON version for programmatic access
        json_path = output_path.with_suffix('.json')
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'issues': [
                {
                    'file': issue.file_path,
                    'function': issue.function_name,
                    'line': issue.line_number,
                    'type': issue.issue_type,
                    'description': issue.description,
                    'complexity': issue.estimated_complexity,
                    'fix': issue.suggested_fix,
                    'severity': issue.severity
                }
                for issue in self.issues
            ]
        }
        json_path.write_text(json.dumps(json_data, indent=2))
        
        print(f"Report saved to: {output_path}")
        print(f"JSON data saved to: {json_path}")


def main():
    """Run the complexity audit."""
    base_path = Path(__file__).parent.parent
    auditor = ComplexityAuditor(base_path)
    
    print("Starting algorithmic complexity audit...")
    stats = auditor.audit_all_actions()
    
    print("\nAudit complete!")
    print(f"Found {stats['total_issues']} issues in {len(stats['files_with_issues'])} files")
    
    if stats['critical_issues'] > 0:
        print(f"\n⚠️  WARNING: {stats['critical_issues']} CRITICAL issues found!")
        print("These are likely causing hours of unnecessary computation.")
    
    # Save report
    report_path = base_path / "audits" / "complexity_audit_report.txt"
    auditor.save_report(report_path)
    
    # Print summary
    print("\n" + auditor.generate_report())
    
    return 0 if stats['critical_issues'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())