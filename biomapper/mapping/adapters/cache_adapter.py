"""
SQLite Cache Adapter implementation for Biomapper Resource Metadata System.

This module provides an adapter for interacting with the SQLite mapping cache,
following the ResourceAdapter protocol.
"""

import sqlite3
import time
import json
import logging
import os.path
import asyncio
from typing import Dict, List, Any, Optional

from biomapper.mapping.metadata.interfaces import BaseResourceAdapter

logger = logging.getLogger(__name__)


class CacheResourceAdapter(BaseResourceAdapter):
    """
    Adapter for the SQLite mapping cache.

    This adapter provides access to the mapping cache database,
    allowing for efficient lookup of previously seen mappings.
    """

    def __init__(self, config: Dict[str, Any], name: str = "sqlite_cache"):
        """
        Initialize the cache adapter.

        Args:
            config: Configuration dictionary with keys:
                - db_path: Path to SQLite database file
            name: Name of the resource (default: "sqlite_cache")
        """
        super().__init__(config, name)
        self.db_path = config.get("db_path")
        self.conn = None

    async def connect(self) -> bool:
        """
        Connect to the SQLite database.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            if not os.path.exists(self.db_path):
                logger.error(f"Database file does not exist: {self.db_path}")
                return False

            # SQLite connections should be created in the same thread they're used in
            # We'll create the connection in each method as needed
            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"Error connecting to SQLite cache: {e}")
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the SQLite database.

        Returns:
            sqlite3.Connection: Connection to the database
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Map an entity using the SQLite cache.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            **kwargs: Additional arguments (unused)

        Returns:
            List of mappings, each containing at least 'target_id' and 'confidence'
        """
        if not self.is_connected:
            await self.connect()

        # Execute in a thread to avoid blocking the event loop
        return await asyncio.to_thread(
            self._map_entity_sync, source_id, source_type, target_type
        )

    def _map_entity_sync(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """
        Synchronous implementation of map_entity.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type

        Returns:
            List of mappings, each containing at least 'target_id' and 'confidence'
        """
        start_time = time.time()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Direct mapping query
            cursor.execute(
                """
                SELECT target_id, confidence, source
                FROM entity_mappings
                WHERE source_id = ? AND source_type = ? AND target_type = ?
                ORDER BY confidence DESC
                """,
                (source_id, source_type, target_type),
            )

            direct_results = [
                {
                    "target_id": row["target_id"],
                    "confidence": row["confidence"],
                    "source": row["source"],
                }
                for row in cursor.fetchall()
            ]

            # If we have direct results, return them
            if direct_results:
                return direct_results

            # Try transitive mapping if no direct results
            # First, find mappings from source to intermediate
            cursor.execute(
                """
                SELECT DISTINCT target_type
                FROM entity_mappings
                WHERE source_id = ? AND source_type = ?
                """,
                (source_id, source_type),
            )

            intermediate_types = [row["target_type"] for row in cursor.fetchall()]

            # For each intermediate type, look for mappings to target
            transitive_results = []
            for intermediate_type in intermediate_types:
                # Get mappings from source to intermediate
                cursor.execute(
                    """
                    SELECT target_id, confidence, source
                    FROM entity_mappings
                    WHERE source_id = ? AND source_type = ? AND target_type = ?
                    ORDER BY confidence DESC
                    """,
                    (source_id, source_type, intermediate_type),
                )

                source_to_intermediate = [
                    {
                        "target_id": row["target_id"],
                        "confidence": row["confidence"],
                        "source": row["source"],
                    }
                    for row in cursor.fetchall()
                ]

                # For each intermediate ID, get mappings to target
                for intermediate in source_to_intermediate:
                    cursor.execute(
                        """
                        SELECT target_id, confidence, source
                        FROM entity_mappings
                        WHERE source_id = ? AND source_type = ? AND target_type = ?
                        ORDER BY confidence DESC
                        """,
                        (intermediate["target_id"], intermediate_type, target_type),
                    )

                    intermediate_to_target = [
                        {
                            "target_id": row["target_id"],
                            "confidence": row["confidence"]
                            * intermediate["confidence"],
                            "source": f"transitive:{intermediate['source']}>{row['source']}",
                            "via": {
                                "id": intermediate["target_id"],
                                "type": intermediate_type,
                            },
                        }
                        for row in cursor.fetchall()
                    ]

                    transitive_results.extend(intermediate_to_target)

            # Sort transitive results by confidence
            transitive_results.sort(key=lambda x: x["confidence"], reverse=True)

            return transitive_results

        except Exception as e:
            logger.error(f"Error in SQLite mapping: {e}")
            return []

        finally:
            conn.close()

    async def update_mappings(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        mappings: List[Dict[str, Any]],
    ) -> bool:
        """
        Update the cache with new mappings.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            mappings: List of mappings to add

        Returns:
            bool: True if update was successful, False otherwise
        """
        if not self.is_connected:
            await self.connect()

        # Execute in a thread to avoid blocking the event loop
        return await asyncio.to_thread(
            self._update_mappings_sync, source_id, source_type, target_type, mappings
        )

    def _update_mappings_sync(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        mappings: List[Dict[str, Any]],
    ) -> bool:
        """
        Synchronous implementation of update_mappings.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            mappings: List of mappings to add

        Returns:
            bool: True if update was successful, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            for mapping in mappings:
                target_id = mapping.get("target_id")
                confidence = mapping.get("confidence", 0.9)
                source = mapping.get("source", "unknown")

                if not target_id:
                    continue

                # Check if mapping already exists
                cursor.execute(
                    """
                    SELECT id, confidence
                    FROM entity_mappings
                    WHERE source_id = ? AND source_type = ? 
                      AND target_id = ? AND target_type = ?
                    """,
                    (source_id, source_type, target_id, target_type),
                )

                existing = cursor.fetchone()

                if existing:
                    # Update with higher confidence if applicable
                    if confidence > existing["confidence"]:
                        cursor.execute(
                            """
                            UPDATE entity_mappings
                            SET confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (confidence, source, existing["id"]),
                        )
                else:
                    # Insert new mapping
                    cursor.execute(
                        """
                        INSERT INTO entity_mappings
                        (source_id, source_type, target_id, target_type, confidence, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_id,
                            source_type,
                            target_id,
                            target_type,
                            confidence,
                            source,
                        ),
                    )

            # Commit transaction
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating mappings: {e}")
            return False

        finally:
            conn.close()

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this resource.

        Returns:
            Dictionary describing the resource's capabilities
        """
        return {
            "name": self.name,
            "type": "cache",
            "supports_batch": False,
            "supports_async": True,
            "max_batch_size": 1,
            "supports_transitive": True,
        }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this resource.

        Returns:
            Dictionary of performance metrics
        """
        if not self.is_connected:
            await self.connect()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Get mapping count
            cursor.execute("SELECT COUNT(*) as count FROM entity_mappings")
            mapping_count = cursor.fetchone()["count"]

            # Get source type count
            cursor.execute(
                "SELECT COUNT(DISTINCT source_type) as count FROM entity_mappings"
            )
            source_type_count = cursor.fetchone()["count"]

            # Get target type count
            cursor.execute(
                "SELECT COUNT(DISTINCT target_type) as count FROM entity_mappings"
            )
            target_type_count = cursor.fetchone()["count"]

            return {
                "mapping_count": mapping_count,
                "source_type_count": source_type_count,
                "target_type_count": target_type_count,
                "avg_response_time_ms": 5,  # Typical value for SQLite lookups
                "success_rate": 0.99,
                "sample_count": mapping_count,
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

        finally:
            conn.close()
