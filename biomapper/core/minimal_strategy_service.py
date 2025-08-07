"""Minimal YAML strategy execution service."""
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, cast
import yaml
from jinja2 import Template
from pydantic import ValidationError

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.models.execution_context import (
    StrategyExecutionContext,
    ProvenanceRecord,
)
from datetime import datetime

logger = logging.getLogger(__name__)


class MinimalStrategyService:
    """Minimal service for executing YAML strategies."""

    def __init__(self, strategies_dir: str):
        """Initialize with strategies directory."""
        self.strategies_dir = Path(strategies_dir)
        self.strategies = self._load_strategies()
        self.action_registry = self._build_action_registry()

    def _load_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load all YAML strategies from directory."""
        strategies = {}

        if not self.strategies_dir.exists():
            logger.warning(f"Strategies directory not found: {self.strategies_dir}")
            return strategies

        for yaml_file in self.strategies_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    strategy_data = yaml.safe_load(f)
                    if strategy_data and "name" in strategy_data:
                        strategies[strategy_data["name"]] = strategy_data
                        logger.info(f"Loaded strategy: {strategy_data['name']}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")

        return strategies

    def _substitute_parameters(self, obj: Any, parameters: Dict[str, Any]) -> Any:
        """Recursively substitute parameter placeholders in a nested structure.

        Args:
            obj: The object to process (dict, list, str, or other)
            parameters: The parameters dictionary for substitution

        Returns:
            The object with all parameter placeholders substituted
        """
        if isinstance(obj, str):
            # Check if the string contains parameter placeholders
            if "${" in obj:
                # Use Jinja2 template for substitution
                # Convert ${parameters.key} to {{ parameters.key }}
                template_str = re.sub(r"\$\{([^}]+)\}", r"{{ \1 }}", obj)
                template = Template(template_str)
                try:
                    return template.render(parameters=parameters)
                except Exception as e:
                    logger.warning(f"Failed to substitute parameters in '{obj}': {e}")
                    return obj
            return obj
        elif isinstance(obj, dict):
            return {
                key: self._substitute_parameters(value, parameters)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._substitute_parameters(item, parameters) for item in obj]
        else:
            return obj

    def _build_action_registry(self) -> Dict[str, type[TypedStrategyAction]]:
        """Build registry of available actions."""
        # Import to ensure all actions are registered
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

        # Use the central action registry which has all registered actions
        logger.info(f"Loaded {len(ACTION_REGISTRY)} actions from registry")
        return ACTION_REGISTRY

    def _create_dual_context(
        self, execution_context: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Optional[StrategyExecutionContext]]:
        """Create both dict and Pydantic contexts for dual support.

        Returns:
            Tuple of (dict_context, pydantic_context)
        """
        dict_context = execution_context

        # Try to create StrategyExecutionContext with sensible defaults
        try:
            # Get the first identifier if available
            identifiers = execution_context.get("current_identifiers", [])
            first_identifier = identifiers[0] if identifiers else "unknown"

            # Map ontology type to valid literal
            ontology_type = execution_context.get("current_ontology_type", "protein")
            valid_types = [
                "gene",
                "protein",
                "metabolite",
                "variant",
                "compound",
                "pathway",
                "disease",
            ]
            mapped_type = "protein"  # default

            # Simple mapping
            for valid_type in valid_types:
                if valid_type.upper() in ontology_type.upper():
                    mapped_type = valid_type
                    break

            # Clean up provenance data to match ProvenanceRecord schema
            raw_provenance = execution_context.get("provenance", [])
            cleaned_provenance = []

            for prov_item in raw_provenance:
                if isinstance(prov_item, dict):
                    # Convert dict provenance to ProvenanceRecord format
                    cleaned_prov = ProvenanceRecord(
                        source=prov_item.get(
                            "source", prov_item.get("action", "unknown")
                        ),
                        timestamp=prov_item.get("timestamp", datetime.now()),
                        action=prov_item.get("action", "unknown"),
                        details=prov_item.get("details", {}),
                    )
                    cleaned_provenance.append(cleaned_prov)

            pydantic_context = StrategyExecutionContext(
                initial_identifier=first_identifier,
                current_identifier=first_identifier,
                ontology_type=cast(Any, mapped_type),
                step_results={},
                provenance=cleaned_provenance,
                custom_action_data=execution_context.copy(),
            )

            logger.debug(f"Created Pydantic context with ontology type: {mapped_type}")
            return dict_context, pydantic_context

        except Exception as e:
            logger.debug(f"Could not create Pydantic context: {e}")
            return dict_context, None

    def _sync_contexts(
        self,
        dict_context: Dict[str, Any],
        pydantic_context: Optional[StrategyExecutionContext],
    ):
        """Synchronize changes between dict and Pydantic contexts."""
        if pydantic_context is None:
            return

        try:
            # Update dict from Pydantic custom_action_data
            for key, value in pydantic_context.custom_action_data.items():
                dict_context[key] = value

            # Update Pydantic from dict (all keys except system ones)
            system_keys = [
                "initial_identifier",
                "current_identifier",
                "step_results",
                "provenance",
                "current_identifiers",
                "current_ontology_type",
            ]
            for key, value in dict_context.items():
                if key not in system_keys:
                    pydantic_context.set_action_data(key, value)

            # Special handling for datasets - ensure it's in both contexts
            # Datasets can be at top level or in custom_action_data
            dict_datasets = dict_context.get("datasets", {})
            dict_custom_datasets = dict_context.get("custom_action_data", {}).get(
                "datasets", {}
            )
            pydantic_datasets = pydantic_context.get_action_data("datasets", {})

            # Merge all datasets
            all_datasets = {}
            all_datasets.update(dict_datasets)
            all_datasets.update(dict_custom_datasets)
            all_datasets.update(pydantic_datasets)

            # Sync to both contexts
            if all_datasets:
                pydantic_context.set_action_data("datasets", all_datasets)
                dict_context["datasets"] = all_datasets
                if "custom_action_data" not in dict_context:
                    dict_context["custom_action_data"] = {}
                dict_context["custom_action_data"]["datasets"] = all_datasets

            logger.debug(
                f"Context sync completed. Dict keys: {list(dict_context.keys())}"
            )
            logger.debug(
                f"Dict datasets: {list(dict_context.get('datasets', {}).keys()) if 'datasets' in dict_context else 'no datasets'}"
            )
            logger.debug(
                f"Pydantic custom_action_data keys: {list(pydantic_context.custom_action_data.keys())}"
            )
            pydantic_datasets = pydantic_context.get_action_data("datasets", {})
            logger.debug(
                f"Pydantic datasets after sync: {list(pydantic_datasets.keys()) if pydantic_datasets else 'no datasets'}"
            )

        except Exception as e:
            logger.debug(f"Context sync failed: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    def _determine_context_preference(self, action_class) -> str:
        """Determine if action prefers dict or Pydantic context.

        Returns:
            'dict' for dict-based actions, 'pydantic' for Pydantic-based
        """

        # Action preference based on known compatibility patterns
        action_name = action_class.__name__

        # MVP actions that work reliably with dict contexts
        mvp_actions = {
            "LoadDatasetIdentifiersAction",
            "MergeWithUniprotResolutionAction",
            "CalculateSetOverlapAction",
            "MergeDatasetsAction",
        }

        if action_name in mvp_actions:
            return "dict"

        # Complex actions that need Pydantic contexts for full functionality
        pydantic_actions = {
            "NightingaleNmrMatchAction",
            "CtsEnrichedMatchAction",
            "VectorEnhancedMatchAction",
            "SemanticMetaboliteMatchAction",
            "CombineMetaboliteMatchesAction",
            "GenerateMetabolomicsReportAction",
        }

        if action_name in pydantic_actions:
            return "pydantic"

        # Default: try Pydantic first, fallback to dict
        return "pydantic"

    async def execute_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str = "",
        target_endpoint_name: str = "",
        input_identifiers: List[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a named strategy with dual context support."""

        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        strategy = self.strategies[strategy_name]

        # Merge default parameters with context overrides
        parameters = strategy.get("parameters", {}).copy()
        if context and "parameters" in context:
            parameters.update(context["parameters"])

        # Initialize execution context as a dict
        execution_context = {
            "current_identifiers": input_identifiers or [],
            "source_endpoint_name": source_endpoint_name,
            "target_endpoint_name": target_endpoint_name,
            "current_ontology_type": "protein",  # Default for our MVP
            "datasets": {},
            "statistics": {},
            "output_files": {},
            "custom_action_data": {},
            "provenance": [],
        }

        # Create dual contexts
        dict_context, pydantic_context = self._create_dual_context(execution_context)

        # Dummy endpoints for MVP
        dummy_endpoint = type(
            "Endpoint",
            (),
            {
                "id": 1,
                "name": "dummy",
                "description": "Dummy endpoint for MVP",
                "type": "file",
            },
        )()

        logger.info(
            f"Executing strategy '{strategy_name}' with {len(strategy.get('steps', []))} steps"
        )

        # Execute each step with smart context selection
        for step in strategy.get("steps", []):
            step_name = step.get("name", "unnamed")
            action_config = step.get("action", {})
            action_type = action_config.get("type")
            # Substitute parameters in action params
            raw_params = action_config.get("params", {})
            action_params = self._substitute_parameters(raw_params, parameters)

            logger.info(f"Executing step '{step_name}' with action '{action_type}'")

            if action_type not in self.action_registry:
                raise ValueError(f"Unknown action type: {action_type}")

            # Create action
            action_class = self.action_registry[action_type]
            action = action_class()

            # Determine preferred context type
            context_preference = self._determine_context_preference(action_class)

            try:
                result_dict = None

                # Try preferred context first
                if context_preference == "pydantic" and pydantic_context:
                    try:
                        logger.debug(f"Trying {action_type} with Pydantic context")
                        # Ensure data is synced before execution
                        self._sync_contexts(dict_context, pydantic_context)

                        # Debug: check context contents before action
                        datasets = pydantic_context.get_action_data("datasets", {})
                        logger.debug(
                            f"Datasets available before {action_type}: {list(datasets.keys())}"
                        )

                        result_dict = await action.execute(
                            current_identifiers=dict_context["current_identifiers"],
                            current_ontology_type=dict_context.get(
                                "current_ontology_type", "protein"
                            ),
                            action_params=action_params,
                            source_endpoint=dummy_endpoint,
                            target_endpoint=dummy_endpoint,
                            context=pydantic_context,
                        )
                        logger.debug(
                            f"Successfully executed {action_type} with Pydantic context"
                        )
                        # Sync contexts after successful execution
                        self._sync_contexts(dict_context, pydantic_context)

                    except (ValidationError, AttributeError, TypeError) as e:
                        logger.debug(f"Pydantic context failed for {action_type}: {e}")
                        logger.debug(f"Falling back to dict context for {action_type}")
                        result_dict = None  # Will trigger fallback

                # Fallback to dict context or if dict is preferred
                if result_dict is None:
                    logger.debug(f"Executing {action_type} with dict context")
                    result_dict = await action.execute(
                        current_identifiers=dict_context["current_identifiers"],
                        current_ontology_type=dict_context.get(
                            "current_ontology_type", "protein"
                        ),
                        action_params=action_params,
                        source_endpoint=dummy_endpoint,
                        target_endpoint=dummy_endpoint,
                        context=dict_context,
                    )

                    # Try to sync back to Pydantic if it exists
                    if pydantic_context:
                        try:
                            # Update custom_action_data from dict changes
                            for key, value in dict_context.items():
                                if key not in [
                                    "current_identifiers",
                                    "current_ontology_type",
                                ]:
                                    pydantic_context.set_action_data(key, value)
                        except Exception as e:
                            logger.debug(
                                f"Failed to sync dict changes to Pydantic: {e}"
                            )

                # Update context with results
                if result_dict:
                    # Update standard fields in dict context
                    if "output_identifiers" in result_dict:
                        dict_context["current_identifiers"] = result_dict[
                            "output_identifiers"
                        ]
                    if "output_ontology_type" in result_dict:
                        dict_context["current_ontology_type"] = result_dict[
                            "output_ontology_type"
                        ]

                    # Merge provenance
                    if "provenance" in result_dict and result_dict["provenance"]:
                        if "provenance" not in dict_context:
                            dict_context["provenance"] = []

                        # Ensure provenance is a list
                        if isinstance(dict_context["provenance"], list):
                            dict_context["provenance"].extend(result_dict["provenance"])
                        else:
                            # Convert dict provenance to list
                            dict_context["provenance"] = result_dict["provenance"]

                        # Also add to Pydantic if available
                        if pydantic_context:
                            try:
                                for prov_item in result_dict["provenance"]:
                                    if isinstance(prov_item, dict):
                                        prov_record = ProvenanceRecord(
                                            source=prov_item.get("source", action_type),
                                            timestamp=prov_item.get(
                                                "timestamp", datetime.now()
                                            ),
                                            action=prov_item.get("action", action_type),
                                            details=prov_item.get("details", {}),
                                        )
                                        pydantic_context.provenance.append(prov_record)
                            except Exception as e:
                                logger.debug(
                                    f"Failed to sync provenance to Pydantic: {e}"
                                )

                    # Merge other result data
                    for key, value in result_dict.items():
                        if key not in [
                            "output_identifiers",
                            "output_ontology_type",
                            "provenance",
                        ]:
                            dict_context[key] = value

                    logger.debug(f"Step '{step_name}' completed successfully")

            except Exception as e:
                logger.error(f"Action '{action_type}' failed: {str(e)}")
                logger.error(f"Context preference was: {context_preference}")
                raise

        logger.info(f"Strategy '{strategy_name}' completed successfully")

        # Return the dict context (backward compatibility)
        return {
            "current_identifiers": dict_context.get("current_identifiers", []),
            "current_ontology_type": dict_context.get(
                "current_ontology_type", "protein"
            ),
            "datasets": dict_context.get("datasets", {}),
            "statistics": dict_context.get("statistics", {}),
            "output_files": dict_context.get("output_files", {}),
            "provenance": dict_context.get("provenance", []),
            "custom_action_data": dict_context.get("custom_action_data", {}),
        }
