"""SQLAlchemy models for the endpoint health monitoring system."""

import datetime
import json
from typing import Any, Dict, List

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from biomapper.db.models import Base


class EndpointPropertyHealth(Base):
    """Health metrics for endpoint property configurations."""

    __tablename__ = "endpoint_property_health"

    health_id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, nullable=False)
    ontology_type = Column(String, nullable=False)
    property_name = Column(String, nullable=False)
    extraction_success_count = Column(Integer, default=0)
    extraction_failure_count = Column(Integer, default=0)
    last_success_time = Column(DateTime)
    last_failure_time = Column(DateTime)
    avg_extraction_time_ms = Column(Float)
    extraction_error_types = Column(Text)  # JSON array of common errors
    sample_size = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        # Foreign key constraint is commented out until we ensure the table exists
        # ForeignKey('endpoint_property_configs.endpoint_id', 'endpoint_property_configs.ontology_type', 'endpoint_property_configs.property_name'),
        UniqueConstraint(
            "endpoint_id",
            "ontology_type",
            "property_name",
            name="uix_endpoint_property_health",
        ),
        Index("idx_endpoint_health", "endpoint_id"),
    )

    def __repr__(self) -> str:
        """String representation of the health record."""
        return f"<EndpointPropertyHealth {self.endpoint_id}:{self.ontology_type}:{self.property_name}>"

    @property
    def error_types_list(self) -> List[str]:
        """Get the error types as a list."""
        if not self.extraction_error_types:
            return []
        return json.loads(self.extraction_error_types)

    @error_types_list.setter
    def error_types_list(self, error_types: List[str]) -> None:
        """Set the error types from a list."""
        self.extraction_error_types = json.dumps(error_types) if error_types else None

    @property
    def success_rate(self) -> float:
        """Calculate the success rate."""
        total = self.extraction_success_count + self.extraction_failure_count
        if total == 0:
            return 0.0
        return self.extraction_success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert the health record to a dictionary."""
        return {
            "health_id": self.health_id,
            "endpoint_id": self.endpoint_id,
            "ontology_type": self.ontology_type,
            "property_name": self.property_name,
            "extraction_success_count": self.extraction_success_count,
            "extraction_failure_count": self.extraction_failure_count,
            "success_rate": self.success_rate,
            "last_success_time": self.last_success_time.isoformat()
            if self.last_success_time
            else None,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "avg_extraction_time_ms": self.avg_extraction_time_ms,
            "error_types": self.error_types_list,
            "sample_size": self.sample_size,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
        }


class HealthCheckLog(Base):
    """Log of health check runs."""

    __tablename__ = "health_check_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    check_time = Column(DateTime, default=datetime.datetime.utcnow)
    endpoints_checked = Column(Integer, default=0)
    configs_checked = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    duration_ms = Column(Integer)
    status = Column(String)
    details = Column(Text)  # JSON object with additional details

    def __repr__(self) -> str:
        """String representation of the health check log."""
        return f"<HealthCheckLog {self.log_id} time={self.check_time} status={self.status}>"

    @property
    def details_dict(self) -> Dict[str, Any]:
        """Get the details as a dictionary."""
        if not self.details:
            return {}
        return json.loads(self.details)

    @details_dict.setter
    def details_dict(self, details: Dict[str, Any]) -> None:
        """Set the details from a dictionary."""
        self.details = json.dumps(details) if details else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the health check log to a dictionary."""
        return {
            "log_id": self.log_id,
            "check_time": self.check_time.isoformat() if self.check_time else None,
            "endpoints_checked": self.endpoints_checked,
            "configs_checked": self.configs_checked,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "details": self.details_dict,
        }
