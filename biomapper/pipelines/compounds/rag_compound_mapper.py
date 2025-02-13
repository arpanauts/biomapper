"""RAG-based compound mapping implementation."""

import logging
from typing import Any, Dict, List, Optional, Union
import numpy as np

import chromadb
from chromadb.config import Settings

from ...core.base_rag import (
    BaseRAGMapper,
    BaseEmbedder,
    BasePromptManager,
    Document,
    RAGError
)
from ...schemas.domain_schema import DomainType
from .compound_mapper import CompoundClass
from ...core.base_store import BaseVectorStore
from ...monitoring.langfuse_tracker import LangfuseTracker
from ...monitoring.metrics import MetricsTracker
from ...schemas.rag_schema import LLMMapperResult, Match, RAGMetrics
from .compound_mapper import CompoundDocument

logger = logging.getLogger(__name__)


class CompoundVectorStore(BaseVectorStore[CompoundDocument]):
    """ChromaDB-based vector store for compounds."""
    
    def __init__(self, path: str = "/home/ubuntu/biomapper/vector_store"):
        """Initialize store with path to ChromaDB files."""
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection("compounds")

    async def add_documents(
        self,
        documents: List[CompoundDocument],
        embeddings: Optional[List[np.ndarray]] = None
    ) -> None:
        """Add documents to the store.
        
        Args:
            documents: List of compound documents
            embeddings: Optional pre-computed embeddings
        """
        if not embeddings:
            # Skip documents without embeddings
            return
            
        metadatas = [doc.metadata for doc in documents]
        ids = [doc.metadata.get("id", str(i)) for i, doc in enumerate(documents)]
        
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            documents=[doc.name for doc in documents]
        )

    async def get_similar(
        self,
        query: Union[str, np.ndarray],
        k: int = 5,
        threshold: float = 0.0,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[CompoundDocument]:
        """Get similar compounds.
        
        Args:
            query: Query string or embedding
            k: Number of results
            threshold: Similarity threshold
            filter_criteria: Optional filters
            
        Returns:
            List of similar compounds
        """
        try:
            if isinstance(query, np.ndarray):
                query_embeddings = [query]
                query_texts = None
            else:
                query_embeddings = None
                query_texts = [query]
                
            results = self.collection.query(
                query_embeddings=query_embeddings,
                query_texts=query_texts,
                n_results=k,
                where=filter_criteria
            )
            
            documents = []
            for i, metadata in enumerate(results["metadatas"][0]):
                doc = CompoundDocument(
                    name=results["documents"][0][i],
                    domain_type=DomainType.COMPOUND,
                    compound_class=CompoundClass.SIMPLE,  # Default to simple compound
                    primary_id=metadata.get("metabolon_id", ""),
                    secondary_id=metadata.get("kegg_id", ""),
                    hmdb_id=metadata.get("hmdb_id", ""),
                    pubchem_id=metadata.get("pubchem_id", ""),
                    metadata=metadata
                )
                documents.append(doc)
                
            return documents
            
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return []

    async def delete(self, document_ids: List[str]) -> None:
        """Delete documents from store."""
        self.collection.delete(ids=document_ids)

    async def clear(self) -> None:
        """Clear all documents from store."""
        self.collection.delete()


class CompoundPromptManager(BasePromptManager):
    """Prompt manager for compound mapping."""
    
    def get_prompt(
        self,
        query: str,
        context: List[Document],
        **kwargs: Any
    ) -> str:
        """Get prompt for compound mapping.
        
        Args:
            query: User query
            context: Retrieved similar compounds
            **kwargs: Additional parameters
            
        Returns:
            Formatted prompt
        """
        # Format context into text
        context_text = "\n".join([
            f"Name: {doc.content}\n"
            f"IDs: {doc.metadata.get('ids', 'None')}\n"
            f"Description: {doc.metadata.get('description', 'None')}\n"
            for doc in context
        ])
        
        # Create prompt
        prompt = f"""Given a compound name and similar known compounds, identify the most likely match.

Query Compound: {query}

Similar Known Compounds:
{context_text}

Based on these similar compounds, determine:
1. The most likely match for the query compound
2. The confidence in this match (0-1)
3. Any relevant compound identifiers (HMDB, ChEBI, etc.)

Format your response as JSON:
{{
    "match": {{
        "name": "matched compound name",
        "confidence": 0.95,
        "ids": {{
            "hmdb_id": "HMDB...",
            "chebi_id": "CHEBI..."
        }}
    }}
}}
"""
        return prompt


class RAGCompoundMapper(BaseRAGMapper):
    """RAG-based compound mapper."""
    
    def __init__(
        self,
        embedder: BaseEmbedder,
        metrics: Optional[MetricsTracker] = None,
        langfuse: Optional[LangfuseTracker] = None,
        store_path: str = "/home/ubuntu/biomapper/vector_store"
    ):
        """Initialize compound mapper.
        
        Args:
            embedder: Text embedder
            metrics: Optional metrics tracker
            langfuse: Optional Langfuse tracker
            store_path: Path to vector store
        """
        vector_store = CompoundVectorStore(path=store_path)
        prompt_manager = CompoundPromptManager()
        
        super().__init__(
            vector_store=vector_store,
            embedder=embedder,
            prompt_manager=prompt_manager,
            metrics=metrics,
            langfuse=langfuse
        )
    
    async def _generate_matches(
        self,
        prompt: str,
        context: List[Document],
        **kwargs: Any
    ) -> List[Match]:
        """Generate matches using LLM.
        
        Args:
            prompt: Generated prompt
            context: Retrieved documents
            **kwargs: Additional parameters
            
        Returns:
            List of matches. If no matches are found, returns a list with a single
            no-match result.
            
        Raises:
            RAGError: If generation fails
        """
        try:
            # TODO: Implement LLM call
            # For now, return mock response with proper Match validation
            if not context:
                return [Match(
                    id="no_match",
                    name="No match found",
                    confidence="0.0",
                    reasoning="No suitable matches found in the compound database"
                )]
                
            return [Match(
                id=str(context[0].id),
                name=context[0].content,
                confidence="0.9",
                reasoning="Found exact match in compound database",
                metadata=context[0].metadata
            )]
        except Exception as e:
            raise RAGError(f"Failed to generate matches: {e}") from e
            
    async def batch_map(
        self,
        queries: List[str],
        batch_size: int = 32,
        **kwargs: Any
    ) -> List[List[Match]]:
        """Map multiple queries in batches.
        
        Args:
            queries: List of queries to map
            batch_size: Size of each batch
            **kwargs: Additional parameters
            
        Returns:
            List of match lists, one for each query
            
        Raises:
            RAGError: If mapping fails
        """
        results = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_embeddings = await self.embedder.embed_batch(batch, batch_size)
            
            # Get similar documents for each query
            batch_similar = []
            for query_embedding in batch_embeddings:
                similar = await self.vector_store.get_similar(
                    query_embedding,
                    k=5,
                    threshold=0.0
                )
                batch_similar.append(similar)
            
            # Generate prompts and matches
            batch_matches = []
            for query, similar in zip(batch, batch_similar):
                prompt = self.prompt_manager.get_prompt(query, similar)
                matches = await self._generate_matches(prompt, similar)
                batch_matches.append(matches)
                
            results.extend(batch_matches)
            
        return results
