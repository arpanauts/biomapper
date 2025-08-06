"""Resource-aware execution engine that checks dependencies before execution."""

import logging
from typing import Any, Dict, Type

from sqlalchemy.ext.asyncio import AsyncSession

from .execution_engine import EnhancedExecutionEngine
from .resource_manager import ResourceManager, ResourceStatus, ResourceUnavailableError
from ..models.job import Job
from ..models.strategy_execution import JobStatus
from biomapper.core.models import StrategyExecutionContext
from biomapper.core.strategy_actions.base import BaseStrategyAction

logger = logging.getLogger(__name__)


class ResourceAwareExecutionEngine(EnhancedExecutionEngine):
    """
    Extended execution engine that ensures resources are available before execution.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        action_registry: Dict[str, Type[BaseStrategyAction]],
        resource_manager: ResourceManager
    ):
        super().__init__(db, action_registry)
        self.resource_manager = resource_manager
    
    async def execute_strategy(
        self,
        job: Job,
        strategy: Dict[str, Any],
        context: StrategyExecutionContext,
        checkpoint_manager,
        progress_tracker
    ) -> Dict[str, Any]:
        """
        Execute strategy with resource checking.
        
        This method first ensures all required resources are available
        before delegating to the parent's execute_strategy method.
        """
        try:
            # Log initial status
            await progress_tracker.log_message(
                "INFO", 
                "Checking resource requirements for strategy"
            )
            
            # Check resource requirements
            required_resources = await self.resource_manager.get_resource_requirements(strategy)
            
            if required_resources:
                await progress_tracker.log_message(
                    "INFO",
                    f"Strategy requires resources: {', '.join(required_resources)}"
                )
                
                # Get current resource status
                resources = await self.resource_manager.get_resource_status()
                
                # Check each required resource
                unavailable_resources = []
                degraded_resources = []
                
                for resource_name in required_resources:
                    if resource_name not in resources:
                        unavailable_resources.append(resource_name)
                        continue
                        
                    resource = resources[resource_name]
                    
                    if resource.status == ResourceStatus.UNAVAILABLE:
                        # Try to auto-start if configured
                        config = self.resource_manager.config.get(resource_name)
                        if config and config.auto_start:
                            await progress_tracker.log_message(
                                "INFO",
                                f"Attempting to auto-start resource: {resource_name}"
                            )
                            success = await self.resource_manager.start_resource(resource_name)
                            if not success:
                                unavailable_resources.append(resource_name)
                        else:
                            unavailable_resources.append(resource_name)
                    elif resource.status == ResourceStatus.DEGRADED:
                        degraded_resources.append(resource_name)
                    elif resource.status == ResourceStatus.UNKNOWN:
                        # Try to check the resource
                        status = await self.resource_manager.check_resource(resource_name)
                        if status != ResourceStatus.HEALTHY:
                            unavailable_resources.append(resource_name)
                
                # Handle unavailable resources
                if unavailable_resources:
                    error_msg = (
                        f"Required resources are not available: {', '.join(unavailable_resources)}. "
                        f"Start them manually or enable auto-start in configuration."
                    )
                    
                    # Update job status
                    job.status = JobStatus.FAILED
                    job.error_message = error_msg
                    await self.db.commit()
                    
                    await progress_tracker.log_message(
                        "ERROR",
                        error_msg
                    )
                    
                    raise ResourceUnavailableError(error_msg)
                
                # Warn about degraded resources
                if degraded_resources:
                    warning_msg = (
                        f"Some resources are degraded: {', '.join(degraded_resources)}. "
                        f"Execution may be slower or less reliable."
                    )
                    await progress_tracker.log_message(
                        "WARNING",
                        warning_msg
                    )
                
                # All resources are available
                await progress_tracker.log_message(
                    "INFO",
                    "All required resources are available"
                )
            else:
                await progress_tracker.log_message(
                    "INFO",
                    "Strategy has no external resource requirements"
                )
            
            # Proceed with execution
            return await super().execute_strategy(
                job, strategy, context, checkpoint_manager, progress_tracker
            )
            
        except ResourceUnavailableError:
            # Re-raise resource errors
            raise
        except Exception as e:
            # Log and re-raise other errors
            logger.error(f"Error in resource-aware execution: {str(e)}")
            raise
    
    async def pre_execution_checks(
        self, 
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform pre-execution checks for a strategy.
        
        Returns a dictionary with:
        - ready: bool - Whether the strategy can be executed
        - required_resources: List[str] - Required resources
        - resource_status: Dict[str, str] - Status of each resource
        - missing_resources: List[str] - Resources that are unavailable
        - warnings: List[str] - Any warnings
        """
        result = {
            "ready": True,
            "required_resources": [],
            "resource_status": {},
            "missing_resources": [],
            "warnings": []
        }
        
        try:
            # Get required resources
            required = await self.resource_manager.get_resource_requirements(strategy)
            result["required_resources"] = required
            
            if not required:
                return result
            
            # Check each resource
            resources = await self.resource_manager.get_resource_status()
            
            for resource_name in required:
                if resource_name not in resources:
                    result["missing_resources"].append(resource_name)
                    result["resource_status"][resource_name] = "not_configured"
                    result["ready"] = False
                    continue
                
                resource = resources[resource_name]
                result["resource_status"][resource_name] = resource.status.value
                
                if resource.status == ResourceStatus.UNAVAILABLE:
                    result["missing_resources"].append(resource_name)
                    result["ready"] = False
                    
                    # Check if auto-start is available
                    config = self.resource_manager.config.get(resource_name)
                    if config and config.auto_start:
                        result["warnings"].append(
                            f"Resource '{resource_name}' will be auto-started when needed"
                        )
                elif resource.status == ResourceStatus.DEGRADED:
                    result["warnings"].append(
                        f"Resource '{resource_name}' is degraded - execution may be affected"
                    )
                elif resource.status == ResourceStatus.UNKNOWN:
                    result["warnings"].append(
                        f"Resource '{resource_name}' status is unknown - will be checked at execution"
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in pre-execution checks: {str(e)}")
            result["ready"] = False
            result["warnings"].append(f"Error checking resources: {str(e)}")
            return result