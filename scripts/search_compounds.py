"""Search compounds in the Chroma database."""

import chromadb
from pathlib import Path
from typing import List, Dict, Any

def get_synonyms(metadata: Dict[str, Any]) -> List[str]:
    """Extract synonyms from metadata, handling both string and list formats."""
    synonyms = metadata.get('synonyms', [])
    if isinstance(synonyms, str):
        # Handle old format where synonyms are comma-separated string
        return [s.strip() for s in synonyms.split(',') if s.strip()]
    return synonyms

def main():
    # Initialize ChromaDB client
    chroma_path = Path("vector_store")
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Get the compounds collection
    collection = client.get_collection("compounds")
    
    # Search for glucose-related compounds using multiple queries
    queries = [
        "glucose d-glucose alpha-glucose beta-glucose dextrose",  # Common names
        "glucose monosaccharide hexose blood-sugar",             # Related terms
        "glucose metabolism glycolysis gluconeogenesis",         # Metabolic terms
    ]
    
    all_results = []
    for query in queries:
        results = collection.query(
            query_texts=[query],
            n_results=30,  # Get more results since we'll filter
            include=["documents", "metadatas"]
        )
        all_results.extend(zip(results['documents'][0], results['metadatas'][0]))
    
    # Deduplicate results
    seen = set()
    unique_results = []
    for doc, metadata in all_results:
        name = metadata.get('name', '')
        if name not in seen:
            seen.add(name)
            unique_results.append((doc, metadata))
    
    # Print results
    print("\nTop glucose-related compounds:")
    print("-" * 50)
    
    count = 0
    for doc, metadata in unique_results:
        name = metadata.get('name', '').lower()
        desc = doc.lower()
        synonyms = get_synonyms(metadata)
        
        # Check if glucose is prominently mentioned
        is_glucose_related = (
            'glucose' in name or
            any('glucose' in syn.lower() for syn in synonyms) or
            desc.startswith('glucose') or
            'glucose is' in desc.lower() or
            'glucose,' in desc.lower()
        )
        
        if is_glucose_related:
            count += 1
            print(f"\n{count}. HMDB ID: {metadata.get('hmdb_id', 'N/A')}")
            print(f"Name: {metadata.get('name', 'N/A')}")
            
            # Show glucose-related synonyms
            glucose_synonyms = [syn for syn in synonyms if 'glucose' in syn.lower()]
            if glucose_synonyms:
                print("Glucose-related synonyms:", ", ".join(glucose_synonyms))
            
            # Show start of description
            desc_preview = doc[:200] + "..." if len(doc) > 200 else doc
            print(f"Description: {desc_preview}")
            
        if count >= 10:  # Show at most 10 results
            break
            
    if count == 0:
        print("\nNo glucose-related compounds found.")
        print("Try adjusting the search terms or checking the database contents.")

if __name__ == "__main__":
    main()
