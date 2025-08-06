"""Unified action registry for API execution."""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from app.models.strategy_execution import ActionInfo
from biomapper.core.strategy_actions.base import BaseStrategyAction

logger = logging.getLogger(__name__)

# Global registry instance
_global_registry = None


def get_action_registry() -> Dict[str, Type[BaseStrategyAction]]:
    """Get the global action registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ActionRegistryService()
    return _global_registry._registry


class ActionRegistryService:
    """Unified action registry for API execution."""
    
    def __init__(self):
        self._registry: Dict[str, Type[BaseStrategyAction]] = {}
        self._action_info: Dict[str, ActionInfo] = {}
        self._custom_dirs: List[Path] = []
        
        # Load actions on initialization
        self._load_builtin_actions()
        self._load_custom_actions()
    
    def _load_builtin_actions(self):
        """Auto-discover and register all built-in actions."""
        # Import the strategy actions module to trigger registration
        try:
            import biomapper.core.strategy_actions
            from biomapper.core.strategy_actions import (
                LOAD_DATASET_IDENTIFIERS,
                MERGE_WITH_UNIPROT_RESOLUTION,
                CALCULATE_SET_OVERLAP,
                MERGE_DATASETS,
                FILTER_DATASET,
                EXPORT_DATASET,
                EXECUTE_MAPPING_PATH,
            )
        except ImportError as e:
            logger.warning(f"Could not import builtin actions: {e}")
        
        # Scan the strategy_actions directory
        actions_dir = Path(__file__).parent.parent.parent.parent / "biomapper" / "core" / "strategy_actions"
        if actions_dir.exists():
            for py_file in actions_dir.glob("*.py"):
                if py_file.name.startswith("_") or py_file.name == "base.py":
                    continue
                
                module_name = f"biomapper.core.strategy_actions.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    self._register_module_actions(module)
                except Exception as e:
                    logger.warning(f"Failed to load actions from {module_name}: {e}")
        
        logger.info(f"Loaded {len(self._registry)} built-in actions")
    
    def _load_custom_actions(self):
        """Load user-defined custom actions."""
        # Check for custom actions directory in config
        custom_dir = Path("/home/ubuntu/biomapper/custom_actions")
        if custom_dir.exists():
            self._custom_dirs.append(custom_dir)
            
            for py_file in custom_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                
                try:
                    # Load module dynamically
                    spec = importlib.util.spec_from_file_location(
                        f"custom_actions.{py_file.stem}",
                        py_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self._register_module_actions(module)
                except Exception as e:
                    logger.warning(f"Failed to load custom actions from {py_file}: {e}")
        
        logger.info(f"Loaded {len(self._custom_dirs)} custom action directories")
    
    def _register_module_actions(self, module):
        """Register all action classes from a module."""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseStrategyAction) and 
                obj != BaseStrategyAction):
                
                # Check for register_action decorator metadata
                if hasattr(obj, "_action_name"):
                    action_name = obj._action_name
                else:
                    # Use class name as fallback
                    action_name = name
                
                self.register_action(action_name, obj)
    
    def register_action(self, action_name: str, action_class: Type[BaseStrategyAction]):
        """Register an action class."""
        if action_name in self._registry:
            logger.debug(f"Overwriting existing action: {action_name}")
        
        self._registry[action_name] = action_class
        
        # Extract action info
        try:
            info = self._extract_action_info(action_name, action_class)
            self._action_info[action_name] = info
        except Exception as e:
            logger.warning(f"Could not extract info for action {action_name}: {e}")
    
    def _extract_action_info(
        self,
        action_name: str,
        action_class: Type[BaseStrategyAction]
    ) -> ActionInfo:
        """Extract metadata about an action."""
        # Get docstring
        description = inspect.getdoc(action_class) or "No description available"
        
        # Determine category
        category = "general"
        if "load" in action_name.lower():
            category = "data_loading"
        elif "merge" in action_name.lower():
            category = "data_merging"
        elif "filter" in action_name.lower():
            category = "data_filtering"
        elif "export" in action_name.lower():
            category = "data_export"
        elif "calculate" in action_name.lower():
            category = "analysis"
        elif "execute" in action_name.lower():
            category = "orchestration"
        
        # Try to get parameter schema
        param_schema = {}
        if hasattr(action_class, "get_params_model"):
            try:
                params_model = action_class().get_params_model()
                if params_model:
                    param_schema = params_model.schema()
            except:
                pass
        
        # Extract required and produced context keys
        required_context = []
        produces_context = []
        
        # Try to infer from execute method signature
        try:
            sig = inspect.signature(action_class.execute)
            if "context" in sig.parameters:
                # Action uses context
                # TODO: Parse docstring or annotations for specifics
                pass
        except:
            pass
        
        # Check if action supports checkpointing
        supports_checkpoint = not getattr(action_class, "_no_checkpoint", False)
        
        # Create action info
        return ActionInfo(
            name=action_name,
            description=description,
            category=category,
            parameters=param_schema,
            required_context=required_context,
            produces_context=produces_context,
            supports_checkpoint=supports_checkpoint,
            estimated_duration=None,
            examples=[]
        )
    
    def get_action(self, action_type: str) -> Optional[Type[BaseStrategyAction]]:
        """Get action class by type name."""
        return self._registry.get(action_type)
    
    def validate_action_params(self, action_type: str, params: dict) -> dict:
        """Validate parameters against action's Pydantic model."""
        action_class = self.get_action(action_type)
        if not action_class:
            raise ValueError(f"Unknown action type: {action_type}")
        
        # If action has a params model, validate against it
        if hasattr(action_class, "get_params_model"):
            try:
                action_instance = action_class()
                params_model = action_instance.get_params_model()
                if params_model:
                    # Validate and return cleaned params
                    validated = params_model(**params)
                    return validated.dict()
            except ValidationError as e:
                raise ValueError(f"Invalid parameters for {action_type}: {e}")
        
        # No validation available, return as-is
        return params
    
    def list_available_actions(self) -> List[ActionInfo]:
        """List all available actions with metadata."""
        return list(self._action_info.values())
    
    def get_action_info(self, action_type: str) -> Optional[ActionInfo]:
        """Get metadata for a specific action."""
        return self._action_info.get(action_type)
    
    def get_actions_by_category(self, category: str) -> List[ActionInfo]:
        """Get all actions in a specific category."""
        return [
            info for info in self._action_info.values()
            if info.category == category
        ]
    
    def search_actions(self, query: str) -> List[ActionInfo]:
        """Search actions by name or description."""
        query_lower = query.lower()
        results = []
        
        for info in self._action_info.values():
            if (query_lower in info.name.lower() or 
                query_lower in info.description.lower()):
                results.append(info)
        
        return results
    
    def reload_actions(self):
        """Reload all actions (useful for development)."""
        self._registry.clear()
        self._action_info.clear()
        self._load_builtin_actions()
        self._load_custom_actions()
        logger.info(f"Reloaded action registry: {len(self._registry)} actions")
    
    def register_custom_directory(self, directory: Path):
        """Register a directory containing custom actions."""
        if directory.exists() and directory.is_dir():
            self._custom_dirs.append(directory)
            
            # Load actions from this directory
            for py_file in directory.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"custom_{directory.name}.{py_file.stem}",
                        py_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self._register_module_actions(module)
                except Exception as e:
                    logger.warning(f"Failed to load actions from {py_file}: {e}")
        else:
            raise ValueError(f"Directory does not exist: {directory}")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the action registry."""
        categories = {}
        for info in self._action_info.values():
            categories[info.category] = categories.get(info.category, 0) + 1
        
        return {
            "total_actions": len(self._registry),
            "categories": categories,
            "custom_directories": len(self._custom_dirs),
            "builtin_actions": [
                name for name in self._registry.keys()
                if not any(str(d) in str(self._registry[name].__module__) 
                          for d in self._custom_dirs)
            ]
        }


# Global registry instance
_action_registry: Optional[ActionRegistryService] = None


def get_action_registry() -> ActionRegistryService:
    """Get the global action registry instance."""
    global _action_registry
    if _action_registry is None:
        _action_registry = ActionRegistryService()
    return _action_registry


def reload_action_registry():
    """Reload the global action registry."""
    global _action_registry
    if _action_registry:
        _action_registry.reload_actions()
    else:
        _action_registry = ActionRegistryService()