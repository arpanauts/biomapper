from typing import Any, Dict, List, Mapping, Optional, TypedDict, Union, cast
import numpy as np
import numpy.typing as npt
import chromadb
from chromadb.api.types import QueryResult, Embedding, Embeddings
from chromadb import Settings as ChromaSettings
from chromadb.errors import InvalidCollectionException

from biomapper.schemas.store_schema import VectorStoreConfig
from biomapper.schemas.rag_schema import CompoundDocument


# Type for Chroma's metadata which can be str, int, float, or bool
MetadataType = Mapping[str, Union[str, int, float, bool]]
# Type for numpy arrays with float32
EmbeddingArray = npt.NDArray[np.float32]


class ChromaQueryResult(TypedDict):
    """Type definition for ChromaDB query results."""

    ids: List[List[str]]
    embeddings: Optional[List[List[List[float]]]]
    documents: List[List[str]]
    metadatas: List[List[Dict[str, Any]]]
    distances: List[List[float]]


class ChromaCompoundStore:
    """Chroma-based vector store for compound data."""

    def __init__(
        self,
        config: Optional[VectorStoreConfig] = None,
        settings: Optional[ChromaSettings] = None,
    ) -> None:
        """Initialize ChromaCompoundStore.

        Args:
            config: Vector store configuration
            settings: ChromaDB settings, useful for testing to enable features like reset
        """
        self.config = config or VectorStoreConfig()
        # Create client using settings if provided, otherwise use default settings
        persist_dir = (
            ":memory:"
            if self.config.persist_directory is None
            else str(self.config.persist_directory)
        )
        # Create settings if not provided
        settings = settings or ChromaSettings()

        # Create client with settings
        self.client: Any
        if persist_dir == ":memory:":
            self.client = chromadb.Client(settings=settings)
        else:
            # Use getattr to avoid mypy errors with PersistentClient
            client_class = getattr(chromadb, "PersistentClient")
            self.client = client_class(path=persist_dir, settings=settings)
        self.collection: Any

        # Create collection if it doesn't exist
        try:
            self.collection = self.client.get_collection(
                name=self.config.collection_name,
            )
        except InvalidCollectionException:
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"description": "Compound mapping vector store"},
            )

    def add_documents(self, documents: List[CompoundDocument]) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of documents to add

        Raises:
            ValueError: If any document is missing an embedding
        """
        # Validate that all documents have embeddings
        if any(doc.embedding is None for doc in documents):
            raise ValueError("Cannot add documents with missing embeddings")

        # Convert embeddings to numpy arrays with correct dtype
        embeddings_array: List[Embedding] = []
        for doc in documents:
            # We can safely cast here since we validated above
            arr = cast(Embedding, doc.embedding)
            embeddings_array.append(arr)

        # Cast metadata to the correct type
        metadatas: List[MetadataType] = [
            cast(MetadataType, doc.metadata) for doc in documents
        ]
        docs = [doc.content for doc in documents]
        # Generate unique IDs for documents
        ids = [str(i) for i in range(len(documents))]

        # Add to collection
        self.collection.add(
            ids=ids,
            documents=docs,
            metadatas=metadatas,
            embeddings=embeddings_array,
        )

    def get_relevant_compounds(
        self, query_embedding: List[float], n_results: int = 5
    ) -> List[CompoundDocument]:
        """Query the vector store for similar documents."""
        # Convert query embedding to numpy array
        query_array = cast(Embeddings, [cast(Embedding, query_embedding)])

        results: QueryResult = self.collection.query(
            query_embeddings=query_array,
            n_results=n_results,
        )

        # Create CompoundDocument objects from results
        documents: List[CompoundDocument] = []
        if results["documents"] and results["metadatas"]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                documents.append(
                    CompoundDocument(
                        content=doc,
                        metadata=cast(Dict[str, str], meta),
                        embedding=None,  # We don't get embeddings back from query
                    )
                )

        return documents
