"""
Centralized path resolution with environment variable support for biomapper.
"""

import os
from pathlib import Path
from typing import Optional
import re
import logging


class PathResolver:
    """Centralized path resolution with environment variable support."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.logger = logging.getLogger(__name__)

        # Default environment variables
        self.env_vars = {
            "DATA_DIR": os.getenv("BIOMAPPER_DATA_DIR", "/procedure/data/local_data"),
            "CACHE_DIR": os.getenv("BIOMAPPER_CACHE_DIR", "/tmp/biomapper/cache"),
            "OUTPUT_DIR": os.getenv("BIOMAPPER_OUTPUT_DIR", "/tmp/biomapper/output"),
            "CONFIG_DIR": os.getenv(
                "BIOMAPPER_CONFIG_DIR", str(self.base_dir / "configs")
            ),
            "BASE_DIR": str(self.base_dir),
        }

        # Create directories if they don't exist
        self._ensure_directories_exist()

    def _ensure_directories_exist(self):
        """Create standard directories if they don't exist."""
        for var_name, path_str in self.env_vars.items():
            if var_name in ["DATA_DIR", "CACHE_DIR", "OUTPUT_DIR"]:
                try:
                    Path(path_str).mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Ensured directory exists: {path_str}")
                except Exception as e:
                    self.logger.warning(f"Could not create directory {path_str}: {e}")

    def resolve_path(
        self, path_str: str, create_parent: bool = False
    ) -> Optional[Path]:
        """
        Resolve a file path with variable substitution and fallback logic.

        Args:
            path_str: Path string potentially containing variables
            create_parent: Whether to create parent directory if it doesn't exist

        Returns:
            Resolved Path object or None if path cannot be resolved
        """
        if not path_str:
            return None

        # Substitute environment variables
        resolved_str = self.substitute_variables(path_str)

        # Try different resolution strategies
        resolved_path = None

        # Strategy 1: Absolute path
        if resolved_str.startswith("/"):
            candidate = Path(resolved_str)
            if candidate.exists():
                resolved_path = candidate

        # Strategy 2: Relative to base directory
        if not resolved_path:
            candidate = self.base_dir / resolved_str.lstrip("/")
            if candidate.exists():
                resolved_path = candidate

        # Strategy 3: Search in common directories
        if not resolved_path:
            resolved_path = self._search_common_directories(resolved_str)

        # Strategy 4: Use filename in data directory (last resort)
        if not resolved_path:
            filename = Path(resolved_str).name
            data_dir = Path(self.env_vars["DATA_DIR"])
            candidate = data_dir / filename
            if candidate.exists():
                resolved_path = candidate
                self.logger.warning(
                    f"Using filename fallback: {path_str} -> {candidate}"
                )

        # Create parent directory if requested
        if resolved_path and create_parent:
            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.warning(
                    f"Could not create parent directory for {resolved_path}: {e}"
                )

        if resolved_path:
            self.logger.debug(f"Resolved path: {path_str} -> {resolved_path}")
        else:
            self.logger.warning(f"Could not resolve path: {path_str}")

        return resolved_path

    def substitute_variables(self, path_str: str) -> str:
        """Substitute environment variables in path string."""

        # Handle ${VAR} syntax
        def replace_var(match):
            var_name = match.group(1)
            return self.env_vars.get(var_name, match.group(0))

        # Replace ${VAR} patterns
        substituted = re.sub(r"\$\{([^}]+)\}", replace_var, path_str)

        # Handle $VAR syntax (less common)
        substituted = re.sub(
            r"\$([A-Z_]+)",
            lambda m: self.env_vars.get(m.group(1), m.group(0)),
            substituted,
        )

        return substituted

    def _search_common_directories(self, path_str: str) -> Optional[Path]:
        """Search for file in common directories."""

        filename = Path(path_str).name

        search_dirs = [
            Path(self.env_vars["DATA_DIR"]),
            Path(self.env_vars["CONFIG_DIR"]),
            self.base_dir / "data",
            self.base_dir / "configs" / "data",
            Path("/procedure/data/local_data"),
            Path("/procedure/data/MAPPING_ONTOLOGIES"),
        ]

        # Add subdirectory search for ontology files
        if "ontologies" in path_str.lower():
            search_dirs.extend(
                [
                    Path(self.env_vars["DATA_DIR"]) / "MAPPING_ONTOLOGIES",
                    Path("/procedure/data/local_data/MAPPING_ONTOLOGIES"),
                ]
            )

        for search_dir in search_dirs:
            if search_dir.exists():
                # Direct file match
                candidate = search_dir / filename
                if candidate.exists():
                    return candidate

                # Recursive search for specific file types
                if filename.endswith((".csv", ".tsv", ".json", ".yaml")):
                    for found_file in search_dir.rglob(filename):
                        return found_file

        return None

    def validate_file_access(self, path: Path, access_mode: str = "r") -> bool:
        """Validate that file exists and is accessible."""
        if not path.exists():
            return False

        if access_mode == "r":
            return os.access(path, os.R_OK)
        elif access_mode == "w":
            return os.access(path.parent, os.W_OK)
        elif access_mode == "rw":
            return os.access(path, os.R_OK) and os.access(path.parent, os.W_OK)

        return False

    def get_safe_output_path(self, requested_path: str) -> Path:
        """Get a safe output path, creating directories as needed."""

        resolved = self.substitute_variables(requested_path)

        # Ensure output goes to designated output directory
        if not resolved.startswith(self.env_vars["OUTPUT_DIR"]):
            filename = Path(resolved).name
            resolved = str(Path(self.env_vars["OUTPUT_DIR"]) / filename)

        output_path = Path(resolved)

        # Create parent directory
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Could not create output directory: {e}")
            # Fallback to temp directory
            import tempfile

            output_path = Path(tempfile.gettempdir()) / output_path.name

        return output_path


# Global path resolver instance
_path_resolver = None


def get_path_resolver() -> PathResolver:
    """Get global path resolver instance."""
    global _path_resolver
    if _path_resolver is None:
        _path_resolver = PathResolver()
    return _path_resolver


def resolve_path(path_str: str) -> Optional[Path]:
    """Convenience function to resolve a path."""
    return get_path_resolver().resolve_path(path_str)


def resolve_output_path(path_str: str) -> Path:
    """Convenience function to get safe output path."""
    return get_path_resolver().get_safe_output_path(path_str)
