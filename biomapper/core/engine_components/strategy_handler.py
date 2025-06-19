"""
Strategy handler module for managing mapping strategy execution.

This module provides high-level orchestration of mapping strategies, including:
- Loading strategies from the database
- Managing strategy execution flow
- Tracking results and provenance
- Handling strategy context across steps
"""

import logging
from typing import List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from biomapper.core.exceptions import (
    StrategyNotFoundError,
    InactiveStrategyError
)
from biomapper.db.models import (
    MappingStrategy,
    Endpoint
)

logger = logging.getLogger(__name__)


class StrategyHandler:
    """Handles loading and validation of mapping strategies."""
    
    def __init__(self, mapping_executor: Any = None):
        """
        Initialize the strategy handler.
        
        Args:
            mapping_executor: Reference to the main MappingExecutor instance
        """
        self.mapping_executor = mapping_executor
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
    
    async def validate_strategy_steps(self, strategy: MappingStrategy) -> List[str]:
        """
        Validate that all steps in a strategy are properly configured.
        
        Args:
            strategy: MappingStrategy object to validate
            
        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []
        
        if not strategy.steps:
            warnings.append(f"Strategy '{strategy.name}' has no steps defined")
            return warnings
        
        # Check for duplicate step orders
        step_orders = [step.step_order for step in strategy.steps]
        if len(step_orders) != len(set(step_orders)):
            warnings.append(f"Strategy '{strategy.name}' has duplicate step orders")
        
        # Validate each step
        for step in strategy.steps:
            if not step.action_type:
                warnings.append(f"Step '{step.step_id}' has no action type defined")
            
            if step.is_active and not step.action_parameters:
                # Some actions might not require parameters, so this is just a warning
                self.logger.debug(f"Step '{step.step_id}' has no action parameters")
        
        return warnings
    
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