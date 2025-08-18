"""Entity-specific strategy actions for biomapper."""

# Import all entity modules to trigger action registration
from . import proteins
from . import metabolites
from . import chemistry

__all__ = ["proteins", "metabolites", "chemistry"]
