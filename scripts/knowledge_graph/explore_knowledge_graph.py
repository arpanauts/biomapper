#!/usr/bin/env python
"""
Knowledge Graph Structure Explorer

This script demonstrates the use of the generalized knowledge graph analyzer
to explore the structure of any ArangoDB-based knowledge graph, including SPOKE.
It automatically discovers node types, relationship types, and identifies
properties that likely contain ontology identifiers.

Example usage:
    # Explore SPOKE database
    python explore_knowledge_graph.py --host localhost --port 8529 --database spoke
    
    # Generate configuration file for a knowledge graph
    python explore_knowledge_graph.py --host localhost --port 8529 --database my_graph --output config.yaml
"""

import asyncio
import argparse
import json
import os
import sys
import yaml
from typing import Dict, Any, Optional

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from biomapper.core.graph_analyzer import KnowledgeGraphAnalyzer, GraphSchemaMapping
from biomapper.spoke.graph_analyzer import ArangoDBGraphAnalyzer
from biomapper.spoke.client import SPOKEConfig


async def explore_knowledge_graph(
    analyzer: KnowledgeGraphAnalyzer, output_file: Optional[str] = None
) -> None:
    """Explore the structure of a knowledge graph.

    Args:
        analyzer: The knowledge graph analyzer to use
        output_file: Optional file to write the configuration to
    """
    print("Connecting to knowledge graph...")

    print("\n" + "=" * 80)
    print("KNOWLEDGE GRAPH EXPLORATION RESULTS")
    print("=" * 80)

    # Discover node types
    print("\nDiscovering node types...")
    node_types = await analyzer.discover_node_types()
    print(f"Found {len(node_types)} node types:")

    for node_type_name, metadata in node_types.items():
        print(f"- {node_type_name}: {metadata.count:,} nodes")

    # Select a node type to explore in detail
    if node_types:
        detailed_node = max(node_types.items(), key=lambda x: x[1].count)[0]
        print(f"\nExploring node type: {detailed_node}")

        node_metadata = node_types[detailed_node]
        if node_metadata.properties:
            print("Properties:")
            for prop_name, prop_type in node_metadata.properties.items():
                print(f"  - {prop_name}: {prop_type}")

            # Show some sample values for interesting properties
            interesting_props = list(node_metadata.properties.keys())[:5]
            print("\nSample values:")
            for prop in interesting_props:
                if prop in node_metadata.sample_values:
                    samples = node_metadata.sample_values[prop]
                    print(f"  - {prop}: {', '.join(str(s) for s in samples[:3])}")

    # Discover relationship types
    print("\nDiscovering relationship types...")
    relationship_types = await analyzer.discover_relationship_types()
    print(f"Found {len(relationship_types)} relationship types:")

    # Sort relationships by count in descending order
    sorted_relationships = sorted(
        relationship_types.items(), key=lambda x: x[1].count, reverse=True
    )

    for rel_name, metadata in sorted_relationships[:10]:  # Show top 10
        source_types = ", ".join(metadata.source_node_types)
        target_types = ", ".join(metadata.target_node_types)
        print(f"- {rel_name}: {metadata.count:,} edges")
        print(f"  Sources: {source_types}")
        print(f"  Targets: {target_types}")

    # Identify ontology fields
    print("\nIdentifying ontology fields...")
    ontology_fields = await analyzer.identify_ontology_fields()
    print(f"Found ontology fields in {len(ontology_fields)} node types:")

    for node_type, fields in ontology_fields.items():
        print(f"- {node_type}:")
        for field_name, confidence in fields:
            print(f"  - {field_name} ({confidence.value})")

    # Generate schema mapping
    print("\nGenerating schema mapping...")
    schema_mapping = await analyzer.generate_schema_mapping("analyzed_graph")

    # Output to file if requested
    if output_file:
        # Convert dataclasses to dict for serialization
        mapping_dict = {
            "graph_name": schema_mapping.graph_name,
            "node_type_mappings": [
                {
                    "node_type": m.node_type,
                    "property_path": m.property_path,
                    "ontology_type": m.ontology_type,
                    "confidence": m.confidence,
                }
                for m in schema_mapping.node_type_mappings
            ],
            "relationship_mappings": schema_mapping.relationship_mappings,
        }

        # Determine output format
        if output_file.endswith(".json"):
            with open(output_file, "w") as f:
                json.dump(mapping_dict, f, indent=2)
        else:  # Default to YAML
            with open(output_file, "w") as f:
                yaml.dump(mapping_dict, f, sort_keys=False)

        print(f"\nSchema mapping written to {output_file}")
    else:
        # Print summary
        print(
            f"Generated mapping with {len(schema_mapping.node_type_mappings)} field mappings"
        )
        print("\nSample mappings:")
        for mapping in schema_mapping.node_type_mappings[:5]:  # Show first 5
            print(
                f"- {mapping.node_type}.{mapping.property_path} -> {mapping.ontology_type}"
            )

    print("\n" + "=" * 80)
    print("EXPLORATION COMPLETE")
    print("=" * 80)


def create_config_from_exploration(
    host: str,
    port: int,
    database: str,
    username: str = "root",
    password: str = "",
    graph_name: str = "knowledge_graph",
) -> Dict[str, Any]:
    """Create a Biomapper configuration from the exploration results.

    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        graph_name: Name for the knowledge graph

    Returns:
        Configuration dictionary
    """
    config = {
        "knowledge_graphs": [
            {
                "name": graph_name,
                "type": "arangodb",
                "optional": True,
                "connection": {
                    "host": host,
                    "port": port,
                    "database": database,
                    "username": username,
                    "password": password,
                    "use_ssl": False,
                },
                "schema_mapping": {},
                "capabilities": {},
            }
        ]
    }

    return config


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Knowledge Graph Structure Explorer")

    parser.add_argument("--host", default="localhost", help="ArangoDB host")
    parser.add_argument("--port", type=int, default=8529, help="ArangoDB port")
    parser.add_argument("--database", default="spoke", help="ArangoDB database name")
    parser.add_argument("--username", default="root", help="ArangoDB username")
    parser.add_argument("--password", default="", help="ArangoDB password")
    parser.add_argument("--use-ssl", action="store_true", help="Use SSL for connection")
    parser.add_argument(
        "--output", help="Output file for schema mapping (YAML or JSON)"
    )
    parser.add_argument(
        "--sample-size", type=int, default=5, help="Number of samples to retrieve"
    )

    args = parser.parse_args()

    # Create the analyzer
    analyzer = ArangoDBGraphAnalyzer(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        database=args.database,
        use_ssl=args.use_ssl,
        sample_size=args.sample_size,
    )

    try:
        await explore_knowledge_graph(analyzer, args.output)
    except Exception as e:
        print(f"Error exploring knowledge graph: {e}")
    finally:
        await analyzer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
