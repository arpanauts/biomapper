"""
Unit tests for MetadataQueryService.

Tests cover retrieval of metadata entities from the metamapper database,
including endpoints, properties, ontology preferences, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.exceptions import DatabaseQueryError, BiomapperError, ErrorCode
from biomapper.db.models import Endpoint, EndpointPropertyConfig, OntologyPreference


class TestMetadataQueryService:
    """Test cases for MetadataQueryService."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock SessionManager instance."""
        return MagicMock(spec=SessionManager)

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession instance."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_session_manager):
        """MetadataQueryService instance with mocked dependencies."""
        return MetadataQueryService(mock_session_manager)

    @pytest.fixture
    def mock_endpoint(self):
        """Mock Endpoint instance."""
        endpoint = MagicMock(spec=Endpoint)
        endpoint.id = 1
        endpoint.name = "test_endpoint"
        endpoint.description = "Test endpoint"
        endpoint.type = "database"
        return endpoint

    @pytest.fixture
    def mock_property_configs(self):
        """Mock EndpointPropertyConfig instances."""
        config1 = MagicMock(spec=EndpointPropertyConfig)
        config1.id = 1
        config1.endpoint_id = 1
        config1.property_name = "id"
        config1.ontology_type = "UniProtKB_AC"
        config1.is_primary_identifier = True
        
        config2 = MagicMock(spec=EndpointPropertyConfig)
        config2.id = 2
        config2.endpoint_id = 1
        config2.property_name = "name"
        config2.ontology_type = "Gene_Name"
        config2.is_primary_identifier = False
        
        return [config1, config2]

    @pytest.fixture
    def mock_ontology_preferences(self):
        """Mock OntologyPreference instances."""
        pref1 = MagicMock(spec=OntologyPreference)
        pref1.id = 1
        pref1.endpoint_id = 1
        pref1.ontology_name = "UniProtKB"
        pref1.priority = 1
        
        pref2 = MagicMock(spec=OntologyPreference)
        pref2.id = 2
        pref2.endpoint_id = 1
        pref2.ontology_name = "HGNC"
        pref2.priority = 2
        
        return [pref1, pref2]

    def test_init(self, mock_session_manager):
        """Test MetadataQueryService initialization."""
        service = MetadataQueryService(mock_session_manager)
        
        assert service.session_manager is mock_session_manager
        assert service.logger is not None

    @pytest.mark.asyncio
    async def test_get_endpoint_properties_success(self, service, mock_session, mock_property_configs):
        """Test successful retrieval of endpoint properties."""
        # Setup mock
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_property_configs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_endpoint_properties(mock_session, "test_endpoint")
        
        # Assert
        assert result == mock_property_configs
        mock_session.execute.assert_called_once()
        
        # Verify the query structure
        call_args = mock_session.execute.call_args[0][0]
        assert hasattr(call_args, 'compile')  # SQLAlchemy statement

    @pytest.mark.asyncio
    async def test_get_endpoint_properties_empty_result(self, service, mock_session):
        """Test retrieval when no endpoint properties are found."""
        # Setup mock
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_endpoint_properties(mock_session, "nonexistent_endpoint")
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ontology_preferences_success(self, service, mock_session, mock_ontology_preferences):
        """Test successful retrieval of ontology preferences."""
        # Setup mock
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_ontology_preferences
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_ontology_preferences(mock_session, "test_endpoint")
        
        # Assert
        assert result == mock_ontology_preferences
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ontology_preferences_empty_result(self, service, mock_session):
        """Test retrieval when no ontology preferences are found."""
        # Setup mock
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_ontology_preferences(mock_session, "nonexistent_endpoint")
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_endpoint_success(self, service, mock_session, mock_endpoint):
        """Test successful retrieval of an endpoint."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_endpoint
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_endpoint(mock_session, "test_endpoint")
        
        # Assert
        assert result == mock_endpoint
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_endpoint_not_found(self, service, mock_session):
        """Test retrieval when endpoint is not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_endpoint(mock_session, "nonexistent_endpoint")
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_endpoint_database_error(self, service, mock_session):
        """Test get_endpoint with database error."""
        # Setup mock to raise SQLAlchemyError
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("Database connection failed"))
        
        # Execute and assert exception
        with pytest.raises(DatabaseQueryError) as exc_info:
            await service.get_endpoint(mock_session, "test_endpoint")
        
        assert "Database error fetching endpoint" in str(exc_info.value)
        assert exc_info.value.details["endpoint"] == "test_endpoint"

    @pytest.mark.asyncio
    async def test_get_ontology_type_success(self, service, mock_session):
        """Test successful retrieval of ontology type."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "UniProtKB_AC"
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_ontology_type(mock_session, "test_endpoint", "id")
        
        # Assert
        assert result == "UniProtKB_AC"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ontology_type_not_found(self, service, mock_session):
        """Test retrieval when ontology type is not found."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute
        result = await service.get_ontology_type(mock_session, "nonexistent_endpoint", "nonexistent_property")
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ontology_type_database_error(self, service, mock_session):
        """Test get_ontology_type with database error."""
        # Setup mock to raise SQLAlchemyError
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("Database connection failed"))
        
        # Execute and assert exception
        with pytest.raises(DatabaseQueryError) as exc_info:
            await service.get_ontology_type(mock_session, "test_endpoint", "test_property")
        
        assert "Database error fetching ontology type" in str(exc_info.value)
        assert exc_info.value.details["endpoint"] == "test_endpoint"
        assert exc_info.value.details["property"] == "test_property"

    @pytest.mark.asyncio
    async def test_get_ontology_type_unexpected_error(self, service, mock_session):
        """Test get_ontology_type with unexpected error."""
        # Setup mock to raise generic exception
        mock_session.execute = AsyncMock(side_effect=ValueError("Unexpected error"))
        
        # Execute and assert exception
        with pytest.raises(BiomapperError) as exc_info:
            await service.get_ontology_type(mock_session, "test_endpoint", "test_property")
        
        assert "An unexpected error occurred while retrieving ontology type" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.DATABASE_QUERY_ERROR
        assert exc_info.value.details["endpoint"] == "test_endpoint"
        assert exc_info.value.details["property"] == "test_property"

    @pytest.mark.asyncio
    async def test_get_ontology_type_multiple_valid_combinations(self, service, mock_session):
        """Test get_ontology_type with different valid/invalid endpoint/property combinations."""
        test_cases = [
            ("valid_endpoint", "valid_property", "UniProtKB_AC"),
            ("valid_endpoint", "invalid_property", None),
            ("invalid_endpoint", "valid_property", None),
            ("invalid_endpoint", "invalid_property", None),
        ]
        
        for endpoint_name, property_name, expected_result in test_cases:
            # Setup mock
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = expected_result
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            # Execute
            result = await service.get_ontology_type(mock_session, endpoint_name, property_name)
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_sql_query_construction(self, service, mock_session):
        """Test that SQL queries are constructed correctly."""
        # Test get_endpoint query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        await service.get_endpoint(mock_session, "test_endpoint")
        
        # Verify execute was called with a select statement
        call_args = mock_session.execute.call_args[0][0]
        assert hasattr(call_args, 'compile')  # SQLAlchemy statement
        
        # Test get_ontology_type query
        mock_result.scalar_one_or_none.return_value = "test_type"
        await service.get_ontology_type(mock_session, "test_endpoint", "test_property")
        
        # Verify execute was called again
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio 
    async def test_logging_behavior(self, service, mock_session, mock_endpoint):
        """Test that appropriate logging occurs."""
        with patch.object(service.logger, 'debug') as mock_debug, \
             patch.object(service.logger, 'warning') as mock_warning:
            
            # Test successful endpoint retrieval (should log debug)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_endpoint
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            await service.get_endpoint(mock_session, "test_endpoint")
            mock_debug.assert_called()
            
            # Test endpoint not found (should log warning)
            mock_result.scalar_one_or_none.return_value = None
            await service.get_endpoint(mock_session, "nonexistent_endpoint")
            mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_session_manager_integration(self, service):
        """Test that service can work with SessionManager (integration-style test)."""
        # This test verifies the service can be initialized and would work
        # with a real SessionManager, though we still mock the session itself
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Verify the service has the session_manager attribute
        assert hasattr(service, 'session_manager')
        assert service.session_manager is not None
        
        # Verify methods can be called (would normally use session from session_manager)
        result = await service.get_endpoint(mock_session, "test")
        assert result is None