"""
Reversible path module for handling bidirectional mapping paths.

This module contains the ReversiblePath class which wraps a MappingPath
to allow execution in reverse direction.
"""

from typing import List, Optional, Any

from biomapper.db.models import MappingPath, MappingPathStep


class ReversiblePath:
    """Wrapper to allow executing a path in reverse direction."""

    def __init__(self, original_path: MappingPath, is_reverse: bool = False):
        """
        Initialize a reversible path.
        
        Args:
            original_path: The original MappingPath object
            is_reverse: Whether this path should be executed in reverse
        """
        self.original_path = original_path
        self.is_reverse = is_reverse

    @property
    def id(self) -> Optional[int]:
        """Return the path ID."""
        return self.original_path.id

    @property
    def name(self) -> Optional[str]:
        """Return the path name, with (Reverse) suffix if reversed."""
        return (
            f"{self.original_path.name} (Reverse)"
            if self.is_reverse
            else self.original_path.name
        )

    @property
    def priority(self) -> Optional[int]:
        """
        Return the path priority.
        
        Reverse paths have slightly lower priority (higher number) than forward paths.
        """
        original_priority = self.original_path.priority if self.original_path.priority is not None else 100
        return original_priority + (5 if self.is_reverse else 0)

    @property
    def steps(self) -> List[MappingPathStep]:
        """
        Return the path steps in appropriate order.
        
        For reverse paths, steps are returned in reverse order.
        """
        if not self.is_reverse:
            return self.original_path.steps
        else:
            # Return steps in reverse order
            return sorted(self.original_path.steps, key=lambda s: -(s.step_order or 0))

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to the original path."""
        return getattr(self.original_path, name)