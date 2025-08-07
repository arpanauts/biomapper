#!/usr/bin/env python3
"""Test metabolite search functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biomapper.rag.metabolite_search import MetaboliteSearcher


async def test_search():
    """Test searching for metabolites."""
    searcher = MetaboliteSearcher(
        qdrant_url="localhost:6333",
        collection_name="hmdb_metabolites",
        embedding_model="BAAI/bge-small-en-v1.5",
    )

    # Test compounds from the Arivale dataset
    test_queries = [
        "glucose",
        "cholesterol",
        "spermidine",
        "histidine",
        "methylhistidine",
        "1-methylhistidine",
    ]

    print("Testing metabolite search with loaded data...\n")

    for query in test_queries:
        print(f"Searching for: {query}")
        try:
            results = await searcher.search_by_name(query, limit=3)
            if results:
                print(f"  Found {len(results)} matches:")
                for i, result in enumerate(results):
                    print(
                        f"  {i+1}. {result['name']} (HMDB{result['hmdb_id']}) - Score: {result['score']:.3f}"
                    )
            else:
                print("  No matches found")
        except Exception as e:
            print(f"  Error: {e}")
        print()

    # Test batch search
    print("Testing batch search...")
    batch_results = await searcher.batch_search(
        ["glucose", "cholesterol", "caffeine"], limit=2
    )
    print(f"Batch search returned {len(batch_results)} result sets")


if __name__ == "__main__":
    asyncio.run(test_search())
