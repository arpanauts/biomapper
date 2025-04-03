"""Example of using the Qdrant vector store for embeddings."""

import os
import logging
import numpy as np
from typing import List, Dict, Any

from biomapper.embedder.generators.text_embedder import TextEmbedder
from biomapper.embedder.storage.qdrant_store import QdrantVectorStore
from biomapper.embedder.search.engine import EmbedderSearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO)

def prepare_sample_data() -> List[Dict[str, Any]]:
    """Prepare sample data for embedding.
    
    Returns:
        List of sample data items
    """
    return [
        {
            "id": "CHEBI:16236",
            "type": "compound",
            "primary_text": "Glucose is a simple sugar with the molecular formula C6H12O6. Glucose is the most abundant monosaccharide, a subcategory of carbohydrates.",
            "metadata": {
                "name": "Glucose",
                "formula": "C6H12O6",
                "inchi": "InChI=1S/C6H12O6/c7-1-2-3(8)4(9)5(10)6(11)12-2/h2-11H,1H2/t2-,3-,4+,5-,6?/m1/s1",
                "smiles": "C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O",
                "molecular_weight": 180.156,
                "synonyms": ["D-Glucose", "Dextrose", "Grape sugar", "Blood sugar"]
            },
            "source": "chebi"
        },
        {
            "id": "CHEBI:27732",
            "type": "compound",
            "primary_text": "Lactose is a disaccharide sugar composed of galactose and glucose. Lactose makes up around 2–8% of milk by weight.",
            "metadata": {
                "name": "Lactose",
                "formula": "C12H22O11",
                "inchi": "InChI=1S/C12H22O11/c13-1-4-6(16)8(18)9(19)11(21-4)23-12-10(20)7(17)5(15)3(2-14)22-12/h3-20H,1-2H2/t3-,4-,5-,6-,7-,8-,9-,10-,11-,12+/m1/s1",
                "smiles": "C([C@@H]1[C@H]([C@@H]([C@H](O1)O[C@H]2[C@@H]([C@H]([C@@H]([C@H](O2)CO)O)O)O)O)O)O",
                "molecular_weight": 342.297,
                "synonyms": ["Milk sugar", "Beta-D-galactopyranosyl-(1->4)-D-glucose"]
            },
            "source": "chebi"
        },
        {
            "id": "CHEBI:17234",
            "type": "compound",
            "primary_text": "Caffeine is a central nervous system stimulant of the methylxanthine class. It is the world's most widely consumed psychoactive drug.",
            "metadata": {
                "name": "Caffeine",
                "formula": "C8H10N4O2",
                "inchi": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
                "molecular_weight": 194.191,
                "synonyms": ["1,3,7-Trimethylpurine-2,6-dione", "Theine", "Guaranine", "Methyltheobromine"]
            },
            "source": "chebi"
        }
    ]

def main():
    """Main example function."""
    # Initialize components
    embedder = TextEmbedder(model_name="all-MiniLM-L6-v2")
    
    # Create Qdrant store
    # For local storage:
    vector_store = QdrantVectorStore(
        collection_name="biomapper_compounds",
        dimension=384,  # Matches the embedding model dimension
        local_path="/tmp/qdrant_storage"  # Local storage path
    )
    
    # For connecting to a Qdrant server:
    # vector_store = QdrantVectorStore(
    #     collection_name="biomapper_compounds",
    #     url="http://localhost:6333",  # Change to your Qdrant server URL
    #     # api_key="your-api-key",  # Uncomment and add your API key for Qdrant Cloud
    # )
    
    # Prepare sample data
    data = prepare_sample_data()
    
    # Generate embeddings
    texts = [item["primary_text"] for item in data]
    embeddings = embedder.embed(texts)
    
    # Store embeddings with metadata
    ids = vector_store.add(embeddings, [item["metadata"] for item in data])
    logging.info(f"Added {len(ids)} items to vector store")
    
    # Create search engine
    search_engine = EmbedderSearchEngine(embedder, vector_store)
    
    # Search example
    query = "What is a sugar found in milk?"
    results = search_engine.search(query, k=2)
    
    # Display results
    logging.info(f"Search query: '{query}'")
    for i, result in enumerate(results):
        logging.info(f"Result {i+1}:")
        logging.info(f"  ID: {result['id']}")
        logging.info(f"  Name: {result['metadata']['name']}")
        logging.info(f"  Similarity: {result['similarity']:.4f}")
        logging.info(f"  Formula: {result['metadata']['formula']}")
    
    # Filtered search example (additional Qdrant capability)
    filtered_results = vector_store.filter_search(
        query_vector=embedder.embed_single(query),
        filter_conditions={"source": "chebi"},
        k=2
    )
    
    logging.info("\nFiltered search results:")
    for i, result in enumerate(filtered_results):
        logging.info(f"Result {i+1}:")
        logging.info(f"  ID: {result['id']}")
        logging.info(f"  Name: {result['metadata']['name']}")
        logging.info(f"  Similarity: {result['similarity']:.4f}")
    
    # Create index for faster filtering (Qdrant-specific feature)
    vector_store.create_payload_index("name")
    logging.info("Created payload index on 'name' field")
    
    # Get total count
    count = vector_store.get_total_count()
    logging.info(f"Total vectors in store: {count}")

if __name__ == "__main__":
    main()
