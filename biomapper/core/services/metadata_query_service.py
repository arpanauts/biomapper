"""
MetadataQueryService - Centralized service for querying metamapper database entities.

This service handles all read-only queries for metadata from the metamapper database,
including Endpoints, EndpointPropertyConfigs, OntologyPreferences, and other metadata tables.
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from ..engine_components.session_manager import SessionManager
from ..exceptions import DatabaseQueryError, BiomapperError, ErrorCode
from ...db.models import (
    Endpoint,
    EndpointPropertyConfig,
    OntologyPreference,
)


class MetadataQueryService:
    """Service for querying metamapper database entities."""
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize the MetadataQueryService.
        
        Args:
            session_manager: SessionManager instance for database sessions
        """
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
    
    async def get_endpoint_properties(self, session: AsyncSession, endpoint_name: str) -> List[EndpointPropertyConfig]:
        """
        Get all property configurations for an endpoint.
        
        Args:
            session: SQLAlchemy async session
            endpoint_name: Name of the endpoint
            
        Returns:
            List of EndpointPropertyConfig objects
        """
        stmt = select(EndpointPropertyConfig).join(
            Endpoint, EndpointPropertyConfig.endpoint_id == Endpoint.id
        ).where(Endpoint.name == endpoint_name)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_ontology_preferences(self, session: AsyncSession, endpoint_name: str) -> List[OntologyPreference]:
        """
        Get ontology preferences for an endpoint.
        
        Args:
            session: SQLAlchemy async session
            endpoint_name: Name of the endpoint
            
        Returns:
            List of OntologyPreference objects
        """
        stmt = select(OntologyPreference).join(
            Endpoint, 
            OntologyPreference.endpoint_id == Endpoint.id
        ).where(Endpoint.name == endpoint_name)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_endpoint(self, session: AsyncSession, endpoint_name: str) -> Optional[Endpoint]:
        """
        Retrieve an endpoint by name.
        
        Args:
            session: SQLAlchemy async session
            endpoint_name: Name of the endpoint to retrieve
            
        Returns:
            The Endpoint if found, None otherwise
            
        Raises:
            DatabaseQueryError: If database error occurs
        """
        try:
            stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
            result = await session.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if endpoint:
                self.logger.debug(f"Found endpoint: {endpoint.name} (ID: {endpoint.id})")
            else:
                self.logger.warning(f"Endpoint not found: {endpoint_name}")
                
            return endpoint
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving endpoint {endpoint_name}: {e}", exc_info=True)
            raise DatabaseQueryError(
                "Database error fetching endpoint",
                details={"endpoint": endpoint_name, "error": str(e)}
            ) from e
    
    async def get_ontology_type(self, session: AsyncSession, endpoint_name: str, property_name: str) -> Optional[str]:
        """
        Retrieve the primary ontology type for a given endpoint and property name.
        
        Args:
            session: SQLAlchemy async session
            endpoint_name: Name of the endpoint
            property_name: Name of the property
            
        Returns:
            The ontology type if found, None otherwise
            
        Raises:
            DatabaseQueryError: If database error occurs
            BiomapperError: If unexpected error occurs
        """
        self.logger.debug(f"Getting ontology type for {endpoint_name}.{property_name}")
        try:
            # Join EndpointPropertyConfig with Endpoint
            stmt = (
                select(EndpointPropertyConfig.ontology_type)
                .join(Endpoint, Endpoint.id == EndpointPropertyConfig.endpoint_id)
                .where(Endpoint.name == endpoint_name)
                .where(EndpointPropertyConfig.property_name == property_name)
                .limit(1)
            )
            result = await session.execute(stmt)
            ontology_type = result.scalar_one_or_none()
            
            if ontology_type:
                self.logger.debug(f"Found ontology type: {ontology_type}")
            else:
                self.logger.warning(f"Ontology type not found for {endpoint_name}.{property_name}")
            
            return ontology_type
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error retrieving ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True
            )
            raise DatabaseQueryError(
                "Database error fetching ontology type",
                details={"endpoint": endpoint_name, "property": property_name, "error": str(e)}
            ) from e
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving ontology type for {endpoint_name}.{property_name}: {e}",
                exc_info=True
            )
            raise BiomapperError(
                "An unexpected error occurred while retrieving ontology type",
                error_code=ErrorCode.DATABASE_QUERY_ERROR,
                details={"endpoint": endpoint_name, "property": property_name, "error": str(e)}
            ) from e