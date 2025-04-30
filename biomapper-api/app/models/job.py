"""
Models related to background jobs.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.mapping import MappingStatus


class Job(BaseModel):
    """Base model for background jobs."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    status: MappingStatus = MappingStatus.PENDING
    progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def update_status(
        self,
        status: MappingStatus,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update job status and related fields."""
        self.status = status
        self.updated_at = datetime.now()

        if progress is not None:
            self.progress = progress

        if error is not None:
            self.error = error

        if result is not None:
            self.result = result

        if status == MappingStatus.COMPLETED or status == MappingStatus.FAILED:
            self.completed_at = datetime.now()
