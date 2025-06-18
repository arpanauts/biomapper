"""
Configuration loader module for loading and parsing mapping strategy configuration files.

This module provides centralized configuration management for mapping strategies,
separating the configuration loading logic from the MappingExecutor's core responsibilities.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

from biomapper.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Handles loading and parsing of mapping strategy configuration files."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the ConfigLoader.
        
        Args:
            logger: Optional logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def load_strategy(self, strategy_name: str, strategies_config_path: str) -> Dict[str, Any]:
        """
        Load a mapping strategy configuration from a YAML file.
        
        This method reads a YAML file containing strategy configuration,
        parses it, and returns the strategy configuration as a dictionary.
        
        Args:
            strategy_name: Name of the strategy to load
            strategies_config_path: Path to the directory containing strategy YAML files
            
        Returns:
            Dict containing the parsed strategy configuration
            
        Raises:
            ConfigurationError: If the strategy file is not found or cannot be parsed
        """
        # Construct the full path to the strategy file
        strategy_file = os.path.join(strategies_config_path, f"{strategy_name}.yaml")
        
        # Check if file exists
        if not os.path.exists(strategy_file):
            # Try with .yml extension as fallback
            strategy_file = os.path.join(strategies_config_path, f"{strategy_name}.yml")
            if not os.path.exists(strategy_file):
                raise ConfigurationError(
                    f"Strategy configuration file not found for '{strategy_name}' "
                    f"in {strategies_config_path}"
                )
        
        self.logger.debug(f"Loading strategy configuration from: {strategy_file}")
        
        try:
            # Read and parse the YAML file
            with open(strategy_file, 'r') as f:
                strategy_config = yaml.safe_load(f)
            
            # Validate basic structure
            if not isinstance(strategy_config, dict):
                raise ConfigurationError(
                    f"Invalid strategy configuration format in {strategy_file}. "
                    "Expected a dictionary at the root level."
                )
            
            # Add the strategy name to the config if not present
            if 'name' not in strategy_config:
                strategy_config['name'] = strategy_name
            
            self.logger.info(f"Successfully loaded strategy '{strategy_name}'")
            
            return strategy_config
            
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML file {strategy_file}: {e}")
            raise ConfigurationError(
                f"Failed to parse strategy configuration file {strategy_file}: {e}"
            )
        except Exception as e:
            self.logger.error(f"Error loading strategy configuration from {strategy_file}: {e}")
            raise ConfigurationError(
                f"Error loading strategy configuration from {strategy_file}: {e}"
            )
    
    def validate_strategy_config(self, strategy_config: Dict[str, Any]) -> bool:
        """
        Validate a strategy configuration dictionary.
        
        This method can be extended to perform more sophisticated validation
        of strategy configurations.
        
        Args:
            strategy_config: Strategy configuration dictionary to validate
            
        Returns:
            True if valid, raises ConfigurationError if invalid
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
        # Basic validation - ensure it's a dictionary
        if not isinstance(strategy_config, dict):
            raise ConfigurationError("Strategy configuration must be a dictionary")
        
        # Add more validation rules as needed
        # For example, checking required fields, valid step definitions, etc.
        
        return True