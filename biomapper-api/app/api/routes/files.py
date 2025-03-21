"""
API routes for file operations.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up logger
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


@router.post("/server/list", response_model=List[Dict[str, Any]])
async def list_server_files(
    directory_path: str = Body(..., description="Path to the directory on the server"),
    extensions: Optional[List[str]] = Body(None, description="File extensions to include (e.g., ['.csv', '.tsv'])"),
    csv_service: CSVService = Depends(get_csv_service),
) -> List[Dict[str, Any]]:
    """
    List files available on the server in the specified directory.
    
    Args:
        directory_path: Path to the directory on the server
        extensions: List of file extensions to include (defaults to .csv and .tsv)
        csv_service: CSV service dependency
        
    Returns:
        List of file information dictionaries
    """
    return await csv_service.list_server_files(directory_path, extensions)


# Add this class to define the request model
class FilePathRequest(BaseModel):
    file_path: str

@router.post("/server/load", response_model=FileUploadResponse)
async def load_server_file(
    request: FilePathRequest,
    csv_service: CSVService = Depends(get_csv_service),
) -> FileUploadResponse:
    """
    Load a file from the server filesystem.
    
    Args:
        file_path: Path to the file on the server
        csv_service: CSV service dependency
        
    Returns:
        Upload response with session ID
    """
    try:
        file_path = request.file_path
        logger.info(f"Received request to load server file: {file_path}")
        
        # Log the raw request for debugging
        logger.debug(f"Request body: {request.dict()}")
        
        # Validate the file path is not empty
        if not file_path or file_path.isspace():
            logger.error("Empty file path provided")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File path cannot be empty"
            )
            
        # Normalize the path to handle any special characters or format issues
        file_path = os.path.normpath(file_path)
        logger.debug(f"Normalized path: {file_path}")
        
        # Validate the file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ['.csv', '.tsv']:
            logger.error(f"Unsupported file extension: {file_ext}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file extension: {file_ext}. Only .csv and .tsv files are supported."
            )
        
        # Check if the file exists and is accessible
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File does not exist: {file_path}"
            )
        
        if not os.path.isfile(file_path):
            logger.error(f"Path is not a file: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Path is not a file: {file_path}"
            )
        
        # Try to open the file to verify read permissions
        try:
            with open(file_path, 'r') as f:
                # Just check if we can read the first line
                f.readline()
        except PermissionError:
            logger.error(f"Permission denied: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {file_path}"
            )
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error opening file: {str(e)}"
            )
        
        # Load the file through the service
        session, _ = await csv_service.load_server_file(file_path)
        
        # Prepare response
        return FileUploadResponse(
            session_id=session.session_id,
            filename=os.path.basename(file_path),
            created_at=session.created_at,
            file_size=session.metadata.get("file_size", 0),
            content_type=session.metadata.get("content_type", ""),
        )
    except HTTPException:
        # Re-raise existing HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error loading server file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load server file: {str(e)}"
        )
