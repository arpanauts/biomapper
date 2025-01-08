from pydantic import BaseModel
from pathlib import Path


class VectorStoreConfig(BaseModel):
    """Configuration for vector store."""

    persist_directory: Path = Path("./vector_store")
    collection_name: str = "compounds"
    embedding_dimension: int = 768
    distance_metric: str = "cosine"
    backend: str = "duckdb+parquet"
