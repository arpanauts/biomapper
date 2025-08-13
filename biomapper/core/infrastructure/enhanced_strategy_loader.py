"""
Enhanced Strategy Loader for Biomapper

Provides comprehensive strategy loading with:
- Parameter resolution and validation
- Path resolution and normalization  
- Environment configuration integration
- Error handling and fallback strategies
- Strategy validation and schema checking
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from .parameter_resolver import ParameterResolver, ParameterResolutionError


class StrategyLoadError(Exception):
    """Exception raised when strategy loading fails."""


class StrategyValidationError(Exception):
    """Exception raised when strategy validation fails."""


class PathResolver:
    """Handles file path resolution and validation."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.logger = logging.getLogger(__name__)

    def resolve_path(self, path_str: str) -> Optional[Path]:
        """
        Resolve a path string to an absolute Path.

        Args:
            path_str: Path string to resolve

        Returns:
            Resolved Path object or None if path cannot be resolved
        """
        try:
            path = Path(path_str)

            # Handle different path types
            if path.is_absolute():
                resolved_path = path
            else:
                # Try relative to base directory
                resolved_path = self.base_dir / path

                # If doesn't exist, try relative to current working directory
                if not resolved_path.exists():
                    resolved_path = Path.cwd() / path

            # Resolve to absolute path
            resolved_path = resolved_path.expanduser().resolve()

            return resolved_path if resolved_path.exists() else None

        except Exception as e:
            self.logger.warning(f"Could not resolve path '{path_str}': {e}")
            return None

    def get_safe_output_path(self, path_str: str) -> Path:
        """
        Get a safe output path, creating directories if needed.

        Args:
            path_str: Output path string

        Returns:
            Resolved Path object for output
        """
        try:
            path = Path(path_str)

            # Make absolute if not already
            if not path.is_absolute():
                path = self.base_dir / path

            # Expand user and resolve
            path = path.expanduser().resolve()

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            return path

        except Exception as e:
            self.logger.error(
                f"Could not create safe output path for '{path_str}': {e}"
            )
            # Fallback to temp directory
            temp_path = Path("/tmp/biomapper/output") / Path(path_str).name
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            return temp_path


class EnhancedStrategyLoader:
    """Enhanced strategy loader with parameter resolution and path handling."""

    def __init__(self, strategies_dir: Optional[str] = None):
        self.strategies_dir = (
            Path(strategies_dir) if strategies_dir else Path("configs/strategies")
        )
        self.parameter_resolver = ParameterResolver()
        self.path_resolver = PathResolver()
        self.logger = logging.getLogger(__name__)

    def load_strategy(
        self, strategy_name: str, validate: bool = True
    ) -> Dict[str, Any]:
        """
        Load and resolve a strategy with full parameter and path resolution.

        Args:
            strategy_name: Name of the strategy to load
            validate: Whether to validate strategy after loading

        Returns:
            Fully resolved strategy configuration

        Raises:
            StrategyLoadError: If strategy cannot be loaded
            ParameterResolutionError: If parameter resolution fails
            StrategyValidationError: If strategy validation fails
        """

        # Find strategy file
        strategy_file = self._find_strategy_file(strategy_name)
        if not strategy_file:
            raise StrategyLoadError(
                f"Strategy '{strategy_name}' not found in {self.strategies_dir}"
            )

        try:
            # Load raw YAML content
            with open(strategy_file, "r") as f:
                raw_content = yaml.safe_load(f)

            if not raw_content:
                raise StrategyLoadError(
                    f"Strategy file '{strategy_file}' is empty or invalid"
                )

            self.logger.info(f"Loading strategy '{strategy_name}' from {strategy_file}")

            # Resolve parameters
            try:
                resolved_content = self.parameter_resolver.resolve_strategy_parameters(
                    raw_content
                )
            except Exception as e:
                self.logger.error(
                    f"Parameter resolution failed for strategy '{strategy_name}': {e}"
                )
                raise ParameterResolutionError(
                    f"Failed to resolve parameters in strategy '{strategy_name}': {e}"
                )

            # Resolve file paths
            resolved_content = self._resolve_file_paths(resolved_content)

            # Validate strategy if requested
            if validate:
                self._validate_strategy(resolved_content)

            self.logger.info(
                f"Successfully loaded and resolved strategy '{strategy_name}'"
            )
            return resolved_content

        except (ParameterResolutionError, StrategyValidationError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Failed to load strategy '{strategy_name}': {e}")
            raise StrategyLoadError(f"Failed to load strategy '{strategy_name}': {e}")

    def list_available_strategies(self) -> List[Dict[str, str]]:
        """
        List all available strategies in the strategies directory.

        Returns:
            List of strategy information dictionaries
        """
        strategies = []

        if not self.strategies_dir.exists():
            self.logger.warning(
                f"Strategies directory not found: {self.strategies_dir}"
            )
            return strategies

        for strategy_file in self.strategies_dir.rglob("*.yaml"):
            try:
                with open(strategy_file, "r") as f:
                    content = yaml.safe_load(f)

                if content:
                    strategies.append(
                        {
                            "name": content.get("name", strategy_file.stem),
                            "description": content.get(
                                "description", "No description available"
                            ),
                            "file": str(strategy_file),
                            "has_parameters": "parameters" in content,
                        }
                    )
            except Exception as e:
                self.logger.warning(
                    f"Could not read strategy file {strategy_file}: {e}"
                )

        return sorted(strategies, key=lambda x: x["name"])

    def _find_strategy_file(self, strategy_name: str) -> Optional[Path]:
        """Find strategy file by name."""

        if not self.strategies_dir.exists():
            self.logger.error(
                f"Strategies directory does not exist: {self.strategies_dir}"
            )
            return None

        # Try exact filename first
        for suffix in [".yaml", ".yml"]:
            candidate = self.strategies_dir / f"{strategy_name}{suffix}"
            if candidate.exists():
                return candidate

        # Search recursively by name in YAML content
        for strategy_file in self.strategies_dir.rglob("*.yaml"):
            try:
                with open(strategy_file, "r") as f:
                    content = yaml.safe_load(f)
                if content and content.get("name") == strategy_name:
                    return strategy_file
            except Exception as e:
                self.logger.debug(f"Could not read {strategy_file}: {e}")
                continue

        return None

    def _resolve_file_paths(self, strategy_content: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve file paths in strategy content."""

        resolved_content = strategy_content.copy()

        # Resolve paths in metadata
        metadata = resolved_content.get("metadata", {})

        # Source files
        for source_file in metadata.get("source_files", []):
            if "path" in source_file:
                original_path = source_file["path"]
                resolved_path = self.path_resolver.resolve_path(original_path)
                if resolved_path:
                    source_file["path"] = str(resolved_path)
                    source_file["resolved"] = True
                else:
                    self.logger.warning(
                        f"Could not resolve source file path: {original_path}"
                    )
                    source_file["resolved"] = False

        # Target files
        for target_file in metadata.get("target_files", []):
            if "path" in target_file:
                original_path = target_file["path"]
                resolved_path = self.path_resolver.resolve_path(original_path)
                if resolved_path:
                    target_file["path"] = str(resolved_path)
                    target_file["resolved"] = True
                else:
                    self.logger.warning(
                        f"Could not resolve target file path: {original_path}"
                    )
                    target_file["resolved"] = False

        # Resolve paths in parameters
        parameters = resolved_content.get("parameters", {})
        for param_name, param_value in parameters.items():
            if isinstance(param_value, str) and (
                "/" in param_value
                or param_value.endswith((".csv", ".tsv", ".json", ".yaml"))
            ):
                resolved_path = self.path_resolver.resolve_path(param_value)
                if resolved_path:
                    parameters[param_name] = str(resolved_path)

        # Resolve paths in step parameters
        for step in resolved_content.get("steps", []):
            action_params = step.get("action", {}).get("params", {})
            for param_name, param_value in action_params.items():
                if isinstance(param_value, str) and (
                    "file" in param_name.lower() or "path" in param_name.lower()
                ):
                    if (
                        param_name.endswith("output_path")
                        or "output" in param_name.lower()
                    ):
                        # Output paths - create safe output path
                        safe_path = self.path_resolver.get_safe_output_path(param_value)
                        action_params[param_name] = str(safe_path)
                    else:
                        # Input paths - resolve existing path
                        resolved_path = self.path_resolver.resolve_path(param_value)
                        if resolved_path:
                            action_params[param_name] = str(resolved_path)
                        else:
                            self.logger.warning(
                                f"Could not resolve path in step '{step.get('name', 'unknown')}': {param_value}"
                            )

        return resolved_content

    def _validate_strategy(self, strategy_content: Dict[str, Any]) -> None:
        """Validate resolved strategy content."""

        validation_errors = []

        # Check required fields
        required_fields = ["name", "steps"]
        for field in required_fields:
            if field not in strategy_content:
                validation_errors.append(f"Missing required field: {field}")

        # Validate steps
        steps = strategy_content.get("steps", [])
        if not steps:
            validation_errors.append("Strategy must have at least one step")

        for i, step in enumerate(steps):
            if "action" not in step:
                validation_errors.append(f"Step {i} missing 'action' field")
            else:
                action = step["action"]
                if "type" not in action:
                    validation_errors.append(f"Step {i} action missing 'type' field")

        # Check file existence for resolved paths
        metadata = strategy_content.get("metadata", {})

        for source_file in metadata.get("source_files", []):
            if source_file.get("resolved", False):
                path = Path(source_file["path"])
                if not path.exists():
                    validation_errors.append(f"Source file not found: {path}")

        # Validate parameter references in steps
        parameters = set(strategy_content.get("parameters", {}).keys())

        for i, step in enumerate(steps):
            step_yaml = yaml.dump(step)
            # Find parameter references
            import re

            param_refs = re.findall(r"\$\{parameters\.([^}]+)\}", step_yaml)

            for param_ref in param_refs:
                if param_ref not in parameters:
                    validation_errors.append(
                        f"Step {i} references undefined parameter: {param_ref}"
                    )

        if validation_errors:
            error_msg = "Strategy validation failed:\n" + "\n".join(
                f"  - {error}" for error in validation_errors
            )
            raise StrategyValidationError(error_msg)


# Convenience functions
def load_strategy_with_resolution(
    strategy_name: str, strategies_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Load strategy with full parameter and path resolution."""
    loader = EnhancedStrategyLoader(strategies_dir)
    return loader.load_strategy(strategy_name, validate=True)


def list_strategies(strategies_dir: Optional[str] = None) -> List[Dict[str, str]]:
    """List all available strategies."""
    loader = EnhancedStrategyLoader(strategies_dir)
    return loader.list_available_strategies()
