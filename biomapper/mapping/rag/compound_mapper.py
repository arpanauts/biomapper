"""RAG-based compound mapping implementation."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np

import chromadb
from chromadb.config import Settings
from pydantic import BaseModel

from .base_rag import BaseRAGMapper, BaseEmbedder, BasePromptManager, Document
from ...monitoring.langfuse_tracker import LangfuseTracker
from ...monitoring.metrics import MetricsTracker
from ...schemas.rag_schema import LLMMapperResult, Match, RAGMetrics
from ...schemas.store_schema import VectorStoreConfig

logger = logging.getLogger(__name__)


class CompoundDocument(Document):
    """Document representing a compound."""
    def __init__(self, content: str, metadata: Dict[str, Any], embedding: Optional[np.ndarray] = None):
        super().__init__(content=content, metadata=metadata, embedding=embedding)


class ChromaCompoundStore(BaseVectorStore[CompoundDocument]):
    """ChromaDB-based vector store for compounds."""
    
    def __init__(self, path: str = "/home/ubuntu/biomapper/vector_store"):
        """Initialize store with path to ChromaDB files."""
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_collection("compounds")

    async def add_documents(self, documents: List[CompoundDocument]) -> None:
        """Add documents to the store."""
        embeddings = [doc.embedding for doc in documents if doc.embedding is not None]
        metadatas = [doc.metadata for doc in documents]
        ids = [doc.metadata.get("hmdb_id", str(i)) for i, doc in enumerate(documents)]
        
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    async def get_relevant(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: float = 0.0
    ) -> List[CompoundDocument]:
        """Get relevant documents for a query embedding."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["metadatas", "documents", "distances"]
        )
        
        documents = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            content = results["documents"][0][i]
            distance = results["distances"][0][i]
            
            # Skip if below similarity threshold
            similarity = 1.0 - distance
            if similarity < threshold:
                continue
                
            documents.append(CompoundDocument(
                content=content,
                metadata={**metadata, "similarity": similarity}
            ))
            
        return documents


class CompoundPromptManager(BasePromptManager):
    """Prompt manager for compound mapping."""
    
    def get_prompt(self, query: str, context: List[Document], **kwargs: Any) -> str:
        """Get prompt for compound mapping."""
        context_str = "\n\n".join([
            f"Compound: {doc.metadata.get('name', 'Unknown')}\n"
            f"Description: {doc.content}\n"
            f"HMDB ID: {doc.metadata.get('hmdb_id', 'Unknown')}\n"
            f"Similarity: {doc.metadata.get('similarity', 0.0):.3f}"
            for doc in context
        ])
        
        prompt = f"""Given a query compound name and relevant compound information from a database, determine if any of the compounds are valid matches.

Query compound: {query}

Relevant compounds from database:
{context_str}

For each potential match, provide:
1. Whether it is a valid match (true/false)
2. Confidence score (0-1)
3. Reasoning for the match

Output in JSON format:
{{
    "matches": [
        {{
            "compound_id": "HMDB ID",
            "compound_name": "Name",
            "confidence": 0.95,
            "reasoning": "Explanation"
        }}
    ]
}}"""
        
        return prompt


class RAGCompoundMapper(BaseRAGMapper):
    """RAG-based compound mapper."""
    
    def __init__(
        self,
        embedder: BaseEmbedder,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
        store_config: Optional[VectorStoreConfig] = None,
    ):
        """Initialize compound mapper."""
        vector_store = ChromaCompoundStore()
        prompt_manager = CompoundPromptManager()
        
        super().__init__(
            vector_store=vector_store,
            embedder=embedder,
            prompt_manager=prompt_manager,
            metrics=metrics,
            langfuse=langfuse,
            store_config=store_config
        )
