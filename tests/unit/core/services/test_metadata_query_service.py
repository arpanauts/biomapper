"""Tests for the MetadataQueryService."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from biomapper.core.services.metadata_query_service import MetadataQueryService
from biomapper.core.exceptions import BiomapperError, ErrorCode


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = MagicMock()
    manager.get_meta_session = MagicMock()
    manager.get_meta_session.return_value.__aenter__.return_value = mock_session
    return manager


@pytest.fixture
def metadata_query_service(mock_session_manager):
    """Create a MetadataQueryService instance with mocked dependencies."""
    return MetadataQueryService(session_manager=mock_session_manager)


@pytest.mark.asyncio
async def test_get_ontology_type_success(metadata_query_service, mock_session):
    """Test successful retrieval of ontology type."""
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar.return_value = "GENE_NAME"
    mock_session.execute.return_value = mock_result
    
    # Call the method
    result = await metadata_query_service.get_ontology_type(
        mock_session,
        "test_endpoint",
        "test_property"
    )
    
    # Assertions
    assert result == "GENE_NAME"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_ontology_type_not_found(metadata_query_service, mock_session):
    """Test get_ontology_type when no result is found."""
    # Mock the query result to return None
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Call the method
    result = await metadata_query_service.get_ontology_type(
        mock_session,
        "test_endpoint",
        "test_property"
    )
    
    # Assertions
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_ontology_type_sql_error(metadata_query_service, mock_session):
    """Test that get_ontology_type properly handles SQLAlchemyError."""
    # Create a mock session that raises SQLAlchemyError when execute is called
    mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")
    
    # Call get_ontology_type and verify it raises DatabaseQueryError with the correct code
    with pytest.raises(BiomapperError) as exc_info:
        await metadata_query_service.get_ontology_type(
            mock_session, "test_endpoint", "test_property"
        )
    
    # Verify the error code and details
    assert exc_info.value.error_code == ErrorCode.DATABASE_QUERY_ERROR
    assert "Database error fetching ontology type" in str(exc_info.value)
    
    # Verify the mock was called
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_endpoint_success(metadata_query_service, mock_session):
    """Test successful retrieval of endpoint."""
    # Create a mock endpoint
    mock_endpoint = MagicMock()
    mock_endpoint.id = 1
    mock_endpoint.name = "test_endpoint"
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_endpoint
    mock_session.execute.return_value = mock_result
    
    # Call the method
    result = await metadata_query_service.get_endpoint(mock_session, "test_endpoint")
    
    # Assertions
    assert result == mock_endpoint
    assert result.name == "test_endpoint"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_endpoint_not_found(metadata_query_service, mock_session):
    """Test get_endpoint when endpoint is not found."""
    # Mock the query result to return None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Call the method and verify it raises an error
    with pytest.raises(BiomapperError) as exc_info:
        await metadata_query_service.get_endpoint(mock_session, "nonexistent_endpoint")
    
    # Verify the error details
    assert "Endpoint 'nonexistent_endpoint' not found" in str(exc_info.value)
    assert exc_info.value.error_code == ErrorCode.DATABASE_QUERY_ERROR


@pytest.mark.asyncio
async def test_get_endpoint_properties_success(metadata_query_service, mock_session):
    """Test successful retrieval of endpoint properties."""
    # Create mock properties
    mock_prop1 = MagicMock()
    mock_prop1.property_name = "prop1"
    mock_prop1.ontology_term = "ONTO1"
    
    mock_prop2 = MagicMock()
    mock_prop2.property_name = "prop2"
    mock_prop2.ontology_term = "ONTO2"
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_prop1, mock_prop2]
    mock_session.execute.return_value = mock_result
    
    # Call the method
    result = await metadata_query_service.get_endpoint_properties(mock_session, 1)
    
    # Assertions
    assert len(result) == 2
    assert result[0].property_name == "prop1"
    assert result[1].property_name == "prop2"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_ontology_preferences_success(metadata_query_service, mock_session):
    """Test successful retrieval of ontology preferences."""
    # Create mock preferences
    mock_pref1 = MagicMock()
    mock_pref1.ontology_term = "ONTO1"
    mock_pref1.preference_order = 1
    
    mock_pref2 = MagicMock()
    mock_pref2.ontology_term = "ONTO2"
    mock_pref2.preference_order = 2
    
    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_pref1, mock_pref2]
    mock_session.execute.return_value = mock_result
    
    # Call the method
    result = await metadata_query_service.get_ontology_preferences(
        mock_session,
        endpoint_id=1,
        property_name="test_property"
    )
    
    # Assertions
    assert len(result) == 2
    assert result[0].preference_order == 1
    assert result[1].preference_order == 2
    mock_session.execute.assert_called_once()