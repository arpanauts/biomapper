"""Enhanced database models for state persistence."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    UUID,
    BigInteger,
    Boolean,
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.strategy_execution import JobStatus


class Job(Base):
    """Job execution tracking with enhanced persistence."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_name = Column(String(255), nullable=False, index=True)
    strategy_version = Column(String(50), nullable=True)
    status = Column(
        SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True
    )

    # User tracking
    created_by = Column(String(255), nullable=True)
    session_id = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_updated = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Execution progress
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    progress_percentage = Column(DECIMAL(5, 2), default=0)

    # Parameters and configuration
    input_parameters = Column(JSON, nullable=False, default={})
    execution_options = Column(JSON, nullable=False, default={})
    strategy_config = Column(JSON, nullable=False)

    # Results and errors
    final_results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Resource tracking
    cpu_seconds = Column(DECIMAL(10, 2), nullable=True)
    memory_mb_peak = Column(Integer, nullable=True)
    execution_time_ms = Column(BigInteger, nullable=True)

    # Metadata
    tags = Column(JSON, nullable=False, default=[])
    description = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Relationships
    steps = relationship(
        "ExecutionStep", back_populates="job", cascade="all, delete-orphan"
    )
    checkpoints = relationship(
        "ExecutionCheckpoint", back_populates="job", cascade="all, delete-orphan"
    )
    logs = relationship(
        "ExecutionLog", back_populates="job", cascade="all, delete-orphan"
    )
    results = relationship(
        "ResultStorage", back_populates="job", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_jobs_status_created", "status", "created_at"),
        Index("idx_jobs_strategy_status", "strategy_name", "status"),
    )


class ExecutionStep(Base):
    """Individual step execution tracking."""

    __tablename__ = "execution_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)

    # Timing
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_ms = Column(BigInteger, nullable=True)

    # Input/Output
    input_params = Column(JSON, nullable=True)
    output_results = Column(JSON, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    can_retry = Column(Boolean, default=True)

    # Metrics
    records_processed = Column(Integer, nullable=True)
    records_matched = Column(Integer, nullable=True)
    records_failed = Column(Integer, nullable=True)
    confidence_score = Column(DECIMAL(5, 4), nullable=True)
    memory_used_mb = Column(Integer, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="steps")

    # Indexes
    __table_args__ = (
        Index("idx_steps_job_index", "job_id", "step_index", unique=True),
        Index("idx_steps_status", "status"),
    )


class ExecutionCheckpoint(Base):
    """Execution checkpoints for recovery."""

    __tablename__ = "execution_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    step_index = Column(Integer, nullable=False)
    checkpoint_type = Column(
        String(50), default="automatic"
    )  # automatic, manual, before_step, after_step, error

    # Timing
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True)

    # State snapshot
    context_data = Column(JSON, nullable=True)  # For small contexts
    variables = Column(JSON, nullable=True)

    # External storage for large contexts
    storage_type = Column(String(50), default="database")  # database, s3, filesystem
    storage_path = Column(Text, nullable=True)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    compressed = Column(Boolean, default=False)

    # Metadata
    is_resumable = Column(Boolean, default=True)
    step_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="checkpoints")

    # Indexes
    __table_args__ = (Index("idx_checkpoints_job_step", "job_id", "step_index"),)


class ExecutionLog(Base):
    """Detailed execution logs."""

    __tablename__ = "execution_logs"

    # SQLite requires Integer (not BigInteger) for autoincrement to work properly
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index = Column(Integer, nullable=True)

    # Log details
    log_level = Column(
        String(20), nullable=False
    )  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    # Timing
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    # Categorization
    category = Column(
        String(50), nullable=True
    )  # action, validation, error, performance
    component = Column(
        String(100), nullable=True
    )  # executor, action, checkpoint, storage

    # Relationships
    job = relationship("Job", back_populates="logs")

    # Indexes
    __table_args__ = (
        Index("idx_logs_job_level", "job_id", "log_level"),
        Index("idx_logs_timestamp", "created_at"),
    )


class ResultStorage(Base):
    """Storage for large execution results."""

    __tablename__ = "result_storage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    step_index = Column(Integer, nullable=True)
    result_key = Column(String(255), nullable=False)

    # Storage options
    storage_type = Column(
        String(50), nullable=False
    )  # inline, s3, filesystem, compressed
    inline_data = Column(JSON, nullable=True)  # For small results
    external_path = Column(Text, nullable=True)  # For large results
    size_bytes = Column(BigInteger, nullable=False)

    # Metadata
    content_type = Column(
        String(100), nullable=True
    )  # application/json, text/csv, etc.
    encoding = Column(String(50), nullable=True)  # utf-8, gzip, etc.
    checksum = Column(String(64), nullable=True)  # SHA256 hash
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    accessed_count = Column(Integer, default=0)
    last_accessed = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    job = relationship("Job", back_populates="results")

    # Indexes
    __table_args__ = (
        Index("idx_results_job_key", "job_id", "step_index", "result_key", unique=True),
        Index("idx_results_expires", "expires_at"),
    )


class JobEvent(Base):
    """Events for real-time job monitoring."""

    __tablename__ = "job_events"

    # SQLite requires Integer (not BigInteger) for autoincrement to work properly
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event details
    event_type = Column(
        String(50), nullable=False
    )  # progress, status_change, error, checkpoint, complete
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    step_name = Column(String(255), nullable=True)
    step_index = Column(Integer, nullable=True)

    # Event data
    data = Column(JSON, nullable=False, default={})
    message = Column(Text, nullable=True)
    severity = Column(String(20), nullable=True)  # info, warning, error, critical

    # Delivery tracking
    delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)
    delivery_error = Column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_events_job_type", "job_id", "event_type"),
        Index("idx_events_timestamp", "timestamp"),
        Index("idx_events_delivered", "delivered", "timestamp"),
    )
