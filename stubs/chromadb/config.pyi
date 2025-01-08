"""Type stubs for chromadb.config."""
from typing import Optional, Union
from pathlib import Path

class Settings:
    """ChromaDB settings."""
    def __init__(
        self,
        chroma_db_impl: str = "duckdb+parquet",
        persist_directory: Optional[Union[str, Path]] = None,
        anonymized_telemetry: bool = True,
    ) -> None: ...
