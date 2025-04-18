"""
Relationship Mapping Executor Module.

This module implements the RelationshipMappingExecutor class for executing
mapping operations between endpoints using discovered relationship paths.
"""

# No external imports needed

# Import needed modules
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class RelationshipMappingExecutor:
    """Executes mappings between endpoints using relationship mapping paths."""
    
    def __init__(self, db_connection=None):
        """
        Initialize the relationship mapping executor.
        
        Args:
            db_connection: Database connection to use. If None, a new connection will be created.
        """
        if db_connection is None:
            db_path = '/home/ubuntu/biomapper/data/metamapper.db'
            self.db_connection = sqlite3.connect(db_path)
            self.db_connection.row_factory = sqlite3.Row
        else:
            self.db_connection = db_connection
        self.cursor = self.db_connection.cursor()
        # For testing, we'll implement a simple executor method directly
        # rather than using the actual MetamappingEngine which requires a dispatcher
    
    async def map_entity(self, relationship_id: int, source_entity: str, 
                        source_ontology: Optional[str] = None, 
                        confidence_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Map an entity using the best available relationship path.
        
        Args:
            relationship_id: ID of the relationship to use
            source_entity: Source entity identifier
            source_ontology: Source ontology type (if None, uses endpoint's highest preference)
            confidence_threshold: Minimum confidence for results
            
        Returns:
            List of mapping results
        """
        # If source ontology not specified, use endpoint's highest preference
        if not source_ontology:
            source_ontology = self._get_default_source_ontology(relationship_id)
            logger.info(f"Using default source ontology: {source_ontology}")
        
        # Get the best mapping path for this relationship and ontology
        path_info = self._get_best_relationship_path(relationship_id, source_ontology)
        
        if not path_info:
            logger.warning(f"No mapping path found for relationship {relationship_id} from {source_ontology}")
            return []
        
        # Get the underlying ontology mapping path
        ontology_path = self._get_ontology_path(path_info["ontology_path_id"])
        
        if not ontology_path:
            logger.warning(f"Ontology path {path_info['ontology_path_id']} not found")
            return []
        
        # Execute the mapping using the ontology path
        logger.info(f"Executing mapping for {source_entity} using path: {source_ontology} -> {path_info['target_ontology']}")
        
        try:
            # Parse the path steps
            path_steps = ontology_path["path_steps"]
            
            # For now, we'll simulate the execution with a simple logging message
            # In a real implementation, this would use the metamapping engine
            logger.info(f"Executing mapping with steps: {path_steps}")
            
            # Simulated results for testing
            results = [
                {
                    "source_id": source_entity,
                    "source_type": source_ontology,
                    "target_id": f"mapped_{source_entity}",
                    "target_type": path_info["target_ontology"],
                    "confidence": 0.95,
                    "path": path_info["ontology_path_id"]
                }
            ]
            
            # Update usage statistics
            self._update_path_usage(path_info["id"])
            
            return results
        except Exception as e:
            logger.error(f"Error executing mapping: {e}")
            return []
    
    async def map_from_endpoint_data(self, relationship_id: int, 
                                   source_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map directly from endpoint data by extracting properties first.
        
        Args:
            relationship_id: ID of the relationship to use
            source_data: Source data from the endpoint
            
        Returns:
            List of mapping results
        """
        # Get the source endpoint
        source_endpoint = self._get_source_endpoint(relationship_id)
        
        if not source_endpoint:
            logger.warning(f"Source endpoint not found for relationship {relationship_id}")
            return []
        
        # Get ordered ontology preferences for source endpoint
        preferences = self._get_ontology_preferences(source_endpoint["endpoint_id"])
        
        # Try each preference in order
        for ont_type, _ in preferences:
            try:
                # Extract the property from source data
                # This is a simplified implementation - in reality, would use property extractors
                source_id = self._extract_property_from_data(
                    source_data, ont_type, source_endpoint["endpoint_id"]
                )
                
                if source_id:
                    logger.info(f"Extracted {ont_type} ID: {source_id}")
                    
                    # Use the extracted ID to perform mapping
                    return await self.map_entity(
                        relationship_id=relationship_id,
                        source_entity=source_id,
                        source_ontology=ont_type
                    )
            except Exception as e:
                # Log and continue to next preference
                logger.warning(f"Failed to extract/map {ont_type}: {e}")
        
        # If we get here, all preferences failed
        logger.warning("Failed to extract/map using any ontology preference")
        return []
    
    def _extract_property_from_data(self, data: Dict[str, Any], 
                                  ontology_type: str, 
                                  endpoint_id: int) -> Optional[str]:
        """
        Extract a property from endpoint data.
        
        This is a simplified implementation. In a real system, you would use
        the property extraction configurations from the database.
        """
        # Simple mapping of ontology types to common field names
        field_mapping = {
            "hmdb": ["HMDB", "hmdb", "hmdb_id"],
            "chebi": ["CHEBI", "chebi", "chebi_id"],
            "pubchem": ["PUBCHEM", "pubchem", "pubchem_id"],
            "kegg": ["KEGG", "kegg", "kegg_id"],
            "inchikey": ["INCHIKEY", "inchikey", "inchi_key"],
            "cas": ["CAS", "cas", "cas_id"],
            "name": ["BIOCHEMICAL_NAME", "name", "compound_name"]
        }
        
        # Try each possible field name
        for field in field_mapping.get(ontology_type.lower(), []):
            if field in data and data[field]:
                return data[field]
        
        return None
    
    def _get_default_source_ontology(self, relationship_id: int) -> str:
        """Get the default (highest preference) source ontology for a relationship."""
        try:
            # Get the source endpoint
            source_endpoint = self._get_source_endpoint(relationship_id)
            
            if not source_endpoint:
                return "hmdb"  # Fallback default
            
            # Get the highest preference ontology
            preferences = self._get_ontology_preferences(source_endpoint["endpoint_id"])
            
            if preferences:
                return preferences[0][0]  # First item, first element (ontology_type)
            
            return "hmdb"  # Fallback default
        except Exception as e:
            logger.error(f"Error getting default source ontology: {e}")
            return "hmdb"  # Fallback default
    
    def _get_best_relationship_path(self, relationship_id: int, 
                                  source_ontology: str) -> Optional[Dict[str, Any]]:
        """Get the best mapping path for a relationship and source ontology."""
        try:
            self.cursor.execute("""
                SELECT id, relationship_id, source_ontology, target_ontology, 
                       ontology_path_id, performance_score
                FROM relationship_mapping_paths
                WHERE relationship_id = ?
                AND LOWER(source_ontology) = LOWER(?)
                ORDER BY performance_score DESC
                LIMIT 1
            """ , (relationship_id, source_ontology))
            row = self.cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "relationship_id": row[1],
                    "source_ontology": row[2],
                    "target_ontology": row[3],
                    "ontology_path_id": row[4],
                    "performance_score": row[5]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting best relationship path: {e}")
            return None
    
    def _get_ontology_path(self, path_id: int) -> Optional[Dict[str, Any]]:
        """Get ontology mapping path by ID."""
        try:
            self.cursor.execute("""
                SELECT id, source_type, target_type, path_steps, performance_score
                FROM mapping_paths
                WHERE id = ?
            """ , (path_id,))
            row = self.cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "source_type": row[1],
                    "target_type": row[2],
                    "path_steps": json.loads(row[3]),
                    "performance_score": row[4]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting ontology path: {e}")
            return None
    
    def _update_path_usage(self, path_id: int) -> bool:
        """Update usage statistics for a path."""
        try:
            self.cursor.execute("""
                UPDATE relationship_mapping_paths
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE id = ?
            """ , (datetime.now().isoformat(), path_id))
            
            self.db_connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating path usage: {e}")
            self.db_connection.rollback()
            return False
    
    def _get_source_endpoint(self, relationship_id: int) -> Optional[Dict[str, Any]]:
        """Get the source endpoint for a relationship."""
        try:
            self.cursor.execute("""
                SELECT e.endpoint_id, e.name, e.description, e.type, e.config
                FROM endpoints e
                JOIN endpoint_relationship_members m ON e.endpoint_id = m.endpoint_id
                WHERE m.relationship_id = ?
                AND m.role = 'source'
            """ , (relationship_id,))
            row = self.cursor.fetchone()
            
            if row:
                return {
                    "endpoint_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "type": row[3],
                    "config": row[4]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting source endpoint: {e}")
            return None
    
    def _get_ontology_preferences(self, endpoint_id: int) -> List[Any]:
        """Get ordered ontology preferences for an endpoint."""
        try:
            self.cursor.execute("""
                SELECT ontology_type, preference_level
                FROM endpoint_ontology_preferences
                WHERE endpoint_id = ?
                ORDER BY preference_level ASC
            """ , (endpoint_id,))
            rows = self.cursor.fetchall()
            
            return [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"Error getting ontology preferences: {e}")
            return []
