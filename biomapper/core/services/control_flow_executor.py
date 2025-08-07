"""Control flow executor for enhanced YAML strategies.

This module provides an execution engine that supports control flow constructs
including conditionals, loops, error handling, and DAG-based execution.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Union
from collections import defaultdict, deque
import logging
from datetime import datetime
import json
import os
from pathlib import Path

from ..models.enhanced_strategy import EnhancedStrategy, EnhancedStepDefinition
from ..models.control_flow import (
    ErrorAction,
    BackoffStrategy,
    ExecutionMode,
    CheckpointTiming,
)
from .expression_evaluator import ConditionEvaluator, ExpressionError
from ..strategy_actions.registry import get_action_class


logger = logging.getLogger(__name__)


class StepExecutionError(Exception):
    """Error during step execution."""

    def __init__(
        self, step_name: str, message: str, original_error: Optional[Exception] = None
    ):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Step '{step_name}' failed: {message}")


class ControlFlowExecutor:
    """Execute strategies with control flow support."""

    def __init__(
        self,
        strategy: EnhancedStrategy,
        initial_context: Optional[Dict[str, Any]] = None,
        checkpoint_dir: Optional[str] = None,
    ):
        """
        Initialize control flow executor.

        Args:
            strategy: Enhanced strategy to execute
            initial_context: Initial execution context
            checkpoint_dir: Directory for checkpoints
        """
        self.strategy = strategy
        self.checkpoint_dir = (
            Path(checkpoint_dir) if checkpoint_dir else Path.cwd() / ".checkpoints"
        )

        # Initialize execution context
        self.context = self._initialize_context(initial_context)

        # Initialize condition evaluator
        self.evaluator = ConditionEvaluator(self.context)

        # Execution state
        self.executed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.skipped_steps: List[str] = []
        self.step_results: Dict[str, Any] = {}
        self.step_metrics: Dict[str, Dict[str, Any]] = {}

        # Variables (strategy-level)
        self.variables = dict(strategy.variables or {})
        self.context["variables"] = self.variables

        # Parameters (runtime)
        self.parameters = dict(strategy.parameters or {})
        self.context["parameters"] = self.parameters

        # Step tracking for loops
        self.loop_state: Dict[str, Dict[str, Any]] = {}

        # Checkpointing
        self.checkpoints: List[str] = []

    def _initialize_context(
        self, initial_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Initialize execution context."""
        context = initial_context or {}

        # Ensure required context keys exist
        context.setdefault("steps", {})
        context.setdefault("datasets", {})
        context.setdefault("metrics", {})
        context.setdefault("env", dict(os.environ))
        context.setdefault("api_keys", {})
        context.setdefault("current_identifiers", [])
        context.setdefault("statistics", {})

        # Add execution metadata
        context["execution"] = {
            "strategy_name": self.strategy.name,
            "strategy_version": self.strategy.version,
            "started_at": datetime.now().isoformat(),
            "dry_run": self.strategy.execution.dry_run
            if self.strategy.execution
            else False,
        }

        return context

    async def execute(self) -> Dict[str, Any]:
        """
        Execute strategy with control flow.

        Returns:
            Final execution context with results
        """
        logger.info(f"Starting execution of strategy: {self.strategy.name}")

        try:
            # Check pre-conditions
            if self.strategy.pre_conditions:
                logger.info("Checking pre-conditions...")
                for condition in self.strategy.pre_conditions:
                    if not self.evaluator.evaluate_condition(condition):
                        raise StepExecutionError(
                            "pre_conditions", f"Pre-condition not met: {condition}"
                        )

            # Execute based on mode
            if (
                self.strategy.execution
                and self.strategy.execution.mode == ExecutionMode.DAG
            ):
                logger.info("Executing strategy in DAG mode")
                await self._execute_dag()
            else:
                logger.info("Executing strategy in sequential mode")
                await self._execute_sequential()

            # Check post-conditions
            if self.strategy.post_conditions:
                logger.info("Checking post-conditions...")
                for condition in self.strategy.post_conditions:
                    if not self.evaluator.evaluate_condition(condition):
                        logger.warning(f"Post-condition not met: {condition}")

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            self.context["execution"]["error"] = str(e)
            raise

        finally:
            # Execute finally steps
            if self.strategy.finally_steps:
                logger.info("Executing finally steps...")
                for step in self.strategy.finally_steps:
                    try:
                        await self._execute_step(step)
                    except Exception as e:
                        logger.error(f"Finally step '{step.name}' failed: {e}")

            # Update execution metadata
            self.context["execution"]["completed_at"] = datetime.now().isoformat()
            self.context["execution"]["executed_steps"] = self.executed_steps
            self.context["execution"]["failed_steps"] = self.failed_steps
            self.context["execution"]["skipped_steps"] = self.skipped_steps

        return self.context

    async def _execute_sequential(self) -> None:
        """Execute steps sequentially with control flow."""
        for step in self.strategy.steps:
            # Convert dict to EnhancedStepDefinition if needed
            if isinstance(step, dict):
                step = EnhancedStepDefinition(**step)

            await self._process_step(step)

    async def _process_step(self, step: EnhancedStepDefinition) -> None:
        """Process a single step with all control flow logic."""
        # Check if step should be skipped
        if step.skip_if_exists:
            if self._check_skip_condition(step.skip_if_exists):
                logger.info(
                    f"Skipping step '{step.name}' - condition met: {step.skip_if_exists}"
                )
                self.skipped_steps.append(step.name)
                return

        # Check condition
        if step.condition and not self.evaluator.evaluate_condition(step.condition):
            logger.info(f"Skipping step '{step.name}' - condition not met")
            self.skipped_steps.append(step.name)
            return

        # Handle loops
        if step.for_each:
            await self._execute_foreach(step)
        elif step.repeat:
            await self._execute_repeat(step)
        elif step.parallel and step.for_each:
            await self._execute_parallel_foreach(step)
        else:
            # Regular step execution
            await self._execute_step_with_error_handling(step)

    async def _execute_step_with_error_handling(
        self, step: EnhancedStepDefinition
    ) -> Any:
        """Execute a step with error handling and retries."""
        error_config = step.on_error or self.strategy.error_handling

        # Determine error action
        if isinstance(error_config, str):
            error_action = ErrorAction(error_config)
            # For continue/skip, don't retry; for retry, use default 3 attempts
            max_attempts = (
                1 if error_action in [ErrorAction.CONTINUE, ErrorAction.SKIP] else 3
            )
            backoff = BackoffStrategy.LINEAR
            delay = 5
        elif error_config:
            error_action = (
                error_config.action
                if hasattr(error_config, "action")
                else ErrorAction.STOP
            )
            max_attempts = getattr(error_config, "max_attempts", 3)
            backoff = getattr(error_config, "backoff", BackoffStrategy.LINEAR)
            delay = getattr(error_config, "delay", 5)
        else:
            error_action = ErrorAction.STOP
            max_attempts = 1
            backoff = BackoffStrategy.LINEAR
            delay = 5

        # Execute with retries
        attempts = 0
        last_error = None

        while attempts < max_attempts:
            try:
                # Create checkpoint if needed
                if step.checkpoint in [CheckpointTiming.BEFORE, CheckpointTiming.BOTH]:
                    await self._create_checkpoint(f"before_{step.name}")

                # Execute step
                result = await self._execute_step(step)

                # Create checkpoint if needed
                if step.checkpoint in [CheckpointTiming.AFTER, CheckpointTiming.BOTH]:
                    await self._create_checkpoint(f"after_{step.name}")

                # Set variables if specified
                if step.set_variables:
                    for var_name, var_value in step.set_variables.items():
                        # Evaluate if it's an expression
                        if isinstance(var_value, str) and "${" in var_value:
                            var_value = self.evaluator.evaluator.evaluate(var_value)
                        self.variables[var_name] = var_value
                        self.context["variables"][var_name] = var_value

                return result

            except Exception as e:
                attempts += 1
                last_error = e
                logger.error(
                    f"Step '{step.name}' failed (attempt {attempts}/{max_attempts}): {e}"
                )

                if error_action == ErrorAction.STOP or attempts >= max_attempts:
                    # Stop execution or max attempts reached
                    self.failed_steps.append(step.name)

                    # Handle fallback
                    if hasattr(error_config, "fallback") and error_config.fallback:
                        logger.info(f"Executing fallback for step '{step.name}'")
                        # Execute fallback action
                        # TODO: Implement fallback execution

                    # Set error variable if specified
                    if (
                        hasattr(error_config, "set_variable")
                        and error_config.set_variable
                    ):
                        var_assignment = error_config.set_variable
                        if "=" in var_assignment:
                            var_name, var_value = var_assignment.split("=", 1)
                            self.variables[var_name.strip()] = var_value.strip()

                    if error_action == ErrorAction.STOP:
                        raise StepExecutionError(step.name, str(e), e)
                    elif error_action == ErrorAction.SKIP:
                        self.skipped_steps.append(step.name)
                        return None
                    elif error_action == ErrorAction.CONTINUE:
                        return None

                elif error_action == ErrorAction.RETRY:
                    # Calculate delay for retry
                    if backoff == BackoffStrategy.EXPONENTIAL:
                        wait_time = delay * (2 ** (attempts - 1))
                    else:  # LINEAR
                        wait_time = delay * attempts

                    logger.info(
                        f"Retrying step '{step.name}' in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)

        # Should not reach here, but handle gracefully
        raise StepExecutionError(
            step.name, f"Failed after {max_attempts} attempts", last_error
        )

    async def _execute_step(self, step: EnhancedStepDefinition) -> Any:
        """Execute a single step."""
        logger.info(f"Executing step: {step.name}")

        # Check if dry run
        if self.strategy.execution and self.strategy.execution.dry_run:
            logger.info(f"[DRY RUN] Would execute step: {step.name}")
            self.executed_steps.append(step.name)
            return {"dry_run": True, "step": step.name}

        # Get action class
        action_type = step.action.get("type")
        if not action_type:
            raise StepExecutionError(step.name, "Step action missing 'type' field")

        action_class = get_action_class(action_type)
        if not action_class:
            raise StepExecutionError(step.name, f"Unknown action type: {action_type}")

        # Create action instance
        action = action_class()

        # Prepare action parameters
        action_params = step.action.get("params", {})

        # Resolve parameter references
        resolved_params = self._resolve_parameters(action_params)

        # Execute action with timeout if specified
        try:
            if step.timeout:
                result = await asyncio.wait_for(
                    self._execute_action(action, resolved_params), timeout=step.timeout
                )
            else:
                result = await self._execute_action(action, resolved_params)

            # Store result
            self.step_results[step.name] = result
            self.context["steps"][step.name] = {
                "result": result,
                "executed_at": datetime.now().isoformat(),
                "success": True,
            }

            # Track metrics if available
            if isinstance(result, dict) and "metrics" in result:
                self.step_metrics[step.name] = result["metrics"]
                self.context["steps"][step.name]["metrics"] = result["metrics"]

            self.executed_steps.append(step.name)
            return result

        except asyncio.TimeoutError:
            raise StepExecutionError(
                step.name, f"Step timed out after {step.timeout} seconds"
            )
        except Exception as e:
            self.context["steps"][step.name] = {
                "error": str(e),
                "executed_at": datetime.now().isoformat(),
                "success": False,
            }
            raise

    async def _execute_action(self, action: Any, params: Dict[str, Any]) -> Any:
        """Execute an action with resolved parameters."""
        # Prepare execution context for action
        action_context = {
            "current_identifiers": self.context.get("current_identifiers", []),
            "datasets": self.context.get("datasets", {}),
            "statistics": self.context.get("statistics", {}),
            "steps": self.step_results,
            "variables": self.variables,
            "parameters": self.parameters,
        }

        # Call action's execute method
        if hasattr(action, "execute_typed"):
            # New typed action
            from ..models.execution_context import StrategyExecutionContext

            # Provide default values for required fields if not present
            current_ids = action_context.get("current_identifiers", [])
            typed_context = StrategyExecutionContext(
                **{
                    "initial_identifier": current_ids[0] if current_ids else "unknown",
                    "current_identifier": current_ids[0] if current_ids else "unknown",
                    "ontology_type": action_context.get(
                        "ontology_type", "gene"
                    ),  # Default to 'gene'
                    "current_identifiers": current_ids,
                    "datasets": action_context.get("datasets", {}),
                    "statistics": action_context.get("statistics", {}),
                }
            )
            result = await action.execute_typed(params, typed_context)
        else:
            # Legacy action
            result = await action.execute(
                current_identifiers=action_context["current_identifiers"],
                current_ontology_type="",  # TODO: Handle this properly
                action_params=params,
                source_endpoint=None,  # TODO: Handle endpoints
                target_endpoint=None,
                context=action_context,
            )

        return result

    async def _execute_foreach(self, step: EnhancedStepDefinition) -> None:
        """Execute step for each item in a collection."""
        items = self._resolve_items(step.for_each.items)

        logger.info(
            f"Executing for_each loop for step '{step.name}' with {len(items)} items"
        )

        for index, item in enumerate(items):
            # Set loop variables
            self.context["foreach"] = {
                "index": index,
                "item": item,
                "total": len(items),
            }
            self.context[step.for_each.as_variable] = item
            self.variables[step.for_each.as_variable] = item

            # Execute step
            await self._execute_step_with_error_handling(step)

        # Clear loop variables
        self.context.pop("foreach", None)
        self.context.pop(step.for_each.as_variable, None)
        self.variables.pop(step.for_each.as_variable, None)

    async def _execute_repeat(self, step: EnhancedStepDefinition) -> None:
        """Execute step repeatedly."""
        max_iterations = step.repeat.max_iterations or 1000
        iterations = 0

        logger.info(f"Executing repeat loop for step '{step.name}'")

        while iterations < max_iterations:
            # Check while condition
            if step.repeat.while_condition:
                if not self.evaluator.evaluate_condition(step.repeat.while_condition):
                    logger.info(
                        f"Repeat loop condition no longer met after {iterations} iterations"
                    )
                    break

            # Set loop variables
            self.context["repeat"] = {
                "iteration": iterations,
                "max_iterations": max_iterations,
            }

            # Execute step
            await self._execute_step_with_error_handling(step)
            iterations += 1

        # Clear loop variables
        self.context.pop("repeat", None)

        logger.info(f"Repeat loop completed after {iterations} iterations")

    async def _execute_parallel_foreach(self, step: EnhancedStepDefinition) -> None:
        """Execute for_each loop in parallel."""
        items = self._resolve_items(step.for_each.items)
        max_workers = step.parallel.max_workers if step.parallel else 3

        logger.info(
            f"Executing parallel for_each for step '{step.name}' with {len(items)} items, max workers: {max_workers}"
        )

        # Create tasks
        semaphore = asyncio.Semaphore(max_workers)

        async def execute_item(index: int, item: Any):
            async with semaphore:
                # Create isolated context for this iteration
                item_context = {
                    "foreach": {"index": index, "item": item, "total": len(items)},
                    step.for_each.as_variable: item,
                }

                # Merge with main context
                self.context.update(item_context)

                # Execute step
                await self._execute_step_with_error_handling(step)

        # Execute all items in parallel
        tasks = [execute_item(i, item) for i, item in enumerate(items)]

        if step.parallel and step.parallel.fail_fast:
            # Stop all if one fails
            results = await asyncio.gather(*tasks, return_exceptions=False)
        else:
            # Continue even if some fail
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Parallel iteration {i} failed: {result}")

    async def _execute_dag(self) -> None:
        """Execute steps as a directed acyclic graph."""
        # Build dependency graph
        graph = self._build_dependency_graph()

        # Topological sort with level-based execution
        levels = self._topological_levels(graph)

        logger.info(f"Executing DAG with {len(levels)} levels")

        for level_num, level_steps in enumerate(levels):
            logger.info(
                f"Executing level {level_num + 1} with {len(level_steps)} steps"
            )

            # Execute steps in this level in parallel
            tasks = []
            for step_name in level_steps:
                step = self._get_step_by_name(step_name)
                if step:
                    tasks.append(self._process_step(step))

            # Wait for all steps in this level to complete
            await asyncio.gather(*tasks)

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph from step definitions."""
        graph = defaultdict(set)

        for step in self.strategy.steps:
            if isinstance(step, dict):
                step = EnhancedStepDefinition(**step)

            if step.depends_on:
                for dep in step.depends_on:
                    graph[dep].add(step.name)
            else:
                # Steps with no dependencies
                graph[step.name] = graph.get(step.name, set())

        return dict(graph)

    def _topological_levels(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Perform topological sort and group into execution levels."""
        # Calculate in-degree for each node
        in_degree = defaultdict(int)
        all_nodes = set()

        for node, neighbors in graph.items():
            all_nodes.add(node)
            for neighbor in neighbors:
                in_degree[neighbor] += 1
                all_nodes.add(neighbor)

        # Find all nodes with no incoming edges
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        levels = []

        while queue:
            # Process current level
            current_level = list(queue)
            levels.append(current_level)
            queue.clear()

            # Remove edges and find next level
            for node in current_level:
                for neighbor in graph.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Check for cycles
        if sum(in_degree.values()) > 0:
            raise StepExecutionError(
                "dag", "Circular dependency detected in step dependencies"
            )

        return levels

    def _get_step_by_name(self, name: str) -> Optional[EnhancedStepDefinition]:
        """Get step definition by name."""
        for step in self.strategy.steps:
            if isinstance(step, dict):
                if step.get("name") == name:
                    return EnhancedStepDefinition(**step)
            elif step.name == name:
                return step
        return None

    def _resolve_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameter references in action parameters."""
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and "${" in value:
                # This is an expression/reference
                try:
                    resolved[key] = self.evaluator.evaluator.evaluate(value)
                except ExpressionError:
                    # If evaluation fails, keep original value
                    resolved[key] = value
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_parameters(value)
            elif isinstance(value, list):
                # Resolve items in lists
                resolved[key] = [
                    self.evaluator.evaluator.evaluate(item)
                    if isinstance(item, str) and "${" in item
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_items(self, items: Union[str, List[Any]]) -> List[Any]:
        """Resolve items for for_each loops."""
        if isinstance(items, str):
            if "${" in items:
                # Evaluate expression to get items
                return self.evaluator.evaluator.evaluate(items)
            else:
                # Treat as a single item
                return [items]
        else:
            return items or []

    def _check_skip_condition(self, condition: str) -> bool:
        """Check if skip condition is met."""
        if "${" in condition:
            # Evaluate as expression
            return bool(self.evaluator.evaluator.evaluate(condition))
        else:
            # Check if file/variable exists
            if condition in self.variables:
                return True
            if Path(condition).exists():
                return True
            return False

    async def _create_checkpoint(self, checkpoint_name: str) -> None:
        """Create a checkpoint of current execution state."""
        if not self.strategy.checkpointing or not self.strategy.checkpointing.enabled:
            return

        checkpoint_path = (
            self.checkpoint_dir
            / f"{self.strategy.name}_{checkpoint_name}_{int(time.time())}.json"
        )
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "strategy_name": self.strategy.name,
            "checkpoint_name": checkpoint_name,
            "timestamp": datetime.now().isoformat(),
            "context": self.context,
            "variables": self.variables,
            "parameters": self.parameters,
            "executed_steps": self.executed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "step_results": self.step_results,
            "step_metrics": self.step_metrics,
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        self.checkpoints.append(str(checkpoint_path))
        logger.info(f"Created checkpoint: {checkpoint_path}")

    async def restore_from_checkpoint(self, checkpoint_path: str) -> None:
        """Restore execution state from a checkpoint."""
        with open(checkpoint_path, "r") as f:
            checkpoint_data = json.load(f)

        self.context = checkpoint_data["context"]
        self.variables = checkpoint_data["variables"]
        self.parameters = checkpoint_data["parameters"]
        self.executed_steps = checkpoint_data["executed_steps"]
        self.failed_steps = checkpoint_data["failed_steps"]
        self.skipped_steps = checkpoint_data["skipped_steps"]
        self.step_results = checkpoint_data["step_results"]
        self.step_metrics = checkpoint_data["step_metrics"]

        # Reinitialize evaluator with restored context
        self.evaluator = ConditionEvaluator(self.context)

        logger.info(f"Restored from checkpoint: {checkpoint_path}")
