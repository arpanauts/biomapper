"""Type stubs for chromadb."""
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

class Collection:
    """ChromaDB collection."""
    def add(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None: ...
    def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]: ...

class Client:
    """ChromaDB client."""
    def __init__(self, settings: Optional["Settings"] = None) -> None: ...
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[Any] = None,
    ) -> Collection: ...
    def get_collection(
        self, name: str, embedding_function: Optional[Any] = None
    ) -> Collection: ...
    def list_collections(self) -> List[Collection]: ...
    def reset(self) -> None: ...

class Settings:
    """ChromaDB settings."""
    def __init__(
        self,
        chroma_db_impl: str = "duckdb+parquet",
        persist_directory: Optional[Union[str, Path]] = None,
        anonymized_telemetry: bool = True,
    ) -> None: ...
