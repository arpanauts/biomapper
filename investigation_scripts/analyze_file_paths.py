#!/usr/bin/env python3
"""
Analyze file path resolution issues in biomapper strategies.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


class FilePathAnalyzer:
    """Analyze file path issues in biomapper strategies."""

    def __init__(self, base_dir: str = "/home/ubuntu/biomapper"):
        self.base_dir = Path(base_dir)
        self.issues = []
        self.resolutions = []

    def analyze_all_strategies(self) -> Dict[str, Any]:
        """Analyze file paths in all strategy files."""

        results = {
            "total_strategies": 0,
            "strategies_with_issues": 0,
            "path_issues": [],
            "resolution_recommendations": [],
        }

        strategy_dir = self.base_dir / "configs" / "strategies"
        print(f"Analyzing strategies in: {strategy_dir}")

        if not strategy_dir.exists():
            print(f"Strategy directory does not exist: {strategy_dir}")
            return results

        for strategy_file in strategy_dir.rglob("*.yaml"):
            results["total_strategies"] += 1

            try:
                with open(strategy_file, "r") as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)

                issues = self.analyze_strategy_file_paths(
                    strategy_file, yaml_content, content
                )

                if issues:
                    results["strategies_with_issues"] += 1
                    results["path_issues"].extend(issues)

            except Exception as e:
                results["path_issues"].append(
                    {
                        "strategy_file": str(strategy_file),
                        "type": "yaml_parse_error",
                        "error": str(e),
                    }
                )

        # Generate resolutions
        results["resolution_recommendations"] = self.generate_path_resolutions(
            results["path_issues"]
        )

        return results

    def analyze_strategy_file_paths(
        self, strategy_file: Path, yaml_content: Dict, raw_content: str
    ) -> List[Dict]:
        """Analyze file paths in a single strategy."""

        issues = []

        # Extract file paths from different locations in YAML
        file_paths = self.extract_file_paths(yaml_content, raw_content)

        for path_info in file_paths:
            path_str = path_info["path"]
            location = path_info["location"]

            # Resolve path
            resolved_path = self.resolve_path(path_str)

            if resolved_path is None:
                issues.append(
                    {
                        "strategy_file": str(strategy_file),
                        "strategy_name": yaml_content.get("name", "unknown"),
                        "type": "path_not_found",
                        "original_path": path_str,
                        "location": location,
                        "severity": "CRITICAL",
                    }
                )
            elif not os.access(resolved_path, os.R_OK):
                issues.append(
                    {
                        "strategy_file": str(strategy_file),
                        "strategy_name": yaml_content.get("name", "unknown"),
                        "type": "path_not_readable",
                        "original_path": path_str,
                        "resolved_path": str(resolved_path),
                        "location": location,
                        "severity": "HIGH",
                    }
                )
            elif path_str.startswith("/procedure/data/"):
                # Absolute paths that might not exist in different environments
                issues.append(
                    {
                        "strategy_file": str(strategy_file),
                        "strategy_name": yaml_content.get("name", "unknown"),
                        "type": "hardcoded_absolute_path",
                        "original_path": path_str,
                        "location": location,
                        "severity": "MEDIUM",
                        "recommendation": "Use environment variables or relative paths",
                    }
                )

        return issues

    def extract_file_paths(self, yaml_content: Dict, raw_content: str) -> List[Dict]:
        """Extract file paths from YAML content."""

        paths = []

        # Check metadata source_files and target_files
        metadata = yaml_content.get("metadata", {})

        for source_file in metadata.get("source_files", []):
            if "path" in source_file:
                paths.append(
                    {"path": source_file["path"], "location": "metadata.source_files"}
                )

        for target_file in metadata.get("target_files", []):
            if "path" in target_file:
                paths.append(
                    {"path": target_file["path"], "location": "metadata.target_files"}
                )

        # Check parameters section
        parameters = yaml_content.get("parameters", {})
        for key, value in parameters.items():
            if isinstance(value, str) and (
                "/" in value or value.endswith((".csv", ".tsv", ".json", ".yaml"))
            ):
                paths.append({"path": value, "location": f"parameters.{key}"})

        # Check action parameters in steps
        for step in yaml_content.get("steps", []):
            action_params = step.get("action", {}).get("params", {})
            for param_name, param_value in action_params.items():
                if isinstance(param_value, str):
                    # Look for file path patterns
                    if (
                        param_value.startswith("/")
                        or param_value.endswith(
                            (".csv", ".tsv", ".json", ".yaml", ".txt")
                        )
                        or "file" in param_name.lower()
                        or "path" in param_name.lower()
                    ):
                        paths.append(
                            {
                                "path": param_value,
                                "location": f'steps.{step.get("name", "unknown")}.action.params.{param_name}',
                            }
                        )

        # Use regex to find additional file paths in raw content
        path_patterns = [
            r'["\']([/\w\-\.]+\.(?:csv|tsv|json|yaml|txt|tsv))["\']',
            r'["\'](/[\w\-\./]+)["\']',
            r"\${[^}]*}[/\w\-\.]+",  # Variable substitution paths
        ]

        for pattern in path_patterns:
            matches = re.finditer(pattern, raw_content)
            for match in matches:
                paths.append({"path": match.group(1), "location": "regex_match"})

        return paths

    def resolve_path(self, path_str: str) -> Optional[Path]:
        """Attempt to resolve a file path."""

        # Handle variable substitutions (basic)
        if "${" in path_str:
            # Replace common variables
            path_str = path_str.replace("${DATA_DIR}", "/procedure/data/local_data")
            path_str = path_str.replace("${CACHE_DIR}", "/tmp/biomapper/cache")
            path_str = path_str.replace("${OUTPUT_DIR}", "/tmp/biomapper/output")

        # Try absolute path first
        if path_str.startswith("/"):
            abs_path = Path(path_str)
            if abs_path.exists():
                return abs_path

        # Try relative to project root
        rel_path = self.base_dir / path_str.lstrip("/")
        if rel_path.exists():
            return rel_path

        # Try common data directories
        common_dirs = [
            self.base_dir / "data",
            self.base_dir / "configs" / "data",
            Path("/procedure/data/local_data"),
            Path("/tmp/biomapper/data"),
        ]

        for base_dir in common_dirs:
            if base_dir.exists():
                candidate = base_dir / Path(path_str).name
                if candidate.exists():
                    return candidate

        return None

    def generate_path_resolutions(self, path_issues: List[Dict]) -> List[Dict]:
        """Generate resolution recommendations for path issues."""

        resolutions = []

        # Group issues by type
        issues_by_type = {}
        for issue in path_issues:
            issue_type = issue["type"]
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # Generate type-specific resolutions
        if "path_not_found" in issues_by_type:
            resolutions.append(
                {
                    "issue_type": "path_not_found",
                    "count": len(issues_by_type["path_not_found"]),
                    "priority": "CRITICAL",
                    "solution": "Create missing files or update paths",
                    "implementation_steps": [
                        "1. Create data directory structure: mkdir -p /procedure/data/local_data",
                        "2. Download/generate missing data files",
                        "3. Update strategy files with correct paths",
                        "4. Add data existence validation to strategy loader",
                    ],
                    "affected_strategies": [
                        issue["strategy_name"]
                        for issue in issues_by_type["path_not_found"]
                    ],
                }
            )

        if "hardcoded_absolute_path" in issues_by_type:
            resolutions.append(
                {
                    "issue_type": "hardcoded_absolute_path",
                    "count": len(issues_by_type["hardcoded_absolute_path"]),
                    "priority": "HIGH",
                    "solution": "Replace with environment variables",
                    "implementation_steps": [
                        "1. Define DATA_DIR environment variable",
                        "2. Update strategy templates to use ${DATA_DIR}",
                        "3. Implement variable substitution in strategy loader",
                        "4. Create environment-specific configuration files",
                    ],
                    "affected_strategies": [
                        issue["strategy_name"]
                        for issue in issues_by_type["hardcoded_absolute_path"]
                    ],
                }
            )

        if "path_not_readable" in issues_by_type:
            resolutions.append(
                {
                    "issue_type": "path_not_readable",
                    "count": len(issues_by_type["path_not_readable"]),
                    "priority": "MEDIUM",
                    "solution": "Fix file permissions",
                    "implementation_steps": [
                        "1. Identify files with permission issues",
                        "2. Set appropriate read permissions: chmod 644 <file>",
                        "3. Verify user/group ownership is correct",
                        "4. Add permission checking to file validation",
                    ],
                }
            )

        return resolutions


def generate_file_path_report(analysis_results: Dict) -> str:
    """Generate comprehensive file path analysis report."""

    report = f"""# File Path Analysis Report

## Summary
- **Total Strategies Analyzed**: {analysis_results['total_strategies']}
- **Strategies with Path Issues**: {analysis_results['strategies_with_issues']}
- **Total Path Issues**: {len(analysis_results['path_issues'])}

## Issues by Severity
"""

    # Count issues by severity
    severity_counts = {}
    for issue in analysis_results["path_issues"]:
        severity = issue.get("severity", "UNKNOWN")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    for severity, count in sorted(
        severity_counts.items(),
        key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(x[0])
        if x[0] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        else 99,
    ):
        report += f"- **{severity}**: {count} issues\n"

    report += "\n## Detailed Issues\n"

    for issue in analysis_results["path_issues"][:10]:  # Show first 10
        strategy_name = issue.get("strategy_name", "unknown")
        issue_type = issue.get("type", "unknown")
        report += f"""
### {strategy_name} ({issue_type})
- **File**: `{issue.get('strategy_file', 'unknown')}`
- **Path**: `{issue.get('original_path', 'unknown')}`
- **Location**: `{issue.get('location', 'unknown')}`
- **Severity**: {issue.get('severity', 'UNKNOWN')}
"""
        if "resolved_path" in issue:
            report += f"- **Resolved To**: `{issue['resolved_path']}`\n"
        if "recommendation" in issue:
            report += f"- **Recommendation**: {issue['recommendation']}\n"

    if len(analysis_results["path_issues"]) > 10:
        report += (
            f"\n... and {len(analysis_results['path_issues']) - 10} more issues.\n"
        )

    report += "\n## Resolution Recommendations\n"

    for resolution in analysis_results["resolution_recommendations"]:
        report += f"""
### {resolution['issue_type']} ({resolution['priority']} Priority)
- **Affected Count**: {resolution['count']} issues
- **Solution**: {resolution['solution']}

**Implementation Steps:**
"""
        for step in resolution["implementation_steps"]:
            report += f"   {step}\n"

        if "affected_strategies" in resolution:
            unique_strategies = list(set(resolution["affected_strategies"]))[:5]
            report += f"\n**Affected Strategies**: {', '.join(unique_strategies)}\n"
            if len(resolution["affected_strategies"]) > 5:
                report += (
                    f"   ... and {len(resolution['affected_strategies']) - 5} more.\n"
                )

    return report


if __name__ == "__main__":
    analyzer = FilePathAnalyzer()
    results = analyzer.analyze_all_strategies()
    report = generate_file_path_report(results)

    with open("/tmp/file_path_analysis_report.md", "w") as f:
        f.write(report)

    print(
        "File path analysis complete. Report saved to /tmp/file_path_analysis_report.md"
    )
    print(
        f"Found {len(results['path_issues'])} path issues across {results['strategies_with_issues']} strategies"
    )
