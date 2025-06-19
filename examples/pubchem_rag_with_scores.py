#!/usr/bin/env python3
"""Example demonstrating PubChemRAGMappingClient with Qdrant similarity scores."""

import asyncio
from biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient


async def main():
    """Demonstrate using PubChemRAGMappingClient with similarity score access."""
    
    # Initialize the client
    config = {
        "qdrant_host": "localhost",
        "qdrant_port": 6333,
        "collection_name": "pubchem_bge_small_v1_5",
        "top_k": 5,
        "score_threshold": 0.5
    }
    
    client = PubChemRAGMappingClient(config)
    
    # Test metabolites
    test_compounds = ["aspirin", "caffeine", "glucose", "unknown_xyz_compound"]
    
    print("Mapping metabolite names to PubChem CIDs...\n")
    
    # Perform mapping (traditional interface)
    results = await client.map_identifiers(test_compounds)
    
    # Display traditional results
    print("=== Traditional Results (Backward Compatible) ===")
    for compound, (target_ids, score_str) in results.items():
        if target_ids:
            print(f"{compound}:")
            print(f"  Target IDs: {', '.join(target_ids[:3])}")  # Show first 3
            print(f"  Best Score: {score_str}")
        else:
            print(f"{compound}: No results found")
    
    # Access detailed results with Qdrant similarity scores
    print("\n=== Detailed Results with Qdrant Scores ===")
    detailed_output = client.get_last_mapping_output()
    
    if detailed_output:
        # Show global metadata
        print("\nMapping Configuration:")
        print(f"  Collection: {detailed_output.metadata['collection']}")
        print(f"  Model: {detailed_output.metadata['embedding_model']}")
        print(f"  Distance Metric: {detailed_output.metadata['distance_metric']}")
        print(f"  Top K: {detailed_output.metadata['top_k']}")
        
        # Show individual results
        print("\nDetailed Results:")
        for result in detailed_output.results:
            print(f"\n{result.identifier}:")
            if result.qdrant_similarity_score is not None:
                print(f"  Qdrant Similarity Score: {result.qdrant_similarity_score:.4f}")
                print(f"  Confidence: {result.confidence:.4f}")
                if result.target_ids:
                    print(f"  Mapped to: {result.target_ids[0]}")
                    if "all_scores" in result.metadata:
                        print(f"  All scores: {[f'{s:.3f}' for s in result.metadata['all_scores']]}")
                print(f"  Score interpretation: {result.metadata.get('score_interpretation', 'N/A')}")
            else:
                print("  No mapping found")
                if "error" in result.metadata:
                    print(f"  Error: {result.metadata['error']}")


if __name__ == "__main__":
    asyncio.run(main())