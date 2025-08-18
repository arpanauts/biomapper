"""Parameter resolution for strategy configuration."""
import os
import re
from typing import Any, Dict, Optional, Set
from pathlib import Path


class ParameterResolutionError(Exception):
    """Raised when parameter resolution fails."""
    pass


class CircularReferenceError(ParameterResolutionError):
    """Raised when circular reference detected in parameter resolution."""
    pass


class ParameterResolver:
    """Resolves parameter placeholders in strategy configurations."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize parameter resolver.
        
        Args:
            base_dir: Base directory for relative path resolution
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self._resolution_cache: Dict[str, Any] = {}
        self._resolving: Set[str] = set()  # Track circular references
    
    def _build_resolution_context(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for parameter resolution.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            Resolution context dictionary
        """
        context = {
            "parameters": strategy.get("parameters", {}),
            "metadata": strategy.get("metadata", {}),
            "env": dict(os.environ),
        }
        return context
    
    def _resolve_value(self, value: str, context: Dict[str, Any], path: str) -> Any:
        """Resolve a single value with parameter substitution.
        
        Args:
            value: Value to resolve
            context: Resolution context
            path: Current resolution path (for circular reference detection)
            
        Returns:
            Resolved value
        """
        if path in self._resolving:
            raise CircularReferenceError(f"Circular reference detected: {path}")
        
        self._resolving.add(path)
        try:
            # Pattern to match ${...} placeholders
            pattern = r'\$\{([^}]+)\}'
            
            def replacer(match):
                placeholder = match.group(1)
                
                # Handle environment variables with defaults
                if ":-" in placeholder:
                    var_name, default = placeholder.split(":-", 1)
                    var_name = var_name.strip()
                    default = default.strip()
                else:
                    var_name = placeholder.strip()
                    default = None
                
                # Try to resolve from context
                try:
                    current = context
                    
                    # Handle complex paths like metadata.source_files[0].path
                    # Split by dots but preserve array indices
                    path_parts = []
                    for part in var_name.split("."):
                        if "[" in part and "]" in part:
                            # Handle array indexing like "source_files[0]"
                            base_part = part.split("[")[0]
                            index_part = part.split("[")[1].split("]")[0]
                            path_parts.append((base_part, "key"))
                            path_parts.append((int(index_part), "index"))
                        else:
                            path_parts.append((part, "key"))
                    
                    for part, access_type in path_parts:
                        if access_type == "key" and isinstance(current, dict) and part in current:
                            current = current[part]
                        elif access_type == "index" and isinstance(current, list) and 0 <= part < len(current):
                            current = current[part]
                        else:
                            # Not found in context path, try environment
                            env_value = os.environ.get(var_name)
                            if env_value is not None:
                                return env_value
                            elif default is not None:
                                return default
                            else:
                                # Return the original placeholder if not found
                                return match.group(0)
                    
                    # Check if the resolved value is empty and we have a default
                    if current == "" and default is not None:
                        return default
                
                except (ValueError, IndexError, KeyError):
                    # Handle parsing errors or access errors
                    env_value = os.environ.get(var_name)
                    if env_value is not None:
                        return env_value
                    elif default is not None:
                        return default
                    else:
                        # Return the original placeholder if not found
                        return match.group(0)
                
                return str(current)
            
            # Replace all placeholders
            result = re.sub(pattern, replacer, value)
            
            # Convert to appropriate type if needed
            if result.lower() == "true":
                return True
            elif result.lower() == "false":
                return False
            elif result.isdigit():
                return int(result)
            else:
                try:
                    return float(result)
                except ValueError:
                    return result
                    
        finally:
            self._resolving.discard(path)
    
    def _check_for_unresolved_placeholders(self, obj: Any, path: str = "", strategy: Dict[str, Any] = None) -> None:
        """Check for unresolved parameter placeholders that indicate circular references.
        
        Args:
            obj: Object to check
            path: Current path for error reporting
            strategy: Original strategy to check if parameter exists
            
        Raises:
            CircularReferenceError: If circular references are detected
        """
        if isinstance(obj, str):
            if "${parameters." in obj:
                # Found an unresolved parameter placeholder
                import re
                pattern = r'\$\{parameters\.([^}]+)\}'
                matches = re.findall(pattern, obj)
                if matches and strategy:
                    # Only raise CircularReferenceError if the parameter actually exists
                    # in the strategy (indicating a circular reference, not a missing parameter)
                    existing_params = []
                    for match in matches:
                        param_path = match.split('.')[0]  # Get the top-level parameter name
                        if param_path in strategy.get("parameters", {}):
                            existing_params.append(match)
                    
                    if existing_params:
                        raise CircularReferenceError(f"Circular reference detected in parameter(s): {', '.join(existing_params)}")
        elif isinstance(obj, dict):
            for key, value in obj.items():
                self._check_for_unresolved_placeholders(value, f"{path}.{key}", strategy)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_for_unresolved_placeholders(item, f"{path}[{i}]", strategy)
    
    def resolve_parameters(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve all parameters in a strategy with multi-pass resolution.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            Strategy with resolved parameters
        """
        # Make a deep copy to avoid modifying the original
        import copy
        result = copy.deepcopy(strategy)
        
        # Multi-pass resolution to handle nested parameter references
        max_passes = 10  # Prevent infinite loops
        for pass_num in range(max_passes):
            context = self._build_resolution_context(result)
            previous_result = copy.deepcopy(result)
            
            def resolve_recursive(obj: Any, path: str = "") -> Any:
                """Recursively resolve parameters in nested structures."""
                if isinstance(obj, str):
                    if "${" in obj:
                        return self._resolve_value(obj, context, path)
                    else:
                        # Apply type conversion to string values without placeholders
                        if obj.lower() == "true":
                            return True
                        elif obj.lower() == "false":
                            return False
                        elif obj.isdigit():
                            return int(obj)
                        else:
                            try:
                                return float(obj)
                            except ValueError:
                                return obj
                elif isinstance(obj, dict):
                    return {k: resolve_recursive(v, f"{path}.{k}") for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [resolve_recursive(item, f"{path}[{i}]") for i, item in enumerate(obj)]
                else:
                    return obj
            
            result = resolve_recursive(result)
            
            # If no changes were made, we're done
            if result == previous_result:
                # Check if there are still unresolved parameter placeholders
                # This indicates circular references or undefined parameters
                self._check_for_unresolved_placeholders(result, strategy=strategy)
                break
        else:
            # If we hit max_passes, it's likely a circular reference
            raise CircularReferenceError(f"Parameter resolution hit maximum passes ({max_passes}), likely circular references detected")
        
        return result