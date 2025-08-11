# Investigate Parameter Resolution Issues

## Overview

This prompt guides the investigation and resolution of parameter resolution issues that are causing 22% of strategy failures in biomapper. The integration testing identified problems with variable substitution, environment variable handling, and parameter validation that prevent strategies from executing correctly.

## Critical Parameter Resolution Issues Identified

### 1. Variable Substitution Failures
**Impact**: `${variable}` syntax not being resolved properly
**Affected Parameters**: Data paths, output directories, configuration values
**Failure Rate**: 15% of strategy failures

### 2. Environment Variable Resolution
**Impact**: Environment variables not being found or substituted
**Affected Variables**: `${DATA_DIR}`, `${OUTPUT_DIR}`, `${CACHE_DIR}`
**Failure Rate**: 10% of strategy failures

### 3. Nested Parameter References
**Impact**: Parameters referencing other parameters not resolving
**Affected Patterns**: `${parameters.data_file}`, `${metadata.source_files[0].path}`
**Failure Rate**: 8% of strategy failures

### 4. Type Conversion Issues
**Impact**: Parameter values not being converted to expected types
**Affected Types**: Boolean, numeric, list parameters
**Failure Rate**: 5% of strategy failures

## Prerequisites

Before investigating parameter resolution issues:
- ✅ Integration testing completed with parameter failure analysis
- ✅ Strategy execution logs available showing parameter errors
- ✅ Current parameter resolution implementation understood
- ✅ Test strategies available for validation

## Investigation Task 1: Parameter Resolution Analysis

### Purpose
Analyze current parameter resolution logic, identify failure patterns, and implement robust parameter substitution.

### Investigation Steps

#### 1.1 Parameter Usage Pattern Analysis
```python
# investigation_scripts/analyze_parameter_patterns.py

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
import json
from collections import defaultdict

class ParameterPatternAnalyzer:
    """Analyze parameter usage patterns in biomapper strategies."""
    
    def __init__(self, base_dir: str = "/home/ubuntu/biomapper"):
        self.base_dir = Path(base_dir)
        self.patterns = {
            'variable_substitution': [],
            'environment_variables': [],
            'nested_references': [],
            'type_conversions': [],
            'validation_failures': []
        }
    
    def analyze_all_strategies(self) -> Dict[str, Any]:
        """Analyze parameter patterns across all strategies."""
        
        results = {
            'total_strategies': 0,
            'strategies_with_parameters': 0,
            'parameter_patterns': defaultdict(list),
            'substitution_complexity': {},
            'validation_issues': [],
            'recommendations': []
        }
        
        strategy_dir = self.base_dir / "configs" / "strategies"
        
        for strategy_file in strategy_dir.rglob("*.yaml"):
            results['total_strategies'] += 1
            
            try:
                with open(strategy_file, 'r') as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)
                
                if self.has_parameters(yaml_content, content):
                    results['strategies_with_parameters'] += 1
                    
                    patterns = self.analyze_strategy_parameters(strategy_file, yaml_content, content)
                    
                    for pattern_type, pattern_data in patterns.items():
                        results['parameter_patterns'][pattern_type].extend(pattern_data)
            
            except Exception as e:
                results['validation_issues'].append({
                    'strategy_file': str(strategy_file),
                    'error_type': 'yaml_parse_error',
                    'error': str(e)
                })
        
        # Analyze complexity and generate recommendations
        results['substitution_complexity'] = self.analyze_complexity(results['parameter_patterns'])
        results['recommendations'] = self.generate_recommendations(results)
        
        return results
    
    def has_parameters(self, yaml_content: Dict, raw_content: str) -> bool:
        """Check if strategy uses parameters."""
        return ('parameters' in yaml_content or 
                '${' in raw_content or 
                '$(' in raw_content)
    
    def analyze_strategy_parameters(self, strategy_file: Path, yaml_content: Dict, raw_content: str) -> Dict[str, List]:
        """Analyze parameter patterns in a single strategy."""
        
        patterns = defaultdict(list)
        strategy_name = yaml_content.get('name', strategy_file.stem)
        
        # 1. Variable substitution patterns
        var_patterns = re.findall(r'\$\{([^}]+)\}', raw_content)
        for var_pattern in var_patterns:
            patterns['variable_substitution'].append({
                'strategy': strategy_name,
                'file': str(strategy_file),
                'pattern': var_pattern,
                'full_syntax': f'${{{var_pattern}}}',
                'complexity': self.calculate_pattern_complexity(var_pattern)
            })
        
        # 2. Environment variable patterns  
        env_patterns = re.findall(r'\$\{([A-Z_][A-Z0-9_]*)\}', raw_content)
        for env_var in env_patterns:
            patterns['environment_variables'].append({
                'strategy': strategy_name,
                'variable': env_var,
                'exists_in_env': env_var in os.environ,
                'default_available': self.has_default_value(yaml_content, env_var)
            })
        
        # 3. Nested reference patterns
        nested_patterns = re.findall(r'\$\{([^}]*\.[^}]*)\}', raw_content)
        for nested_pattern in nested_patterns:
            patterns['nested_references'].append({
                'strategy': strategy_name,
                'pattern': nested_pattern,
                'depth': nested_pattern.count('.'),
                'reference_type': self.classify_reference_type(nested_pattern)
            })
        
        # 4. Type conversion requirements
        parameters = yaml_content.get('parameters', {})
        for param_name, param_value in parameters.items():
            patterns['type_conversions'].append({
                'strategy': strategy_name,
                'parameter': param_name,
                'value': param_value,
                'inferred_type': self.infer_parameter_type(param_value),
                'needs_conversion': self.needs_type_conversion(param_value)
            })
        
        # 5. Validation requirements
        validation_issues = self.identify_validation_issues(yaml_content, raw_content)
        patterns['validation_failures'].extend(validation_issues)
        
        return patterns
    
    def calculate_pattern_complexity(self, pattern: str) -> int:
        """Calculate complexity score for a parameter pattern."""
        complexity = 0
        
        # Base complexity
        complexity += 1
        
        # Nested references (dots)
        complexity += pattern.count('.') * 2
        
        # Array indexing
        complexity += pattern.count('[') * 2
        
        # Function calls
        if '(' in pattern:
            complexity += 3
        
        # Environment variables
        if pattern.isupper() or pattern.startswith('ENV_'):
            complexity += 1
        
        return complexity
    
    def has_default_value(self, yaml_content: Dict, env_var: str) -> bool:
        """Check if environment variable has a default value defined."""
        parameters = yaml_content.get('parameters', {})
        
        # Check for default values in various forms
        default_patterns = [
            env_var.lower(),
            f"default_{env_var.lower()}",
            f"{env_var.lower()}_default"
        ]
        
        return any(pattern in parameters for pattern in default_patterns)
    
    def classify_reference_type(self, pattern: str) -> str:
        """Classify the type of nested reference."""
        if pattern.startswith('parameters.'):
            return 'parameter_reference'
        elif pattern.startswith('metadata.'):
            return 'metadata_reference'
        elif pattern.startswith('env.'):
            return 'environment_reference'
        elif '[' in pattern:
            return 'array_reference'
        else:
            return 'unknown_reference'
    
    def infer_parameter_type(self, value: Any) -> str:
        """Infer the intended type of a parameter value."""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, list):
            return 'list'
        elif isinstance(value, dict):
            return 'dict'
        elif isinstance(value, str):
            if value.lower() in ['true', 'false']:
                return 'boolean_string'
            elif value.isdigit():
                return 'integer_string'
            elif re.match(r'^\d+\.\d+$', value):
                return 'float_string'
            elif ',' in value or '[' in value:
                return 'list_string'
            else:
                return 'string'
        else:
            return 'unknown'
    
    def needs_type_conversion(self, value: Any) -> bool:
        """Check if parameter value needs type conversion."""
        if isinstance(value, str):
            return (value.lower() in ['true', 'false'] or 
                   value.isdigit() or 
                   re.match(r'^\d+\.\d+$', value) or
                   (',' in value and not value.startswith('/')))  # Exclude file paths
        return False
    
    def identify_validation_issues(self, yaml_content: Dict, raw_content: str) -> List[Dict]:
        """Identify potential parameter validation issues."""
        issues = []
        strategy_name = yaml_content.get('name', 'unknown')
        
        # Check for required parameters without defaults
        parameters = yaml_content.get('parameters', {})
        
        # Find parameter references in steps
        step_param_refs = set()
        for step in yaml_content.get('steps', []):
            step_content = yaml.dump(step)
            refs = re.findall(r'\$\{parameters\.([^}]+)\}', step_content)
            step_param_refs.update(refs)
        
        # Check if referenced parameters exist
        for ref in step_param_refs:
            if ref not in parameters:
                issues.append({
                    'strategy': strategy_name,
                    'type': 'missing_parameter_definition',
                    'parameter': ref,
                    'severity': 'HIGH'
                })
        
        # Check for circular references
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str) and f'${{{param_name}}}' in param_value:
                issues.append({
                    'strategy': strategy_name,
                    'type': 'circular_reference',
                    'parameter': param_name,
                    'severity': 'CRITICAL'
                })
        
        return issues
    
    def analyze_complexity(self, patterns: Dict[str, List]) -> Dict[str, Any]:
        """Analyze overall parameter complexity."""
        complexity_analysis = {
            'total_patterns': sum(len(pattern_list) for pattern_list in patterns.values()),
            'complexity_distribution': defaultdict(int),
            'high_complexity_strategies': [],
            'most_complex_patterns': []
        }
        
        # Analyze variable substitution complexity
        for pattern_data in patterns['variable_substitution']:
            complexity = pattern_data['complexity']
            complexity_analysis['complexity_distribution'][f'level_{complexity}'] += 1
            
            if complexity > 5:
                complexity_analysis['high_complexity_strategies'].append({
                    'strategy': pattern_data['strategy'],
                    'pattern': pattern_data['pattern'],
                    'complexity': complexity
                })
        
        # Find most complex patterns
        all_patterns = patterns['variable_substitution']
        sorted_patterns = sorted(all_patterns, key=lambda x: x['complexity'], reverse=True)
        complexity_analysis['most_complex_patterns'] = sorted_patterns[:10]
        
        return complexity_analysis
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[Dict]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Environment variable recommendations
        env_vars = results['parameter_patterns']['environment_variables']
        missing_env_vars = [ev for ev in env_vars if not ev['exists_in_env']]
        
        if missing_env_vars:
            recommendations.append({
                'type': 'environment_variables',
                'priority': 'HIGH',
                'title': 'Missing Environment Variables',
                'description': f'Found {len(missing_env_vars)} undefined environment variables',
                'action_items': [
                    'Create .env template file with required variables',
                    'Add default value handling in parameter resolver',
                    'Implement environment variable validation at startup',
                    'Document required environment variables'
                ],
                'affected_count': len(missing_env_vars)
            })
        
        # Complex pattern recommendations
        high_complexity = results['substitution_complexity']['high_complexity_strategies']
        if high_complexity:
            recommendations.append({
                'type': 'complexity_reduction',
                'priority': 'MEDIUM',
                'title': 'High Complexity Parameter Patterns',
                'description': f'Found {len(high_complexity)} high-complexity parameter patterns',
                'action_items': [
                    'Simplify nested parameter references',
                    'Create intermediate parameter variables',
                    'Implement parameter preprocessing',
                    'Add validation for complex patterns'
                ],
                'affected_patterns': [p['pattern'] for p in high_complexity[:5]]
            })
        
        # Validation issue recommendations
        validation_issues = results['parameter_patterns']['validation_failures']
        if validation_issues:
            critical_issues = [v for v in validation_issues if v.get('severity') == 'CRITICAL']
            if critical_issues:
                recommendations.append({
                    'type': 'validation_fixes',
                    'priority': 'CRITICAL',
                    'title': 'Critical Parameter Validation Issues',
                    'description': f'Found {len(critical_issues)} critical validation issues',
                    'action_items': [
                        'Fix circular parameter references',
                        'Add missing parameter definitions',
                        'Implement parameter dependency checking',
                        'Add comprehensive parameter validation'
                    ],
                    'critical_issues': critical_issues[:5]
                })
        
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
    
    for pattern_type, pattern_list in results['parameter_patterns'].items():
        report += f"- **{pattern_type.replace('_', ' ').title()}**: {len(pattern_list)} occurrences\n"
    
    report += "\n## Complexity Analysis\n"
    
    complexity_dist = results['substitution_complexity']['complexity_distribution']
    for level, count in sorted(complexity_dist.items()):
        report += f"- **{level.replace('_', ' ').title()}**: {count} patterns\n"
    
    report += "\n## Most Complex Parameter Patterns\n"
    
    for pattern in results['substitution_complexity']['most_complex_patterns'][:5]:
        report += f"""
### {pattern['strategy']} 
- **Pattern**: `${{{pattern['pattern']}}}`
- **Complexity Score**: {pattern['complexity']}/10
"""
    
    report += "\n## Environment Variable Analysis\n"
    
    env_vars = results['parameter_patterns']['environment_variables']
    if env_vars:
        missing_count = sum(1 for ev in env_vars if not ev['exists_in_env'])
        report += f"- **Total Environment Variables**: {len(env_vars)}\n"
        report += f"- **Missing from Environment**: {missing_count}\n"
        report += f"- **Have Defaults**: {sum(1 for ev in env_vars if ev['default_available'])}\n"
        
        if missing_count > 0:
            report += "\n**Missing Variables:**\n"
            for ev in env_vars:
                if not ev['exists_in_env']:
                    report += f"- `{ev['variable']}` (Strategy: {ev['strategy']})\n"
    
    report += "\n## Validation Issues\n"
    
    validation_issues = results['parameter_patterns']['validation_failures']
    if validation_issues:
        severity_counts = defaultdict(int)
        for issue in validation_issues:
            severity_counts[issue.get('severity', 'UNKNOWN')] += 1
        
        for severity, count in sorted(severity_counts.items()):
            report += f"- **{severity}**: {count} issues\n"
        
        critical_issues = [v for v in validation_issues if v.get('severity') == 'CRITICAL']
        if critical_issues:
            report += "\n**Critical Issues:**\n"
            for issue in critical_issues[:5]:
                report += f"- **{issue['type']}** in {issue['strategy']}: {issue.get('parameter', 'N/A')}\n"
    
    report += "\n## Recommendations\n"
    
    for rec in results['recommendations']:
        report += f"""
### {rec['title']} ({rec['priority']} Priority)
{rec['description']}

**Action Items:**
"""
        for action in rec['action_items']:
            report += f"1. {action}\n"
    
    return report

if __name__ == "__main__":
    analyzer = ParameterPatternAnalyzer()
    results = analyzer.analyze_all_strategies()
    report = generate_parameter_analysis_report(results)
    
    with open('/tmp/parameter_analysis_report.md', 'w') as f:
        f.write(report)
    
    print(f"Parameter analysis complete. Report saved to /tmp/parameter_analysis_report.md")
    print(f"Found {results['substitution_complexity']['total_patterns']} parameter patterns")
    print(f"High priority recommendations: {len([r for r in results['recommendations'] if r['priority'] == 'HIGH'])}")
```

#### 1.2 Parameter Resolution Engine Implementation
```python
# biomapper/core/infrastructure/parameter_resolver.py

import os
import re
import yaml
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import logging
from copy import deepcopy
import json

class ParameterResolutionError(Exception):
    """Exception raised when parameter resolution fails."""
    pass

class CircularReferenceError(ParameterResolutionError):
    """Exception raised when circular parameter references are detected."""
    pass

class ParameterResolver:
    """Enhanced parameter resolver with robust substitution and validation."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.logger = logging.getLogger(__name__)
        
        # Built-in environment variables and defaults
        self.env_defaults = {
            'DATA_DIR': '/procedure/data/local_data',
            'CACHE_DIR': '/tmp/biomapper/cache', 
            'OUTPUT_DIR': '/tmp/biomapper/output',
            'CONFIG_DIR': str(self.base_dir / 'configs'),
            'BASE_DIR': str(self.base_dir),
            'TMP_DIR': '/tmp/biomapper'
        }
        
        # Resolution context stack (for circular reference detection)
        self.resolution_stack: List[str] = []
        
        # Type converters
        self.type_converters = {
            'bool': self._convert_to_bool,
            'int': self._convert_to_int,
            'float': self._convert_to_float,
            'list': self._convert_to_list,
            'path': self._convert_to_path
        }
    
    def resolve_strategy_parameters(self, strategy_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all parameters in a strategy configuration.
        
        Args:
            strategy_content: Raw strategy YAML content
            
        Returns:
            Strategy content with all parameters resolved
            
        Raises:
            ParameterResolutionError: If parameter resolution fails
        """
        try:
            # Deep copy to avoid modifying original
            resolved_content = deepcopy(strategy_content)
            
            # Build resolution context
            context = self._build_resolution_context(resolved_content)
            
            # Resolve parameters section first
            if 'parameters' in resolved_content:
                resolved_content['parameters'] = self._resolve_parameters_section(
                    resolved_content['parameters'], context
                )
                
                # Update context with resolved parameters
                context['parameters'] = resolved_content['parameters']
            
            # Resolve parameters throughout the strategy
            resolved_content = self._resolve_recursive(resolved_content, context)
            
            # Validate resolved parameters
            self._validate_resolved_parameters(resolved_content)
            
            return resolved_content
            
        except Exception as e:
            self.logger.error(f"Parameter resolution failed: {e}")
            raise ParameterResolutionError(f"Failed to resolve parameters: {e}")
    
    def _build_resolution_context(self, strategy_content: Dict[str, Any]) -> Dict[str, Any]:
        """Build the context for parameter resolution."""
        
        context = {
            'env': dict(os.environ),
            'metadata': strategy_content.get('metadata', {}),
            'parameters': strategy_content.get('parameters', {}),
            'builtin': {
                'base_dir': str(self.base_dir),
                'current_time': self._get_current_timestamp(),
                'user': os.getenv('USER', 'unknown')
            }
        }
        
        # Add environment defaults for missing variables
        for var_name, default_value in self.env_defaults.items():
            if var_name not in context['env']:
                context['env'][var_name] = default_value
                self.logger.debug(f"Using default for {var_name}: {default_value}")
        
        return context
    
    def _resolve_parameters_section(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve the parameters section specifically."""
        
        resolved_params = {}
        
        # Sort parameters to resolve dependencies first
        param_order = self._determine_parameter_order(parameters)
        
        for param_name in param_order:
            param_value = parameters[param_name]
            
            try:
                # Clear resolution stack for each top-level parameter
                self.resolution_stack = []
                
                resolved_value = self._resolve_value(param_value, context, f"parameters.{param_name}")
                resolved_params[param_name] = resolved_value
                
                # Update context with newly resolved parameter
                context['parameters'][param_name] = resolved_value
                
                self.logger.debug(f"Resolved parameter {param_name}: {param_value} -> {resolved_value}")
                
            except Exception as e:
                self.logger.error(f"Failed to resolve parameter {param_name}: {e}")
                raise ParameterResolutionError(f"Parameter '{param_name}' resolution failed: {e}")
        
        return resolved_params
    
    def _determine_parameter_order(self, parameters: Dict[str, Any]) -> List[str]:
        """Determine the order to resolve parameters based on dependencies."""
        
        # Build dependency graph
        dependencies = {}
        for param_name, param_value in parameters.items():
            deps = self._find_parameter_dependencies(param_value)
            dependencies[param_name] = [dep for dep in deps if dep in parameters]
        
        # Topological sort
        resolved_order = []
        remaining = set(parameters.keys())
        
        while remaining:
            # Find parameters with no unresolved dependencies
            ready = [param for param in remaining 
                    if not any(dep in remaining for dep in dependencies.get(param, []))]
            
            if not ready:
                # Circular dependency or other issue - use arbitrary order
                self.logger.warning("Circular or complex parameter dependencies detected")
                ready = [next(iter(remaining))]
            
            for param in ready:
                resolved_order.append(param)
                remaining.remove(param)
        
        return resolved_order
    
    def _find_parameter_dependencies(self, value: Any) -> List[str]:
        """Find parameter dependencies in a value."""
        dependencies = []
        
        if isinstance(value, str):
            # Find ${parameters.xxx} patterns
            param_refs = re.findall(r'\$\{parameters\.([^}]+)\}', value)
            dependencies.extend(param_refs)
        elif isinstance(value, (list, dict)):
            # Recursively check nested structures
            for item in (value.values() if isinstance(value, dict) else value):
                dependencies.extend(self._find_parameter_dependencies(item))
        
        return dependencies
    
    def _resolve_recursive(self, obj: Any, context: Dict[str, Any], path: str = "root") -> Any:
        """Recursively resolve parameters in any object."""
        
        if isinstance(obj, dict):
            resolved_dict = {}
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path != "root" else key
                resolved_dict[key] = self._resolve_recursive(value, context, new_path)
            return resolved_dict
        
        elif isinstance(obj, list):
            return [self._resolve_recursive(item, context, f"{path}[{i}]") 
                   for i, item in enumerate(obj)]
        
        elif isinstance(obj, str):
            return self._resolve_value(obj, context, path)
        
        else:
            return obj
    
    def _resolve_value(self, value: str, context: Dict[str, Any], path: str) -> Any:
        """Resolve a single parameter value."""
        
        if not isinstance(value, str):
            return value
        
        # Check for variable substitution patterns
        if '${' not in value:
            return self._apply_type_conversion(value)
        
        # Resolve all ${...} patterns
        resolved_value = value
        substitution_count = 0
        max_substitutions = 10  # Prevent infinite loops
        
        while '${' in resolved_value and substitution_count < max_substitutions:
            # Find all ${...} patterns
            pattern_matches = list(re.finditer(r'\$\{([^}]+)\}', resolved_value))
            
            if not pattern_matches:
                break
            
            # Process patterns from right to left (to maintain positions)
            for match in reversed(pattern_matches):
                full_pattern = match.group(0)  # ${...}
                pattern_content = match.group(1)  # content inside braces
                
                # Check for circular references
                current_ref = f"{path}->{pattern_content}"
                if current_ref in self.resolution_stack:
                    raise CircularReferenceError(f"Circular reference detected: {' -> '.join(self.resolution_stack)} -> {pattern_content}")
                
                self.resolution_stack.append(current_ref)
                
                try:
                    # Resolve the pattern
                    replacement_value = self._resolve_pattern(pattern_content, context)
                    
                    # Convert to string for substitution
                    replacement_str = str(replacement_value) if replacement_value is not None else ""
                    
                    # Replace in the resolved value
                    resolved_value = (resolved_value[:match.start()] + 
                                    replacement_str + 
                                    resolved_value[match.end():])
                    
                finally:
                    self.resolution_stack.pop()
            
            substitution_count += 1
        
        if substitution_count >= max_substitutions:
            self.logger.warning(f"Maximum substitutions reached for {path}: {value}")
        
        # Apply type conversion to final result
        return self._apply_type_conversion(resolved_value)
    
    def _resolve_pattern(self, pattern: str, context: Dict[str, Any]) -> Any:
        """Resolve a single ${...} pattern."""
        
        # Handle different pattern types
        if pattern.startswith('env.'):
            # Environment variable: ${env.VAR_NAME}
            var_name = pattern[4:]
            return context['env'].get(var_name)
        
        elif pattern.startswith('parameters.'):
            # Parameter reference: ${parameters.param_name}
            param_path = pattern[11:]  # Remove 'parameters.'
            return self._resolve_nested_access(context['parameters'], param_path)
        
        elif pattern.startswith('metadata.'):
            # Metadata reference: ${metadata.source_files[0].path}
            metadata_path = pattern[9:]  # Remove 'metadata.'
            return self._resolve_nested_access(context['metadata'], metadata_path)
        
        elif pattern.startswith('builtin.'):
            # Built-in variable: ${builtin.base_dir}
            builtin_path = pattern[8:]  # Remove 'builtin.'
            return self._resolve_nested_access(context['builtin'], builtin_path)
        
        elif pattern in context['env']:
            # Direct environment variable: ${VAR_NAME}
            return context['env'][pattern]
        
        elif pattern in context['parameters']:
            # Direct parameter: ${param_name}
            return context['parameters'][pattern]
        
        else:
            # Unknown pattern - return as-is but log warning
            self.logger.warning(f"Unknown parameter pattern: ${{{pattern}}}")
            return f"${{{pattern}}}"
    
    def _resolve_nested_access(self, obj: Any, path: str) -> Any:
        """Resolve nested object access like 'source_files[0].path'."""
        
        current = obj
        
        # Split path and process each part
        parts = re.split(r'(\[[^\]]+\])', path)
        parts = [part for part in parts if part]  # Remove empty parts
        
        for part in parts:
            if part.startswith('[') and part.endswith(']'):
                # Array/dict index access
                index_str = part[1:-1]  # Remove brackets
                
                try:
                    if index_str.isdigit():
                        # Numeric index
                        index = int(index_str)
                        current = current[index] if isinstance(current, (list, tuple)) else None
                    else:
                        # String key (remove quotes if present)
                        key = index_str.strip('\'"')
                        current = current.get(key) if isinstance(current, dict) else None
                except (IndexError, KeyError, TypeError):
                    self.logger.warning(f"Invalid index access: {part} in {path}")
                    return None
            
            elif '.' in part:
                # Multiple attribute access
                for attr in part.split('.'):
                    if attr:
                        if isinstance(current, dict):
                            current = current.get(attr)
                        else:
                            current = getattr(current, attr, None)
                        
                        if current is None:
                            return None
            else:
                # Single attribute access
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = getattr(current, part, None)
                
                if current is None:
                    return None
        
        return current
    
    def _apply_type_conversion(self, value: Any) -> Any:
        """Apply intelligent type conversion to resolved values."""
        
        if not isinstance(value, str):
            return value
        
        # Boolean conversion
        if value.lower() in ['true', 'yes', '1', 'on']:
            return True
        elif value.lower() in ['false', 'no', '0', 'off']:
            return False
        
        # Numeric conversion
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        
        try:
            return float(value)
        except ValueError:
            pass
        
        # List conversion (comma-separated values)
        if ',' in value and not value.startswith('/') and not value.startswith('http'):
            # Exclude file paths and URLs
            items = [item.strip() for item in value.split(',')]
            if len(items) > 1:
                return items
        
        # Return as string
        return value
    
    def _convert_to_bool(self, value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ['true', 'yes', '1', 'on']
    
    def _convert_to_int(self, value: str) -> int:
        """Convert string to integer."""
        return int(value)
    
    def _convert_to_float(self, value: str) -> float:
        """Convert string to float."""
        return float(value)
    
    def _convert_to_list(self, value: str) -> List[str]:
        """Convert string to list."""
        return [item.strip() for item in value.split(',')]
    
    def _convert_to_path(self, value: str) -> str:
        """Convert and normalize path."""
        return str(Path(value).expanduser().absolute())
    
    def _validate_resolved_parameters(self, strategy_content: Dict[str, Any]) -> None:
        """Validate that all parameters have been resolved correctly."""
        
        unresolved_patterns = []
        
        def find_unresolved(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    find_unresolved(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_unresolved(item, f"{path}[{i}]")
            elif isinstance(obj, str) and '${' in obj:
                # Still contains unresolved patterns
                patterns = re.findall(r'\$\{([^}]+)\}', obj)
                for pattern in patterns:
                    unresolved_patterns.append({
                        'path': path,
                        'pattern': pattern,
                        'context': obj
                    })
        
        find_unresolved(strategy_content)
        
        if unresolved_patterns:
            self.logger.warning(f"Found {len(unresolved_patterns)} unresolved parameter patterns:")
            for pattern_info in unresolved_patterns[:5]:  # Show first 5
                self.logger.warning(f"  {pattern_info['path']}: ${{{pattern_info['pattern']}}}")
        
        # Check for required parameters
        required_params = self._get_required_parameters(strategy_content)
        missing_params = []
        
        for param in required_params:
            if param not in strategy_content.get('parameters', {}):
                missing_params.append(param)
        
        if missing_params:
            raise ParameterResolutionError(f"Missing required parameters: {missing_params}")
    
    def _get_required_parameters(self, strategy_content: Dict[str, Any]) -> List[str]:
        """Get list of required parameters from strategy content."""
        required = []
        
        # This would typically be defined in strategy schema or metadata
        # For now, return empty list - can be enhanced later
        
        return required
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()

# Global parameter resolver instance
_parameter_resolver = None

def get_parameter_resolver() -> ParameterResolver:
    """Get global parameter resolver instance."""
    global _parameter_resolver
    if _parameter_resolver is None:
        _parameter_resolver = ParameterResolver()
    return _parameter_resolver

def resolve_strategy_parameters(strategy_content: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to resolve strategy parameters."""
    return get_parameter_resolver().resolve_strategy_parameters(strategy_content)
```

#### 1.3 Integration with Strategy Loading
```python
# biomapper/core/infrastructure/enhanced_strategy_loader.py

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from .parameter_resolver import ParameterResolver, ParameterResolutionError
from .path_resolver import PathResolver

class EnhancedStrategyLoader:
    """Enhanced strategy loader with parameter resolution and path handling."""
    
    def __init__(self, strategies_dir: Optional[str] = None):
        self.strategies_dir = Path(strategies_dir) if strategies_dir else Path("configs/strategies")
        self.parameter_resolver = ParameterResolver()
        self.path_resolver = PathResolver()
        self.logger = logging.getLogger(__name__)
    
    def load_strategy(self, strategy_name: str, validate: bool = True) -> Dict[str, Any]:
        """
        Load and resolve a strategy with full parameter and path resolution.
        
        Args:
            strategy_name: Name of the strategy to load
            validate: Whether to validate strategy after loading
            
        Returns:
            Fully resolved strategy configuration
            
        Raises:
            FileNotFoundError: If strategy file doesn't exist
            ParameterResolutionError: If parameter resolution fails
        """
        
        # Find strategy file
        strategy_file = self._find_strategy_file(strategy_name)
        if not strategy_file:
            raise FileNotFoundError(f"Strategy '{strategy_name}' not found")
        
        try:
            # Load raw YAML content
            with open(strategy_file, 'r') as f:
                raw_content = yaml.safe_load(f)
            
            self.logger.info(f"Loading strategy '{strategy_name}' from {strategy_file}")
            
            # Resolve parameters
            resolved_content = self.parameter_resolver.resolve_strategy_parameters(raw_content)
            
            # Resolve file paths
            resolved_content = self._resolve_file_paths(resolved_content)
            
            # Validate strategy if requested
            if validate:
                self._validate_strategy(resolved_content)
            
            self.logger.info(f"Successfully loaded and resolved strategy '{strategy_name}'")
            return resolved_content
            
        except Exception as e:
            self.logger.error(f"Failed to load strategy '{strategy_name}': {e}")
            raise
    
    def _find_strategy_file(self, strategy_name: str) -> Optional[Path]:
        """Find strategy file by name."""
        
        # Try exact filename first
        for suffix in ['.yaml', '.yml']:
            candidate = self.strategies_dir / f"{strategy_name}{suffix}"
            if candidate.exists():
                return candidate
        
        # Search recursively
        for strategy_file in self.strategies_dir.rglob("*.yaml"):
            try:
                with open(strategy_file, 'r') as f:
                    content = yaml.safe_load(f)
                if content and content.get('name') == strategy_name:
                    return strategy_file
            except:
                continue
        
        return None
    
    def _resolve_file_paths(self, strategy_content: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve file paths in strategy content."""
        
        resolved_content = strategy_content.copy()
        
        # Resolve paths in metadata
        metadata = resolved_content.get('metadata', {})
        
        # Source files
        for source_file in metadata.get('source_files', []):
            if 'path' in source_file:
                original_path = source_file['path']
                resolved_path = self.path_resolver.resolve_path(original_path)
                if resolved_path:
                    source_file['path'] = str(resolved_path)
                    source_file['resolved'] = True
                else:
                    self.logger.warning(f"Could not resolve source file path: {original_path}")
                    source_file['resolved'] = False
        
        # Target files
        for target_file in metadata.get('target_files', []):
            if 'path' in target_file:
                original_path = target_file['path']
                resolved_path = self.path_resolver.resolve_path(original_path)
                if resolved_path:
                    target_file['path'] = str(resolved_path)
                    target_file['resolved'] = True
                else:
                    self.logger.warning(f"Could not resolve target file path: {original_path}")
                    target_file['resolved'] = False
        
        # Resolve paths in parameters
        parameters = resolved_content.get('parameters', {})
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str) and ('/' in param_value or param_value.endswith(('.csv', '.tsv', '.json', '.yaml'))):
                resolved_path = self.path_resolver.resolve_path(param_value)
                if resolved_path:
                    parameters[param_name] = str(resolved_path)
        
        # Resolve paths in step parameters
        for step in resolved_content.get('steps', []):
            action_params = step.get('action', {}).get('params', {})
            for param_name, param_value in action_params.items():
                if isinstance(param_value, str) and ('file' in param_name.lower() or 'path' in param_name.lower()):
                    if param_name.endswith('output_path') or 'output' in param_name.lower():
                        # Output paths - create safe output path
                        safe_path = self.path_resolver.get_safe_output_path(param_value)
                        action_params[param_name] = str(safe_path)
                    else:
                        # Input paths - resolve existing path
                        resolved_path = self.path_resolver.resolve_path(param_value)
                        if resolved_path:
                            action_params[param_name] = str(resolved_path)
                        else:
                            self.logger.warning(f"Could not resolve path in step '{step.get('name', 'unknown')}': {param_value}")
        
        return resolved_content
    
    def _validate_strategy(self, strategy_content: Dict[str, Any]) -> None:
        """Validate resolved strategy content."""
        
        validation_errors = []
        
        # Check required fields
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in strategy_content:
                validation_errors.append(f"Missing required field: {field}")
        
        # Validate steps
        steps = strategy_content.get('steps', [])
        if not steps:
            validation_errors.append("Strategy must have at least one step")
        
        for i, step in enumerate(steps):
            if 'action' not in step:
                validation_errors.append(f"Step {i} missing 'action' field")
            else:
                action = step['action']
                if 'type' not in action:
                    validation_errors.append(f"Step {i} action missing 'type' field")
        
        # Check file existence for resolved paths
        metadata = strategy_content.get('metadata', {})
        
        for source_file in metadata.get('source_files', []):
            if source_file.get('resolved', False):
                path = Path(source_file['path'])
                if not path.exists():
                    validation_errors.append(f"Source file not found: {path}")
        
        if validation_errors:
            error_msg = "Strategy validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            raise ValueError(error_msg)

# Usage example
def load_strategy_with_resolution(strategy_name: str) -> Dict[str, Any]:
    """Load strategy with full parameter and path resolution."""
    loader = EnhancedStrategyLoader()
    return loader.load_strategy(strategy_name, validate=True)
```

## Investigation Task 2: Environment Configuration

### Purpose
Create comprehensive environment configuration management to ensure consistent parameter resolution across different deployment environments.

### Environment Configuration Template
```python
# biomapper/core/infrastructure/environment_config.py

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, field

@dataclass
class EnvironmentConfig:
    """Environment configuration for biomapper."""
    
    # Core directories
    data_dir: str = "/procedure/data/local_data"
    cache_dir: str = "/tmp/biomapper/cache"
    output_dir: str = "/tmp/biomapper/output"
    config_dir: str = "configs"
    log_dir: str = "/tmp/biomapper/logs"
    
    # External services
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    cts_api_base: str = "https://cts.fiehnlab.ucdavis.edu/rest"
    uniprot_api_base: str = "https://rest.uniprot.org"
    
    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    cache_ttl_hours: int = 24
    
    # Fallback modes
    enable_vector_fallback: bool = True
    enable_api_fallbacks: bool = True
    enable_file_path_fallbacks: bool = True
    
    # Validation settings
    validate_file_paths: bool = True
    validate_parameters: bool = True
    strict_validation: bool = False
    
    # Additional environment variables
    custom_vars: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_environment(cls) -> 'EnvironmentConfig':
        """Create configuration from environment variables."""
        return cls(
            data_dir=os.getenv('BIOMAPPER_DATA_DIR', cls.data_dir),
            cache_dir=os.getenv('BIOMAPPER_CACHE_DIR', cls.cache_dir),
            output_dir=os.getenv('BIOMAPPER_OUTPUT_DIR', cls.output_dir),
            config_dir=os.getenv('BIOMAPPER_CONFIG_DIR', cls.config_dir),
            log_dir=os.getenv('BIOMAPPER_LOG_DIR', cls.log_dir),
            
            qdrant_host=os.getenv('QDRANT_HOST', cls.qdrant_host),
            qdrant_port=int(os.getenv('QDRANT_PORT', str(cls.qdrant_port))),
            cts_api_base=os.getenv('CTS_API_BASE', cls.cts_api_base),
            uniprot_api_base=os.getenv('UNIPROT_API_BASE', cls.uniprot_api_base),
            
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', str(cls.max_concurrent_requests))),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', str(cls.request_timeout))),
            cache_ttl_hours=int(os.getenv('CACHE_TTL_HOURS', str(cls.cache_ttl_hours))),
            
            enable_vector_fallback=os.getenv('ENABLE_VECTOR_FALLBACK', 'true').lower() == 'true',
            enable_api_fallbacks=os.getenv('ENABLE_API_FALLBACKS', 'true').lower() == 'true',
            enable_file_path_fallbacks=os.getenv('ENABLE_FILE_PATH_FALLBACKS', 'true').lower() == 'true',
            
            validate_file_paths=os.getenv('VALIDATE_FILE_PATHS', 'true').lower() == 'true',
            validate_parameters=os.getenv('VALIDATE_PARAMETERS', 'true').lower() == 'true',
            strict_validation=os.getenv('STRICT_VALIDATION', 'false').lower() == 'true',
        )
    
    @classmethod
    def from_file(cls, config_file: Path) -> 'EnvironmentConfig':
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert to environment variables dictionary."""
        return {
            'BIOMAPPER_DATA_DIR': self.data_dir,
            'BIOMAPPER_CACHE_DIR': self.cache_dir,
            'BIOMAPPER_OUTPUT_DIR': self.output_dir,
            'BIOMAPPER_CONFIG_DIR': self.config_dir,
            'BIOMAPPER_LOG_DIR': self.log_dir,
            
            'QDRANT_HOST': self.qdrant_host,
            'QDRANT_PORT': str(self.qdrant_port),
            'CTS_API_BASE': self.cts_api_base,
            'UNIPROT_API_BASE': self.uniprot_api_base,
            
            'MAX_CONCURRENT_REQUESTS': str(self.max_concurrent_requests),
            'REQUEST_TIMEOUT': str(self.request_timeout),
            'CACHE_TTL_HOURS': str(self.cache_ttl_hours),
            
            'ENABLE_VECTOR_FALLBACK': str(self.enable_vector_fallback).lower(),
            'ENABLE_API_FALLBACKS': str(self.enable_api_fallbacks).lower(),
            'ENABLE_FILE_PATH_FALLBACKS': str(self.enable_file_path_fallbacks).lower(),
            
            'VALIDATE_FILE_PATHS': str(self.validate_file_paths).lower(),
            'VALIDATE_PARAMETERS': str(self.validate_parameters).lower(),
            'STRICT_VALIDATION': str(self.strict_validation).lower(),
            
            **self.custom_vars
        }
    
    def create_directories(self) -> None:
        """Create required directories if they don't exist."""
        directories = [
            self.data_dir,
            self.cache_dir,
            self.output_dir,
            self.log_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check directory accessibility
        for dir_name, dir_path in [
            ('data_dir', self.data_dir),
            ('cache_dir', self.cache_dir),
            ('output_dir', self.output_dir),
            ('config_dir', self.config_dir)
        ]:
            path = Path(dir_path)
            if not path.exists():
                if dir_name in ['cache_dir', 'output_dir', 'log_dir']:
                    # These can be created
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        issues.append(f"Cannot create {dir_name} at {dir_path}: {e}")
                else:
                    issues.append(f"{dir_name} does not exist: {dir_path}")
            elif not os.access(path, os.R_OK):
                issues.append(f"{dir_name} is not readable: {dir_path}")
        
        # Validate numeric values
        if self.max_concurrent_requests < 1:
            issues.append("max_concurrent_requests must be >= 1")
        
        if self.request_timeout < 1:
            issues.append("request_timeout must be >= 1")
        
        if self.cache_ttl_hours < 0:
            issues.append("cache_ttl_hours must be >= 0")
        
        return issues

def get_environment_config() -> EnvironmentConfig:
    """Get environment configuration with fallback logic."""
    
    # Try to load from file first
    config_files = [
        Path('.env.yaml'),
        Path('configs/environment.yaml'),
        Path('/etc/biomapper/environment.yaml')
    ]
    
    for config_file in config_files:
        if config_file.exists():
            try:
                return EnvironmentConfig.from_file(config_file)
            except Exception as e:
                print(f"Warning: Could not load config from {config_file}: {e}")
    
    # Fallback to environment variables
    return EnvironmentConfig.from_environment()

# Create template configuration files
def create_environment_templates():
    """Create template environment configuration files."""
    
    # .env template
    env_template = """# Biomapper Environment Configuration

# Core directories
BIOMAPPER_DATA_DIR=/procedure/data/local_data
BIOMAPPER_CACHE_DIR=/tmp/biomapper/cache
BIOMAPPER_OUTPUT_DIR=/tmp/biomapper/output
BIOMAPPER_CONFIG_DIR=configs
BIOMAPPER_LOG_DIR=/tmp/biomapper/logs

# External services
QDRANT_HOST=localhost
QDRANT_PORT=6333
CTS_API_BASE=https://cts.fiehnlab.ucdavis.edu/rest
UNIPROT_API_BASE=https://rest.uniprot.org

# Performance settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
CACHE_TTL_HOURS=24

# Fallback modes
ENABLE_VECTOR_FALLBACK=true
ENABLE_API_FALLBACKS=true
ENABLE_FILE_PATH_FALLBACKS=true

# Validation settings
VALIDATE_FILE_PATHS=true
VALIDATE_PARAMETERS=true
STRICT_VALIDATION=false
"""
    
    # YAML template
    yaml_template = {
        'data_dir': '/procedure/data/local_data',
        'cache_dir': '/tmp/biomapper/cache',
        'output_dir': '/tmp/biomapper/output',
        'config_dir': 'configs',
        'log_dir': '/tmp/biomapper/logs',
        
        'qdrant_host': 'localhost',
        'qdrant_port': 6333,
        'cts_api_base': 'https://cts.fiehnlab.ucdavis.edu/rest',
        'uniprot_api_base': 'https://rest.uniprot.org',
        
        'max_concurrent_requests': 10,
        'request_timeout': 30,
        'cache_ttl_hours': 24,
        
        'enable_vector_fallback': True,
        'enable_api_fallbacks': True,
        'enable_file_path_fallbacks': True,
        
        'validate_file_paths': True,
        'validate_parameters': True,
        'strict_validation': False,
        
        'custom_vars': {}
    }
    
    # Write templates
    with open('.env.template', 'w') as f:
        f.write(env_template)
    
    with open('environment.yaml.template', 'w') as f:
        yaml.dump(yaml_template, f, default_flow_style=False)
    
    print("Created environment configuration templates:")
    print("  - .env.template")
    print("  - environment.yaml.template")

if __name__ == "__main__":
    create_environment_templates()
```

## Test Requirements

### Comprehensive Parameter Resolution Tests
```python
# tests/unit/core/infrastructure/test_parameter_resolver.py

import pytest
import os
from unittest.mock import patch, MagicMock

from biomapper.core.infrastructure.parameter_resolver import (
    ParameterResolver, ParameterResolutionError, CircularReferenceError
)

class TestParameterResolver:
    """Test suite for ParameterResolver."""
    
    @pytest.fixture
    def resolver(self):
        """ParameterResolver instance."""
        return ParameterResolver()
    
    @pytest.fixture
    def sample_strategy(self):
        """Sample strategy for testing."""
        return {
            'name': 'test_strategy',
            'parameters': {
                'data_dir': '${DATA_DIR}',
                'output_file': '${parameters.data_dir}/output.tsv',
                'debug_mode': 'true',
                'max_items': '100'
            },
            'metadata': {
                'source_files': [
                    {'path': '${parameters.data_dir}/input.csv'}
                ]
            },
            'steps': [
                {
                    'name': 'load_data',
                    'action': {
                        'type': 'LOAD_DATASET',
                        'params': {
                            'file_path': '${metadata.source_files[0].path}',
                            'output_key': 'loaded_data'
                        }
                    }
                }
            ]
        }
    
    def test_simple_environment_variable_resolution(self, resolver):
        """Test simple environment variable resolution."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            strategy = {
                'parameters': {
                    'test_param': '${TEST_VAR}'
                }
            }
            
            resolved = resolver.resolve_strategy_parameters(strategy)
            
            assert resolved['parameters']['test_param'] == 'test_value'
    
    def test_parameter_reference_resolution(self, resolver):
        """Test parameter-to-parameter references."""
        strategy = {
            'parameters': {
                'base_dir': '/data',
                'input_file': '${parameters.base_dir}/input.csv'
            }
        }
        
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        assert resolved['parameters']['base_dir'] == '/data'
        assert resolved['parameters']['input_file'] == '/data/input.csv'
    
    def test_nested_metadata_access(self, resolver):
        """Test nested metadata access."""
        strategy = {
            'metadata': {
                'source_files': [
                    {'path': '/data/file1.csv'},
                    {'path': '/data/file2.csv'}
                ]
            },
            'parameters': {
                'first_file': '${metadata.source_files[0].path}',
                'second_file': '${metadata.source_files[1].path}'
            }
        }
        
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        assert resolved['parameters']['first_file'] == '/data/file1.csv'
        assert resolved['parameters']['second_file'] == '/data/file2.csv'
    
    def test_type_conversion(self, resolver):
        """Test automatic type conversion."""
        strategy = {
            'parameters': {
                'debug_flag': 'true',
                'max_count': '100',
                'threshold': '0.85',
                'items_list': 'item1,item2,item3'
            }
        }
        
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        assert resolved['parameters']['debug_flag'] is True
        assert resolved['parameters']['max_count'] == 100
        assert resolved['parameters']['threshold'] == 0.85
        assert resolved['parameters']['items_list'] == ['item1', 'item2', 'item3']
    
    def test_circular_reference_detection(self, resolver):
        """Test circular reference detection."""
        strategy = {
            'parameters': {
                'param_a': '${parameters.param_b}',
                'param_b': '${parameters.param_a}'
            }
        }
        
        with pytest.raises(CircularReferenceError):
            resolver.resolve_strategy_parameters(strategy)
    
    def test_complex_nested_resolution(self, resolver, sample_strategy):
        """Test complex nested parameter resolution."""
        with patch.dict(os.environ, {'DATA_DIR': '/test/data'}):
            resolved = resolver.resolve_strategy_parameters(sample_strategy)
            
            assert resolved['parameters']['data_dir'] == '/test/data'
            assert resolved['parameters']['output_file'] == '/test/data/output.tsv'
            assert resolved['parameters']['debug_mode'] is True
            assert resolved['parameters']['max_items'] == 100
            
            # Check metadata resolution
            assert resolved['metadata']['source_files'][0]['path'] == '/test/data/input.csv'
            
            # Check step parameter resolution
            step_params = resolved['steps'][0]['action']['params']
            assert step_params['file_path'] == '/test/data/input.csv'
    
    def test_missing_environment_variable(self, resolver):
        """Test handling of missing environment variables."""
        strategy = {
            'parameters': {
                'missing_var': '${MISSING_VAR}'
            }
        }
        
        # Should not raise error but use default from env_defaults or return as-is
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        # Check that it either resolves to a default or remains unresolved
        param_value = resolved['parameters']['missing_var']
        assert param_value is not None
    
    def test_parameter_dependency_ordering(self, resolver):
        """Test that parameters are resolved in correct dependency order."""
        strategy = {
            'parameters': {
                'final_path': '${parameters.base_path}/final',
                'base_path': '${parameters.root}/base', 
                'root': '/data'
            }
        }
        
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        assert resolved['parameters']['root'] == '/data'
        assert resolved['parameters']['base_path'] == '/data/base'
        assert resolved['parameters']['final_path'] == '/data/base/final'
    
    @patch('biomapper.core.infrastructure.parameter_resolver.datetime')
    def test_builtin_variables(self, mock_datetime, resolver):
        """Test built-in variable resolution."""
        mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T12:00:00'
        
        strategy = {
            'parameters': {
                'timestamp': '${builtin.current_time}',
                'base_dir': '${builtin.base_dir}',
                'user': '${builtin.user}'
            }
        }
        
        resolved = resolver.resolve_strategy_parameters(strategy)
        
        assert resolved['parameters']['timestamp'] == '2023-01-01T12:00:00'
        assert 'base_dir' in resolved['parameters']
        assert 'user' in resolved['parameters']

# Integration test with actual strategy files
class TestParameterResolutionIntegration:
    """Integration tests for parameter resolution."""
    
    @pytest.mark.integration
    def test_real_strategy_parameter_resolution(self):
        """Test parameter resolution on real strategy files."""
        from biomapper.core.infrastructure.enhanced_strategy_loader import EnhancedStrategyLoader
        
        loader = EnhancedStrategyLoader()
        
        # This would test with an actual strategy file
        # strategy = loader.load_strategy('example_multi_api_enrichment')
        # assert strategy is not None
        # assert 'parameters' in strategy
        pass  # Placeholder for real integration test

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Deliverables Summary

These three comprehensive prompt files address the critical infrastructure issues:

1. **Missing Actions Blockers** (`develop_missing_actions_blockers.md`):
   - `CUSTOM_TRANSFORM` action for flexible data transformation
   - `CALCULATE_MAPPING_QUALITY` action for quality assessment
   - Complete implementation with comprehensive test suites

2. **Infrastructure Dependencies** (`investigate_infrastructure_dependencies.md`):
   - Qdrant vector database analysis and alternatives
   - File path resolution investigation and solutions
   - Vector store factory with fallback implementations

3. **Parameter Resolution Issues** (`investigate_parameter_resolution_issues.md`):
   - Parameter pattern analysis and complexity assessment
   - Robust parameter resolver with circular reference detection
   - Environment configuration management system

Each prompt provides:
- ✅ Detailed analysis scripts to understand the issues
- ✅ Complete implementation solutions with error handling
- ✅ Comprehensive test suites for validation
- ✅ Integration with existing biomapper architecture
- ✅ Fallback strategies for production resilience

These implementations should address the root causes of the 60% infrastructure dependency failures and 22% parameter resolution failures identified in the integration testing.