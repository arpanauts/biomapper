# Code Quality and Configuration Management Roadmap

## 1. Recent Accomplishments

- Fixed indentation errors in `biomapper/core/mapping_executor.py` that were causing test failures
- Analyzed key areas for code quality improvement
- Created comprehensive improvement plan for configuration management and error handling
- Documented detailed implementation strategies for the central configuration system
- Resolved execution path bugs in try-except blocks that were previously causing syntax errors

## 2. Current Project State

The Biomapper project is currently in a transition state as we work to improve code quality and maintenance while continuing development of core functionality. Key observations:

- **Core Mapping Functionality**: The core mapping functionality is working but has some maintainability challenges, particularly around configuration and error handling
- **Configuration Management**: Currently using a mix of constants and module-level configurations which makes testing and environment management difficult
- **Error Handling**: Error handling is inconsistent across the codebase, with some areas having detailed custom exceptions and others using generic exceptions
- **Test Coverage**: Tests are in place but some were failing due to indentation and syntax errors that have now been fixed
- **Stability**: No critical blockers currently exist, but technical debt is accumulating in configuration management

## 3. Technical Context

### 3.1 Current Configuration Approach

The project currently uses module-level constants for configuration:

```python
# In utils/config.py
CONFIG_DB_URL = "sqlite+aiosqlite:///data/metamapper.db"
CACHE_DB_URL = "sqlite+aiosqlite:///data/metamapper_cache.db"
```

And these are imported directly into modules:

```python
# In mapping_executor.py
from ..utils.config import CONFIG_DB_URL, CACHE_DB_URL

class MappingExecutor:
    def __init__(
        self,
        metamapper_db_url: str = CONFIG_DB_URL,
        mapping_cache_db_url: str = CACHE_DB_URL,
    ):
        # ...
```

### 3.2 Proposed Configuration System

We have designed a centralized configuration system using the Singleton pattern:

```python
from typing import Dict, Any, Optional, List, Union, Type, cast
import os
import json
import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class Config:
    """
    Centralized configuration management system using the Singleton pattern.
    
    Handles loading configuration from multiple sources with priority:
    1. Environment variables
    2. Config files (specified or default)
    3. Default values
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'Config':
        """Get or create the singleton Config instance."""
        if cls._instance is None:
            cls._instance = Config(config_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration system.
        
        Args:
            config_path: Optional path to config file. If None, will search in default locations.
        """
        self._config = {}
        
        # Load default configurations
        self._load_defaults()
        
        # Load from config file
        if config_path:
            self._load_from_file(config_path)
        else:
            # Try standard locations
            for path in self._get_default_config_paths():
                if path.exists():
                    self._load_from_file(str(path))
                    break
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate configuration
        self._validate_config()
    
    def _get_default_config_paths(self) -> List[Path]:
        """Get list of default config file paths to check."""
        return [
            Path("./config.yaml"),
            Path("./config.json"),
            Path.home() / ".biomapper" / "config.yaml",
            Path.home() / ".biomapper" / "config.json",
            Path("/etc/biomapper/config.yaml"),
            Path("/etc/biomapper/config.json"),
        ]
    
    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self._config = {
            "database": {
                "config_db_url": "sqlite+aiosqlite:///data/metamapper.db",
                "cache_db_url": "sqlite+aiosqlite:///data/metamapper_cache.db",
            },
            "api": {
                "host": "localhost",
                "port": 8000,
                "debug": False,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None,  # None means log to stdout
            },
            "cache": {
                "ttl": 86400,  # 24 hours in seconds
                "max_size": 1000,
            },
            # Other default configurations...
        }
    
    def _load_from_file(self, file_path: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the config file (YAML or JSON)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Config file not found: {file_path}")
                return
                
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {path.suffix}")
                    return
                
            # Deep merge with existing config
            self._merge_configs(self._config, file_config)
            logger.info(f"Loaded configuration from {file_path}")
                
        except Exception as e:
            logger.error(f"Error loading config from {file_path}: {e}")
            # Continue with existing config
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        Environment variables should be prefixed with BIOMAPPER_ and use __ as a separator
        for nested keys. For example:
        - BIOMAPPER_DATABASE__CONFIG_DB_URL
        - BIOMAPPER_API__PORT
        """
        prefix = "BIOMAPPER_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and split by double underscore
                config_key = key[len(prefix):].lower()
                parts = config_key.split('__')
                
                # Handle typing based on existing config values
                typed_value = self._convert_env_value(value, parts)
                
                # Navigate to the right spot in the config dict
                current = self._config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value
                current[parts[-1]] = typed_value
                logger.debug(f"Set config from env: {key} -> {typed_value}")
    
    def _convert_env_value(self, value: str, parts: List[str]) -> Any:
        """
        Convert environment variable value to the appropriate type based on existing config.
        
        Args:
            value: String value from environment variable
            parts: Parts of the config key (e.g. ['database', 'port'])
            
        Returns:
            Converted value (int, bool, float, or str)
        """
        # Try to determine expected type from existing config
        try:
            current = self._config
            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    # Can't determine type, use string
                    break
                    
            target_key = parts[-1]
            if target_key in current:
                existing_value = current[target_key]
                existing_type = type(existing_value)
                
                # Convert based on existing type
                if existing_type == bool:
                    return value.lower() in ('true', 'yes', '1', 'y')
                elif existing_type == int:
                    return int(value)
                elif existing_type == float:
                    return float(value)
                # Otherwise fall through to string
        except Exception:
            pass
        
        # Default String conversion with special handling for common values
        if value.lower() in ('true', 'yes', 'y'):
            return True
        elif value.lower() in ('false', 'no', 'n'):
            return False
        
        # Try numeric conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            # Default to string
            return value
    
    def _validate_config(self) -> None:
        """
        Validate the configuration and ensure required values are present.
        
        Raises:
            ConfigError: If validation fails
        """
        # Example validation
        required_fields = [
            ('database', 'config_db_url'),
            ('database', 'cache_db_url'),
        ]
        
        for field_path in required_fields:
            current = self._config
            path_str = '.'.join(field_path)
            
            try:
                for part in field_path:
                    if part not in current:
                        raise ValueError(f"Missing required config: {path_str}")
                    current = current[part]
                
                if current is None or current == '':
                    raise ValueError(f"Empty required config: {path_str}")
            except Exception as e:
                logger.error(f"Configuration validation error: {e}")
                # In a real implementation, you might raise a ConfigError here
                # For now, just log the error and continue with defaults
    
    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """
        Deep merge two configuration dictionaries.
        
        Args:
            base: Base configuration dict (modified in place)
            update: Dict with values to update
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                # Recursive merge for nested dicts
                self._merge_configs(base[key], value)
            else:
                # Direct update for non-dict values
                base[key] = value
    
    # Public interface methods
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Configuration key path using dot notation (e.g. 'database.config_db_url')
            default: Default value to return if key not found
            
        Returns:
            Configuration value or default
        """
        parts = key_path.split('.')
        current = self._config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    # Convenience getters for common config values
    
    def get_db_url(self) -> str:
        """Get the main database URL."""
        return cast(str, self.get('database.config_db_url'))
    
    def get_cache_db_url(self) -> str:
        """Get the cache database URL."""
        return cast(str, self.get('database.cache_db_url'))
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get the logging configuration."""
        return cast(Dict[str, Any], self.get('logging', {}))
```

### 3.3 Error Handling Improvements

The error handling system will be restructured to provide:

1. A clear hierarchy of exception types
2. Consistent error codes
3. Better context information for debugging

```python
from typing import Optional, Dict, Any
import enum


class ErrorCode(enum.Enum):
    """Standardized error codes for Biomapper."""
    
    # General errors (1-99)
    UNKNOWN_ERROR = 1
    CONFIGURATION_ERROR = 2
    NOT_IMPLEMENTED = 3
    
    # Client errors (100-199)
    CLIENT_INITIALIZATION_ERROR = 100
    CLIENT_EXECUTION_ERROR = 101
    CLIENT_TIMEOUT_ERROR = 102
    
    # Database errors (200-299)
    DATABASE_CONNECTION_ERROR = 200
    DATABASE_QUERY_ERROR = 201
    DATABASE_TRANSACTION_ERROR = 202
    
    # Cache errors (300-399)
    CACHE_RETRIEVAL_ERROR = 300
    CACHE_STORAGE_ERROR = 301
    
    # Mapping errors (400-499)
    NO_PATH_FOUND_ERROR = 400
    MAPPING_EXECUTION_ERROR = 401
    INVALID_INPUT_ERROR = 402
    
    # API errors (500-599)
    API_VALIDATION_ERROR = 500
    API_AUTHENTICATION_ERROR = 501
    API_AUTHORIZATION_ERROR = 502


class BiomapperError(Exception):
    """Base class for all Biomapper exceptions."""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base error with standard fields.
        
        Args:
            message: Human-readable error message
            error_code: Standardized error code
            details: Additional context for debugging
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Format the error as a string."""
        result = f"[{self.error_code.name}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            result += f" ({details_str})"
        return result


class ConfigurationError(BiomapperError):
    """Error raised when there's a configuration issue."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message, 
            error_code=ErrorCode.CONFIGURATION_ERROR,
            details=details
        )


class ClientError(BiomapperError):
    """Base class for client-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode,
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        _details = details or {}
        if client_name:
            _details["client_name"] = client_name
        super().__init__(message, error_code=error_code, details=_details)


class ClientInitializationError(ClientError):
    """Error raised when a client fails to initialize."""
    
    def __init__(
        self, 
        message: str, 
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message, 
            error_code=ErrorCode.CLIENT_INITIALIZATION_ERROR,
            client_name=client_name,
            details=details
        )


class ClientExecutionError(ClientError):
    """Error raised when a client operation fails."""
    
    def __init__(
        self, 
        message: str, 
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message, 
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            client_name=client_name,
            details=details
        )
```

## 4. Next Steps

### Phase 1: Error Handling Refactoring

1. **Create Exception Hierarchy**: 
   - Implement the proposed error code system in `core/exceptions.py`
   - Add detailed documentation for error codes and exception types

2. **Update Core Components**:
   - Modify `MappingExecutor` to use the new exception types for consistency
   - Update client classes to properly raise and handle specific exceptions

3. **Improve Error Logging**:
   - Implement standardized error logging format across the codebase
   - Add context information to error messages for easier debugging

### Phase 2: Centralized Configuration

1. **Implement Config Class**:
   - Implement the singleton `Config` class in `utils/config.py`
   - Add support for loading from environment variables and files

2. **Update Core Classes**:
   - Modify `MappingExecutor` to use the new configuration system
   - Create proper getter methods for commonly used configuration values

3. **Documentation and Testing**:
   - Add comprehensive documentation for the configuration system
   - Add unit tests for configuration loading and validation

### Phase 3: Integration and Testing

1. **Integrate Configuration with Error Handling**:
   - Use configuration for error handling settings (verbosity, etc.)
   - Add configuration values for retry behavior and timeouts

2. **Integration Points**:
   - Update API and CLI entry points to initialize configuration
   - Add configuration values for per-module settings

3. **System Testing**:
   - Create a comprehensive test suite for the new configuration system
   - Test error handling in various scenarios, including edge cases

## 5. Open Questions & Considerations

1. **Configuration Initialization Point**:
   - Main options are entry points (CLI, API) or lazy loading in core classes
   - Question: Given project's architecture, where is the best place to initialize?
   - Suggested approach: Initialize at entry points with fallback to lazy initialization

2. **Access Pattern for Config**:
   - Should modules access specific getters or use generic getter with dot notation?
   - Question: Which approach balances type safety with flexibility?
   - Recommended: Use specific getters for core values and dot notation for feature flags

3. **Environmental Specificity**:
   - How to handle differences between development, testing, and production?
   - Options: Environment-specific config files vs. environment variables
   - Consider: Adding environment detection to choose appropriate defaults

4. **Performance Considerations**:
   - Singleton pattern has thread safety concerns in some contexts
   - Question: Do we need thread-local configuration or other synchronization?
   - Need to evaluate: Actual multi-threading usage in the application

5. **Migration Strategy**:
   - Question: Should we migrate all modules at once or incrementally?
   - Recommendation: Incremental approach starting with core components
   - Will require a transition period where both systems coexist