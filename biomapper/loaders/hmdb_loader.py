from pathlib import Path
from typing import Any
import logging
import chromadb
from sentence_transformers import SentenceTransformer

from ..processors.hmdb import HMDBProcessor
from ..schemas.metabolite_schema import MetaboliteDocument

logger = logging.getLogger(__name__)


class HMDBLoader:
    """Load HMDB metabolites into Chroma database."""

    client: Any  # Type hint as Any due to ChromaDB's incomplete type hints
    collection: Any  # Type hint as Any due to ChromaDB's incomplete type hints
    model: SentenceTransformer
    batch_size: int

    def __init__(
        self,
        chroma_path: str,
        collection_name: str = "compounds",
        embedding_model: str = "all-MiniLM-L6-v2",
        batch_size: int = 100,
    ) -> None:
        """Initialize the loader.

        Args:
            chroma_path: Path to Chroma database
            collection_name: Name of collection to store compounds in
            embedding_model: Name of sentence-transformer model to use
            batch_size: Number of compounds to process at once
        """
        logger.info(f"Initializing loader with database at {chroma_path}")
        self.client = chromadb.Client(chromadb.Settings(persist_directory=chroma_path))
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except ValueError:
            self.collection = self.client.create_collection(name=collection_name)
        self.model = SentenceTransformer(embedding_model)
        self.batch_size = batch_size
        logger.info(f"Using embedding model: {embedding_model}")

    async def load_file(self, xml_path: Path) -> None:
        """Load HMDB metabolites from XML file into vector store.

        Args:
            xml_path: Path to HMDB metabolites XML file
        """
        logger.info(f"Starting to load compounds from {xml_path}")

        # Clear existing data by recreating the collection
        logger.info("Clearing existing collection...")
        collection_name = self.collection.name
        try:
            self.client.reset()
            self.collection = self.client.create_collection(name=collection_name)
        except ValueError:
            # Collection might not exist yet
            pass

        processor = HMDBProcessor(xml_path)

        total_processed = 0
        total_errors = 0
        async for batch in processor.process_batch(self.batch_size):
            try:
                # Convert to MetaboliteDocument
                metabolites = [
                    doc for doc in batch if isinstance(doc, MetaboliteDocument)
                ]

                if metabolites:
                    # Extract IDs and generate search texts
                    ids = [doc.hmdb_id for doc in metabolites]
                    texts = [doc.to_search_text() for doc in metabolites]

                    # Generate embeddings
                    embeddings = self.model.encode(texts).tolist()

                    # Add documents to collection
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=[
                            {
                                "name": str(doc.name),
                                "synonyms": ", ".join(map(str, doc.synonyms)),
                                "description": str(doc.description or ""),
                            }
                            for doc in metabolites
                        ],
                    )

                    total_processed += len(metabolites)
                    logger.debug(f"Added batch of {len(metabolites)} compounds")

            except Exception as e:
                total_errors += 1
                logger.error(f"Error processing batch: {e}")

        logger.info(
            f"Finished loading compounds. Processed: {total_processed}, Errors: {total_errors}"
        )
