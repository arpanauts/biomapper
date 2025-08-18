"""
Simplified service for mapping operations with Biomapper.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from core.minimal_strategy_service import MinimalStrategyService

logger = logging.getLogger(__name__)


class MapperService:
    """Simplified service for mapping operations with Biomapper."""

    def __init__(self):
        logger.info("Initializing MapperService...")
        
        # Initialize MinimalStrategyService
        strategies_dir = Path(__file__).parent.parent.parent / "configs" / "strategies"
        try:
            self.strategy_service = MinimalStrategyService(str(strategies_dir))
            logger.info(f"MinimalStrategyService initialized with {strategies_dir}")
        except Exception as e:
            logger.error(f"Failed to create MinimalStrategyService: {e}", exc_info=True)
            raise
        
        logger.info("MapperService initialized.")
    
    async def execute_strategy(self, strategy_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a strategy by name.
        
        Args:
            strategy_name: Name of the strategy to execute
            parameters: Strategy parameters
            
        Returns:
            Execution results
        """
        try:
            # Use MinimalStrategyService to execute
            result = await self.strategy_service.execute_strategy(strategy_name, parameters)
            return result
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}", exc_info=True)
            raise
    
    def list_strategies(self) -> list:
        """List available strategies.
        
        Returns:
            List of strategy names
        """
        try:
            return self.strategy_service.list_available_strategies()
        except Exception as e:
            logger.error(f"Failed to list strategies: {e}", exc_info=True)
            return []