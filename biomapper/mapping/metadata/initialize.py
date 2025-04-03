"""
Database initialization for the Resource Metadata System.

This module provides functions to initialize the metadata database tables
and validate the database structure.
"""

import os
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def initialize_metadata_system(db_path: str) -> bool:
    """
    Initialize the metadata tables in the SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))
            
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create resource_metadata table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT NOT NULL UNIQUE,
            resource_type TEXT NOT NULL,
            connection_info TEXT,
            priority INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create ontology_coverage table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ontology_coverage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            ontology_type TEXT NOT NULL,
            support_level TEXT NOT NULL,
            entity_count INTEGER,
            last_updated TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resource_metadata(id),
            UNIQUE (resource_id, ontology_type)
        )
        ''')
        
        # Create performance_metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            source_type TEXT,
            target_type TEXT,
            avg_response_time_ms REAL,
            success_rate REAL,
            sample_count INTEGER,
            last_updated TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resource_metadata(id),
            UNIQUE (resource_id, operation_type, source_type, target_type)
        )
        ''')
        
        # Create operation_logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            source_type TEXT,
            target_type TEXT,
            query TEXT,
            response_time_ms INTEGER,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_id) REFERENCES resource_metadata(id)
        )
        ''')
        
        # Create index on operation_logs for faster analysis
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_operation_logs_resource
        ON operation_logs (resource_id, operation_type)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully initialized metadata system at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing metadata system: {e}")
        return False


def verify_metadata_schema(db_path: str) -> Optional[list]:
    """
    Verify that the metadata schema exists and is correctly structured.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        list: List of missing tables or columns, or None if all valid
    """
    required_tables = [
        "resource_metadata",
        "ontology_coverage",
        "performance_metrics",
        "operation_logs"
    ]
    
    missing = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check each required table
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                missing.append(f"Missing table: {table}")
                
        conn.close()
        
        return missing if missing else None
        
    except Exception as e:
        logger.error(f"Error verifying metadata schema: {e}")
        return [f"Error: {e}"]


def get_metadata_db_path() -> str:
    """
    Get the path to the metadata database, respecting environment variables.
    
    Returns:
        str: Path to the metadata database
    """
    # First check environment variable
    db_path = os.environ.get("BIOMAPPER_METADATA_DB")
    
    if db_path:
        return db_path
        
    # Default to the standard location
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, ".biomapper", "metadata.db")
