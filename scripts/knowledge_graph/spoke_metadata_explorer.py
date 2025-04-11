#!/usr/bin/env python
"""
SPOKE Metadata Explorer

This script provides focused exploration of SPOKE's structure
to identify the metadata needed for the Biomapper's mapping system.
It uses more targeted queries than the general analyzer to avoid timeouts.
"""

import sys
import json
import argparse
import time
from arango import ArangoClient
from typing import Dict, List, Any, Set, Optional

def explore_spoke_structure(
    host: str = "localhost",
    port: int = 8529,
    database: str = "spokeV6",
    username: str = "root",
    password: str = "ph",
    limit: int = 10,
):
    """Explore SPOKE's structure with focused queries.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        limit: Limit on sample sizes
    """
    print(f"Connecting to SPOKE at http://{host}:{port}, database: {database}")
    
    client = ArangoClient(hosts=f"http://{host}:{port}")
    db = client.db(database, username=username, password=password)
    
    # Check what collections exist
    collections = db.collections()
    document_collections = [c for c in collections if c['type'] == 2]  # Document collections
    edge_collections = [c for c in collections if c['type'] == 3]  # Edge collections
    
    print(f"\nFound {len(document_collections)} document collections and {len(edge_collections)} edge collections")
    
    # Print collection names
    print("\nDocument collections:")
    for c in document_collections:
        print(f"- {c['name']}")
    
    print("\nEdge collections:")
    for c in edge_collections:
        print(f"- {c['name']}")
    
    # For SPOKE, the main nodes are typically in a collection called "Nodes"
    # Let's explore that first
    if 'Nodes' in [c['name'] for c in document_collections]:
        explore_nodes_collection(db, limit)
    
    # Now explore edges
    if 'Edges' in [c['name'] for c in edge_collections]:
        explore_edges_collection(db, limit)


def explore_nodes_collection(db, limit: int = 10):
    """Explore the Nodes collection to identify node types and ontology fields.
    
    Args:
        db: ArangoDB database connection
        limit: Maximum number of samples to examine
    """
    print("\n==== Exploring Nodes Collection ====")
    
    # Step 1: Get node types
    aql_query = """
        FOR doc IN Nodes
        COLLECT type = doc.type WITH COUNT INTO count
        SORT count DESC
        RETURN {
            type: type,
            count: count
        }
    """
    
    print("\nQuerying node types (this might take a moment)...")
    try:
        cursor = db.aql.execute(aql_query, timeout=120)  # 2 minute timeout
        node_types = list(cursor)
        
        print(f"Found {len(node_types)} node types:")
        for node in node_types[:10]:  # Show top 10
            print(f"- {node['type']}: {node['count']:,} nodes")
        
        if len(node_types) > 10:
            print(f"... and {len(node_types) - 10} more types")
        
        # Step 2: Explore interesting node types for ontology fields
        interesting_types = [
            "Compound", "Gene", "Protein", "Pathway", "Disease", 
            "Symptom", "Anatomy", "CellType", "Food"
        ]
        
        # Filter to types that actually exist
        available_types = [nt['type'] for nt in node_types]
        types_to_explore = [t for t in interesting_types if t in available_types]
        
        for node_type in types_to_explore:
            print(f"\nExploring {node_type} node type...")
            # Get sample nodes of this type
            aql_query = f"""
                FOR doc IN Nodes
                FILTER doc.type == "{node_type}"
                LIMIT {limit}
                RETURN doc
            """
            
            cursor = db.aql.execute(aql_query, timeout=60)
            sample_nodes = list(cursor)
            
            if not sample_nodes:
                print(f"No {node_type} nodes found")
                continue
            
            # Analyze the properties
            print(f"Sample properties for {node_type}:")
            
            # Combine all properties from samples
            all_props = set()
            for node in sample_nodes:
                all_props.update(node.keys())
            
            # Print regular properties
            regular_props = [p for p in all_props if p not in ['_id', '_key', '_rev', 'type', 'properties']]
            if regular_props:
                print("Regular properties:")
                for prop in sorted(regular_props):
                    sample_values = [str(node.get(prop, '')) for node in sample_nodes if prop in node][:3]
                    print(f"  - {prop}: {', '.join(sample_values)}")
            
            # Check for nested properties (common in SPOKE)
            if 'properties' in all_props:
                print("Nested properties:")
                # Collect all nested properties from samples
                nested_props = set()
                for node in sample_nodes:
                    if 'properties' in node and isinstance(node['properties'], dict):
                        nested_props.update(node['properties'].keys())
                
                # Print nested properties
                for prop in sorted(nested_props):
                    sample_values = [
                        str(node['properties'].get(prop, '')) 
                        for node in sample_nodes 
                        if 'properties' in node and prop in node['properties']
                    ][:3]
                    print(f"  - properties.{prop}: {', '.join(sample_values)}")
            
            # Identify potential ontology identifiers
            ontology_patterns = {
                'chebi': r'CHEBI:\d+',
                'hmdb': r'HMDB\d+',
                'pubchem': r'CID\d+',
                'uniprot': r'[A-Z\d]{6,10}',
                'ensembl': r'ENS[A-Z]*\d+',
                'symbol': r'[A-Za-z0-9]+',
                'mondo': r'MONDO:\d{7}',
                'doid': r'DOID:\d+',
                'mesh': r'[A-Z]\d{6}',
            }
            
            print("\nPotential ontology identifiers:")
            found_ontology = False
            
            # Check nested properties for identifiers
            for node in sample_nodes:
                if 'properties' in node and isinstance(node['properties'], dict):
                    props = node['properties']
                    for prop_name, value in props.items():
                        for ont_name in ['chebi', 'hmdb', 'pubchem', 'uniprot', 'ensembl']:
                            if ont_name in prop_name.lower() and value:
                                print(f"  - properties.{prop_name}: {value} (likely {ont_name})")
                                found_ontology = True
                                break
            
            if not found_ontology:
                print("  No obvious ontology identifiers found")
    
    except Exception as e:
        print(f"Error exploring nodes: {str(e)}")


def explore_edges_collection(db, limit: int = 10):
    """Explore the Edges collection to identify relationship types.
    
    Args:
        db: ArangoDB database connection
        limit: Maximum number of samples to examine
    """
    print("\n==== Exploring Edges Collection ====")
    
    # Step 1: Get relationship types (labels)
    aql_query = """
        FOR edge IN Edges
        COLLECT label = edge.label WITH COUNT INTO count
        SORT count DESC
        RETURN {
            label: label,
            count: count
        }
    """
    
    print("\nQuerying relationship types (this might take a moment)...")
    try:
        cursor = db.aql.execute(aql_query, timeout=120)  # 2 minute timeout
        relationship_types = list(cursor)
        
        print(f"Found {len(relationship_types)} relationship types:")
        for rel in relationship_types[:10]:  # Show top 10
            print(f"- {rel['label']}: {rel['count']:,} edges")
        
        if len(relationship_types) > 10:
            print(f"... and {len(relationship_types) - 10} more types")
        
        # Step 2: Explore interesting relationship types
        interesting_relations = [
            "ASSOCIATES_DaG", "PARTICIPATES_GpP", "PARTICIPATES_DpP", 
            "INTERACTS_CmG", "PARTICIPATES_CpP"
        ]
        
        # Use top relations if specified ones don't exist
        available_relations = [rt['label'] for rt in relationship_types]
        relations_to_explore = [
            r for r in interesting_relations if r in available_relations
        ] or [rt['label'] for rt in relationship_types[:5]]  # Use top 5 if specified ones not found
        
        for rel_type in relations_to_explore:
            print(f"\nExploring {rel_type} relationship type...")
            # Get sample edges of this type
            aql_query = f"""
                FOR edge IN Edges
                FILTER edge.label == "{rel_type}"
                LIMIT {limit}
                RETURN edge
            """
            
            cursor = db.aql.execute(aql_query, timeout=60)
            sample_edges = list(cursor)
            
            if not sample_edges:
                print(f"No {rel_type} edges found")
                continue
            
            # Identify source and target node types
            source_ids = []
            target_ids = []
            for edge in sample_edges:
                source_ids.append(edge['_from'])
                target_ids.append(edge['_to'])
            
            # Get node types for a sample of sources and targets
            source_types = get_node_types_for_ids(db, source_ids)
            target_types = get_node_types_for_ids(db, target_ids)
            
            print(f"Source node types: {', '.join(source_types)}")
            print(f"Target node types: {', '.join(target_types)}")
            
            # Show relationship example
            if sample_edges:
                edge = sample_edges[0]
                print(f"Example: {edge['_from']} --[{rel_type}]--> {edge['_to']}")
                
                # Check for properties
                edge_props = [k for k in edge.keys() if k not in ['_id', '_key', '_rev', '_from', '_to', 'label']]
                if edge_props:
                    print("Relationship properties:")
                    for prop in edge_props:
                        print(f"  - {prop}: {edge[prop]}")
    
    except Exception as e:
        print(f"Error exploring edges: {str(e)}")


def get_node_types_for_ids(db, node_ids: List[str]) -> Set[str]:
    """Get node types for a list of node IDs.
    
    Args:
        db: ArangoDB database connection
        node_ids: List of node IDs
        
    Returns:
        Set of node types
    """
    node_types = set()
    
    if not node_ids:
        return node_types
    
    # Extract collection name and keys
    collection_keys = {}
    for node_id in node_ids:
        parts = node_id.split('/')
        if len(parts) == 2:
            collection, key = parts
            if collection not in collection_keys:
                collection_keys[collection] = []
            collection_keys[collection].append(key)
    
    # For SPOKE, all nodes are typically in the Nodes collection
    if 'Nodes' in collection_keys and collection_keys['Nodes']:
        keys = collection_keys['Nodes'][:10]  # Limit to 10 keys for efficiency
        
        # Convert list of keys to AQL array format
        keys_str = ', '.join([f'"{k}"' for k in keys])
        aql_query = f"""
            FOR doc IN Nodes
            FILTER doc._key IN [{keys_str}]
            RETURN doc.type
        """
        
        try:
            cursor = db.aql.execute(aql_query)
            node_types.update([t for t in cursor if t])
        except Exception as e:
            print(f"Error getting node types: {str(e)}")
    
    return node_types


def extract_metadata_config(
    host: str,
    port: int, 
    database: str,
    username: str,
    password: str,
    output_file: Optional[str] = None
):
    """Extract a metadata configuration for Biomapper.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        output_file: Output file path for the configuration
    """
    # Generate a configuration based on common SPOKE patterns
    config = {
        "name": "spoke",
        "type": "knowledge_graph",
        "description": "SPOKE Knowledge Graph",
        "config": {
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": password,
        },
        "capabilities": [
            {
                "name": "compound_to_gene",
                "description": "Map compounds to genes",
                "confidence": 0.9
            },
            {
                "name": "gene_to_disease",
                "description": "Map genes to diseases",
                "confidence": 0.9
            },
            {
                "name": "compound_to_pathway",
                "description": "Map compounds to pathways",
                "confidence": 0.9
            },
            {
                "name": "gene_to_pathway",
                "description": "Map genes to pathways",
                "confidence": 0.9
            },
            {
                "name": "protein_to_pathway",
                "description": "Map proteins to pathways",
                "confidence": 0.9
            }
        ],
        "schema_mapping": {
            "node_types": {
                "Compound": {
                    "ontology_types": ["chebi", "hmdb", "pubchem"],
                    "property_map": {
                        "properties.chebi": "chebi",
                        "properties.hmdb": "hmdb"
                    }
                },
                "Gene": {
                    "ontology_types": ["ensembl", "gene_symbol"],
                    "property_map": {
                        "properties.ensembl": "ensembl",
                        "name": "gene_symbol"
                    }
                },
                "Protein": {
                    "ontology_types": ["uniprot"],
                    "property_map": {
                        "properties.uniprot": "uniprot"
                    }
                },
                "Disease": {
                    "ontology_types": ["mondo", "doid", "mesh"],
                    "property_map": {
                        "properties.mondo": "mondo",
                        "properties.doid": "doid",
                        "properties.mesh": "mesh"
                    }
                }
            }
        }
    }
    
    # Save to file if specified
    if output_file:
        if output_file.endswith('.json'):
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)
        else:  # Default to YAML
            import yaml
            with open(output_file, 'w') as f:
                yaml.dump(config, f, sort_keys=False)
        
        print(f"\nMetadata configuration written to {output_file}")
    else:
        # Print the configuration
        print("\n==== Generated Metadata Configuration ====")
        print(json.dumps(config, indent=2))
    
    return config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SPOKE Metadata Explorer")
    
    parser.add_argument("--host", default="localhost", help="SPOKE host")
    parser.add_argument("--port", type=int, default=8529, help="SPOKE port")
    parser.add_argument("--database", default="spokeV6", help="SPOKE database name")
    parser.add_argument("--username", default="root", help="SPOKE username")
    parser.add_argument("--password", default="ph", help="SPOKE password")
    parser.add_argument("--limit", type=int, default=10, help="Limit sample size")
    parser.add_argument("--output", help="Output file for metadata configuration (YAML or JSON)")
    parser.add_argument("--config-only", action="store_true", help="Generate config without exploration")
    
    args = parser.parse_args()
    
    try:
        print("="*80)
        print("SPOKE METADATA EXPLORER")
        print("="*80)
        
        if not args.config_only:
            explore_spoke_structure(
                host=args.host,
                port=args.port,
                database=args.database,
                username=args.username,
                password=args.password,
                limit=args.limit,
            )
        
        # Generate a metadata configuration
        extract_metadata_config(
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password,
            output_file=args.output,
        )
        
        print("\n" + "="*80)
        print("EXPLORATION COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
