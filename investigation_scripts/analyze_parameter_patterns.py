#!/usr/bin/env python3
"""
Parameter Pattern Analysis Script for Biomapper

Analyzes parameter usage patterns in biomapper strategies to identify:
- Variable substitution failures
- Environment variable resolution issues  
- Nested parameter references
- Type conversion requirements
- Validation issues
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any
import json
from collections import defaultdict


class ParameterPatternAnalyzer:
    """Analyze parameter usage patterns in biomapper strategies."""

    def __init__(self, base_dir: str = "/home/ubuntu/biomapper"):
        self.base_dir = Path(base_dir)
        self.patterns = {
            "variable_substitution": [],
            "environment_variables": [],
            "nested_references": [],
            "type_conversions": [],
            "validation_failures": [],
        }

    def analyze_all_strategies(self) -> Dict[str, Any]:
        """Analyze parameter patterns across all strategies."""

        results = {
            "total_strategies": 0,
            "strategies_with_parameters": 0,
            "parameter_patterns": defaultdict(list),
            "substitution_complexity": {},
            "validation_issues": [],
            "recommendations": [],
        }

        strategy_dir = self.base_dir / "configs" / "strategies"

        if not strategy_dir.exists():
            print(f"Warning: Strategy directory not found at {strategy_dir}")
            return results

        for strategy_file in strategy_dir.rglob("*.yaml"):
            results["total_strategies"] += 1

            try:
                with open(strategy_file, "r") as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)

                if self.has_parameters(yaml_content, content):
                    results["strategies_with_parameters"] += 1

                    patterns = self.analyze_strategy_parameters(
                        strategy_file, yaml_content, content
                    )

                    for pattern_type, pattern_data in patterns.items():
                        results["parameter_patterns"][pattern_type].extend(pattern_data)

            except Exception as e:
                results["validation_issues"].append(
                    {
                        "strategy_file": str(strategy_file),
                        "error_type": "yaml_parse_error",
                        "error": str(e),
                    }
                )

        # Analyze complexity and generate recommendations
        results["substitution_complexity"] = self.analyze_complexity(
            results["parameter_patterns"]
        )
        results["recommendations"] = self.generate_recommendations(results)

        return results

    def has_parameters(self, yaml_content: Dict, raw_content: str) -> bool:
        """Check if strategy uses parameters."""
        return (
            "parameters" in yaml_content or "${" in raw_content or "$(" in raw_content
        )

    def analyze_strategy_parameters(
        self, strategy_file: Path, yaml_content: Dict, raw_content: str
    ) -> Dict[str, List]:
        """Analyze parameter patterns in a single strategy."""

        patterns = defaultdict(list)
        strategy_name = yaml_content.get("name", strategy_file.stem)

        # 1. Variable substitution patterns
        var_patterns = re.findall(r"\$\{([^}]+)\}", raw_content)
        for var_pattern in var_patterns:
            patterns["variable_substitution"].append(
                {
                    "strategy": strategy_name,
                    "file": str(strategy_file),
                    "pattern": var_pattern,
                    "full_syntax": f"${{{var_pattern}}}",
                    "complexity": self.calculate_pattern_complexity(var_pattern),
                }
            )

        # 2. Environment variable patterns
        env_patterns = re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", raw_content)
        for env_var in env_patterns:
            patterns["environment_variables"].append(
                {
                    "strategy": strategy_name,
                    "variable": env_var,
                    "exists_in_env": env_var in os.environ,
                    "default_available": self.has_default_value(yaml_content, env_var),
                }
            )

        # 3. Nested reference patterns
        nested_patterns = re.findall(r"\$\{([^}]*\.[^}]*)\}", raw_content)
        for nested_pattern in nested_patterns:
            patterns["nested_references"].append(
                {
                    "strategy": strategy_name,
                    "pattern": nested_pattern,
                    "depth": nested_pattern.count("."),
                    "reference_type": self.classify_reference_type(nested_pattern),
                }
            )

        # 4. Type conversion requirements
        parameters = yaml_content.get("parameters", {})
        for param_name, param_value in parameters.items():
            patterns["type_conversions"].append(
                {
                    "strategy": strategy_name,
                    "parameter": param_name,
                    "value": param_value,
                    "inferred_type": self.infer_parameter_type(param_value),
                    "needs_conversion": self.needs_type_conversion(param_value),
                }
            )

        # 5. Validation requirements
        validation_issues = self.identify_validation_issues(yaml_content, raw_content)
        patterns["validation_failures"].extend(validation_issues)

        return patterns

    def calculate_pattern_complexity(self, pattern: str) -> int:
        """Calculate complexity score for a parameter pattern."""
        complexity = 0

        # Base complexity
        complexity += 1

        # Nested references (dots)
        complexity += pattern.count(".") * 2

        # Array indexing
        complexity += pattern.count("[") * 2

        # Function calls
        if "(" in pattern:
            complexity += 3

        # Environment variables
        if pattern.isupper() or pattern.startswith("ENV_"):
            complexity += 1

        return complexity

    def has_default_value(self, yaml_content: Dict, env_var: str) -> bool:
        """Check if environment variable has a default value defined."""
        parameters = yaml_content.get("parameters", {})

        # Check for default values in various forms
        default_patterns = [
            env_var.lower(),
            f"default_{env_var.lower()}",
            f"{env_var.lower()}_default",
        ]

        return any(pattern in parameters for pattern in default_patterns)

    def classify_reference_type(self, pattern: str) -> str:
        """Classify the type of nested reference."""
        if pattern.startswith("parameters."):
            return "parameter_reference"
        elif pattern.startswith("metadata."):
            return "metadata_reference"
        elif pattern.startswith("env."):
            return "environment_reference"
        elif "[" in pattern:
            return "array_reference"
        else:
            return "unknown_reference"

    def infer_parameter_type(self, value: Any) -> str:
        """Infer the intended type of a parameter value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, str):
            if value.lower() in ["true", "false"]:
                return "boolean_string"
            elif value.isdigit():
                return "integer_string"
            elif re.match(r"^\d+\.\d+$", value):
                return "float_string"
            elif "," in value or "[" in value:
                return "list_string"
            else:
                return "string"
        else:
            return "unknown"

    def needs_type_conversion(self, value: Any) -> bool:
        """Check if parameter value needs type conversion."""
        if isinstance(value, str):
            return (
                value.lower() in ["true", "false"]
                or value.isdigit()
                or re.match(r"^\d+\.\d+$", value)
                or ("," in value and not value.startswith("/"))
            )  # Exclude file paths
        return False

    def identify_validation_issues(
        self, yaml_content: Dict, raw_content: str
    ) -> List[Dict]:
        """Identify potential parameter validation issues."""
        issues = []
        strategy_name = yaml_content.get("name", "unknown")

        # Check for required parameters without defaults
        parameters = yaml_content.get("parameters", {})

        # Find parameter references in steps
        step_param_refs = set()
        for step in yaml_content.get("steps", []):
            step_content = yaml.dump(step)
            refs = re.findall(r"\$\{parameters\.([^}]+)\}", step_content)
            step_param_refs.update(refs)

        # Check if referenced parameters exist
        for ref in step_param_refs:
            if ref not in parameters:
                issues.append(
                    {
                        "strategy": strategy_name,
                        "type": "missing_parameter_definition",
                        "parameter": ref,
                        "severity": "HIGH",
                    }
                )

        # Check for circular references
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str) and f"${{{param_name}}}" in param_value:
                issues.append(
                    {
                        "strategy": strategy_name,
                        "type": "circular_reference",
                        "parameter": param_name,
                        "severity": "CRITICAL",
                    }
                )

        return issues

    def analyze_complexity(self, patterns: Dict[str, List]) -> Dict[str, Any]:
        """Analyze overall parameter complexity."""
        complexity_analysis = {
            "total_patterns": sum(
                len(pattern_list) for pattern_list in patterns.values()
            ),
            "complexity_distribution": defaultdict(int),
            "high_complexity_strategies": [],
            "most_complex_patterns": [],
        }

        # Analyze variable substitution complexity
        for pattern_data in patterns["variable_substitution"]:
            complexity = pattern_data["complexity"]
            complexity_analysis["complexity_distribution"][f"level_{complexity}"] += 1

            if complexity > 5:
                complexity_analysis["high_complexity_strategies"].append(
                    {
                        "strategy": pattern_data["strategy"],
                        "pattern": pattern_data["pattern"],
                        "complexity": complexity,
                    }
                )

        # Find most complex patterns
        all_patterns = patterns["variable_substitution"]
        sorted_patterns = sorted(
            all_patterns, key=lambda x: x["complexity"], reverse=True
        )
        complexity_analysis["most_complex_patterns"] = sorted_patterns[:10]

        return complexity_analysis

    def generate_recommendations(self, results: Dict[str, Any]) -> List[Dict]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Environment variable recommendations
        env_vars = results["parameter_patterns"]["environment_variables"]
        missing_env_vars = [ev for ev in env_vars if not ev["exists_in_env"]]

        if missing_env_vars:
            recommendations.append(
                {
                    "type": "environment_variables",
                    "priority": "HIGH",
                    "title": "Missing Environment Variables",
                    "description": f"Found {len(missing_env_vars)} undefined environment variables",
                    "action_items": [
                        "Create .env template file with required variables",
                        "Add default value handling in parameter resolver",
                        "Implement environment variable validation at startup",
                        "Document required environment variables",
                    ],
                    "affected_count": len(missing_env_vars),
                }
            )

        # Complex pattern recommendations
        high_complexity = results["substitution_complexity"][
            "high_complexity_strategies"
        ]
        if high_complexity:
            recommendations.append(
                {
                    "type": "complexity_reduction",
                    "priority": "MEDIUM",
                    "title": "High Complexity Parameter Patterns",
                    "description": f"Found {len(high_complexity)} high-complexity parameter patterns",
                    "action_items": [
                        "Simplify nested parameter references",
                        "Create intermediate parameter variables",
                        "Implement parameter preprocessing",
                        "Add validation for complex patterns",
                    ],
                    "affected_patterns": [p["pattern"] for p in high_complexity[:5]],
                }
            )

        # Validation issue recommendations
        validation_issues = results["parameter_patterns"]["validation_failures"]
        if validation_issues:
            critical_issues = [
                v for v in validation_issues if v.get("severity") == "CRITICAL"
            ]
            if critical_issues:
                recommendations.append(
                    {
                        "type": "validation_fixes",
                        "priority": "CRITICAL",
                        "title": "Critical Parameter Validation Issues",
                        "description": f"Found {len(critical_issues)} critical validation issues",
                        "action_items": [
                            "Fix circular parameter references",
                            "Add missing parameter definitions",
                            "Implement parameter dependency checking",
                            "Add comprehensive parameter validation",
                        ],
                        "critical_issues": critical_issues[:5],
                    }
                )

        return recommendations


def generate_parameter_analysis_report(results: Dict[str, Any]) -> str:
    """Generate comprehensive parameter analysis report."""

    report = f"""# Parameter Resolution Analysis Report

## Executive Summary
- **Total Strategies Analyzed**: {results['total_strategies']}
- **Strategies Using Parameters**: {results['strategies_with_parameters']}
- **Total Parameter Patterns**: {results['substitution_complexity']['total_patterns']}

## Parameter Pattern Distribution
"""

    for pattern_type, pattern_list in results["parameter_patterns"].items():
        report += f"- **{pattern_type.replace('_', ' ').title()}**: {len(pattern_list)} occurrences\n"

    report += "\n## Complexity Analysis\n"

    complexity_dist = results["substitution_complexity"]["complexity_distribution"]
    for level, count in sorted(complexity_dist.items()):
        report += f"- **{level.replace('_', ' ').title()}**: {count} patterns\n"

    report += "\n## Most Complex Parameter Patterns\n"

    for pattern in results["substitution_complexity"]["most_complex_patterns"][:5]:
        report += f"""
### {pattern['strategy']} 
- **Pattern**: `${{{pattern['pattern']}}}`
- **Complexity Score**: {pattern['complexity']}/10
"""

    report += "\n## Environment Variable Analysis\n"

    env_vars = results["parameter_patterns"]["environment_variables"]
    if env_vars:
        missing_count = sum(1 for ev in env_vars if not ev["exists_in_env"])
        report += f"- **Total Environment Variables**: {len(env_vars)}\n"
        report += f"- **Missing from Environment**: {missing_count}\n"
        report += f"- **Have Defaults**: {sum(1 for ev in env_vars if ev['default_available'])}\n"

        if missing_count > 0:
            report += "\n**Missing Variables:**\n"
            for ev in env_vars:
                if not ev["exists_in_env"]:
                    report += f"- `{ev['variable']}` (Strategy: {ev['strategy']})\n"

    report += "\n## Validation Issues\n"

    validation_issues = results["parameter_patterns"]["validation_failures"]
    if validation_issues:
        severity_counts = defaultdict(int)
        for issue in validation_issues:
            severity_counts[issue.get("severity", "UNKNOWN")] += 1

        for severity, count in sorted(severity_counts.items()):
            report += f"- **{severity}**: {count} issues\n"

        critical_issues = [
            v for v in validation_issues if v.get("severity") == "CRITICAL"
        ]
        if critical_issues:
            report += "\n**Critical Issues:**\n"
            for issue in critical_issues[:5]:
                report += f"- **{issue['type']}** in {issue['strategy']}: {issue.get('parameter', 'N/A')}\n"

    report += "\n## Recommendations\n"

    for rec in results["recommendations"]:
        report += f"""
### {rec['title']} ({rec['priority']} Priority)
{rec['description']}

**Action Items:**
"""
        for action in rec["action_items"]:
            report += f"1. {action}\n"

    return report


if __name__ == "__main__":
    analyzer = ParameterPatternAnalyzer()
    results = analyzer.analyze_all_strategies()
    report = generate_parameter_analysis_report(results)

    # Ensure output directory exists
    output_dir = Path("/tmp")
    output_dir.mkdir(exist_ok=True)

    with open("/tmp/parameter_analysis_report.md", "w") as f:
        f.write(report)

    print(
        "Parameter analysis complete. Report saved to /tmp/parameter_analysis_report.md"
    )
    print(
        f"Found {results['substitution_complexity']['total_patterns']} parameter patterns"
    )
    print(
        f"High priority recommendations: {len([r for r in results['recommendations'] if r['priority'] == 'HIGH'])}"
    )

    # Save detailed JSON results for further analysis
    with open("/tmp/parameter_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("Detailed results saved to /tmp/parameter_analysis_results.json")
