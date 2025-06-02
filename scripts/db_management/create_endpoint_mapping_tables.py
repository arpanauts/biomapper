#!/usr/bin/env python3
"""
Create endpoint mapping tables in the metamapper database.

This script directly applies the SQL schema changes needed for the endpoint-mapping architecture.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Default path to the SQLite database
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/metamapper.db")
print(f"Using database path: {os.path.abspath(DEFAULT_DB_PATH)}")


def connect_to_database(db_path=None):
    """Connect to the SQLite database."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_endpoint_tables(conn):
    """Create the endpoint-related tables."""
    cursor = conn.cursor()

    # Endpoints table - defines actual data sources (not mapping tools)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS endpoints (
        endpoint_id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        endpoint_type TEXT NOT NULL,
        connection_info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoints_name ON endpoints(name)
    """
    )

    print("Created endpoints table")


def create_mapping_resources_table(conn):
    """Create the mapping resources table."""
    cursor = conn.cursor()

    # Mapping Resources table - defines mapping tools/services (not data endpoints)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS mapping_resources (
        resource_id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        resource_type TEXT NOT NULL,
        connection_info TEXT,
        priority INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_mapping_resources_name ON mapping_resources(name)
    """
    )

    print("Created mapping_resources table")


def create_relationships_tables(conn):
    """Create the relationship-related tables."""
    cursor = conn.cursor()

    # Endpoint Relationships table - defines relationships between endpoints
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS endpoint_relationships (
        relationship_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoint_relationships_name ON endpoint_relationships(name)
    """
    )

    # Endpoint Relationship Members table - maps endpoints to relationships
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS endpoint_relationship_members (
        relationship_id INTEGER NOT NULL,
        endpoint_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        priority INTEGER,
        PRIMARY KEY (relationship_id, endpoint_id),
        FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id) ON DELETE CASCADE,
        FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoint_relationship_members_endpoint 
    ON endpoint_relationship_members(endpoint_id)
    """
    )

    print("Created relationship tables")


def create_ontology_tables(conn):
    """Create the ontology-related tables."""
    cursor = conn.cursor()

    # Endpoint Ontology Preferences table - defines preferred ontology types for endpoints
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS endpoint_ontology_preferences (
        endpoint_id INTEGER NOT NULL,
        ontology_type TEXT NOT NULL,
        preference_level INTEGER NOT NULL,
        PRIMARY KEY (endpoint_id, ontology_type),
        FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoint_ontology_preferences_endpoint 
    ON endpoint_ontology_preferences(endpoint_id)
    """
    )

    # Ontology Coverage table - maps which ontologies each mapping resource supports
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS ontology_coverage (
        resource_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,
        target_type TEXT NOT NULL,
        support_level TEXT NOT NULL,
        PRIMARY KEY (resource_id, source_type, target_type),
        FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id) ON DELETE CASCADE
    )
    """
    )

    # Create indexes for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_ontology_coverage_resource ON ontology_coverage(resource_id)
    """
    )

    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_ontology_coverage_types 
    ON ontology_coverage(source_type, target_type)
    """
    )

    print("Created ontology tables")


def create_performance_table(conn):
    """Create the performance metrics table."""
    cursor = conn.cursor()

    # Performance Metrics table - tracks success rates and response times for mapping resources
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS performance_metrics (
        metric_id INTEGER PRIMARY KEY,
        resource_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,
        target_type TEXT NOT NULL,
        success_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        avg_response_time REAL,
        last_updated TIMESTAMP,
        FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id) ON DELETE CASCADE
    )
    """
    )

    # Create indexes for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_performance_metrics_resource ON performance_metrics(resource_id)
    """
    )

    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_performance_metrics_types 
    ON performance_metrics(source_type, target_type)
    """
    )

    print("Created performance metrics table")


def create_property_configs_table(conn):
    """Create the endpoint property configs table."""
    cursor = conn.cursor()

    # Endpoint Property Configs table - defines how to extract specific properties from endpoints
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS endpoint_property_configs (
        config_id INTEGER PRIMARY KEY,
        endpoint_id INTEGER NOT NULL,
        ontology_type TEXT NOT NULL,
        property_name TEXT NOT NULL,
        extraction_method TEXT NOT NULL,
        extraction_pattern TEXT NOT NULL,
        transform_method TEXT,
        UNIQUE (endpoint_id, ontology_type, property_name),
        FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
    )
    """
    )

    # Create indexes for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoint_property_configs_endpoint 
    ON endpoint_property_configs(endpoint_id)
    """
    )

    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_endpoint_property_configs_ontology 
    ON endpoint_property_configs(ontology_type)
    """
    )

    print("Created endpoint property configs table")


def create_mapping_cache_tables(conn):
    """Create the mapping cache-related tables."""
    cursor = conn.cursor()

    # Mapping Cache table - stores results of mapping operations
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS mapping_cache (
        mapping_id INTEGER PRIMARY KEY,
        source_id TEXT NOT NULL,
        source_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        target_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        mapping_path TEXT,
        resource_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resource_id) REFERENCES mapping_resources(resource_id) ON DELETE SET NULL
    )
    """
    )

    # Create indexes for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_mapping_cache_source ON mapping_cache(source_id, source_type)
    """
    )

    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_mapping_cache_target ON mapping_cache(target_id, target_type)
    """
    )

    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_mapping_cache_lookup 
    ON mapping_cache(source_id, source_type, target_type)
    """
    )

    # Relationship Mappings table - links mapping cache entries to endpoint relationships
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS relationship_mappings (
        relationship_id INTEGER NOT NULL,
        mapping_id INTEGER NOT NULL,
        PRIMARY KEY (relationship_id, mapping_id),
        FOREIGN KEY (relationship_id) REFERENCES endpoint_relationships(relationship_id) ON DELETE CASCADE,
        FOREIGN KEY (mapping_id) REFERENCES mapping_cache(mapping_id) ON DELETE CASCADE
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_relationship_mappings_relationship 
    ON relationship_mappings(relationship_id)
    """
    )

    print("Created mapping cache tables")


def create_mapping_paths_table(conn):
    """Create the mapping paths table."""
    cursor = conn.cursor()

    # Mapping Paths table - stores discovered mapping paths between ontology types
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS mapping_paths (
        path_id INTEGER PRIMARY KEY,
        source_type TEXT NOT NULL,
        target_type TEXT NOT NULL,
        path_steps TEXT NOT NULL,
        confidence REAL NOT NULL,
        usage_count INTEGER DEFAULT 0,
        last_used TIMESTAMP,
        discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_mapping_paths_lookup ON mapping_paths(source_type, target_type)
    """
    )

    print("Created mapping paths table")


def main():
    """Main function to create the endpoint mapping tables."""
    print("Creating endpoint mapping tables...")

    conn = connect_to_database()

    try:
        # Create all tables in the correct order for foreign key constraints
        print("Calling create_endpoint_tables...")
        create_endpoint_tables(conn)
        print("Calling create_mapping_resources_table...")
        create_mapping_resources_table(conn)
        print("Calling create_relationships_tables...")
        create_relationships_tables(conn)
        print("Calling create_ontology_tables...")
        create_ontology_tables(conn)
        print("Calling create_performance_table...")
        create_performance_table(conn)
        print("Calling create_property_configs_table...")
        create_property_configs_table(conn)
        print("Calling create_mapping_cache_tables...")
        create_mapping_cache_tables(conn)
        print("Calling create_mapping_paths_table...")
        create_mapping_paths_table(conn)

        # Commit all changes
        conn.commit()
        print("All endpoint mapping tables created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
