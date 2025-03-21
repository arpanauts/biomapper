"""
API routes for file operations.
"""
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import get_csv_service, get_session
from app.core.session import Session
from app.models.file import FileUploadResponse, ColumnsResponse, CSVPreviewResponse
from app.services.csv_service import CSVService

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    csv_service: CSVService = Depends(get_csv_service),
) -> FileUploadResponse:
    """
    Upload a CSV file for mapping.
    
    Args:
        file: CSV file to upload
        csv_service: CSV service dependency
        
    Returns:
        Upload response with session ID
    """
    session, file_path = await csv_service.save_file(file)
    
    return FileUploadResponse(
        session_id=session.session_id,
        filename=file.filename,
        created_at=session.created_at,
        file_size=session.metadata.get("file_size", 0),
        content_type=session.metadata.get("content_type", ""),
    )


@router.get("/{session_id}/columns", response_model=ColumnsResponse)
async def get_columns(
    session: Session = Depends(get_session),
    csv_service: CSVService = Depends(get_csv_service),
    with_types: bool = Query(False, description="Include column type information"),
) -> ColumnsResponse:
    """
    Get column names from an uploaded CSV file.
    
    Args:
        session: Session dependency
        csv_service: CSV service dependency
        with_types: Whether to include column type information
        
    Returns:
        Column names and optional type information
    """
    columns = await csv_service.get_columns(session)
    
    if with_types:
        column_types = await csv_service.get_column_types(session)
        return ColumnsResponse(columns=columns, column_types=column_types)
    
    return ColumnsResponse(columns=columns)


@router.get("/{session_id}/preview", response_model=CSVPreviewResponse)
async def preview_file(
    session: Session = Depends(get_session),
    csv_service: CSVService = Depends(get_csv_service),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of rows to preview"),
) -> CSVPreviewResponse:
    """
    Get a preview of the CSV data.
    
    Args:
        session: Session dependency
        csv_service: CSV service dependency
        limit: Maximum number of rows to return
        
    Returns:
        CSV preview with columns and rows
    """
    preview = await csv_service.preview_data(session, limit)
    
    return CSVPreviewResponse(
        columns=preview["columns"],
        rows=preview["rows"],
        total_rows=preview["total_rows"],
        preview_rows=preview["preview_rows"],
    )
