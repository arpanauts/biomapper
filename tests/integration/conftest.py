"""
Pytest fixtures for integration tests.

This file contains fixtures that setup test environments for integration tests,
including database mocks and configurations.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.db.models import (
    Endpoint, 
    EndpointPropertyConfig,
    MappingPath,
    MappingResource,
    MappingPathStep,
    OntologyPreference
)
from biomapper.db.cache_models import (
    EntityMapping,
    MappingSession,
    PathExecutionLog
)


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
    executor = MappingExecutor()
    
    # Mock session creation methods
    executor.async_metamapper_session = AsyncMock()
    executor.async_cache_session = AsyncMock()
    
    # Mock session context managers to return mock sessions
    mock_meta_session = AsyncMock(spec=AsyncSession)
    mock_cache_session = AsyncMock(spec=AsyncSession)
    
    executor.async_metamapper_session.return_value.__aenter__.return_value = mock_meta_session
    executor.async_cache_session.return_value.__aenter__.return_value = mock_cache_session
    
    # Mock frequently used methods
    executor._create_mapping_session_log = AsyncMock(return_value=1)  # Return a fake session ID
    executor._update_mapping_session_log = AsyncMock()
    executor._check_cache = AsyncMock(return_value={})  # Return empty cache results by default
    executor._cache_results = AsyncMock()
    
    # Return the mocked executor
    return executor, mock_meta_session, mock_cache_session


@pytest.fixture
def mock_direct_path():
    """Create a mock direct mapping path."""
    path = MagicMock(spec=MappingPath)
    path.id = 1
    path.name = "UKBB_to_Arivale_Protein_via_UniProt"
    path.source_type = "UNIPROTKB_AC"
    path.target_type = "ARIVALE_PROTEIN_ID"
    path.priority = 1
    
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
        
        target_endpoint = MagicMock(spec=Endpoint)
        target_endpoint.id = 2
        target_endpoint.name = target_endpoint_name
        
        # Mock endpoint properties
        source_property_config = MagicMock(spec=EndpointPropertyConfig)
        source_property_config.property_name = source_property
        source_property_config.ontology_type = source_property
        
        target_property_config = MagicMock(spec=EndpointPropertyConfig)
        target_property_config.property_name = target_property
        target_property_config.ontology_type = target_property
        
        # Configure the mock session to return our mocked objects
        def execute_side_effect(stmt, **kwargs):
            result_mock = MagicMock()
            scalars_mock = MagicMock()
            
            # Handle endpoint queries
            if isinstance(stmt, select) and "Endpoint" in str(stmt):
                if source_endpoint_name in str(stmt):
                    scalars_mock.return_value.first.return_value = source_endpoint
                    scalars_mock.return_value.all.return_value = [source_endpoint]
                elif target_endpoint_name in str(stmt):
                    scalars_mock.return_value.first.return_value = target_endpoint
                    scalars_mock.return_value.all.return_value = [target_endpoint]
                    
            # Handle property config queries
            elif isinstance(stmt, select) and "EndpointPropertyConfig" in str(stmt):
                if source_endpoint_name in str(stmt) and source_property in str(stmt):
                    scalars_mock.return_value.first.return_value = source_property_config
                    scalars_mock.return_value.all.return_value = [source_property_config]
                elif target_endpoint_name in str(stmt) and target_property in str(stmt):
                    scalars_mock.return_value.first.return_value = target_property_config
                    scalars_mock.return_value.all.return_value = [target_property_config]
            
            result_mock.scalars.return_value = scalars_mock
            return AsyncMock(return_value=result_mock)
            
        mock_meta_session.execute.side_effect = execute_side_effect
    
    return configure


@pytest.fixture
def setup_mock_paths(mock_direct_path, mock_historical_path):
    """Configure mock path-related query responses."""
    def configure(mock_session, source_ontology, target_ontology):
        # Configure the mock session to return our mocked path objects
        def execute_side_effect(stmt, **kwargs):
            result_mock = MagicMock()
            scalars_mock = MagicMock()
            
            # Handle path queries
            if isinstance(stmt, select) and "MappingPath" in str(stmt):
                if source_ontology in str(stmt) and target_ontology in str(stmt):
                    # Return both paths ordered by priority
                    scalars_mock.return_value.all.return_value = [mock_direct_path, mock_historical_path]
                    # First path (direct) as default for single result
                    scalars_mock.return_value.first.return_value = mock_direct_path
                
            result_mock.scalars.return_value = scalars_mock
            return AsyncMock(return_value=result_mock)
            
        mock_meta_session.execute.side_effect = execute_side_effect
    
    return configure
