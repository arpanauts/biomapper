"""
Pytest fixtures for integration tests.

This file contains fixtures that setup test environments for integration tests,
including database mocks and configurations.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.db.models import (
    Endpoint, 
    EndpointPropertyConfig,
    MappingPath,
    MappingPathStep
)
from .test_fixtures import create_mock_mapping_executor


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    mock = AsyncMock(spec=AsyncSession)
    
    # Configure execute to return an empty result by default
    mock.execute.return_value = MagicMock()
    mock.execute.return_value.scalars.return_value.all.return_value = []
    mock.execute.return_value.scalars.return_value.first.return_value = None
    
    # Make commit and rollback no-ops
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    
    return mock


@pytest.fixture
def mock_mapping_executor():
    """Create a MappingExecutor with mocked database sessions."""
    return create_mock_mapping_executor()


@pytest.fixture
def mock_direct_path():
    """Create a mock direct mapping path."""
    path = MagicMock(spec=MappingPath)
    path.id = 1
    path.name = "UKBB_to_Arivale_Protein_via_UniProt"
    path.source_type = "UNIPROTKB_AC"
    path.target_type = "ARIVALE_PROTEIN_ID"
    path.priority = 1
    path.is_reverse = False  # Add is_reverse attribute
    
    # Mock steps
    step = MagicMock(spec=MappingPathStep)
    step.mapping_resource_id = 1
    step.step_order = 1
    
    path.steps = [step]
    
    return path


@pytest.fixture
def mock_historical_path():
    """Create a mock historical resolution path."""
    path = MagicMock(spec=MappingPath)
    path.id = 2
    path.name = "UKBB_to_Arivale_Protein_via_Historical_Resolution"
    path.source_type = "UNIPROTKB_AC"
    path.target_type = "ARIVALE_PROTEIN_ID"
    path.priority = 2
    path.is_reverse = False  # Add is_reverse attribute
    
    # Mock steps for historical resolution
    step1 = MagicMock(spec=MappingPathStep)
    step1.mapping_resource_id = 10  # UniProtHistoricalResolver
    step1.step_order = 1
    
    step2 = MagicMock(spec=MappingPathStep)
    step2.mapping_resource_id = 1  # Arivale lookup
    step2.step_order = 2
    
    path.steps = [step1, step2]
    
    return path


@pytest.fixture
def setup_mock_endpoints():
    """Configure mock endpoint-related query responses."""
    def configure(mock_session, source_endpoint_name, target_endpoint_name, source_property, target_property):
        # Mock endpoints
        source_endpoint = MagicMock(spec=Endpoint)
        source_endpoint.id = 1
        source_endpoint.name = source_endpoint_name
        # Add connection_details for CSV adapter
        source_endpoint.connection_details = {
            "file_path": f"tests/integration/data/mock_client_files/{source_endpoint_name.lower()}.tsv",
            "delimiter": "\t"
        }
        source_endpoint.file_path = source_endpoint.connection_details["file_path"]  # Direct attribute access
        
        target_endpoint = MagicMock(spec=Endpoint)
        target_endpoint.id = 2
        target_endpoint.name = target_endpoint_name
        # Add connection_details for CSV adapter
        target_endpoint.connection_details = {
            "file_path": f"tests/integration/data/mock_client_files/{target_endpoint_name.lower()}.tsv",
            "delimiter": "\t"
        }
        target_endpoint.file_path = target_endpoint.connection_details["file_path"]  # Direct attribute access
        
        # Mock endpoint properties
        source_property_config = MagicMock(spec=EndpointPropertyConfig)
        source_property_config.property_name = source_property
        source_property_config.ontology_type = source_property
        
        target_property_config = MagicMock(spec=EndpointPropertyConfig)
        target_property_config.property_name = target_property
        target_property_config.ontology_type = target_property
        
        # Configure the mock session to return our mocked objects
        async def execute_side_effect(stmt, **kwargs):
            result_mock = MagicMock()
            scalars_mock = MagicMock()
            
            # Handle endpoint queries
            stmt_str = str(stmt)
            if "endpoints" in stmt_str.lower():
                if source_endpoint_name in stmt_str:
                    scalars_mock.first.return_value = source_endpoint
                    scalars_mock.all.return_value = [source_endpoint]
                elif target_endpoint_name in stmt_str:
                    scalars_mock.first.return_value = target_endpoint
                    scalars_mock.all.return_value = [target_endpoint]
                else:
                    scalars_mock.first.return_value = None
                    scalars_mock.all.return_value = []
                    
            # Handle property config queries
            elif "endpoint_property_configs" in stmt_str.lower():
                # Handle queries for source property config
                if str(source_endpoint.id) in stmt_str and source_property in stmt_str:
                    scalars_mock.first.return_value = source_property_config
                    scalars_mock.all.return_value = [source_property_config]
                # Handle queries for target property config
                elif str(target_endpoint.id) in stmt_str and target_property in stmt_str:
                    scalars_mock.first.return_value = target_property_config
                    scalars_mock.all.return_value = [target_property_config]
                else:
                    scalars_mock.first.return_value = None
                    scalars_mock.all.return_value = []
            else:
                scalars_mock.first.return_value = None
                scalars_mock.all.return_value = []
            
            result_mock.scalars.return_value = scalars_mock
            return result_mock
            
        mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    
    return configure


@pytest.fixture
def setup_mock_paths(mock_direct_path, mock_historical_path):
    """Configure mock path-related query responses."""
    def configure(mock_session, source_ontology, target_ontology):
        # Configure the mock session to return our mocked path objects
        async def execute_side_effect(stmt, **kwargs):
            result_mock = MagicMock()
            
            # Handle different types of queries
            stmt_str = str(stmt)
            
            # Handle the complex query from _find_direct_paths
            if "mapping_paths" in stmt_str and "mapping_path_steps" in stmt_str:
                # This is the complex join query from _find_direct_paths
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [mock_direct_path, mock_historical_path]
                result_mock.scalars.return_value = scalars_mock
                return result_mock
            
            # Handle simple path queries
            elif "MappingPath" in stmt_str:
                scalars_mock = MagicMock()
                if source_ontology in stmt_str and target_ontology in stmt_str:
                    # Return both paths ordered by priority
                    scalars_mock.all.return_value = [mock_direct_path, mock_historical_path]
                    # First path (direct) as default for single result
                    scalars_mock.first.return_value = mock_direct_path
                else:
                    scalars_mock.all.return_value = []
                    scalars_mock.first.return_value = None
                result_mock.scalars.return_value = scalars_mock
                return result_mock
            
            # Default return for other queries
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            scalars_mock.first.return_value = None
            result_mock.scalars.return_value = scalars_mock
            return result_mock
            
        # Keep existing execute mock for backward compatibility
        if hasattr(mock_session.execute, 'side_effect'):
            original_side_effect = mock_session.execute.side_effect
            
            async def combined_side_effect(stmt, **kwargs):
                # Try new handler first
                result = await execute_side_effect(stmt, **kwargs)
                if result.scalars.return_value.all.return_value:
                    return result
                # Fall back to original if exists
                if original_side_effect:
                    # Check if original is async
                    if asyncio.iscoroutinefunction(original_side_effect):
                        return await original_side_effect(stmt, **kwargs)
                    else:
                        return original_side_effect(stmt, **kwargs)
                return result
                
            mock_session.execute.side_effect = combined_side_effect
        else:
            mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    
    return configure
