"""Script to search compounds using ChromaDB."""

import argparse
import asyncio
from typing import Dict, List, Optional, Any

from biomapper.mapping.rag.chroma import ChromaVectorStore
from biomapper.mapping.rag.embedder import ChromaEmbedder
from biomapper.schemas.store_schema import VectorStoreConfig


async def search_compounds(
    query: str,
    k: int = 5,
    collection_name: str = "compounds",
    metadata_filters: Optional[Dict[str, Any]] = None,
    content_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search for compounds using ChromaDB.

    Args:
        query: Search query
        k: Number of results to return
        collection_name: Name of the ChromaDB collection to search in
        metadata_filters: Optional filters for metadata fields (e.g., {"hmdb_id": "HMDB0000001"})
        content_filters: Optional filters for document content

    Returns:
        List of compound documents with their metadata
    """
    # Initialize embedder and vector store
    embedder = ChromaEmbedder()
    store = ChromaVectorStore(
        config=VectorStoreConfig(
            collection_name=collection_name, persist_directory="vector_store"
        )
    )

    # Get query embedding
    query_embedding = await embedder.embed_text(query)

    # Search for relevant documents
    documents = await store.get_relevant(
        query_embedding=query_embedding,
        k=k,
        where=metadata_filters,
        where_document=content_filters,
    )

    # Format results
    results = []
    for doc in documents:
        result = {"content": doc.content, **doc.metadata}
        results.append(result)

    return results


async def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Search compounds using ChromaDB")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-k", type=int, default=5, help="Number of results to return")
    parser.add_argument(
        "--collection",
        default="compounds",
        help="ChromaDB collection name to search in (default: compounds)",
    )
    parser.add_argument(
        "--hmdb-id",
        help="Filter by HMDB ID",
    )
    parser.add_argument(
        "--name",
        help="Filter by compound name",
    )
    parser.add_argument(
        "--domain-type",
        help="Filter by domain type",
    )
    args = parser.parse_args()

    # Build metadata filters
    metadata_filters = {}
    if args.hmdb_id:
        metadata_filters["hmdb_id"] = args.hmdb_id
    if args.name:
        metadata_filters["name"] = args.name
    if args.domain_type:
        metadata_filters["domain_type"] = args.domain_type

    # Search compounds
    results = await search_compounds(
        query=args.query,
        k=args.k,
        collection_name=args.collection,
        metadata_filters=metadata_filters if metadata_filters else None,
    )

    # Print results
    print(f"\nFound {len(results)} results for query: {args.query}")
    print(f"Collection: {args.collection}\n")
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  HMDB ID: {result['hmdb_id']}")
        print(f"  Name: {result['name']}")
        print(f"  Description: {result.get('description', '')[:200]}...")
        if result.get("synonyms"):
            print(f"  Synonyms: {result['synonyms'][:200]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
