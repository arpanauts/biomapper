"""
Strategy handler module for managing mapping strategy execution.

This module provides high-level orchestration of mapping strategies, including:
- Loading strategies from the database
- Managing strategy execution flow
- Tracking results and provenance
- Handling strategy context across steps
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError,
    MappingExecutionError
)
from biomapper.core.engine_components.action_executor import ActionExecutor
from biomapper.db.models import (
    MappingStrategy,
    MappingStrategyStep,
    Endpoint
)

logger = logging.getLogger(__name__)


def get_current_utc_time() -> datetime:
    """Return the current time in UTC timezone."""
    return datetime.now(timezone.utc)


class StrategyHandler:
    """Handles loading and execution of mapping strategies."""
    
    def __init__(self, mapping_executor: Any = None):
        """
        Initialize the strategy handler.
        
        Args:
            mapping_executor: Reference to the main MappingExecutor instance
        """
        self.mapping_executor = mapping_executor
        self.action_executor = ActionExecutor(mapping_executor)
        self.logger = logger
    
    async def load_strategy(self, session: AsyncSession, strategy_name: str) -> MappingStrategy:
        """
        Load a mapping strategy from the database.
        
        Args:
            session: Active database session
            strategy_name: Name of the strategy to load
            
        Returns:
            MappingStrategy object with steps loaded
            
        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            InactiveStrategyError: If strategy is not active
        """
        # Query for the strategy with its steps
        stmt = (
            select(MappingStrategy)
            .where(MappingStrategy.name == strategy_name)
            .options(selectinload(MappingStrategy.steps))
        )
        
        result = await session.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise StrategyNotFoundError(f"Strategy '{strategy_name}' not found in database")
        
        if not strategy.is_active:
            raise InactiveStrategyError(f"Strategy '{strategy_name}' is not active")
        
        self.logger.info(f"Loaded strategy '{strategy_name}' with {len(strategy.steps)} steps")
        return strategy
    
    async def execute_strategy(
        self,
        session: AsyncSession,
        strategy: MappingStrategy,
        input_identifiers: List[str],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        batch_size: int = 1000,
        min_confidence: float = 0.0,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a mapping strategy.
        
        Args:
            session: Active database session
            strategy: MappingStrategy object to execute
            input_identifiers: List of input identifiers
            source_endpoint: Source endpoint configuration
            target_endpoint: Target endpoint configuration
            use_cache: Whether to use caching
            max_cache_age_days: Maximum cache age
            batch_size: Batch size for processing
            min_confidence: Minimum confidence threshold
            initial_context: Initial context values
            
        Returns:
            Dictionary containing execution results and statistics
        """
        start_time = get_current_utc_time()
        
        # Initialize strategy context
        strategy_context = initial_context or {}
        strategy_context.update({
            "strategy_name": strategy.name,
            "source_endpoint": source_endpoint.name,
            "target_endpoint": target_endpoint.name,
            "initial_count": len(input_identifiers)
        })
        
        # Initialize tracking variables
        current_identifiers = input_identifiers.copy()
        current_ontology_type = strategy.default_source_ontology_type or "UNKNOWN"
        step_results = []
        
        # Sort steps by order
        sorted_steps = sorted(strategy.steps, key=lambda s: s.step_order)
        
        # Execute each step
        for step_idx, step in enumerate(sorted_steps):
            if not step.is_active:
                self.logger.info(f"Skipping inactive step: {step.step_id}")
                continue
            
            # Call progress callback if provided
            if 'progress_callback' in strategy_context and strategy_context['progress_callback']:
                strategy_context['progress_callback'](step_idx, len(sorted_steps), f"Executing {step.step_id}")
            
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
            if not current_identifiers and step != sorted_steps[-1]:
                self.logger.warning("No identifiers remaining, stopping strategy execution")
                break
        
        # Calculate final statistics
        end_time = get_current_utc_time()
        duration_seconds = (end_time - start_time).total_seconds()
        
        return {
            "strategy_name": strategy.name,
            "execution_status": "completed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "initial_count": len(input_identifiers),
            "final_count": len(current_identifiers),
            "final_ontology_type": current_ontology_type,
            "step_results": step_results,
            "context": strategy_context
        }
    
    async def get_endpoint_by_name(self, session: AsyncSession, endpoint_name: str) -> Optional[Endpoint]:
        """
        Retrieve an endpoint configuration by name.
        
        Args:
            session: Active database session
            endpoint_name: Name of the endpoint to retrieve
            
        Returns:
            Endpoint object if found, None otherwise
        """
        stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()