"""Configuration management for biomapper.

This module provides a centralized configuration management system
that loads settings from multiple sources with a defined precedence:
1. Environment variables (highest precedence)
2. Configuration files (YAML/JSON)
3. Default values (lowest precedence)

The Config class is implemented as a Singleton to ensure consistent
configuration across the application.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union, List, TypeVar
from pathlib import Path
import threading
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

T = TypeVar('T')


class Config:
    """Singleton configuration manager for the Biomapper application.
    
    Provides hierarchical configuration loading from multiple sources with clear precedence:
    1. Environment variables (highest precedence)
    2. Configuration files (YAML/JSON)
    3. Default values (lowest precedence)
    
    Usage:
        config = Config.get_instance()
        db_url = config.get("database.url", "sqlite:///default.db")
        api_timeout = config.get("api.timeout", 30)
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    # Configuration sources
    _env_prefix = "BIOMAPPER_"
    _config_paths = [
        # System-wide configuration
        Path("/etc/biomapper/config.yaml"),
        Path("/etc/biomapper/config.yml"),
        Path("/etc/biomapper/config.json"),
        
        # User configuration
        Path.home() / ".config" / "biomapper" / "config.yaml",
        Path.home() / ".config" / "biomapper" / "config.yml",
        Path.home() / ".config" / "biomapper" / "config.json",
        
        # Project configuration (relative to the repo root)
        Path(__file__).parent.parent.parent / "config.yaml",
        Path(__file__).parent.parent.parent / "config.yml",
        Path(__file__).parent.parent.parent / "config.json",
    ]
    
    def __init__(self) -> None:
        """Initialize the configuration manager.
        
        This should not be called directly. Use Config.get_instance() instead.
        """
        if Config._instance is not None:
            raise RuntimeError("Config is a singleton. Use Config.get_instance() instead.")
        
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Configuration hierarchy (from lowest to highest precedence)
        self._defaults: Dict[str, Any] = self._get_defaults()
        self._file_config: Dict[str, Any] = self._load_file_config()
        self._env_config: Dict[str, Any] = self._load_env_config()
        
        logger.info(f"Configuration initialized from {len(self._file_config)} file settings "
                   f"and {len(self._env_config)} environment variables")
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """Get the singleton instance of the Config class.
        
        Returns:
            The singleton Config instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._lock:
            cls._instance = None
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Define default configuration values.
        
        Returns:
            Dictionary containing default configuration values
        """
        project_root = Path(__file__).parent.parent.parent
        
        return {
            "database": {
                "config_db_url": f"sqlite+aiosqlite:///{project_root}/data/metamapper.db",
                "cache_db_url": f"sqlite+aiosqlite:///{project_root}/data/mapping_cache.db",
                "connection_pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 1800,
            },
            "paths": {
                "root": str(project_root),
                "data": str(project_root / "data"),
                "logs": str(project_root / "logs"),
                "cache": str(project_root / "data" / "cache"),
                "embeddings": str(project_root / "data" / "embeddings"),
                "uploads": str(project_root / "data" / "uploads"),
                "results": str(project_root / "data" / "results"),
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": str(project_root / "logs" / "biomapper.log"),
            },
            "spoke": {
                "base_url": "https://spoke.rbvi.ucsf.edu/api/v1",
                "timeout": 30,
                "max_retries": 3,
                "backoff_factor": 0.5,
            },
            "mapping": {
                "default_cache_enabled": True,
                "default_max_cache_age_days": 30,
                "default_bidirectional": True,
            },
            "embeddings": {
                "default_model": "text-embedding-ada-002",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            "api": {
                "host": "127.0.0.1",
                "port": 8000,
                "workers": 4,
                "timeout": 300,
                "cors_origins": ["*"],
            },
        }
    
    def _load_file_config(self) -> Dict[str, Any]:
        """Load configuration from YAML or JSON files.
        
        Returns:
            Dictionary containing configuration values from files
        """
        config: Dict[str, Any] = {}
        
        for config_path in self._config_paths:
            if not config_path.exists():
                continue
            
            try:
                with open(config_path, "r") as f:
                    if config_path.suffix in [".yaml", ".yml"]:
                        file_config = yaml.safe_load(f)
                    elif config_path.suffix == ".json":
                        file_config = json.load(f)
                    else:
                        logger.warning(f"Unsupported config file format: {config_path}")
                        continue
                    
                    if file_config and isinstance(file_config, dict):
                        # Update with the new configuration using deep_update
                        self._deep_update(config, file_config)
                        logger.info(f"Loaded configuration from {config_path}")
                
            except Exception as e:
                logger.warning(f"Error loading configuration from {config_path}: {e}")
        
        return config
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Environment variables are expected to follow the format:
        BIOMAPPER_SECTION_SUBSECTION_KEY=value
        
        For example:
        BIOMAPPER_DATABASE_CONFIG_DB_URL=postgresql://user:pass@localhost/db
        
        Returns:
            Dictionary containing configuration values from environment variables
        """
        config: Dict[str, Any] = {}
        
        for env_var, value in os.environ.items():
            if not env_var.startswith(self._env_prefix):
                continue
            
            # Remove prefix and split into parts (lowercase for consistency)
            parts = env_var[len(self._env_prefix):].lower().split("_")
            
            # Skip if no parts
            if not parts:
                continue
            
            # Convert value to appropriate type if possible
            typed_value = self._convert_value(value)
            
            # Build nested dict structure from parts
            current = config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # If we encounter a non-dict, convert it to a dict with a special key
                    current[part] = {"_": current[part]}
                current = current[part]
            
            # Set the final value
            current[parts[-1]] = typed_value
        
        return config
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted value (bool, int, float, or original string)
        """
        # Handle boolean values
        if value.lower() in ["true", "yes", "1"]:
            return True
        if value.lower() in ["false", "no", "0"]:
            return False
        
        # Handle numeric values
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Handle JSON values
        try:
            if (value.startswith("{") and value.endswith("}")) or \
               (value.startswith("[") and value.endswith("]")):
                return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Return as string if no conversion applied
        return value
    
    def _deep_update(self, original: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively update a nested dictionary.
        
        Args:
            original: Dictionary to update
            update: Dictionary containing updates
        """
        for key, value in update.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value
    
    def get(self, key_path: str, default: Optional[T] = None) -> Union[Dict[str, Any], T]:
        """Get a configuration value using dot notation.
        
        Searches for the key in environment variables, then in configuration files,
        and finally falls back to the provided default or the system defaults.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., "database.url")
            default: Default value to return if the key is not found
            
        Returns:
            The configuration value, or the default if not found
            
        Examples:
            >>> config = Config.get_instance()
            >>> db_url = config.get("database.config_db_url")
            >>> spoke_timeout = config.get("spoke.timeout", 30)
        """
        parts = key_path.split(".")
        
        # Try to get from environment variables first
        env_value = self._get_from_nested_dict(self._env_config, parts)
        if env_value is not None:
            return env_value
        
        # Then try from file configuration
        file_value = self._get_from_nested_dict(self._file_config, parts)
        if file_value is not None:
            return file_value
        
        # Finally, try from defaults
        default_value = self._get_from_nested_dict(self._defaults, parts)
        if default_value is not None:
            return default_value
        
        # If not found anywhere, return the provided default
        return default
    
    def _get_from_nested_dict(self, d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
        """Get a value from a nested dictionary using a list of keys.
        
        Args:
            d: Dictionary to search in
            keys: List of keys forming a path to the desired value
            
        Returns:
            The value if found, or None if not found
        """
        result = d
        for key in keys:
            if not isinstance(result, dict) or key not in result:
                return None
            result = result[key]
        return result
    
    def set_for_testing(self, key_path: str, value: Any) -> None:
        """Set a configuration value for testing purposes.
        
        WARNING: This should only be used in tests!
        
        Args:
            key_path: Dot-separated path to the configuration value
            value: The value to set
        """
        parts = key_path.split(".")
        
        # Set in env_config to override other sources
        current = self._env_config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration as a dictionary.
        
        Returns:
            A deep copy of the merged configuration
        """
        # Start with defaults
        result = self._deep_copy(self._defaults)
        
        # Apply file config
        self._deep_update(result, self._file_config)
        
        # Apply env config (highest precedence)
        self._deep_update(result, self._env_config)
        
        return result
    
    def _deep_copy(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary.
        
        Args:
            obj: Dictionary to copy
            
        Returns:
            A deep copy of the dictionary
        """
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    def set_env_prefix(self, prefix: str) -> None:
        """Set the environment variable prefix (primarily for testing).
        
        Args:
            prefix: The prefix to use for environment variables
        """
        self._env_prefix = prefix
        # Reload environment configuration
        self._env_config = self._load_env_config()
    
    def add_config_path(self, path: Union[str, Path]) -> None:
        """Add a configuration file path.
        
        Args:
            path: Path to a configuration file
        """
        path = Path(path) if isinstance(path, str) else path
        if path not in self._config_paths:
            self._config_paths.append(path)
            # Reload file configuration
            self._file_config = self._load_file_config()
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._file_config = self._load_file_config()
        self._env_config = self._load_env_config()
        logger.info("Configuration reloaded")