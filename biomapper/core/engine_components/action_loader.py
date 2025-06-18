"""
Action loader module for dynamically loading and instantiating strategy action classes.

This module provides a unified interface for loading action classes either from:
1. The action registry (for built-in actions registered with @register_action)
2. Direct class paths (for custom actions specified with action_class_path)
"""

import importlib
import logging
from typing import Type, Optional, Dict, Any

from biomapper.core.exceptions import ConfigurationError
from biomapper.core.strategy_actions.base import StrategyAction

logger = logging.getLogger(__name__)


class ActionLoader:
    """Handles dynamic loading and instantiation of strategy action classes."""
    
    def __init__(self):
        """Initialize the action loader."""
        self._registry: Optional[Dict[str, Type[StrategyAction]]] = None
        self._loaded_modules = set()
    
    @property
    def action_registry(self) -> Dict[str, Type[StrategyAction]]:
        """Lazily load and return the action registry."""
        if self._registry is None:
            # Import the registry and trigger action registrations
            from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
            import biomapper.core.strategy_actions
            self._registry = ACTION_REGISTRY
        return self._registry
    
    def load_action_class(self, action_type: str) -> Type[StrategyAction]:
        """
        Load an action class by type or class path.
        
        Args:
            action_type: Either a registered action type (e.g., "CONVERT_IDENTIFIERS_LOCAL")
                        or a full class path (e.g., "biomapper.core.strategy_actions.load_endpoint_identifiers.LoadEndpointIdentifiersAction")
        
        Returns:
            The action class ready for instantiation
            
        Raises:
            ConfigurationError: If the action cannot be loaded
        """
        # First check if it's a registered action type
        if action_type in self.action_registry:
            logger.debug(f"Found action '{action_type}' in registry")
            return self.action_registry[action_type]
        
        # If not in registry, try to load it as a class path
        if '.' in action_type:
            logger.debug(f"Attempting to load action from class path: {action_type}")
            return self._load_from_class_path(action_type)
        
        # Neither registry nor class path
        raise ConfigurationError(
            f"Unknown action type: '{action_type}'. "
            f"Action must be either registered in ACTION_REGISTRY or specified as a full class path."
        )
    
    def _load_from_class_path(self, class_path: str) -> Type[StrategyAction]:
        """
        Load an action class from a full class path.
        
        Args:
            class_path: Full dotted path to the class (e.g., "module.submodule.ClassName")
            
        Returns:
            The loaded action class
            
        Raises:
            ConfigurationError: If the class cannot be loaded or is not a valid StrategyAction
        """
        try:
            # Split module path and class name
            module_path, class_name = class_path.rsplit('.', 1)
            
            # Import the module
            if module_path not in self._loaded_modules:
                logger.info(f"Importing module: {module_path}")
                module = importlib.import_module(module_path)
                self._loaded_modules.add(module_path)
            else:
                # Module already loaded, get it from sys.modules
                import sys
                module = sys.modules[module_path]
            
            # Get the class from the module
            if not hasattr(module, class_name):
                raise ConfigurationError(
                    f"Module '{module_path}' does not have class '{class_name}'"
                )
            
            action_class = getattr(module, class_name)
            
            # Verify it's a StrategyAction subclass
            if not issubclass(action_class, StrategyAction):
                raise ConfigurationError(
                    f"Class '{class_path}' is not a subclass of StrategyAction"
                )
            
            logger.info(f"Successfully loaded action class: {class_path}")
            return action_class
            
        except ImportError as e:
            raise ConfigurationError(
                f"Failed to import module for action class '{class_path}': {str(e)}"
            )
        except AttributeError as e:
            raise ConfigurationError(
                f"Failed to load action class '{class_path}': {str(e)}"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Unexpected error loading action class '{class_path}': {str(e)}"
            )
    
    def instantiate_action(self, action_type: str, db_session: Any) -> StrategyAction:
        """
        Load and instantiate an action with the given database session.
        
        Args:
            action_type: Action type or class path
            db_session: Database session to pass to the action constructor
            
        Returns:
            Instantiated action ready for execution
            
        Raises:
            ConfigurationError: If the action cannot be loaded or instantiated
        """
        action_class = self.load_action_class(action_type)
        
        try:
            action_instance = action_class(db_session)
            logger.debug(f"Instantiated action: {action_type}")
            return action_instance
        except Exception as e:
            raise ConfigurationError(
                f"Failed to instantiate action '{action_type}': {str(e)}"
            )