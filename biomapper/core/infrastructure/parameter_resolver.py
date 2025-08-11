"""
Enhanced Parameter Resolver for Biomapper

Provides robust parameter resolution with support for:
- Environment variable substitution with defaults
- Nested parameter references with circular reference detection
- Metadata and built-in variable access
- Type conversion and validation
- Complex pattern handling
"""

import os
import re
import yaml
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import logging
from copy import deepcopy
import json
from datetime import datetime

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
        
        # Check for direct circular references first
        self._check_circular_dependencies(dependencies)
        
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
    
    def _check_circular_dependencies(self, dependencies: Dict[str, List[str]]) -> None:
        """Check for circular dependencies and raise error if found."""
        
        def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for param in dependencies:
            if param not in visited:
                if has_cycle(param, visited, set()):
                    raise CircularReferenceError(f"Circular dependency detected in parameters")
    
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
            return context['env'].get(var_name, f"${{{pattern}}}")
        
        elif pattern.startswith('parameters.'):
            # Parameter reference: ${parameters.param_name}
            param_path = pattern[11:]  # Remove 'parameters.'
            result = self._resolve_nested_access(context['parameters'], param_path)
            return result if result is not None else f"${{{pattern}}}"
        
        elif pattern.startswith('metadata.'):
            # Metadata reference: ${metadata.source_files[0].path}
            metadata_path = pattern[9:]  # Remove 'metadata.'
            result = self._resolve_nested_access(context['metadata'], metadata_path)
            return result if result is not None else f"${{{pattern}}}"
        
        elif pattern.startswith('builtin.'):
            # Built-in variable: ${builtin.base_dir}
            builtin_path = pattern[8:]  # Remove 'builtin.'
            result = self._resolve_nested_access(context['builtin'], builtin_path)
            return result if result is not None else f"${{{pattern}}}"
        
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
        # Be more careful about what we convert to lists
        if (',' in value and 
            not value.startswith('/') and 
            not value.startswith('http') and
            not value.startswith('{') and  # Don't convert JSON-like strings
            not value.startswith('[') and  # Don't convert array-like strings
            '"' not in value):  # Don't convert strings with quotes
            
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