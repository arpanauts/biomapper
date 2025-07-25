"""
Dependency injection for FastAPI routes.
"""
from typing import Generator

from fastapi import HTTPException, status, Request

from app.core.session import Session, session_manager
from app.services.csv_service import CSVService
from app.services.mapper_service import MapperService


def get_session(session_id: str) -> Session:
    """Dependency for getting a valid session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found or expired",
        )
    return session


def get_csv_service() -> Generator[CSVService, None, None]:
    """Dependency for CSV service."""
    service = CSVService()
    try:
        yield service
    finally:
        # Any cleanup needed
        pass


def get_mapper_service(request: Request) -> MapperService:
    """Dependency for mapper service.
    
    Returns the singleton MapperService instance from the application state.
    
    Args:
        request: The FastAPI request object.
        
    Returns:
        MapperService: The singleton mapper service instance.
    """
    return request.app.state.mapper_service
