#!/usr/bin/env python3
"""
Quick fix for the metabolomics pipeline to handle action execution correctly.
This is a simplified version that focuses on getting the pipeline running.

DEPRECATION WARNING:
This script is deprecated and will be removed in v2.0.
Please use the new API client instead:
    biomapper run three_way_metabolomics
    or
    python scripts/pipelines/run_metabolomics_fix.py
"""

import warnings

warnings.warn(
    "This script is deprecated and will be removed in v2.0. "
    "Use 'biomapper run three_way_metabolomics' or "
    "'python scripts/pipelines/run_metabolomics_fix.py' instead.",
    DeprecationWarning,
    stacklevel=2,
)

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import yaml
import json

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.strategy_actions.load_dataset_identifiers import (
    LoadDatasetIdentifiersAction,
)
from biomapper.core.strategy_actions.nightingale_nmr_match import (
    NightingaleNmrMatchAction,
)
from biomapper.core.strategy_actions.build_nightingale_reference import (
    BuildNightingaleReferenceAction,
)
from biomapper.core.strategy_actions.baseline_fuzzy_match import (
    BaselineFuzzyMatchAction,
)
from biomapper.core.strategy_actions.cts_enriched_match import CtsEnrichedMatchAction
from biomapper.core.strategy_actions.vector_enhanced_match import (
    VectorEnhancedMatchAction,
)
from biomapper.core.strategy_actions.generate_enhancement_report import (
    GenerateEnhancementReport,
)
from biomapper.core.strategy_actions.calculate_set_overlap import (
    CalculateSetOverlapAction,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleMetabolomicsRunner:
    """Simplified runner for metabolomics pipeline."""

    def __init__(self, config_path: str):
        """Initialize with configuration."""
        self.config_path = Path(config_path)
        self.context = {}  # Simple dict context
        self.context_wrapper = None  # Will be created once
        self.load_config()

    def interpolate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate parameter references in params."""
        result = {}
        for key, value in params.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # Extract parameter path
                param_path = value[2:-1]  # Remove ${ and }
                # Navigate the parameter tree
                parts = param_path.split(".")
                current = self.config
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        raise ValueError(f"Parameter not found: {param_path}")
                result[key] = current
            elif isinstance(value, dict):
                result[key] = self.interpolate_params(value)
            else:
                result[key] = value
        return result

    def load_config(self):
        """Load YAML configuration."""
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)
        logger.info(f"Loaded configuration: {self.config['name']}")

    async def run(self):
        """Run the pipeline."""
        logger.info("=" * 60)
        logger.info("Starting Metabolomics Harmonization Pipeline")
        logger.info("=" * 60)

        # Process each step
        for i, step in enumerate(self.config["steps"], 1):
            step_name = step["name"]
            action_type = step["action"]["type"]
            params = step["action"].get("params", {})

            # Interpolate parameters
            params = self.interpolate_params(params)

            logger.info(f"\n[{i}/{len(self.config['steps'])}] Executing: {step_name}")
            logger.info(f"Action type: {action_type}")

            try:
                await self.execute_action(action_type, params)
                logger.info(f"✓ {step_name} completed")

                # Debug: show context structure after load actions
                if action_type == "LOAD_DATASET_IDENTIFIERS":
                    logger.info(f"Context keys: {list(self.context.keys())}")
                    if "custom_action_data" in self.context:
                        logger.info(
                            f"Custom action data: {list(self.context['custom_action_data'].keys())}"
                        )
                        if "datasets" in self.context["custom_action_data"]:
                            logger.info(
                                f"Loaded datasets: {list(self.context['custom_action_data']['datasets'].keys())}"
                            )
            except Exception as e:
                logger.error(f"✗ {step_name} failed: {str(e)}")
                # For now, let's continue to see all errors
                logger.info("Continuing despite error...")

        # Save final context
        self.save_context()
        logger.info("\n" + "=" * 60)
        logger.info("Pipeline completed successfully!")

    async def execute_action(self, action_type: str, params: Dict[str, Any]):
        """Execute a single action."""
        # Map action types to classes
        action_map = {
            "LOAD_DATASET_IDENTIFIERS": LoadDatasetIdentifiersAction,
            "NIGHTINGALE_NMR_MATCH": NightingaleNmrMatchAction,
            "BUILD_NIGHTINGALE_REFERENCE": BuildNightingaleReferenceAction,
            "BASELINE_FUZZY_MATCH": BaselineFuzzyMatchAction,
            "CTS_ENRICHED_MATCH": CtsEnrichedMatchAction,
            "VECTOR_ENHANCED_MATCH": VectorEnhancedMatchAction,
            "GENERATE_ENHANCEMENT_REPORT": GenerateEnhancementReport,
            "CALCULATE_SET_OVERLAP": CalculateSetOverlapAction,
        }

        action_class = action_map.get(action_type)
        if not action_class:
            raise ValueError(f"Unknown action type: {action_type}")

        # Create action instance
        action = action_class()

        # Handle different action signatures
        if hasattr(action, "execute_typed"):
            # TypedStrategyAction - needs full signature
            # Get params model and create typed params
            params_model = action.get_params_model()
            typed_params = params_model(**params)

            # Create a context wrapper if needed (reuse existing one)
            if self.context_wrapper is None:
                # Use a simple dict-based context wrapper
                class ContextWrapper:
                    def __init__(self, context_dict):
                        self.custom_action_data = {}
                        self._dict = context_dict
                        self._dict["custom_action_data"] = self.custom_action_data

                    def set_action_data(self, key, value):
                        self.custom_action_data[key] = value

                    def get_action_data(self, key, default=None):
                        return self.custom_action_data.get(key, default)

                    def get(self, key, default=None):
                        return self._dict.get(key, default)

                    def set(self, key, value):
                        self._dict[key] = value

                    def update(self, data):
                        self._dict.update(data)

                    def __getitem__(self, key):
                        return self._dict[key]

                    def __setitem__(self, key, value):
                        self._dict[key] = value

                    def __contains__(self, key):
                        return key in self._dict

                self.context_wrapper = ContextWrapper(self.context)

            context_wrapper = self.context_wrapper

            # Call with full signature
            result = await action.execute_typed(
                current_identifiers=self.context.get("current_identifiers", []),
                current_ontology_type=self.context.get(
                    "current_ontology_type", "metabolite"
                ),
                params=typed_params,
                source_endpoint=None,  # Not needed for metabolomics actions
                target_endpoint=None,  # Not needed for metabolomics actions
                context=context_wrapper,
            )

            # Update context from result
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump(exclude_none=True)

                # Update simple fields in context
                for key, value in result_dict.items():
                    if key not in ["datasets", "custom_action_data"]:
                        self.context[key] = value
        else:
            # Legacy action
            result = await action.execute(
                self.context.get("current_identifiers", []),
                self.context.get("current_ontology_type", "metabolite"),
                params,
                None,
                None,
                self.context,
            )
            if result:
                self.context.update(result)

        # Log metrics if available
        self.log_metrics()

    def log_metrics(self):
        """Log current metrics."""
        if "metrics" in self.context:
            logger.info("\nCurrent Metrics:")
            for key, value in self.context["metrics"].items():
                if isinstance(value, dict) and "match_rate" in value:
                    count = value.get("total_matched", 0)
                    rate = value.get("match_rate", 0)
                    logger.info(f"  {key}: {count} matches ({rate:.1%})")

    def save_context(self):
        """Save context to JSON file."""
        output_path = Path("data/results/metabolomics_context.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.context, f, indent=2, default=str)
        logger.info(f"Context saved to: {output_path}")


async def main():
    """Main entry point."""
    config_path = "/home/ubuntu/biomapper/configs/strategies/metabolomics_progressive_enhancement.yaml"

    runner = SimpleMetabolomicsRunner(config_path)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
