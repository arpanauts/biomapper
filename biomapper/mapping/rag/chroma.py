"""ChromaDB vector store implementation."""

from typing import Any, Dict, List, Mapping, Optional, Union, cast
import numpy as np
import chromadb
from chromadb.api.types import Embedding, Embeddings, Where, WhereDocument
from chromadb import Settings as ChromaSettings
from chromadb.errors import InvalidCollectionException

from .base_rag import BaseVectorStore, Document, RetrievalError
from ...schemas.store_schema import VectorStoreConfig


# Type for Chroma's metadata which can be str, int, float, or bool
MetadataType = Mapping[str, Union[str, int, float, bool]]


class ChromaDocument(Document):
    """Document for ChromaDB storage."""


class ChromaVectorStore(BaseVectorStore[ChromaDocument]):
    """ChromaDB-based vector store implementation."""

    def __init__(
        self,
        config: Optional[VectorStoreConfig] = None,
        settings: Optional[ChromaSettings] = None,
    ) -> None:
        """Initialize ChromaVectorStore.
        
        Args:
            config: Vector store configuration
            settings: ChromaDB settings
        """
        self.config = config or VectorStoreConfig()
        persist_dir = (
            ":memory:"
            if self.config.persist_directory is None
            else str(self.config.persist_directory)
        )
        settings = settings or ChromaSettings()

        # Create client
        self.client: Any
        if persist_dir == ":memory:":
            self.client = chromadb.Client(settings=settings)
        else:
            client_class = getattr(chromadb, "PersistentClient")
            self.client = client_class(path=persist_dir, settings=settings)

        # Create or get collection
        try:
            self.collection = self.client.get_collection(
                name=self.config.collection_name,
            )
        except InvalidCollectionException:
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"description": "RAG vector store"},
            )

    async def add_documents(self, documents: List[ChromaDocument]) -> None:
        """Add documents to the vector store.
        
        Args:
            documents: List of documents to add

        Raises:
            ValueError: If any document is missing an embedding
        """
        # Validate embeddings
        if any(doc.embedding is None for doc in documents):
            raise ValueError("Cannot add documents with missing embeddings")

        # Convert embeddings to list format
        embeddings_array: List[Embedding] = []
        for doc in documents:
            # We can safely cast here since we validated above
            arr = cast(Embedding, doc.embedding)
            embeddings_array.append(arr.tolist())

        # Cast metadata to the correct type
        metadatas: List[MetadataType] = [
            cast(MetadataType, doc.metadata) for doc in documents
        ]
        docs = [doc.content for doc in documents]
        ids = [str(i) for i in range(len(documents))]

        # Add to collection
        try:
            self.collection.add(
                ids=ids,
                documents=docs,
                metadatas=metadatas,
                embeddings=embeddings_array,
            )
        except Exception as e:
            raise RetrievalError(f"Failed to add documents: {e}") from e

    async def get_relevant(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: float = 0.0,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[ChromaDocument]:
        """Get relevant documents for a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of documents to retrieve
            threshold: Minimum similarity threshold (not used in ChromaDB)
            where: Optional metadata filter (e.g., {"hmdb_id": "HMDB0000001"})
            where_document: Optional document content filter

        Returns:
            List of relevant documents

        Raises:
            RetrievalError: If retrieval fails
        """
        try:
            # Convert query embedding to list format
            query_array = cast(Embeddings, [cast(Embedding, query_embedding.tolist())])

            # Convert filters to ChromaDB format
            chroma_where = cast(Where, where) if where else None
            chroma_where_document = cast(WhereDocument, where_document) if where_document else None

            # Query collection
            results = self.collection.query(
                query_embeddings=query_array,
                n_results=k,
                where=chroma_where,
                where_document=chroma_where_document,
            )

            # Create ChromaDocument objects from results
            documents: List[ChromaDocument] = []
            if results["documents"] and results["metadatas"]:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    documents.append(
                        ChromaDocument(
                            content=doc,
                            metadata=cast(Dict[str, Any], meta),
                            embedding=None,  # We don't get embeddings back from query
                        )
                    )

            return documents

        except Exception as e:
            raise RetrievalError(f"Failed to retrieve documents: {e}") from e

    async def clear(self) -> None:
        """Clear all documents from the store."""
        try:
            self.collection.delete(where={})
        except Exception as e:
            raise RetrievalError(f"Failed to clear store: {e}") from e
