"""Execution context models for biomapper core."""

from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class CacheConfig(BaseModel):
    """Configuration for caching behavior.

    Attributes:
        enabled: Whether caching is enabled
        ttl_seconds: Time to live in seconds
    """

    model_config = ConfigDict(strict=True)

    enabled: bool = True
    ttl_seconds: int = Field(default=86400, gt=0)  # 24 hours default


class BatchConfig(BaseModel):
    """Configuration for batch processing.

    Attributes:
        size: Number of items to process in a batch
        parallel: Whether to process batches in parallel
    """

    model_config = ConfigDict(strict=True)

    size: int = Field(default=50, gt=0)
    parallel: bool = False


class ExecutionConfig(BaseModel):
    """Configuration for execution behavior.

    Attributes:
        cache: Cache configuration
        batch: Batch processing configuration
        timeout_seconds: Timeout in seconds
        retry_attempts: Number of retry attempts
    """

    model_config = ConfigDict(strict=True)

    cache: CacheConfig = Field(default_factory=CacheConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)
    timeout_seconds: int = Field(default=600, gt=0)  # 10 minutes default
    retry_attempts: int = Field(default=3, ge=0)


class StepResult(BaseModel):
    """Result of a single execution step.

    Attributes:
        action: Name of the action performed
        timestamp: When the action was performed
        success: Whether the action succeeded
        data: Result data from the action
        error: Error message if action failed
    """

    model_config = ConfigDict(strict=True)

    action: str
    timestamp: datetime
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is not empty."""
        if not v:
            raise ValueError("action cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_success_error_consistency(self) -> "StepResult":
        """Validate that success=True doesn't have an error."""
        if self.success and self.error:
            raise ValueError("Cannot have error when success is True")
        return self


class ProvenanceRecord(BaseModel):
    """Record of provenance information for execution tracking.

    Attributes:
        source: The data source
        timestamp: When the action occurred
        action: The action performed
        details: Additional details about the action
    """

    model_config = ConfigDict(strict=True)

    source: str
    timestamp: datetime
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "action")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are not empty."""
        if not v:
            raise ValueError("Field cannot be empty")
        return v


OntologyType = Literal[
    "gene", "protein", "metabolite", "variant", "compound", "pathway", "disease"
]


class StrategyExecutionContext(BaseModel):
    """Context for strategy execution tracking.

    Attributes:
        initial_identifier: The starting identifier
        current_identifier: The current identifier (may change during execution)
        ontology_type: Type of biological entity
        step_results: Results from each execution step
        provenance: List of provenance records
        custom_action_data: Custom data storage for actions
        config: Execution configuration
    """

    model_config = ConfigDict(strict=True)

    initial_identifier: str
    current_identifier: str
    ontology_type: OntologyType
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    custom_action_data: Dict[str, Any] = Field(default_factory=dict)
    config: ExecutionConfig = Field(default_factory=ExecutionConfig)

    # Internal tracking - using PrivateAttr to avoid Pydantic validation
    _identifier_history: List[str] = []

    def __init__(self, **data: Any) -> None:
        """Initialize with identifier history tracking."""
        super().__init__(**data)
        self._identifier_history = [self.initial_identifier]
        if self.current_identifier != self.initial_identifier:
            self._identifier_history.append(self.current_identifier)

    @property
    def identifier_history(self) -> List[str]:
        """Get the history of identifier changes."""
        return self._identifier_history.copy()

    def __setattr__(self, name: str, value: Any) -> None:
        """Track changes to current_identifier."""
        if name == "current_identifier" and hasattr(self, "current_identifier"):
            # Track the change only if it's different from the current value
            if (
                value != self.current_identifier
                and value not in self._identifier_history
            ):
                self._identifier_history.append(value)
        super().__setattr__(name, value)

    def add_step_result(
        self, step_name: str, data: Dict[str, Any], success: bool = True
    ) -> None:
        """Add a step result to the context.

        Args:
            step_name: Name of the step
            data: Result data from the step
            success: Whether the step succeeded
        """
        self.step_results[step_name] = StepResult(
            action=step_name,
            timestamp=datetime.now(),
            success=success,
            data=data,
            error=data.get("error") if not success else None,
        )

    def add_provenance(self, provenance_data: Dict[str, Any]) -> None:
        """Add a provenance record.

        Args:
            provenance_data: Provenance information
        """
        self.provenance.append(
            ProvenanceRecord(
                source=provenance_data["source"],
                timestamp=provenance_data.get("timestamp", datetime.now()),
                action=provenance_data["action"],
                details=provenance_data.get("details", {}),
            )
        )

    def set_action_data(self, key: str, value: Any) -> None:
        """Store custom data for an action.

        Args:
            key: Data key
            value: Data value
        """
        self.custom_action_data[key] = value

    def get_action_data(self, key: str, default: Any = None) -> Any:
        """Retrieve custom data for an action.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            The stored value or default
        """
        return self.custom_action_data.get(key, default)

    def is_successful(self) -> bool:
        """Check if all steps have been successful.

        Returns:
            True if all steps succeeded, False otherwise
        """
        if not self.step_results:
            return True
        return all(step.success for step in self.step_results.values())

    def get_last_step_result(self) -> Optional[StepResult]:
        """Get the most recent step result.

        Returns:
            The last step result or None
        """
        if not self.step_results:
            return None
        # Get the most recent step by timestamp
        return max(self.step_results.values(), key=lambda x: x.timestamp)

    def get_step_result(self, step_name: str) -> Optional[StepResult]:
        """Get a specific step result by name.

        Args:
            step_name: Name of the step

        Returns:
            The step result or None
        """
        return self.step_results.get(step_name)

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution.

        Returns:
            Dictionary with execution summary
        """
        total_steps = len(self.step_results)
        successful_steps = sum(1 for step in self.step_results.values() if step.success)
        failed_steps = total_steps - successful_steps

        return {
            "initial_identifier": self.initial_identifier,
            "current_identifier": self.current_identifier,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": successful_steps / total_steps if total_steps > 0 else 0.0,
        }
