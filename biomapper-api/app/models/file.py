"""
Models related to file operations.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    session_id: str
    filename: str
    created_at: datetime
    file_size: int
    content_type: str


class ColumnsResponse(BaseModel):
    """Response model for column retrieval."""

    columns: List[str]
    column_types: Optional[Dict[str, str]] = None


class CSVPreviewResponse(BaseModel):
    """Response model for CSV preview."""

    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    preview_rows: int = Field(..., description="Number of rows in the preview")
