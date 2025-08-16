"""Base models with standard configuration for flexibility and backward compatibility."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, Optional, Set


class FlexibleBaseModel(BaseModel):
    """Base model with flexible configuration for all action parameters.
    
    This base model allows extra fields to ensure backward compatibility
    when strategies or configurations include additional parameters not
    yet defined in the model schema.
    """
    
    model_config = ConfigDict(
        extra='allow',              # Allow extra fields for backward compatibility
        validate_assignment=True,   # Validate on assignment
        use_enum_values=True,       # Use enum values not names
        populate_by_name=True,      # Allow population by field name or alias
        str_strip_whitespace=True,  # Strip whitespace from strings
        json_schema_extra={
            'allow_mutation': True
        }
    )
    
    def get_extra_fields(self) -> Dict[str, Any]:
        """Get any extra fields that were passed but not defined in the model.
        
        Returns:
            Dictionary of field names to values for extra fields
        """
        # In Pydantic 2.x, extra fields are stored in __pydantic_extra__
        if hasattr(self, '__pydantic_extra__'):
            return self.__pydantic_extra__ or {}
        # Fallback for older versions or edge cases
        defined_fields = set(self.model_fields.keys())
        all_fields = set(self.__dict__.keys())
        extra_fields = all_fields - defined_fields
        return {k: self.__dict__[k] for k in extra_fields}
    
    def has_extra_fields(self) -> bool:
        """Check if any extra fields were provided.
        
        Returns:
            True if extra fields exist, False otherwise
        """
        return bool(self.get_extra_fields())
    
    def to_dict_with_extras(self) -> Dict[str, Any]:
        """Export model data including extra fields.
        
        Returns:
            Dictionary with all model fields plus any extra fields
        """
        # model_dump() already includes extra fields in Pydantic 2.x
        return self.model_dump()
    
    def get_defined_fields(self) -> Set[str]:
        """Get the set of fields defined in the model schema.
        
        Returns:
            Set of field names defined in the model
        """
        return set(self.model_fields.keys())


class StrictBaseModel(BaseModel):
    """Strict base model for when validation is critical.
    
    Use this model when you need to ensure no extra fields are accepted
    and the model should be immutable after creation.
    """
    
    model_config = ConfigDict(
        extra='forbid',             # Forbid extra fields for strict validation
        validate_assignment=True,   # Validate on assignment
        frozen=True,                # Immutable after creation
        use_enum_values=True,       # Use enum values not names
    )


class ActionParamsBase(FlexibleBaseModel):
    """Base for all action parameter models.
    
    Provides common fields that all actions should support,
    including debug and trace flags, timeout settings, and
    other universal parameters.
    """
    
    # Common fields all actions should have
    debug: bool = Field(default=False, description="Enable debug mode for detailed logging")
    trace: bool = Field(default=False, description="Enable trace mode for execution tracing")
    timeout: Optional[int] = Field(default=None, description="Execution timeout in seconds")
    continue_on_error: bool = Field(default=False, description="Continue execution even if this action fails")
    retry_count: int = Field(default=0, description="Number of retries on failure")
    retry_delay: int = Field(default=1, description="Delay between retries in seconds")
    
    def validate_params(self) -> bool:
        """Override to add custom validation logic.
        
        Returns:
            True if parameters are valid, False otherwise
        """
        return True
    
    def log_extra_fields(self) -> None:
        """Log any extra fields that were provided."""
        extra = self.get_extra_fields()
        if extra:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Extra fields provided: {list(extra.keys())}")
    
    def migrate_legacy_params(self) -> Dict[str, Any]:
        """Override to handle legacy parameter names.
        
        Returns:
            Dictionary with migrated parameter names
        """
        return self.model_dump()


class DatasetOperationParams(ActionParamsBase):
    """Base for dataset operation parameters.
    
    Common base for actions that operate on datasets,
    providing standard input/output key fields.
    """
    
    input_key: str = Field(..., description="Key of the input dataset in context")
    output_key: str = Field(..., description="Key for the output dataset in context")
    
    def validate_params(self) -> bool:
        """Validate that input and output keys are different."""
        if self.input_key == self.output_key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Input and output keys are the same: {self.input_key}")
        return True


class FileOperationParams(ActionParamsBase):
    """Base for file operation parameters.
    
    Common base for actions that read from or write to files,
    providing standard file path validation.
    """
    
    file_path: str = Field(..., description="Path to the file")
    create_dirs: bool = Field(default=True, description="Create parent directories if they don't exist")
    
    def validate_file_path(self) -> bool:
        """Validate that the file path is valid.
        
        Returns:
            True if path is valid, False otherwise
        """
        from pathlib import Path
        try:
            path = Path(self.file_path)
            if self.create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid file path: {self.file_path} - {e}")
            return False


class APIOperationParams(ActionParamsBase):
    """Base for API operation parameters.
    
    Common base for actions that interact with external APIs,
    providing standard API configuration fields.
    """
    
    api_url: Optional[str] = Field(default=None, description="API endpoint URL")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    max_retries: int = Field(default=3, description="Maximum number of API call retries")
    request_timeout: int = Field(default=30, description="API request timeout in seconds")
    rate_limit_delay: float = Field(default=0.1, description="Delay between API calls in seconds")
    
    def validate_api_config(self) -> bool:
        """Validate API configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if self.api_url and not (self.api_url.startswith('http://') or self.api_url.startswith('https://')):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid API URL: {self.api_url}")
            return False
        return True


# Type aliases for common parameter patterns
FlexibleParams = FlexibleBaseModel
StrictParams = StrictBaseModel
ActionParams = ActionParamsBase
DatasetParams = DatasetOperationParams
FileParams = FileOperationParams
APIParams = APIOperationParams