from typing import Dict, Type, Callable

# The central registry for all strategy actions
ACTION_REGISTRY: Dict[str, Type] = {}

def register_action(name: str) -> Callable:
    """A decorator to register a new strategy action class."""
    def decorator(cls):
        if name in ACTION_REGISTRY:
            print(f"Warning: Action '{name}' is already registered. Overwriting.")
        ACTION_REGISTRY[name] = cls
        return cls
    return decorator
