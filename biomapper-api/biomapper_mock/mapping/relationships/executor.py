"""Mock RelationshipMappingExecutor"""
from typing import Dict, Any
import pandas as pd


class RelationshipMappingExecutor:
    """Mock RelationshipMappingExecutor class"""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    async def map_from_endpoint_data(self, relationship_id, source_data):
        """Mock implementation of map_from_endpoint_data."""
        return [
            {
                "source_id": list(source_data.values())[0],
                "source_type": list(source_data.keys())[0],
                "target_id": f"mapped_{list(source_data.values())[0]}",
                "target_type": "SPOKE",
                "confidence": 0.95,
                "path_id": 1,
            }
        ]

    def execute(self, data: pd.DataFrame) -> Dict[str, Any]:
        return {"status": "mock", "data": data.to_dict()}
