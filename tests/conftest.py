"""
Global pytest configuration and shared fixtures.
"""
import sys
import json
from unittest.mock import MagicMock

# Mock the PydanticEncoder for tests
class PydanticEncoder(json.JSONEncoder):
    """Mock encoder that handles additional types"""
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

# Add to module scope
sys.modules['biomapper.utils.json_utils'] = MagicMock()
sys.modules['biomapper.utils.json_utils'].PydanticEncoder = PydanticEncoder