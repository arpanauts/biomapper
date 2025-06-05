"""
Strategy action handlers for YAML-defined mapping strategies.

Each action handler implements a specific operation that can be used
as a step in a mapping strategy.
"""

from .convert_identifiers_local import ConvertIdentifiersLocalAction
from .execute_mapping_path import ExecuteMappingPathAction
from .filter_by_target_presence import FilterByTargetPresenceAction

__all__ = [
    "ConvertIdentifiersLocalAction",
    "ExecuteMappingPathAction", 
    "FilterByTargetPresenceAction"
]