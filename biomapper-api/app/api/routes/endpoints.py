"""
Endpoints API routes.
"""
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_mapper_service
from app.services.mapper_service import MapperService


class EndpointResponse(BaseModel):
    """Response model for endpoint information."""

    name: str
    description: str
    type: str

    class Config:
        orm_mode = True  # Use this to map SQLAlchemy models to Pydantic models


router = APIRouter()


@router.get("/", response_model=List[EndpointResponse])
async def list_endpoints(mapper_service: MapperService = Depends(get_mapper_service)):
    """Retrieve a list of all available data endpoints."""
    return await mapper_service.get_endpoints()
