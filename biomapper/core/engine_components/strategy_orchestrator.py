"""
Strategy orchestrator module for managing the execution flow of mapping strategies.

This module provides high-level orchestration of mapping strategies defined in YAML,
separating the strategy execution logic from the MappingExecutor's other responsibilities.
It handles:
- Loading and validating strategies via StrategyHandler
- Iterating through strategy steps
- Managing execution context flow between steps
- Deciding step types (mapping path vs custom action)
- Collecting results and metrics
"""

import logging
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from biomapper.core.exceptions import (
    ConfigurationError,
    MappingExecutionError,
)
from biomapper.core.engine_components.action_executor import ActionExecutor

if TYPE_CHECKING:
    from biomapper.core.mapping_executor import MappingExecutor
    from biomapper.core.engine_components.strategy_handler import StrategyHandler
    from biomapper.core.engine_components.cache_manager import CacheManager

logger = logging.getLogger(__name__)


def get_current_utc_time() -> datetime:
    """Return the current time in UTC timezone."""
    return datetime.now(timezone.utc)


class StrategyOrchestrator:
    """Orchestrates the execution of YAML-defined mapping strategies."""
    
    def __init__(
        self,
        metamapper_session_factory: sessionmaker,
        cache_manager: 'CacheManager',
        strategy_handler: 'StrategyHandler',
        path_execution_manager: Optional[Any] = None,
        resource_clients_provider: Optional[Callable] = None,
        mapping_executor: Optional['MappingExecutor'] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the StrategyOrchestrator.
        
        Args:
            metamapper_session_factory: Factory for creating database sessions
            cache_manager: Instance of CacheManager for cache operations
            strategy_handler: Instance of StrategyHandler for loading/validating strategies
            path_execution_manager: Component for executing mapping paths (optional initially)
            resource_clients_provider: Callable to get initialized resource clients
            mapping_executor: Reference to MappingExecutor (temporary for backwards compatibility)
            logger: Logger instance
        """
        self.metamapper_session_factory = metamapper_session_factory
        self.cache_manager = cache_manager
        self.strategy_handler = strategy_handler
        self.path_execution_manager = path_execution_manager
        self.resource_clients_provider = resource_clients_provider
        self.mapping_executor = mapping_executor
        self.logger = logger or logging.getLogger(__name__)
        self.action_executor = ActionExecutor(mapping_executor)
    
    async def execute_strategy(
        self,
        strategy_name: str,
        input_identifiers: List[str],
        initial_context: Optional[Dict[str, Any]] = None,
        source_endpoint_name: Optional[str] = None,
        target_endpoint_name: Optional[str] = None,
        mapping_session_id: Optional[int] = None,
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        batch_size: int = 250,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Execute a YAML-defined mapping strategy.
        
        This method orchestrates the execution of a multi-step mapping strategy,
        delegating the actual execution of steps to the StrategyHandler while
        managing the overall flow and result collection.
        
        Args:
            strategy_name: Name of the strategy to execute
            input_identifiers: List of identifiers to map
            initial_context: Optional initial context values
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            mapping_session_id: Optional session ID for tracking
            source_ontology_type: Optional override for source ontology type
            target_ontology_type: Optional override for target ontology type
            use_cache: Whether to use caching
            max_cache_age_days: Maximum cache age in days
            progress_callback: Optional callback function(current_step, total_steps, status)
            batch_size: Size of batches for processing
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict[str, Any]: A MappingResultBundle-structured dictionary containing:
                - 'results': Dict[str, Dict] mapping source IDs to their mapped values
                - 'metadata': Dict with execution metadata
                - 'step_results': List[Dict] with detailed results from each step
                - 'statistics': Dict with mapping statistics
                - 'final_identifiers': List of identifiers after all steps
                - 'final_ontology_type': Final ontology type after all conversions
                - 'summary': Dict with consolidated summary including strategy_name, total_mapped, and step_results
        """
        start_time = get_current_utc_time()
        
        async with self.metamapper_session_factory() as session:
            # Load the strategy
            strategy = await self.strategy_handler.load_strategy(session, strategy_name)
            
            # Load endpoints if names provided
            source_endpoint = None
            target_endpoint = None
            
            if source_endpoint_name:
                source_endpoint = await self.strategy_handler.get_endpoint_by_name(session, source_endpoint_name)
                if not source_endpoint:
                    raise ConfigurationError(f"Source endpoint '{source_endpoint_name}' not found")
            
            if target_endpoint_name:
                target_endpoint = await self.strategy_handler.get_endpoint_by_name(session, target_endpoint_name)
                if not target_endpoint:
                    raise ConfigurationError(f"Target endpoint '{target_endpoint_name}' not found")
            
            # Initialize tracking variables
            current_identifiers = input_identifiers.copy()
            current_ontology_type = source_ontology_type or strategy.default_source_ontology_type or "UNKNOWN"
            step_results = []
            
            # Initialize strategy context
            strategy_context = initial_context or {}
            strategy_context.update({
                'initial_identifiers': input_identifiers.copy(),
                'current_identifiers': current_identifiers.copy(),
                'current_ontology_type': current_ontology_type,
                'step_results': [],
                'all_provenance': [],
                'mapping_results': {},
                'progress_callback': progress_callback,
                'mapping_session_id': mapping_session_id,
                'strategy_name': strategy.name,
                'source_endpoint': source_endpoint.name if source_endpoint else None,
                'target_endpoint': target_endpoint.name if target_endpoint else None,
                'initial_count': len(input_identifiers),
                'mapping_executor': self.mapping_executor  # Add mapping executor to context
            })
            
            # Sort steps by order
            sorted_steps = sorted(strategy.steps, key=lambda s: s.step_order)
            
            # Execute each step
            for step_idx, step in enumerate(sorted_steps):
                if not step.is_active:
                    self.logger.info(f"Skipping inactive step: {step.step_id}")
                    continue
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(step_idx, len(sorted_steps), f"Executing {step.step_id}")
                
                step_start_time = get_current_utc_time()
                
                try:
                    # Execute the action
                    result = await self.action_executor.execute_action(
                        step=step,
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_ontology_type,
                        source_endpoint=source_endpoint,
                        target_endpoint=target_endpoint,
                        use_cache=use_cache,
                        max_cache_age_days=max_cache_age_days,
                        batch_size=batch_size,
                        min_confidence=min_confidence,
                        strategy_context=strategy_context,
                        db_session=session
                    )
                    
                    # Track step result
                    step_result = {
                        "step_id": step.step_id,
                        "description": step.description,
                        "action_type": step.action_type,
                        "status": "success",
                        "input_count": len(current_identifiers),
                        "output_count": len(result.get('output_identifiers', [])),
                        "duration_seconds": (get_current_utc_time() - step_start_time).total_seconds(),
                        "details": result.get('details', {})
                    }
                    
                    # Update current state
                    current_identifiers = result.get('output_identifiers', [])
                    current_ontology_type = result.get('output_ontology_type', current_ontology_type)
                    
                    # Update context with current state
                    strategy_context['current_identifiers'] = current_identifiers
                    strategy_context['current_ontology_type'] = current_ontology_type
                    
                    # Accumulate provenance if present
                    if 'provenance' in result:
                        strategy_context['all_provenance'].extend(result['provenance'])
                    
                except Exception as e:
                    self.logger.error(f"Step {step.step_id} failed: {str(e)}")
                    
                    step_result = {
                        "step_id": step.step_id,
                        "description": step.description,
                        "action_type": step.action_type,
                        "status": "failed",
                        "error": str(e),
                        "duration_seconds": (get_current_utc_time() - step_start_time).total_seconds()
                    }
                    
                    # Check if step is required
                    if step.is_required:
                        raise MappingExecutionError(
                            f"Required step '{step.step_id}' failed: {str(e)}"
                        )
                
                step_results.append(step_result)
                
                # Stop if no identifiers remain and we have more steps
                if not current_identifiers and step_idx < len(sorted_steps) - 1:
                    self.logger.warning("No identifiers remaining, stopping strategy execution")
                    break
            
            # Update context with results
            strategy_context['step_results'] = step_results
            strategy_context['current_identifiers'] = current_identifiers
            strategy_context['current_ontology_type'] = current_ontology_type
            
            overall_provenance = strategy_context.get('all_provenance', [])
        
        # Calculate final statistics
        end_time = get_current_utc_time()
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Build final results using the provenance data
        final_results = self._build_final_results(
            input_identifiers=input_identifiers,
            current_identifiers=current_identifiers,
            overall_provenance=overall_provenance,
            strategy_name=strategy_name,
            source_ontology_type=source_ontology_type or strategy.default_source_ontology_type,
            target_ontology_type=target_ontology_type or strategy.default_target_ontology_type,
        )
        
        # Calculate summary statistics
        mapped_count = len([r for r in final_results.values() if r['mapped_value'] is not None])
        
        # Return comprehensive results
        return {
            'results': final_results,
            'metadata': {
                'strategy_name': strategy_name,
                'execution_status': 'completed',
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration_seconds,
            },
            'step_results': step_results,
            'statistics': {
                'initial_count': len(input_identifiers),
                'final_count': len(current_identifiers),
                'mapped_count': mapped_count,
            },
            'final_identifiers': current_identifiers,
            'final_ontology_type': current_ontology_type,
            'summary': {
                'strategy_name': strategy_name,
                'total_input': len(input_identifiers),
                'total_mapped': mapped_count,
                'steps_executed': len(step_results),
                'step_results': step_results,
            },
        }
    
    def _build_final_results(
        self,
        input_identifiers: List[str],
        current_identifiers: List[str],
        overall_provenance: List[Dict[str, Any]],
        strategy_name: str,
        source_ontology_type: str,
        target_ontology_type: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build the final mapping results from provenance data.
        
        Args:
            input_identifiers: Original input identifiers
            current_identifiers: Final identifiers after all steps
            overall_provenance: Complete provenance chain
            strategy_name: Name of the executed strategy
            source_ontology_type: Source ontology type
            target_ontology_type: Target ontology type
            
        Returns:
            Dictionary mapping source IDs to their mapping results
        """
        mapping_results = {}
        
        # Initialize all input identifiers as unmapped
        for input_id in input_identifiers:
            mapping_results[input_id] = {
                'mapped_value': None,
                'confidence': 0.0,
                'error': 'No mapping found',
                'source_ontology': source_ontology_type,
                'target_ontology': target_ontology_type,
                'strategy_name': strategy_name,
                'provenance': []
            }
        
        # Process provenance to build complete mapping chains
        if overall_provenance:
            # Helper function to trace through the complete mapping chain
            def trace_mapping_chain(source_id, provenance_list, visited=None):
                """Recursively trace through the mapping chain to find final target."""
                if visited is None:
                    visited = set()
                
                if source_id in visited:
                    return []
                
                visited.add(source_id)
                
                # Find provenance entries where this ID is the source
                mappings = [p for p in provenance_list if p.get('source_id') == source_id and p.get('target_id')]
                
                if not mappings:
                    # Check if it was filtered but passed
                    filter_entries = [p for p in provenance_list if p.get('source_id') == source_id and p.get('action') == 'filter_passed']
                    if filter_entries:
                        return [source_id]
                    return []
                
                # For each mapping, trace to see if it maps further
                final_targets = []
                for mapping in mappings:
                    target = mapping['target_id']
                    further_mappings = trace_mapping_chain(target, provenance_list, visited)
                    if further_mappings:
                        final_targets.extend(further_mappings)
                    else:
                        final_targets.append(target)
                
                return final_targets
            
            # For each original input identifier, trace through the provenance chain
            for input_id in input_identifiers:
                input_provenance = [p for p in overall_provenance if p.get('source_id') == input_id]
                
                # Trace through the chain to find final targets
                final_targets = trace_mapping_chain(input_id, overall_provenance)
                
                if final_targets:
                    # Calculate confidence based on the provenance chain
                    confidence = 1.0
                    for prov in input_provenance:
                        if 'confidence' in prov:
                            confidence = min(confidence, prov['confidence'])
                    
                    mapping_results[input_id] = {
                        'mapped_value': final_targets[0],
                        'all_mapped_values': final_targets,
                        'confidence': confidence,
                        'source_ontology': source_ontology_type,
                        'target_ontology': target_ontology_type,
                        'strategy_name': strategy_name,
                        'provenance': input_provenance
                    }
        else:
            # Fallback: If no provenance but we have current_identifiers
            if len(current_identifiers) == len(input_identifiers):
                for i, input_id in enumerate(input_identifiers):
                    if i < len(current_identifiers):
                        mapping_results[input_id] = {
                            'mapped_value': current_identifiers[i],
                            'confidence': 1.0,
                            'source_ontology': source_ontology_type,
                            'target_ontology': target_ontology_type,
                            'strategy_name': strategy_name,
                            'provenance': []
                        }
        
        return mapping_results