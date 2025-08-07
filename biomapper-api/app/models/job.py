"""Database models for job management."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.models.strategy_execution import JobStatus

Base = declarative_base()


class Job(Base):
    """Job execution tracking."""

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)  # UUID
    strategy_name = Column(String(255), nullable=False)
    strategy_config = Column(JSON, nullable=False)  # Full strategy YAML/dict
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_updated = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Execution details
    current_step = Column(String(255), nullable=True)
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)

    # Context and results
    parameters = Column(JSON, nullable=False, default={})
    context = Column(JSON, nullable=False, default={})
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Options and metadata
    options = Column(JSON, nullable=False, default={})
    tags = Column(JSON, nullable=False, default=[])
    description = Column(Text, nullable=True)

    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)
    memory_peak_mb = Column(Integer, nullable=True)

    # User/session tracking
    session_id = Column(String(36), nullable=True)
    user_id = Column(String(255), nullable=True)  # For future auth integration

    # Relationships
    checkpoints = relationship(
        "Checkpoint", back_populates="job", cascade="all, delete-orphan"
    )
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
    steps = relationship("JobStep", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "strategy_name": self.strategy_name,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "current_step": self.current_step,
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "parameters": self.parameters,
            "results": self.results,
            "error_message": self.error_message,
            "tags": self.tags,
            "description": self.description,
        }


class Checkpoint(Base):
    """Execution checkpoints for recovery."""

    __tablename__ = "checkpoints"

    id = Column(String(36), primary_key=True)  # UUID
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_index = Column(Integer, nullable=False)

    # Checkpoint data
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    context_snapshot = Column(JSON, nullable=False)
    parameters_snapshot = Column(JSON, nullable=False)

    # Metadata
    can_resume = Column(Boolean, default=True)
    size_bytes = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    checkpoint_type = Column(
        String(50), default="automatic"
    )  # automatic, manual, pre_error

    # Relationships
    job = relationship("Job", back_populates="checkpoints")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "can_resume": self.can_resume,
            "size_bytes": self.size_bytes,
            "description": self.description,
            "checkpoint_type": self.checkpoint_type,
        }


class JobLog(Base):
    """Detailed logs for job execution."""

    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)

    # Log details
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    step_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="logs")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "step_name": self.step_name,
            "message": self.message,
            "details": self.details,
        }


class JobStep(Base):
    """Individual step execution tracking."""

    __tablename__ = "job_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)

    # Step details
    name = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False)
    step_index = Column(Integer, nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Execution details
    retry_count = Column(Integer, default=0)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Metrics
    memory_used_mb = Column(Integer, nullable=True)
    records_processed = Column(Integer, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="steps")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "action_type": self.action_type,
            "step_index": self.step_index,
            "status": self.status.value if self.status else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }


class JobEvent(Base):
    """Events emitted during job execution for real-time updates."""

    __tablename__ = "job_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), nullable=False, index=True)

    # Event details
    event_type = Column(
        String(50), nullable=False
    )  # progress, log, error, complete, checkpoint
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    step_name = Column(String(255), nullable=True)
    data = Column(JSON, nullable=False, default={})
    message = Column(Text, nullable=True)

    # For event streaming
    delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "step_name": self.step_name,
            "data": self.data,
            "message": self.message,
        }
