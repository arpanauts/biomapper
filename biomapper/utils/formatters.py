import json
from datetime import datetime

class PydanticEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle Pydantic models and other special types."""
    
    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle Pydantic models if they exist in the codebase
        # Pydantic v2 uses model_dump, v1 uses dict
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
            return obj.model_dump()
        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()
        # Handle enum values if needed (example, actual Enum usage might vary)
        if hasattr(obj, "value") and hasattr(obj, "__class__") and hasattr(obj.__class__, "__members__"):
             # Check if it's a standard Enum or similar structure
            if obj.__class__.__name__ in obj.__class__.__members__:
                 return obj.value
        # Let the base class handle anything else
        return super().default(obj)
