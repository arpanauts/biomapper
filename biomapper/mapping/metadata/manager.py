"""
Resource Metadata Manager for Biomapper.

This module provides the ResourceMetadataManager class, which is responsible
for managing resource metadata, including registration, queries, and updates.
"""

import sqlite3
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from biomapper.mapping.metadata.initialize import get_metadata_db_path

logger = logging.getLogger(__name__)

class ResourceMetadataManager:
    """
    Manager for resource metadata.
    
    This class provides methods for registering, querying, and updating
    resource metadata in the SQLite database.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the ResourceMetadataManager.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses the default path.
        """
        self.db_path = db_path or get_metadata_db_path()
        self.conn = None
        
    def connect(self) -> bool:
        """
        Connect to the metadata database.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Enable returning clause for better inserts
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception as e:
            logger.error(f"Error connecting to metadata database: {e}")
            return False
            
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
            
    def register_resource(
        self,
        name: str,
        resource_type: str,
        connection_info: Dict[str, Any],
        priority: int = 0
    ) -> Optional[int]:
        """
        Register a new resource or update an existing one.
        
        Args:
            name: Name of the resource
            resource_type: Type of resource (e.g., 'cache', 'graph', 'api')
            connection_info: Connection details as a dictionary
            priority: Priority of the resource (higher is more preferred)
            
        Returns:
            int: ID of the registered resource, or None if registration failed
        """
        if not self.conn and not self.connect():
            return None
            
        cursor = self.conn.cursor()
        resource_id = None
        
        try:
            # Check if resource already exists
            cursor.execute(
                "SELECT id FROM resource_metadata WHERE resource_name = ?",
                (name,)
            )
            existing = cursor.fetchone()
            
            # Convert connection_info to JSON
            connection_info_json = json.dumps(connection_info)
            
            if existing:
                # Update existing resource
                cursor.execute(
                    """
                    UPDATE resource_metadata
                    SET resource_type = ?, connection_info = ?, priority = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE resource_name = ?
                    """,
                    (resource_type, connection_info_json, priority, name)
                )
                resource_id = existing[0]
                logger.info(f"Updated resource {name} (ID: {resource_id})")
            else:
                # Create new resource
                cursor.execute(
                    """
                    INSERT INTO resource_metadata
                    (resource_name, resource_type, connection_info, priority)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, resource_type, connection_info_json, priority)
                )
                resource_id = cursor.lastrowid
                logger.info(f"Registered new resource {name} (ID: {resource_id})")
                
            self.conn.commit()
            return resource_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error registering resource {name}: {e}")
            return None
            
    def register_ontology_coverage(
        self,
        resource_name: str,
        ontology_type: str,
        support_level: str,
        entity_count: Optional[int] = None
    ) -> bool:
        """
        Register ontology coverage for a resource.
        
        Args:
            resource_name: Name of the resource
            ontology_type: Type of ontology (e.g., 'chebi', 'hmdb')
            support_level: Level of support ('full', 'partial', 'none')
            entity_count: Approximate count of entities, if available
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        if not self.conn and not self.connect():
            return False
            
        cursor = self.conn.cursor()
        
        try:
            # Get resource ID
            cursor.execute(
                "SELECT id FROM resource_metadata WHERE resource_name = ?",
                (resource_name,)
            )
            resource = cursor.fetchone()
            
            if not resource:
                logger.error(f"Resource {resource_name} not found")
                return False
                
            resource_id = resource[0]
            
            # Check if coverage already exists
            cursor.execute(
                """
                SELECT id FROM ontology_coverage
                WHERE resource_id = ? AND ontology_type = ?
                """,
                (resource_id, ontology_type)
            )
            coverage = cursor.fetchone()
            
            if coverage:
                # Update existing coverage
                cursor.execute(
                    """
                    UPDATE ontology_coverage
                    SET support_level = ?, entity_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE resource_id = ? AND ontology_type = ?
                    """,
                    (support_level, entity_count, resource_id, ontology_type)
                )
                logger.info(f"Updated ontology coverage for {resource_name}: {ontology_type}")
            else:
                # Create new coverage
                cursor.execute(
                    """
                    INSERT INTO ontology_coverage
                    (resource_id, ontology_type, support_level, entity_count, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (resource_id, ontology_type, support_level, entity_count)
                )
                logger.info(f"Added ontology coverage for {resource_name}: {ontology_type}")
                
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error registering ontology coverage: {e}")
            return False
            
    def update_performance_metrics(
        self,
        resource_name: str,
        operation_type: str,
        source_type: Optional[str],
        target_type: Optional[str],
        response_time_ms: int,
        success: bool
    ) -> bool:
        """
        Update performance metrics for a resource.
        
        Args:
            resource_name: Name of the resource
            operation_type: Type of operation ('lookup', 'map', etc.)
            source_type: Source ontology type, if applicable
            target_type: Target ontology type, if applicable
            response_time_ms: Response time in milliseconds
            success: Whether the operation was successful
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if not self.conn and not self.connect():
            return False
            
        cursor = self.conn.cursor()
        
        try:
            # Get resource ID
            cursor.execute(
                "SELECT id FROM resource_metadata WHERE resource_name = ?",
                (resource_name,)
            )
            resource = cursor.fetchone()
            
            if not resource:
                logger.error(f"Resource {resource_name} not found")
                return False
                
            resource_id = resource[0]
            
            # Check if metrics already exist
            cursor.execute(
                """
                SELECT id, avg_response_time_ms, success_rate, sample_count
                FROM performance_metrics
                WHERE resource_id = ? AND operation_type = ? 
                  AND (source_type = ? OR (source_type IS NULL AND ? IS NULL))
                  AND (target_type = ? OR (target_type IS NULL AND ? IS NULL))
                """,
                (resource_id, operation_type, source_type, source_type, 
                 target_type, target_type)
            )
            metrics = cursor.fetchone()
            
            # Add operation log
            cursor.execute(
                """
                INSERT INTO operation_logs
                (resource_id, operation_type, source_type, target_type, 
                 response_time_ms, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (resource_id, operation_type, source_type, target_type, 
                 response_time_ms, "success" if success else "failure")
            )
            
            if metrics:
                # Update existing metrics with exponential moving average
                metrics_id = metrics[0]
                avg_time = metrics[1]
                success_rate = metrics[2]
                sample_count = metrics[3]
                
                # Update with 10% weight for new data
                weight = 0.1
                new_avg_time = (1 - weight) * avg_time + weight * response_time_ms
                new_success_rate = (1 - weight) * success_rate + weight * (1.0 if success else 0.0)
                new_sample_count = sample_count + 1
                
                cursor.execute(
                    """
                    UPDATE performance_metrics
                    SET avg_response_time_ms = ?, success_rate = ?, 
                        sample_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_avg_time, new_success_rate, new_sample_count, metrics_id)
                )
            else:
                # Create new metrics
                cursor.execute(
                    """
                    INSERT INTO performance_metrics
                    (resource_id, operation_type, source_type, target_type,
                     avg_response_time_ms, success_rate, sample_count, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """,
                    (resource_id, operation_type, source_type, target_type,
                     response_time_ms, 1.0 if success else 0.0)
                )
                
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating performance metrics: {e}")
            return False
            
    def get_resources_by_priority(
        self, 
        source_type: Optional[str] = None, 
        target_type: Optional[str] = None,
        operation_type: str = "map"
    ) -> List[Dict[str, Any]]:
        """
        Get resources ordered by priority for the given operation.
        
        Args:
            source_type: Source ontology type, if applicable
            target_type: Target ontology type, if applicable
            operation_type: Type of operation
            
        Returns:
            List of resources with their priority and performance metrics
        """
        if not self.conn and not self.connect():
            return []
            
        cursor = self.conn.cursor()
        
        try:
            query_parts = [
                """
                SELECT r.id, r.resource_name, r.resource_type, r.priority,
                       r.connection_info, pm.avg_response_time_ms, pm.success_rate
                FROM resource_metadata r
                """
            ]
            params = []
            
            # Add joins for source and target types if specified
            if source_type:
                query_parts.append("""
                LEFT JOIN ontology_coverage source_oc 
                ON r.id = source_oc.resource_id AND source_oc.ontology_type = ?
                """)
                params.append(source_type)
                
            if target_type:
                query_parts.append("""
                LEFT JOIN ontology_coverage target_oc 
                ON r.id = target_oc.resource_id AND target_oc.ontology_type = ?
                """)
                params.append(target_type)
                
            query_parts.append("""
            LEFT JOIN performance_metrics pm ON r.id = pm.resource_id 
            AND pm.operation_type = ?
            """)
            params.append(operation_type)
            
            if source_type:
                query_parts.append("AND (pm.source_type = ? OR pm.source_type IS NULL)")
                params.append(source_type)
                
            if target_type:
                query_parts.append("AND (pm.target_type = ? OR pm.target_type IS NULL)")
                params.append(target_type)
                
            query_parts.append("WHERE r.is_active = 1")
            
            # Filter by ontology coverage if specified
            conditions = []
            if source_type:
                conditions.append("(source_oc.id IS NULL OR source_oc.support_level != 'none')")
            if target_type:
                conditions.append("(target_oc.id IS NULL OR target_oc.support_level != 'none')")
                
            if conditions:
                query_parts.append("AND " + " AND ".join(conditions))
                
            # Order by priority and performance
            query_parts.append("""
            ORDER BY 
                r.priority DESC,
                IFNULL(pm.success_rate, 0) DESC,
                IFNULL(pm.avg_response_time_ms, 10000) ASC
            """)
            
            query = " ".join(query_parts)
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                connection_info = {}
                if row[4]:  # connection_info
                    try:
                        connection_info = json.loads(row[4])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in connection_info for resource {row[1]}")
                
                results.append({
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "priority": row[3],
                    "connection_info": connection_info,
                    "avg_response_time_ms": row[5],
                    "success_rate": row[6]
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting resources by priority: {e}")
            return []
            
    def get_resource_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a resource by name.
        
        Args:
            name: Name of the resource
            
        Returns:
            Resource information, or None if not found
        """
        if not self.conn and not self.connect():
            return None
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT id, resource_name, resource_type, connection_info, priority
                FROM resource_metadata
                WHERE resource_name = ?
                """,
                (name,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
                
            connection_info = {}
            if row[3]:  # connection_info
                try:
                    connection_info = json.loads(row[3])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in connection_info for resource {row[1]}")
                    
            return {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "connection_info": connection_info,
                "priority": row[4]
            }
            
        except Exception as e:
            logger.error(f"Error getting resource by name: {e}")
            return None
            
    def get_ontology_coverage(self, resource_name: str) -> Dict[str, str]:
        """
        Get ontology coverage for a resource.
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Dictionary mapping ontology types to support levels
        """
        if not self.conn and not self.connect():
            return {}
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT oc.ontology_type, oc.support_level
                FROM ontology_coverage oc
                JOIN resource_metadata r ON oc.resource_id = r.id
                WHERE r.resource_name = ?
                """,
                (resource_name,)
            )
            
            return {row[0]: row[1] for row in cursor.fetchall()}
            
        except Exception as e:
            logger.error(f"Error getting ontology coverage: {e}")
            return {}
            
    def get_performance_summary(
        self, 
        resource_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance summary for resources.
        
        Args:
            resource_name: Name of the resource, or None for all resources
            
        Returns:
            List of performance summaries
        """
        if not self.conn and not self.connect():
            return []
            
        cursor = self.conn.cursor()
        
        try:
            query = """
            SELECT r.resource_name, pm.operation_type, pm.source_type, 
                   pm.target_type, pm.avg_response_time_ms, pm.success_rate, 
                   pm.sample_count, pm.last_updated
            FROM performance_metrics pm
            JOIN resource_metadata r ON pm.resource_id = r.id
            """
            params = []
            
            if resource_name:
                query += " WHERE r.resource_name = ?"
                params.append(resource_name)
                
            query += " ORDER BY pm.avg_response_time_ms ASC"
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "resource_name": row[0],
                    "operation_type": row[1],
                    "source_type": row[2],
                    "target_type": row[3],
                    "avg_response_time_ms": row[4],
                    "success_rate": row[5],
                    "sample_count": row[6],
                    "last_updated": row[7]
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return []
