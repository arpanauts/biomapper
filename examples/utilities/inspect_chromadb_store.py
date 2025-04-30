#!/usr/bin/env python3
"""Script to inspect the ChromaDB vector store."""

import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
client = chromadb.PersistentClient(
    path="/home/ubuntu/biomapper/vector_store", settings=Settings(allow_reset=True)
)

# Get the compounds collection
collection = client.get_collection("compounds")

# Get collection info
count = collection.count()
print(f"\nCollection 'compounds' contains {count} documents")

# Get a few example documents to verify content
if count > 0:
    print("\nExample documents:")
    results = collection.get(limit=5)
    for i, (id, metadata) in enumerate(zip(results["ids"], results["metadatas"])):
        print(f"\nDocument {i+1}:")
        print(f"  ID: {id}")
        print(f"  Metadata: {metadata}")
