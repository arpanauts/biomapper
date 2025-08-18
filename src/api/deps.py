"""
Dependency injection for FastAPI routes.
"""
from fastapi import Request

from src.api.services.mapper_service import MapperService


def get_mapper_service(request: Request) -> MapperService:
    """Dependency for mapper service.

    Returns the singleton MapperService instance from the application state.

    Args:
        request: The FastAPI request object.

    Returns:
        MapperService: The singleton mapper service instance.
    """
    return request.app.state.mapper_service