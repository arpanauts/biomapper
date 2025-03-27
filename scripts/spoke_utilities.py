#!/usr/bin/env python
"""
SPOKE Knowledge Graph Utilities

This module provides utility functions for working with the SPOKE knowledge graph,
including database exploration, schema extraction, and configuration generation.
These utilities support Biomapper's generalized knowledge graph architecture.
"""

import asyncio
import json
import os
import time
import yaml
import argparse
from typing import Dict, List, Set, Any, Optional, Tuple

from arango import ArangoClient

from biomapper.spoke.default_schema import get_default_schema_mapping, create_spoke_config


def list_arango_databases(
    host: str = "localhost",
    port: int = 8529,
    username: str = "root",
    password: str = "ph"
) -> List[str]:
    """List available ArangoDB databases.
    
    Args:
        host: ArangoDB host
        port: ArangoDB port
        username: Database username
        password: Database password
        
    Returns:
        List of database names
    """
    print(f"Connecting to ArangoDB at http://{host}:{port}")
    client = ArangoClient(hosts=f"http://{host}:{port}")
    
    try:
        # Connect to _system database which always exists
        sys_db = client.db("_system", username=username, password=password)
        print("Connected to _system database")
        
        # List all databases
        databases = sys_db.databases()
        print("\nAvailable databases:")
        for db in databases:
            print(f"- {db}")
        
        # Check if we can access each database
        print("\nChecking database accessibility:")
        for db_name in databases:
            try:
                db = client.db(db_name, username=username, password=password)
                collections = [c['name'] for c in db.collections() if not c['name'].startswith('_')]
                print(f"- {db_name}: {len(collections)} collections")
                # Print a few collections as examples
                if collections:
                    print(f"  Example collections: {', '.join(collections[:5])}")
                    if len(collections) > 5:
                        print(f"  ...and {len(collections) - 5} more")
            except Exception as e:
                print(f"- {db_name}: ERROR - {str(e)}")
        
        return databases
        
    except Exception as e:
        print(f"Error connecting to ArangoDB: {str(e)}")
        return []


def check_database_connection(
    host: str,
    port: int,
    database: str,
    username: str = "root",
    password: str = "ph"
) -> Dict[str, Any]:
    """Check connection to a specific ArangoDB database.
    
    Args:
        host: ArangoDB host
        port: ArangoDB port
        database: Database name
        username: Database username
        password: Database password
        
    Returns:
        Connection status information
    """
    # Step 1: Basic connection
    print(f"Checking connection to {database} at http://{host}:{port}...")
    client = ArangoClient(hosts=f"http://{host}:{port}")
    
    result = {
        "success": False,
        "host": host,
        "port": port,
        "database": database,
        "collections": [],
        "collections_count": 0,
        "nodes_collection": None,
        "edges_collection": None,
        "nodes_sample": None,
        "edges_sample": None,
        "node_types": [],
        "relationship_types": []
    }
    
    try:
        # Try to connect to the specified database
        db = client.db(database, username=username, password=password)
        print(f"✓ Successfully connected to database '{database}'")
        result["success"] = True
        
        # Step 2: List all collections
        print("Listing collections...")
        collections = db.collections()
        doc_collections = [c for c in collections if c['type'] == 2]
        edge_collections = [c for c in collections if c['type'] == 3]
        
        result["collections"] = [c['name'] for c in collections]
        result["collections_count"] = len(collections)
        
        print(f"✓ Found {len(collections)} collections:")
        print(f"  - {len(doc_collections)} document collections")
        print(f"  - {len(edge_collections)} edge collections")
        
        for c in collections:
            try:
                collection_info = db.collection(c['name'])
                count = collection_info.count()
                print(f"  - {c['name']}: {count:,} documents")
            except Exception as e:
                print(f"  - {c['name']}: Error getting count - {str(e)}")
        
        # Step 3: Check for Nodes and Edges collections
        if 'Nodes' in [c['name'] for c in collections]:
            print("✓ Found 'Nodes' collection")
            result["nodes_collection"] = "Nodes"
            
            # Sample a node
            try:
                cursor = db.aql.execute("FOR doc IN Nodes LIMIT 1 RETURN doc", batch_size=1)
                first_node = next(cursor, None)
                if first_node:
                    result["nodes_sample"] = first_node
                    print(f"✓ Successfully sampled a node with keys: {', '.join(first_node.keys())}")
                    
                    # Try to get node types if time allows
                    try:
                        start_time = time.time()
                        cursor = db.aql.execute(
                            "FOR doc IN Nodes COLLECT type = doc.type RETURN type",
                            batch_size=100
                        )
                        node_types = list(cursor)
                        result["node_types"] = node_types
                        print(f"✓ Found {len(node_types)} node types in {time.time() - start_time:.1f}s")
                    except Exception as e:
                        print(f"× Error retrieving node types: {str(e)}")
            except Exception as e:
                print(f"× Error sampling node: {str(e)}")
        
        if 'Edges' in [c['name'] for c in collections]:
            print("✓ Found 'Edges' collection")
            result["edges_collection"] = "Edges"
            
            # Sample an edge
            try:
                cursor = db.aql.execute("FOR edge IN Edges LIMIT 1 RETURN edge", batch_size=1)
                first_edge = next(cursor, None)
                if first_edge:
                    result["edges_sample"] = first_edge
                    print(f"✓ Successfully sampled an edge with keys: {', '.join(first_edge.keys())}")
                    
                    # Try to get relationship types if time allows
                    try:
                        start_time = time.time()
                        cursor = db.aql.execute(
                            "FOR edge IN Edges COLLECT label = edge.label RETURN label",
                            batch_size=100
                        )
                        relationship_types = list(cursor)
                        result["relationship_types"] = relationship_types
                        print(f"✓ Found {len(relationship_types)} relationship types in {time.time() - start_time:.1f}s")
                    except Exception as e:
                        print(f"× Error retrieving relationship types: {str(e)}")
            except Exception as e:
                print(f"× Error sampling edge: {str(e)}")
        
        return result
    
    except Exception as e:
        print(f"× Error connecting to database: {str(e)}")
        return result


def generate_config_for_spoke(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    use_ssl: bool = False,
    output_file: str = None
) -> Dict[str, Any]:
    """Generate configuration for SPOKE using default schema mapping.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        use_ssl: Use SSL for connection
        output_file: Output file path
        
    Returns:
        Generated configuration
    """
    # Check database connection first
    connection_info = check_database_connection(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )
    
    if not connection_info["success"]:
        print(f"Failed to connect to SPOKE database. Using default schema only.")
    
    # Create configuration using default schema
    config = create_spoke_config(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        use_ssl=use_ssl
    )
    
    # Save to file if requested
    if output_file:
        if output_file.endswith('.json'):
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)
        else:  # Default to YAML
            with open(output_file, 'w') as f:
                yaml.dump(config, f, sort_keys=False)
        print(f"SPOKE configuration saved to {output_file}")
    
    return config


def main():
    """Main command-line interface for SPOKE utilities."""
    parser = argparse.ArgumentParser(
        description="SPOKE Knowledge Graph Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all available ArangoDB databases:
    python spoke_utilities.py list-dbs

  Check connection to SPOKE database:
    python spoke_utilities.py check-db --database spokeV6

  Generate configuration for SPOKE:
    python spoke_utilities.py generate-config --database spokeV6 --output spoke_config.yaml
        """
    )
    
    # Common arguments
    parser.add_argument("--host", default="localhost", help="ArangoDB host")
    parser.add_argument("--port", type=int, default=8529, help="ArangoDB port")
    parser.add_argument("--username", default="root", help="Database username")
    parser.add_argument("--password", default="ph", help="Database password")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List databases command
    list_db_parser = subparsers.add_parser("list-dbs", help="List available ArangoDB databases")
    
    # Check database connection command
    check_db_parser = subparsers.add_parser("check-db", help="Check connection to a specific database")
    check_db_parser.add_argument("--database", required=True, help="Database name")
    
    # Generate configuration command
    config_parser = subparsers.add_parser("generate-config", help="Generate configuration for SPOKE")
    config_parser.add_argument("--database", required=True, help="Database name")
    config_parser.add_argument("--use-ssl", action="store_true", help="Use SSL for connection")
    config_parser.add_argument("--output", help="Output file path (JSON or YAML)")
    
    args = parser.parse_args()
    
    if args.command == "list-dbs":
        list_arango_databases(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password
        )
    
    elif args.command == "check-db":
        check_database_connection(
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password
        )
    
    elif args.command == "generate-config":
        generate_config_for_spoke(
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password,
            use_ssl=args.use_ssl,
            output_file=args.output
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
