"""Script to verify ChromaDB store and display its contents."""

import chromadb
from chromadb.config import Settings


def main():
    # Initialize ChromaDB with persistent storage
    client = chromadb.PersistentClient(
        path="/home/ubuntu/biomapper/vector_store", settings=Settings(allow_reset=True)
    )

    # List all collections
    print("\nAvailable collections:")
    print("-" * 50)
    collections = client.list_collections()

    if not collections:
        print("No collections found in the database.")
        return

    for collection_name in collections:
        collection = client.get_collection(name=collection_name)
        print(f"\nCollection name: {collection_name}")
        count = collection.count()
        print(f"Collection count: {count}")

        # Get a sample of documents if collection is not empty
        if count > 0:
            results = collection.get(limit=3)
            print("\nSample document metadata:")
            print("-" * 30)
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    print(metadata)

            print("\nSample document IDs:")
            print("-" * 30)
            if results["ids"]:
                for id in results["ids"]:
                    print(id)

            print("\nSample embeddings shape:")
            print("-" * 30)
            if results["embeddings"]:
                print(f"Number of embeddings: {len(results['embeddings'])}")
                print(f"Embedding dimension: {len(results['embeddings'][0])}")


if __name__ == "__main__":
    main()
