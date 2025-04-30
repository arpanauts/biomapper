"""Search engine for embeddings."""

from typing import List, Dict, Any, Optional, Union
import logging
import numpy as np

from ..core.base import BaseEmbedder, BaseVectorStore
from ..models.schemas import EmbedderItem


class EmbedderSearchEngine:
    """Search engine for embeddings."""

    def __init__(self, embedder: BaseEmbedder, vector_store: BaseVectorStore):
        """Initialize the search engine.

        Args:
            embedder: Embedder for query text
            vector_store: Vector store for search
        """
        self.embedder = embedder
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        k: int = 10,
        filter_types: Optional[List[str]] = None,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search for similar items.

        Args:
            query: Query text
            k: Number of results
            filter_types: Optional list of types to filter results (e.g., "pubmed_article")
            min_similarity: Minimum similarity score threshold

        Returns:
            List of search results with metadata
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_single(query)

        # Search vector store
        results = self.vector_store.search(query_embedding, k=k)

        # Apply filters
        filtered_results = []
        for result in results:
            # Check similarity threshold
            if result.get("similarity", 0) < min_similarity:
                continue

            # Check type filter
            if filter_types:
                result_type = result.get("metadata", {}).get("type")
                if result_type not in filter_types:
                    continue

            filtered_results.append(result)

        return filtered_results[:k]

    def format_results(
        self, results: List[Dict[str, Any]], format_type: str = "text"
    ) -> Union[str, List[Dict]]:
        """Format search results for display or further processing.

        Args:
            results: Search results from the search method
            format_type: Output format (text, json, markdown)

        Returns:
            Formatted results as string or dict
        """
        if format_type == "json":
            return results

        elif format_type == "markdown":
            lines = ["# Search Results", ""]

            for i, result in enumerate(results):
                metadata = result.get("metadata", {})
                similarity = result.get("similarity", 0.0)

                lines.append(f"## Result {i+1} - Similarity: {similarity:.4f}")
                lines.append(f"**ID**: {result.get('id')}")

                if "type" in metadata:
                    lines.append(f"**Type**: {metadata['type']}")

                # Format based on type
                if metadata.get("type") == "pubmed_article":
                    if "title" in metadata:
                        lines.append(f"**Title**: {metadata['title']}")
                    if "abstract" in metadata:
                        # Truncate long abstracts
                        abstract = metadata["abstract"]
                        if len(abstract) > 300:
                            abstract = abstract[:300] + "..."
                        lines.append(f"**Abstract**: {abstract}")
                    if "authors" in metadata:
                        authors = metadata.get("authors", [])
                        authors_str = ", ".join(authors[:3])
                        if len(authors) > 3:
                            authors_str += " et al."
                        lines.append(f"**Authors**: {authors_str}")
                    if "journal" in metadata:
                        lines.append(f"**Journal**: {metadata['journal']}")
                    if "publication_date" in metadata:
                        lines.append(f"**Date**: {metadata['publication_date']}")
                    if "mesh_terms" in metadata:
                        terms = metadata.get("mesh_terms", [])
                        if terms:
                            terms_str = ", ".join(terms[:5])
                            if len(terms) > 5:
                                terms_str += "..."
                            lines.append(f"**MeSH Terms**: {terms_str}")

                elif metadata.get("type") == "pubchem_compound":
                    if "name" in metadata:
                        lines.append(f"**Name**: {metadata['name']}")
                    if "molecular_formula" in metadata:
                        lines.append(f"**Formula**: {metadata['molecular_formula']}")
                    if "synonyms" in metadata:
                        synonyms = metadata.get("synonyms", [])
                        if synonyms:
                            syns_str = ", ".join(synonyms[:3])
                            if len(synonyms) > 3:
                                syns_str += "..."
                            lines.append(f"**Synonyms**: {syns_str}")
                    if "description" in metadata:
                        lines.append(f"**Description**: {metadata['description']}")

                lines.append("")  # Empty line between results

            return "\n".join(lines)

        else:  # Default to text format
            lines = ["Search Results:"]

            for i, result in enumerate(results):
                metadata = result.get("metadata", {})
                similarity = result.get("similarity", 0.0)

                lines.append(
                    f"\n[{i+1}] ID: {result.get('id')} - Similarity: {similarity:.4f}"
                )

                # Format based on type
                if metadata.get("type") == "pubmed_article":
                    if "title" in metadata:
                        lines.append(f"Title: {metadata['title']}")
                    if "abstract" in metadata:
                        # Truncate long abstracts
                        abstract = metadata["abstract"]
                        if len(abstract) > 200:
                            abstract = abstract[:200] + "..."
                        lines.append(f"Abstract: {abstract}")
                    if "authors" in metadata:
                        authors = metadata.get("authors", [])
                        authors_str = ", ".join(authors[:3])
                        if len(authors) > 3:
                            authors_str += " et al."
                        lines.append(f"Authors: {authors_str}")

                elif metadata.get("type") == "pubchem_compound":
                    if "name" in metadata:
                        lines.append(f"Name: {metadata['name']}")
                    if "molecular_formula" in metadata:
                        lines.append(f"Formula: {metadata['molecular_formula']}")
                    if "description" in metadata:
                        lines.append(f"Description: {metadata['description']}")

                # Generic fallback for other types
                else:
                    for key, value in metadata.items():
                        if key not in ["id", "type", "source"] and isinstance(
                            value, (str, int, float)
                        ):
                            lines.append(f"{key}: {value}")

            return "\n".join(lines)
