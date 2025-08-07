"""Mock biomapper module for testing purposes."""
import pandas as pd
from pathlib import Path
from typing import Optional, Union, Dict, List, Any
from pydantic import BaseModel


def load_tabular_file(
    file_path: Union[str, Path],
    sep: Optional[str] = None,
    encoding: Optional[str] = None,
    **kwargs,
) -> pd.DataFrame:
    """Mock implementation of load_tabular_file."""
    # Simple implementation that loads CSV/TSV files
    file_path = Path(file_path)

    if sep is None:
        if file_path.suffix.lower() in [".tsv", ".txt"]:
            sep = "\t"
        else:
            sep = ","

    if encoding is None:
        encoding = "utf-8"

    try:
        return pd.read_csv(file_path, sep=sep, encoding=encoding, **kwargs)
    except UnicodeDecodeError:
        # Try with latin-1 if utf-8 fails
        return pd.read_csv(file_path, sep=sep, encoding="latin-1", **kwargs)


def get_max_file_size() -> int:
    """Mock implementation of get_max_file_size."""
    return 100 * 1024 * 1024  # 100MB


# Mock core.models.strategy
class Strategy(BaseModel):
    """Mock Strategy model."""

    id: str
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = {}


# Mock core.mapping_executor
class MappingExecutor:
    """Mock MappingExecutor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def execute_mapping(
        self, source_data: pd.DataFrame, strategy: Strategy, **kwargs
    ) -> Dict[str, Any]:
        """Mock mapping execution."""
        return {
            "status": "completed",
            "mapped_count": len(source_data),
            "results": [
                {
                    "source_id": str(row.iloc[0]),
                    "mapped_id": f"MAPPED_{row.iloc[0]}",
                    "confidence": 0.95,
                }
                for _, row in source_data.iterrows()
            ],
        }


# Mock mapping.relationships.executor
class RelationshipMappingExecutor:
    """Mock RelationshipMappingExecutor."""

    async def map_from_endpoint_data(
        self, relationship_id: str, source_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
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
