"""Progressive wrapper system for filtering unmatched identifiers and tracking stage statistics.

This module provides a generic progressive wrapper that filters out already-matched proteins 
before each mapping action and manages stage-by-stage statistics, following the 2025 
standardization framework.
"""

import time
from typing import Any, Dict, List, Optional, Set, Union
from abc import ABC, abstractmethod
import logging

from biomapper.core.standards.context_handler import UniversalContext
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction


class ProgressiveStage:
    """Statistics for a single progressive stage.
    
    Attributes:
        name: Human-readable name of the stage
        matched: Number of identifiers matched in this stage
        unmatched: Number of identifiers remaining unmatched after this stage
        new_matches: Number of new matches found in this stage
        cumulative_matched: Total matched identifiers up to this stage
        method: Description of the matching method used
        execution_time: Time taken to execute this stage (in seconds)
        start_time: When the stage started executing
        end_time: When the stage finished executing
    """
    
    def __init__(
        self,
        name: str,
        method: str = "Unknown",
        stage_number: int = 0
    ):
        self.name = name
        self.method = method
        self.stage_number = stage_number
        self.matched = 0
        self.unmatched = 0
        self.new_matches = 0
        self.cumulative_matched = 0
        self.execution_time = 0.0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary format for context storage."""
        return {
            "name": self.name,
            "matched": self.matched,
            "unmatched": self.unmatched,
            "new_matches": self.new_matches,
            "cumulative_matched": self.cumulative_matched,
            "method": self.method,
            "time": f"{self.execution_time:.1f}s"
        }


class ProgressiveWrapper:
    """Generic progressive wrapper that filters unmatched identifiers and tracks statistics.
    
    This wrapper filters out already-matched identifiers before executing each stage,
    tracks detailed statistics per stage, and maintains cumulative progress information.
    It follows the 2025 standardization framework using UniversalContext for robust
    context handling.
    
    Example:
        wrapper = ProgressiveWrapper(1, "direct_match")
        result = await wrapper.execute_stage(action_instance, params, context)
        
        # Access progressive statistics
        stats = context["progressive_stats"]
        print(f"Stage 1 matched: {stats['stages'][1]['matched']}")
    """
    
    def __init__(self, stage_number: int, stage_name: str, method: str = "Unknown"):
        """Initialize the progressive wrapper.
        
        Args:
            stage_number: Sequential number of this stage (1, 2, 3, ...)
            stage_name: Human-readable name for this stage
            method: Description of the matching method used in this stage
        """
        self.stage_number = stage_number
        self.stage_name = stage_name
        self.method = method
        self.logger = logging.getLogger(f"{__name__}.ProgressiveWrapper")
        
        # Efficient set for tracking matched identifiers
        self._matched_identifiers: Set[str] = set()
        
        # Current stage statistics
        self._current_stage = ProgressiveStage(stage_name, method, stage_number)
    
    async def execute_stage(
        self, 
        action_instance: TypedStrategyAction, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a stage with progressive filtering and statistics tracking.
        
        This method:
        1. Wraps context using UniversalContext for robust handling
        2. Filters parameters to only include unmatched identifiers
        3. Executes the action with filtered data
        4. Updates progressive statistics
        5. Returns results with updated context
        
        Args:
            action_instance: The action to execute
            params: Parameters for the action
            context: Execution context (dict format)
            
        Returns:
            Dictionary containing execution results
        """
        # Wrap context for 2025 standards compliance
        ctx = UniversalContext.wrap(context)
        
        # Initialize progressive stats if not present
        self._initialize_progressive_stats(ctx)
        
        # Filter parameters to unmatched identifiers only
        filtered_params = self._filter_to_unmatched(params, ctx)
        
        # Start timing
        self._current_stage.start_time = time.time()
        
        try:
            # Execute action with filtered parameters
            self.logger.info(f"Executing stage {self.stage_number}: {self.stage_name}")
            self.logger.debug(f"Processing {len(self._get_identifiers_from_params(filtered_params))} unmatched identifiers")
            
            result = await action_instance.execute(
                current_identifiers=self._get_identifiers_from_params(filtered_params),
                current_ontology_type="protein",  # Default for protein-focused wrapper
                action_params=filtered_params,
                source_endpoint=None,
                target_endpoint=None,
                context=ctx.unwrap()
            )
            
            # End timing
            self._current_stage.end_time = time.time()
            self._current_stage.execution_time = self._current_stage.end_time - self._current_stage.start_time
            
            # Update statistics based on results
            self._update_stage_statistics(result, ctx)
            
            # Store stage statistics in context
            self._store_stage_statistics(ctx)
            
            self.logger.info(f"Stage {self.stage_number} completed: {self._current_stage.new_matches} new matches found")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in stage {self.stage_number}: {str(e)}", exc_info=True)
            # Still update timing and store partial stats
            if self._current_stage.start_time:
                self._current_stage.end_time = time.time()
                self._current_stage.execution_time = self._current_stage.end_time - self._current_stage.start_time
            self._store_stage_statistics(ctx)
            raise
    
    def _initialize_progressive_stats(self, ctx: UniversalContext) -> None:
        """Initialize progressive statistics structure in context if not present."""
        if not ctx.has_key("progressive_stats"):
            ctx.set("progressive_stats", {
                "stages": {},
                "total_processed": 0,
                "final_match_rate": 0.0,
                "total_time": "0.0s"
            })
    
    def _filter_to_unmatched(self, params: Dict[str, Any], ctx: UniversalContext) -> Dict[str, Any]:
        """Filter parameters to only include unmatched identifiers.
        
        This method examines the parameters and context to identify which identifiers
        have already been matched in previous stages, removing them from processing.
        
        Args:
            params: Original parameters
            ctx: Universal context wrapper
            
        Returns:
            Filtered parameters containing only unmatched identifiers
        """
        filtered_params = params.copy()
        
        # Get current identifiers from various possible parameter names (2025 standards compliance)
        identifiers = self._get_identifiers_from_params(params)
        
        if not identifiers:
            self.logger.warning("No identifiers found in parameters for filtering")
            return filtered_params
        
        # Convert to set for efficient operations
        identifier_set = set(identifiers) if isinstance(identifiers, list) else {identifiers}
        
        # Filter out already matched identifiers
        unmatched = identifier_set - self._matched_identifiers
        
        self.logger.debug(f"Filtering: {len(identifier_set)} total, {len(self._matched_identifiers)} already matched, {len(unmatched)} unmatched")
        
        # Update parameters with filtered identifiers
        filtered_params = self._update_params_with_filtered_identifiers(filtered_params, list(unmatched))
        
        return filtered_params
    
    def _get_identifiers_from_params(self, params: Dict[str, Any]) -> List[str]:
        """Extract identifiers from parameters using standardized parameter names.
        
        Checks for identifiers in standard parameter names following 2025 framework.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            List of identifiers found in parameters
        """
        # Standard parameter names (2025 framework compliance)
        identifier_keys = [
            "identifiers",
            "input_identifiers", 
            "current_identifiers",
            "protein_identifiers",
            "uniprot_ids"
        ]
        
        for key in identifier_keys:
            if key in params:
                identifiers = params[key]
                if isinstance(identifiers, list):
                    return identifiers
                elif isinstance(identifiers, str):
                    return [identifiers]
                elif identifiers is not None:
                    return [str(identifiers)]
        
        # Fallback: check for any key containing "identifier"
        for key, value in params.items():
            if "identifier" in key.lower() and value:
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    return [value]
        
        return []
    
    def _update_params_with_filtered_identifiers(
        self, 
        params: Dict[str, Any], 
        filtered_identifiers: List[str]
    ) -> Dict[str, Any]:
        """Update parameters with filtered identifiers.
        
        Args:
            params: Original parameters
            filtered_identifiers: List of identifiers after filtering
            
        Returns:
            Updated parameters with filtered identifiers
        """
        updated_params = params.copy()
        
        # Update all identifier fields with filtered list
        identifier_keys = [
            "identifiers",
            "input_identifiers", 
            "current_identifiers",
            "protein_identifiers",
            "uniprot_ids"
        ]
        
        for key in identifier_keys:
            if key in updated_params:
                updated_params[key] = filtered_identifiers
                break
        else:
            # If no standard key found, add identifiers with default key
            updated_params["identifiers"] = filtered_identifiers
        
        return updated_params
    
    def _update_stage_statistics(self, result: Dict[str, Any], ctx: UniversalContext) -> None:
        """Update stage statistics based on action results.
        
        Args:
            result: Results from action execution
            ctx: Universal context wrapper
        """
        # Extract matched identifiers from result
        new_matched = self._extract_matched_identifiers(result)
        new_matches_count = len(new_matched)
        
        # Update matched identifiers set
        self._matched_identifiers.update(new_matched)
        
        # Update stage statistics
        self._current_stage.new_matches = new_matches_count
        self._current_stage.matched = new_matches_count
        self._current_stage.cumulative_matched = len(self._matched_identifiers)
        
        # Calculate unmatched count (requires knowledge of total)
        total_processed = self._get_total_processed_count(ctx)
        self._current_stage.unmatched = total_processed - self._current_stage.cumulative_matched
        
        # Update context totals
        self._update_context_totals(ctx, total_processed)
    
    def _extract_matched_identifiers(self, result: Dict[str, Any]) -> Set[str]:
        """Extract newly matched identifiers from action result.
        
        Args:
            result: Action execution result
            
        Returns:
            Set of newly matched identifiers
        """
        matched = set()
        
        # Standard result keys that might contain matched identifiers
        result_keys = [
            "output_identifiers",
            "matched_identifiers", 
            "resolved_identifiers",
            "successful_matches"
        ]
        
        for key in result_keys:
            if key in result:
                identifiers = result[key]
                if isinstance(identifiers, list):
                    matched.update(identifiers)
                elif isinstance(identifiers, str):
                    matched.add(identifiers)
        
        # Also check details section
        details = result.get("details", {})
        if isinstance(details, dict):
            for key in result_keys:
                if key in details:
                    identifiers = details[key]
                    if isinstance(identifiers, list):
                        matched.update(identifiers)
                    elif isinstance(identifiers, str):
                        matched.add(identifiers)
        
        return matched
    
    def _get_total_processed_count(self, ctx: UniversalContext) -> int:
        """Get total number of identifiers being processed.
        
        Args:
            ctx: Universal context wrapper
            
        Returns:
            Total count of identifiers
        """
        # Try to get from progressive stats first
        progressive_stats = ctx.get("progressive_stats", {})
        if "total_processed" in progressive_stats and progressive_stats["total_processed"] > 0:
            return progressive_stats["total_processed"]
        
        # Fallback: estimate from current_identifiers or datasets
        current_identifiers = ctx.get_current_identifiers()
        if current_identifiers and isinstance(current_identifiers, list):
            return len(current_identifiers)
        
        # Fallback: use matched + assumed unmatched
        return len(self._matched_identifiers) + 100  # Conservative estimate
    
    def _update_context_totals(self, ctx: UniversalContext, total_processed: int) -> None:
        """Update total statistics in context.
        
        Args:
            ctx: Universal context wrapper
            total_processed: Total number of identifiers processed
        """
        progressive_stats = ctx.get("progressive_stats", {})
        
        # Update totals
        progressive_stats["total_processed"] = total_processed
        progressive_stats["final_match_rate"] = (
            len(self._matched_identifiers) / total_processed if total_processed > 0 else 0.0
        )
        
        # Calculate total time from all stages
        total_time = 0.0
        for stage_data in progressive_stats.get("stages", {}).values():
            if isinstance(stage_data, dict) and "time" in stage_data:
                time_str = stage_data["time"]
                if time_str.endswith("s"):
                    try:
                        total_time += float(time_str[:-1])
                    except ValueError:
                        pass
        
        progressive_stats["total_time"] = f"{total_time:.1f}s"
        
        # Update context
        ctx.set("progressive_stats", progressive_stats)
    
    def _store_stage_statistics(self, ctx: UniversalContext) -> None:
        """Store current stage statistics in context.
        
        Args:
            ctx: Universal context wrapper
        """
        progressive_stats = ctx.get("progressive_stats", {})
        
        if "stages" not in progressive_stats:
            progressive_stats["stages"] = {}
        
        progressive_stats["stages"][self.stage_number] = self._current_stage.to_dict()
        
        ctx.set("progressive_stats", progressive_stats)
    
    def get_matched_identifiers(self) -> Set[str]:
        """Get the set of identifiers matched so far.
        
        Returns:
            Set of matched identifiers
        """
        return self._matched_identifiers.copy()
    
    def get_unmatched_count(self, total_count: int) -> int:
        """Get the number of unmatched identifiers.
        
        Args:
            total_count: Total number of identifiers
            
        Returns:
            Number of unmatched identifiers
        """
        return total_count - len(self._matched_identifiers)
    
    def reset_statistics(self) -> None:
        """Reset all statistics and matched identifier tracking."""
        self._matched_identifiers.clear()
        self._current_stage = ProgressiveStage(self.stage_name, self.method, self.stage_number)


class ProgressiveOrchestrator:
    """Orchestrator for managing multiple progressive stages.
    
    This class coordinates the execution of multiple progressive stages,
    ensuring proper filtering and statistics tracking across all stages.
    
    Example:
        orchestrator = ProgressiveOrchestrator()
        orchestrator.add_stage(1, "direct_match", action1, params1)
        orchestrator.add_stage(2, "composite_expansion", action2, params2)
        results = await orchestrator.execute_all(context)
    """
    
    def __init__(self):
        """Initialize the progressive orchestrator."""
        self.stages: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"{__name__}.ProgressiveOrchestrator")
    
    def add_stage(
        self,
        stage_number: int,
        stage_name: str,
        action_instance: TypedStrategyAction,
        params: Dict[str, Any],
        method: str = "Unknown"
    ) -> None:
        """Add a stage to the orchestrator.
        
        Args:
            stage_number: Sequential number of the stage
            stage_name: Human-readable name for the stage
            action_instance: The action to execute for this stage
            params: Parameters for the action
            method: Description of the matching method
        """
        stage_config = {
            "stage_number": stage_number,
            "stage_name": stage_name,
            "action_instance": action_instance,
            "params": params,
            "method": method
        }
        
        # Insert in order by stage number
        inserted = False
        for i, existing_stage in enumerate(self.stages):
            if existing_stage["stage_number"] > stage_number:
                self.stages.insert(i, stage_config)
                inserted = True
                break
        
        if not inserted:
            self.stages.append(stage_config)
    
    async def execute_all(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all stages in sequence with progressive filtering.
        
        Args:
            context: Execution context
            
        Returns:
            Combined results from all stages
        """
        ctx = UniversalContext.wrap(context)
        combined_results = {"stages": [], "final_context": context}
        
        # Execute each stage with the same progressive wrapper context
        for stage_config in self.stages:
            wrapper = ProgressiveWrapper(
                stage_config["stage_number"],
                stage_config["stage_name"],
                stage_config["method"]
            )
            
            try:
                stage_result = await wrapper.execute_stage(
                    stage_config["action_instance"],
                    stage_config["params"],
                    ctx.unwrap()
                )
                
                combined_results["stages"].append({
                    "stage_number": stage_config["stage_number"],
                    "stage_name": stage_config["stage_name"],
                    "result": stage_result
                })
                
                self.logger.info(f"Completed stage {stage_config['stage_number']}: {stage_config['stage_name']}")
                
            except Exception as e:
                self.logger.error(f"Failed stage {stage_config['stage_number']}: {str(e)}", exc_info=True)
                # Continue with remaining stages
                combined_results["stages"].append({
                    "stage_number": stage_config["stage_number"],
                    "stage_name": stage_config["stage_name"],
                    "error": str(e)
                })
        
        # Update final context
        combined_results["final_context"] = ctx.unwrap()
        
        return combined_results