"""Utilities for CLI scripts."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from tqdm import tqdm
from .client import BiomapperClient


def run_strategy(
    strategy_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function to run a strategy from CLI.

    Args:
        strategy_name: Name of strategy or path to YAML file
        parameters: Optional parameter overrides
        output_dir: Optional output directory
        **kwargs: Additional options passed to execute_strategy

    Returns:
        Execution result dictionary
    """

    async def _run():
        async with BiomapperClient() as client:
            # Prepare context with required fields
            context = {
                "source_endpoint_name": "",  # Not used for metabolomics strategies
                "target_endpoint_name": "",  # Not used for metabolomics strategies
                "input_identifiers": [],     # Strategies load their own data
                "parameters": parameters or {},
                "options": kwargs
            }
            if output_dir:
                context["parameters"]["output_dir"] = str(output_dir)
            return await client.execute_strategy(strategy_name, context)

    return asyncio.run(_run())


def run_with_progress(
    strategy_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Run strategy with progress bar.

    Args:
        strategy_name: Name of strategy or path to YAML file
        parameters: Optional parameter overrides
        output_dir: Optional output directory
        **kwargs: Additional options passed to execute_strategy

    Returns:
        Execution result dictionary
    """

    async def _run():
        async with BiomapperClient() as client:
            context = parameters or {}
            if output_dir:
                context["output_dir"] = str(output_dir)

            # For now, execute without real-time progress tracking
            # This will be enhanced when the API supports WebSocket/SSE
            print(f"Executing strategy: {strategy_name}")
            with tqdm(desc="Processing", unit="step") as pbar:
                result = await client.execute_strategy(strategy_name, context)
                pbar.update(1)
                pbar.set_description("Complete")

            return result

    return asyncio.run(_run())


def parse_parameters(param_str: Optional[str]) -> Dict[str, Any]:
    """Parse parameters from CLI argument.

    Args:
        param_str: JSON string or file path

    Returns:
        Parsed parameters dictionary
    """
    if not param_str:
        return {}

    # Check if it's a file path
    if not param_str.startswith("{") and Path(param_str).exists():
        with open(param_str) as f:
            return json.load(f)

    # Otherwise parse as JSON string
    try:
        return json.loads(param_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing parameters: {e}", file=sys.stderr)
        sys.exit(1)


def print_result(result: Dict[str, Any], verbose: bool = False):
    """Print execution result in a user-friendly format.

    Args:
        result: Execution result dictionary
        verbose: Whether to print detailed output
    """
    if result.get("success"):
        print("✓ Pipeline completed successfully")

        # Print output files if any
        if output_files := result.get("output_files"):
            print("\nOutput files:")
            for file in output_files:
                print(f"  - {file}")

        # Print summary statistics if available
        if stats := result.get("statistics"):
            print("\nStatistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        if verbose and (details := result.get("details")):
            print("\nDetailed results:")
            print(json.dumps(details, indent=2))
    else:
        print(
            f"✗ Pipeline failed: {result.get('error', 'Unknown error')}",
            file=sys.stderr,
        )
        if verbose and (traceback := result.get("traceback")):
            print("\nTraceback:", file=sys.stderr)
            print(traceback, file=sys.stderr)


class ExecutionOptions:
    """Options for strategy execution."""

    def __init__(
        self,
        checkpoint_enabled: bool = True,
        retry_failed_steps: bool = True,
        debug: bool = False,
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ):
        self.checkpoint_enabled = checkpoint_enabled
        self.retry_failed_steps = retry_failed_steps
        self.debug = debug
        self.max_retries = max_retries
        self.timeout = timeout

    def to_dict(self) -> Dict[str, Any]:
        """Convert options to dictionary for API."""
        return {
            "checkpoint_enabled": self.checkpoint_enabled,
            "retry_failed_steps": self.retry_failed_steps,
            "debug": self.debug,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
        }


async def execute_strategy_async(
    client: BiomapperClient,
    strategy_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    options: Optional[ExecutionOptions] = None,
) -> Dict[str, Any]:
    """Execute a strategy asynchronously with options.

    Args:
        client: BiomapperClient instance
        strategy_name: Name of strategy or path to YAML file
        parameters: Optional parameter overrides
        options: Execution options

    Returns:
        Execution result dictionary
    """
    context = parameters or {}

    # Add execution options to context
    if options:
        context["options"] = options.to_dict()

    return await client.execute_strategy(strategy_name, context)
