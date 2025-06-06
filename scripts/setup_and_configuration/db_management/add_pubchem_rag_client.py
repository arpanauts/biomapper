#!/usr/bin/env python3
"""Add PubChemRAGMappingClient to the metamapper database."""

import sys
import sqlite3
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from biomapper.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_pubchem_rag_client():
    """Add PubChemRAGMappingClient to mapping_resources table."""
    
    # Use the direct path since we know where it is
    db_path = str(project_root / "data" / "metamapper.db")
    logger.info(f"Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if resource already exists
        cursor.execute(
            "SELECT id FROM mapping_resources WHERE name = ?",
            ("PubChem_RAG_Search",)
        )
        existing = cursor.fetchone()
        
        if existing:
            logger.info("PubChem_RAG_Search resource already exists. Updating...")
            cursor.execute("""
                UPDATE mapping_resources
                SET description = ?,
                    resource_type = ?,
                    client_class_path = ?,
                    input_ontology_term = ?,
                    output_ontology_term = ?,
                    config_template = ?
                WHERE name = ?
            """, (
                "PubChem RAG-based semantic search for metabolite name resolution using Qdrant vector database",
                "rag_client",
                "biomapper.mapping.clients.pubchem_rag_client.PubChemRAGMappingClient",
                "NAME",
                "PUBCHEM_CID",
                '{"qdrant_host": "localhost", "qdrant_port": 6333, "collection_name": "pubchem_bge_small_v1_5", "top_k": 5, "score_threshold": 0.7}',
                "PubChem_RAG_Search"
            ))
        else:
            logger.info("Adding new PubChem_RAG_Search resource...")
            cursor.execute("""
                INSERT INTO mapping_resources (
                    name, description, resource_type, client_class_path,
                    input_ontology_term, output_ontology_term, config_template
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "PubChem_RAG_Search",
                "PubChem RAG-based semantic search for metabolite name resolution using Qdrant vector database",
                "rag_client",
                "biomapper.mapping.clients.pubchem_rag_client.PubChemRAGMappingClient",
                "NAME",
                "PUBCHEM_CID",
                '{"qdrant_host": "localhost", "qdrant_port": 6333, "collection_name": "pubchem_bge_small_v1_5", "top_k": 5, "score_threshold": 0.7}'
            ))
        
        # Add mapping path steps if needed
        cursor.execute(
            "SELECT id FROM mapping_resources WHERE name = ?",
            ("PubChem_RAG_Search",)
        )
        resource_id = cursor.fetchone()[0]
        
        # Check if we need to create a mapping path
        cursor.execute("""
            SELECT id FROM mapping_paths 
            WHERE name = ? OR name = ?
        """, ("NAME -> PUBCHEM_CID (RAG)", "Metabolite Name to PubChem CID (RAG)"))
        
        path_exists = cursor.fetchone()
        
        if not path_exists:
            logger.info("Creating mapping path for RAG search...")
            cursor.execute("""
                INSERT INTO mapping_paths (
                    name, description, priority, source_type, target_type, is_active
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "Metabolite Name to PubChem CID (RAG)",
                "Semantic search for metabolite names using PubChem embeddings in Qdrant",
                50,  # Medium priority - use after direct lookups but before LLM
                "NAME",
                "PUBCHEM_CID",
                1    # Active
            ))
            path_id = cursor.lastrowid
            
            # Add the mapping step
            cursor.execute("""
                INSERT INTO mapping_path_steps (
                    mapping_path_id, step_order, mapping_resource_id, description
                ) VALUES (?, ?, ?, ?)
            """, (
                path_id,
                1,
                resource_id,
                "Use RAG semantic search to find PubChem CIDs"
            ))
            
            logger.info(f"Created mapping path with ID: {path_id}")
        else:
            logger.info("Mapping path already exists")
        
        conn.commit()
        logger.info("Successfully added/updated PubChem RAG client configuration")
        
    except Exception as e:
        logger.error(f"Error adding PubChem RAG client: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    add_pubchem_rag_client()