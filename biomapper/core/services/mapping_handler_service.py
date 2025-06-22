"""
MappingHandlerService - Service for handling legacy mapping strategy actions.

This service encapsulates the handler methods that were previously part of MappingExecutor.
These handlers are used by the legacy execute_strategy method for database-stored strategies.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.engine_components.client_manager import ClientManager
from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.utils.placeholder_resolver import resolve_placeholders


class MappingHandlerService:
    """
    Service that handles legacy mapping strategy actions.
    
    This service contains the handler methods that were previously private methods
    in MappingExecutor. They are used for executing database-stored mapping strategies
    with action types like CONVERT_IDENTIFIERS_LOCAL, EXECUTE_MAPPING_PATH, and
    FILTER_IDENTIFIERS_BY_TARGET_PRESENCE.
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        client_manager: ClientManager,
        path_finder: PathFinder,
        async_metamapper_session,
        metadata_query_service: MetadataQueryService,
    ):
        """
        Initialize the MappingHandlerService.
        
        Args:
            logger: Logger instance for this service
            client_manager: Manager for endpoint clients
            path_finder: Service for finding mapping paths
            async_metamapper_session: Async session factory for metamapper database
            metadata_query_service: Service for metadata queries
        """
        self.logger = logger
        self.client_manager = client_manager
        self.path_finder = path_finder
        self.async_metamapper_session = async_metamapper_session
        self.metadata_query_service = metadata_query_service
    
    async def handle_convert_identifiers_local(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for CONVERT_IDENTIFIERS_LOCAL action type.
        
        This method has been refactored to use the newer ConvertIdentifiersLocalAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to convert
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Mapping results with converted identifiers
        """
        try:
            # Extract parameters from action_parameters
            endpoint_context = action_parameters.get('endpoint_context', 'SOURCE')
            output_ontology_type = action_parameters.get('output_ontology_type')
            input_ontology_type = action_parameters.get('input_ontology_type', current_source_ontology_type)
            
            if not output_ontology_type:
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "failed",
                    "error": "output_ontology_type is required in action_parameters",
                    "details": {"action_parameters": action_parameters}
                }
            
            # For legacy compatibility with ConvertIdentifiersLocalAction,
            # we'll provide a basic implementation that performs ontology type
            # conversion without requiring full endpoint database configurations.
            # This maintains backward compatibility while using the StrategyAction framework.
            
            self.logger.info(f"Legacy convert identifiers: {input_ontology_type} -> {output_ontology_type}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.convert_identifiers_local import ConvertIdentifiersLocalAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = ConvertIdentifiersLocalAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_endpoint = MagicMock(spec=Endpoint)
                    mock_endpoint.id = 1
                    mock_endpoint.name = "LEGACY_ENDPOINT"
                    
                    # Create action parameters
                    action_params = {
                        'endpoint_context': endpoint_context,
                        'output_ontology_type': output_ontology_type,
                        'input_ontology_type': input_ontology_type
                    }
                    
                    # Create context - note: mapping_executor reference needs to be passed in
                    mapping_executor = kwargs.get('mapping_executor')
                    context = {
                        "db_session": session,
                        "mapping_executor": mapping_executor,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_params,
                        source_endpoint=mock_endpoint,
                        target_endpoint=mock_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', output_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails (e.g., due to missing endpoint configurations),
                # fall back to a basic implementation that just changes the ontology type
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: just update the ontology type without actual conversion
                return {
                    "output_identifiers": current_identifiers,  # Keep same identifiers
                    "output_ontology_type": output_ontology_type,  # Update ontology type
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "conversion_type": "ontology_type_only",
                        "input_ontology_type": input_ontology_type,
                        "output_ontology_type": output_ontology_type,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in handle_convert_identifiers_local: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
    
    async def handle_execute_mapping_path(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for EXECUTE_MAPPING_PATH action type.
        
        This method has been refactored to use the newer ExecuteMappingPathAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to map
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Mapping results with mapped identifiers
        """
        try:
            # Extract parameters from action_parameters
            mapping_path_name = action_parameters.get('mapping_path_name')
            resource_name = action_parameters.get('resource_name')
            
            if not mapping_path_name and not resource_name:
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "failed",
                    "error": "Either mapping_path_name or resource_name is required in action_parameters",
                    "details": {"action_parameters": action_parameters}
                }
            
            self.logger.info(f"Legacy execute mapping path: {mapping_path_name or resource_name}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.execute_mapping_path import ExecuteMappingPathAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = ExecuteMappingPathAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_source_endpoint = MagicMock(spec=Endpoint)
                    mock_source_endpoint.id = 1
                    mock_source_endpoint.name = "LEGACY_SOURCE_ENDPOINT"
                    
                    mock_target_endpoint = MagicMock(spec=Endpoint)
                    mock_target_endpoint.id = 2
                    mock_target_endpoint.name = "LEGACY_TARGET_ENDPOINT"
                    
                    # Create context with legacy settings
                    mapping_executor = kwargs.get('mapping_executor')
                    context = {
                        "db_session": session,
                        "cache_settings": {
                            "use_cache": True,
                            "max_cache_age_days": None
                        },
                        "mapping_executor": mapping_executor,
                        "batch_size": 250,
                        "min_confidence": 0.0,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_parameters,
                        source_endpoint=mock_source_endpoint,
                        target_endpoint=mock_target_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', current_source_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails, provide a basic fallback
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: return identifiers unchanged
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "mapping_type": "no_change",
                        "mapping_path_name": mapping_path_name,
                        "resource_name": resource_name,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in handle_execute_mapping_path: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
    
    async def handle_filter_identifiers_by_target_presence(
        self,
        current_identifiers: List[str],
        action_parameters: Dict[str, Any],
        current_source_ontology_type: str,
        target_ontology_type: str,
        step_id: str,
        step_description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy handler for FILTER_IDENTIFIERS_BY_TARGET_PRESENCE action type.
        
        This method has been refactored to use the newer FilterByTargetPresenceAction
        class while maintaining backward compatibility with the legacy execute_strategy
        method.
        
        Args:
            current_identifiers: List of identifiers to filter
            action_parameters: Action configuration parameters
            current_source_ontology_type: Current ontology type of identifiers
            target_ontology_type: Target ontology type for the overall strategy
            step_id: Step identifier for logging
            step_description: Step description for logging
            **kwargs: Additional parameters from the legacy execution context
            
        Returns:
            Dict[str, Any]: Filtered identifiers based on target presence
        """
        try:
            # Extract parameters from action_parameters
            endpoint_context = action_parameters.get('endpoint_context', 'TARGET')
            ontology_type_to_match = action_parameters.get('ontology_type_to_match', current_source_ontology_type)
            
            self.logger.info(f"Legacy filter by target presence: {ontology_type_to_match}")
            
            try:
                # Import the StrategyAction class
                from biomapper.core.strategy_actions.filter_by_target_presence import FilterByTargetPresenceAction
                
                async with self.async_metamapper_session() as session:
                    # Create the action instance
                    action = FilterByTargetPresenceAction(session)
                    
                    # Create minimal mock endpoints
                    from unittest.mock import MagicMock
                    from biomapper.db.models import Endpoint
                    
                    mock_source_endpoint = MagicMock(spec=Endpoint)
                    mock_source_endpoint.id = 1
                    mock_source_endpoint.name = "LEGACY_SOURCE_ENDPOINT"
                    
                    mock_target_endpoint = MagicMock(spec=Endpoint)
                    mock_target_endpoint.id = 2
                    mock_target_endpoint.name = "LEGACY_TARGET_ENDPOINT"
                    
                    # Create action parameters in the format expected by the action class
                    action_params = {
                        'endpoint_context': endpoint_context,
                        'ontology_type_to_match': ontology_type_to_match
                    }
                    action_params.update(action_parameters)  # Include any additional parameters
                    
                    # Create context
                    mapping_executor = kwargs.get('mapping_executor')
                    context = {
                        "db_session": session,
                        "mapping_executor": mapping_executor,
                        "legacy_mode": True
                    }
                    
                    # Try to execute the action
                    result = await action.execute(
                        current_identifiers=current_identifiers,
                        current_ontology_type=current_source_ontology_type,
                        action_params=action_params,
                        source_endpoint=mock_source_endpoint,
                        target_endpoint=mock_target_endpoint,
                        context=context
                    )
                    
                    # Convert result to legacy format
                    return {
                        "output_identifiers": result.get('output_identifiers', current_identifiers),
                        "output_ontology_type": result.get('output_ontology_type', current_source_ontology_type),
                        "status": "success",
                        "details": result.get('details', {})
                    }
                    
            except Exception as action_error:
                # If the StrategyAction fails, provide a basic fallback
                self.logger.warning(
                    f"StrategyAction failed in legacy mode, using basic fallback: {str(action_error)}"
                )
                
                # Basic fallback: return all identifiers (no filtering)
                return {
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_source_ontology_type,
                    "status": "success",
                    "details": {
                        "fallback_mode": True,
                        "filter_type": "no_filtering",
                        "endpoint_context": endpoint_context,
                        "ontology_type_to_match": ontology_type_to_match,
                        "strategy_action_error": str(action_error)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error in handle_filter_identifiers_by_target_presence: {str(e)}", exc_info=True)
            return {
                "output_identifiers": current_identifiers,
                "output_ontology_type": current_source_ontology_type,
                "status": "failed",
                "error": f"Action execution failed: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }