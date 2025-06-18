"""
Placeholder resolution utility for biomapper.

This module provides a centralized way to resolve placeholders (e.g., ${VAR})
in strings and other values used throughout the biomapper application.
"""

import os
import re
from typing import Any, Dict, Optional, Union


def resolve_placeholders(value: Any, context: Dict[str, Any]) -> Any:
    """
    Resolve placeholders in a value using context and environment variables.
    
    This function processes values that may contain placeholder expressions
    like ${VAR_NAME} and resolves them using:
    1. Context dictionary values
    2. Environment variables
    3. Default fallback values for known placeholders
    
    Args:
        value: The value to process (typically a string, but can be other types)
        context: Dictionary of context values for placeholder resolution
        
    Returns:
        The value with placeholders resolved. If the input is not a string,
        it's returned unchanged.
        
    Examples:
        >>> context = {"DATA_DIR": "/data", "OUTPUT_DIR": "/output"}
        >>> resolve_placeholders("${DATA_DIR}/file.csv", context)
        '/data/file.csv'
        
        >>> resolve_placeholders("${DATA_DIR}/file.csv", {})  # Falls back to env
        '/path/from/env/file.csv'  # if DATA_DIR env var is set
    """
    # Only process strings
    if not isinstance(value, str):
        return value
    
    # Find all placeholder patterns ${VAR_NAME}
    placeholder_pattern = re.compile(r'\$\{([^}]+)\}')
    
    def replace_placeholder(match):
        var_name = match.group(1)
        
        # Try context first
        if var_name in context:
            return str(context[var_name])
        
        # Try environment variables
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        
        # Handle known defaults
        if var_name == 'DATA_DIR':
            # Import settings here to avoid circular imports
            try:
                from biomapper.core.config import settings
                return settings.data_dir
            except ImportError:
                # Fallback if settings not available
                return os.environ.get('DATA_DIR', '/data')
        
        # If no resolution found, return the original placeholder
        return match.group(0)
    
    # Replace all placeholders
    resolved = placeholder_pattern.sub(replace_placeholder, value)
    return resolved


def resolve_file_path(
    file_path: str, 
    context: Dict[str, Any], 
    create_dirs: bool = False
) -> str:
    """
    Resolve placeholders in a file path and optionally create directories.
    
    This is a specialized version of resolve_placeholders for file paths
    that can also create parent directories if needed.
    
    Args:
        file_path: The file path containing placeholders
        context: Dictionary of context values for placeholder resolution
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Resolved absolute file path
        
    Examples:
        >>> resolve_file_path("${OUTPUT_DIR}/results.csv", {"OUTPUT_DIR": "/tmp"})
        '/tmp/results.csv'
    """
    # First resolve placeholders
    resolved_path = resolve_placeholders(file_path, context)
    
    # Make absolute
    resolved_path = os.path.abspath(resolved_path)
    
    # Create parent directories if requested
    if create_dirs:
        parent_dir = os.path.dirname(resolved_path)
        os.makedirs(parent_dir, exist_ok=True)
    
    return resolved_path