from typing import Dict, Type, Callable, Optional

# The central registry for all strategy actions
ACTION_REGISTRY: Dict[str, Type] = {}


def register_action(name: str) -> Callable:
    """A decorator to register a new strategy action class."""

    def decorator(cls):
        if name in ACTION_REGISTRY:
            print(f"Warning: Action '{name}' is already registered. Overwriting.")
        ACTION_REGISTRY[name] = cls
        # Set the action name as an attribute for discovery
        cls._action_name = name
        return cls

    return decorator


def get_action_class(name: str) -> Optional[Type]:
    """Get an action class by name from the registry."""
    return ACTION_REGISTRY.get(name)
