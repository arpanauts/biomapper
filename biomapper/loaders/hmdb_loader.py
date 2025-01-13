from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection
import asyncio
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from ..processors.hmdb import HMDBProcessor
from ..schemas.metabolite_schema import MetaboliteDocument

logger = logging.getLogger(__name__)

class HMDBLoader:
    """Load HMDB metabolites into Chroma database."""
    
    client: chromadb.PersistentClient
    collection: Collection
    model: SentenceTransformer
    batch_size: int
    
    def __init__(
        self,
        chroma_path: str,
        collection_name: str = "compounds",
        embedding_model: str = "all-MiniLM-L6-v2",
        batch_size: int = 100
    ) -> None:
        """Initialize the loader.
        
        Args:
            chroma_path: Path to Chroma database
            collection_name: Name of collection to store compounds in
            embedding_model: Name of sentence-transformer model to use
            batch_size: Number of compounds to process at once
        """
        logger.info(f"Initializing loader with database at {chroma_path}")
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.model = SentenceTransformer(embedding_model)
        self.batch_size = batch_size
        logger.info(f"Using embedding model: {embedding_model}")
    
    async def load_file(self, xml_path: Path) -> None:
        """Load compounds from HMDB XML file into Chroma.
        
        Args:
            xml_path: Path to HMDB metabolites XML file
        """
        logger.info(f"Starting to load compounds from {xml_path}")
        
        # Clear existing data by recreating the collection
        logger.info("Clearing existing collection...")
        collection_name = self.collection.name
        try:
            self.client.delete_collection(collection_name)
        except ValueError:
            # Collection might not exist yet
            pass
        self.collection = self.client.create_collection(name=collection_name)
        
        processor = HMDBProcessor(xml_path)
        total_processed = 0
        total_errors = 0
        
        try:
            async for batch in processor.process_batch(self.batch_size):
                try:
                    # Generate IDs and texts for embedding
                    ids = [doc.hmdb_id for doc in batch]
                    texts = [doc.to_search_text() for doc in batch]
                    
                    # Generate embeddings
                    embeddings = self.model.encode(texts).tolist()
                    
                    # Create metadata
                    metadatas: List[Dict[str, Any]] = [{
                        "hmdb_id": doc.hmdb_id,
                        "name": doc.name,
                        "synonyms": doc.synonyms,  
                        "description": doc.description or ""
                    } for doc in batch]
                    
                    # Add to collection
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        documents=texts
                    )
                    
                    total_processed += len(batch)
                    logger.debug(f"Added batch of {len(batch)} compounds")
                    
                except Exception as e:
                    total_errors += 1
                    logger.error(f"Error processing batch: {e}")
                    continue
            
            logger.info(f"Completed loading compounds:")
            logger.info(f"- Total processed: {total_processed}")
            logger.info(f"- Total errors: {total_errors}")
            
        except Exception as e:
            logger.error(f"Fatal error during loading: {e}")
            raise
