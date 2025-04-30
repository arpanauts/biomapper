"""
Health check endpoints for API monitoring.
"""
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Dict with API status
    """
    return {"status": "healthy", "version": "0.1.0"}
