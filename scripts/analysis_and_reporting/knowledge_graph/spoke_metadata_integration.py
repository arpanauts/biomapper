#!/usr/bin/env python
"""
SPOKE Knowledge Graph Metadata Integration Demo

This script demonstrates how to:
1. Analyze the SPOKE database structure using the graph analyzer
2. Generate a schema mapping configuration
3. Register the discovered capabilities with the resource metadata system
4. Perform mapping operations using the discovered metadata

This creates a complete end-to-end flow from discovery to actual use.
"""

import asyncio
import argparse
import json
import os
import sys
import yaml
from typing import Dict, List, Any, Optional, Tuple

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from biomapper.core.graph_analyzer import GraphSchemaMapping, OntologyTypeMapping
from biomapper.metadata.kg_manager import KnowledgeGraphManager
from biomapper.metadata.models import ResourceCapability, ResourceRegistration

# We'll create a direct SPOKE client instead of using the factory for now
from biomapper.spoke.client import SPOKEConfig, SPOKEDBClient
from biomapper.spoke.graph_analyzer import SPOKEGraphAnalyzer


async def analyze_spoke_and_register(
    host: str,
    port: int,
    database: str,
    username: str = "root",
    password: str = "",
    sample_size: int = 5,
    verbose: bool = False,
) -> Tuple[GraphSchemaMapping, ResourceRegistration]:
    """Analyze SPOKE and register its capabilities with the metadata system.

    Args:
        host: SPOKE host
        port: SPOKE port
        database: SPOKE database name
        username: SPOKE username
        password: SPOKE password
        sample_size: Number of samples to retrieve
        verbose: Whether to print verbose output

    Returns:
        Tuple of (schema_mapping, resource_registration)
    """
    spoke_config = SPOKEConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
    )

    # Step 1: Create the SPOKE analyzer
    print("\n[Step 1] Creating SPOKE analyzer...")
    analyzer = SPOKEGraphAnalyzer(config=spoke_config, sample_size=sample_size)

    # Step 2: Discover node types in SPOKE
    print("\n[Step 2] Discovering node types in SPOKE...")
    node_types = await analyzer.discover_node_types()
    if verbose:
        print(f"Found {len(node_types)} node types:")
        for node_type_name, metadata in node_types.items():
            print(f"- {node_type_name}: {metadata.count:,} nodes")
    else:
        print(f"Found {len(node_types)} node types.")

    # Step 3: Discover relationship types in SPOKE
    print("\n[Step 3] Discovering relationship types in SPOKE...")
    relationship_types = await analyzer.discover_relationship_types()
    if verbose:
        print(f"Found {len(relationship_types)} relationship types:")
        top_relationships = sorted(
            relationship_types.items(), key=lambda x: x[1].count, reverse=True
        )[:5]  # Show top 5
        for rel_name, metadata in top_relationships:
            source_types = ", ".join(metadata.source_node_types)
            target_types = ", ".join(metadata.target_node_types)
            print(f"- {rel_name}: {metadata.count:,} edges")
            print(f"  Sources: {source_types}")
            print(f"  Targets: {target_types}")
    else:
        print(f"Found {len(relationship_types)} relationship types.")

    # Step 4: Identify ontology fields in SPOKE
    print("\n[Step 4] Identifying ontology fields...")
    ontology_fields = await analyzer.identify_ontology_fields()
    if verbose:
        print(f"Found ontology fields in {len(ontology_fields)} node types:")
        for node_type, fields in ontology_fields.items():
            print(f"- {node_type}:")
            for field_name, confidence in fields:
                print(f"  - {field_name} ({confidence.value})")
    else:
        print(f"Found ontology fields in {len(ontology_fields)} node types.")

    # Step 5: Generate schema mapping for SPOKE
    print("\n[Step 5] Generating schema mapping...")
    schema_mapping = await analyzer.generate_schema_mapping("spoke")

    # Create a list of capabilities based on the discovered relationships
    capabilities = []

    # For each relationship, create a capability
    for rel_name, metadata in relationship_types.items():
        # Only create capabilities for relationships that connect different node types
        if metadata.source_node_types and metadata.target_node_types:
            for source_type in metadata.source_node_types:
                for target_type in metadata.target_node_types:
                    # Skip self-relationships unless they're important
                    if (
                        source_type == target_type
                        and source_type != "Compound"
                        and source_type != "Gene"
                    ):
                        continue

                    # Create a capability name
                    capability_name = f"{source_type.lower()}_to_{target_type.lower()}"

                    # Add to capabilities if not already present
                    if capability_name not in [c.name for c in capabilities]:
                        capabilities.append(
                            ResourceCapability(
                                name=capability_name,
                                description=f"Map {source_type} to {target_type} using {rel_name}",
                                confidence=0.9,  # High confidence since directly discovered
                            )
                        )

    print(
        f"Generated {len(schema_mapping.node_type_mappings)} ontology field mappings."
    )
    print(f"Identified {len(capabilities)} mapping capabilities.")

    # Step 6: Register with the metadata system
    print("\n[Step 6] Registering with the metadata system...")

    # Create a resource registration
    resource_registration = ResourceRegistration(
        name="spoke",
        type="knowledge_graph",
        description="SPOKE Knowledge Graph",
        config={
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        },
        capabilities=capabilities,
        schema_mapping={
            "node_types": {
                m.node_type: {
                    "ontology_types": [m.ontology_type],
                    "property_map": {m.property_path: m.ontology_type},
                }
                for m in schema_mapping.node_type_mappings
            }
        },
    )

    # Initialize the knowledge graph manager
    kg_manager = KnowledgeGraphManager.get_instance()

    # Register the resource
    kg_manager.register_resource(resource_registration)
    print(f"Registered SPOKE as a resource with {len(capabilities)} capabilities.")

    return schema_mapping, resource_registration


async def demonstrate_mapping_with_metadata(
    resource_registration: ResourceRegistration,
    verbose: bool = False,
) -> None:
    """Demonstrate mapping entities using the registered metadata.

    Args:
        resource_registration: The resource registration to use
        verbose: Whether to print verbose output
    """
    print("\n[Step 7] Demonstrating mapping with registered metadata...")

    # Create a SPOKE client directly since we haven't implemented the factory yet
    spoke_config = SPOKEConfig(
        host=resource_registration.config["host"],
        port=resource_registration.config["port"],
        username=resource_registration.config["username"],
        password=resource_registration.config["password"],
        database=resource_registration.config["database"],
    )
    spoke_client = SPOKEDBClient(config=spoke_config)

    # Find a Compound node type if it exists in the resource's schema mapping
    compound_mapping = None
    gene_mapping = None

    if "node_types" in resource_registration.schema_mapping:
        node_types = resource_registration.schema_mapping["node_types"]

        # Look for Compound node type
        if "Compound" in node_types:
            compound_mapping = node_types["Compound"]

        # Look for Gene node type
        if "Gene" in node_types:
            gene_mapping = node_types["Gene"]

    if compound_mapping:
        print("\nDemonstrating compound mapping:")

        # Get ontology types for Compound
        ontology_types = compound_mapping.get("ontology_types", [])
        if ontology_types:
            print(f"Found ontology types for Compound: {', '.join(ontology_types)}")

            # Try to map a compound using the first ontology type
            ontology_type = ontology_types[0]

            # Example identifiers to try
            example_ids = [
                "CHEBI:17234",  # Glucose
                "CHEBI:18167",  # 5-Hydroxytryptamine (Serotonin)
                "CHEBI:16866",  # Adenosine triphosphate (ATP)
            ]

            for example_id in example_ids:
                print(
                    f"\nTrying to map {example_id} ({ontology_type}) to other entities..."
                )

                # Find the compound in SPOKE
                nodes = await spoke_client.query_nodes(
                    node_type="Compound",
                    properties={ontology_type: example_id},
                )

                if nodes:
                    print(f"Found {len(nodes)} node(s) matching {example_id}")

                    # Get the first node
                    node = nodes[0]
                    node_id = node.get("_id")

                    if node_id:
                        # Now demonstrate mapping to genes if the capability exists
                        if "compound_to_gene" in [
                            c.name for c in resource_registration.capabilities
                        ]:
                            print("Mapping compound to genes...")

                            # Use the relationship to map to genes
                            genes = await spoke_client.query_relationships(
                                source_id=node_id,
                                source_type="Compound",
                                target_type="Gene",
                            )

                            if genes:
                                print(f"Found {len(genes)} related genes")
                                if verbose:
                                    for i, gene in enumerate(
                                        genes[:5]
                                    ):  # Show up to 5 genes
                                        rel_type = gene.get("label", "Unknown")
                                        target_id = gene.get("_to", "Unknown")
                                        print(f"  {i+1}. {target_id} via {rel_type}")
                            else:
                                print("No related genes found")

                        # Try mapping to diseases if the capability exists
                        if "compound_to_disease" in [
                            c.name for c in resource_registration.capabilities
                        ]:
                            print("Mapping compound to diseases...")

                            # Use the relationship to map to diseases
                            diseases = await spoke_client.query_relationships(
                                source_id=node_id,
                                source_type="Compound",
                                target_type="Disease",
                            )

                            if diseases:
                                print(f"Found {len(diseases)} related diseases")
                                if verbose:
                                    for i, disease in enumerate(
                                        diseases[:5]
                                    ):  # Show up to 5 diseases
                                        rel_type = disease.get("label", "Unknown")
                                        target_id = disease.get("_to", "Unknown")
                                        print(f"  {i+1}. {target_id} via {rel_type}")
                            else:
                                print("No related diseases found")
                else:
                    print(f"No nodes found for {example_id}")
        else:
            print("No ontology types found for Compound node type")
    else:
        print("Compound node type not found in schema mapping")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SPOKE Metadata Integration Demo")

    parser.add_argument("--host", default="localhost", help="SPOKE host")
    parser.add_argument("--port", type=int, default=8529, help="SPOKE port")
    parser.add_argument("--database", default="spoke", help="SPOKE database name")
    parser.add_argument("--username", default="root", help="SPOKE username")
    parser.add_argument("--password", default="", help="SPOKE password")
    parser.add_argument(
        "--sample-size", type=int, default=5, help="Number of samples to retrieve"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output", help="Output file for resource registration (YAML or JSON)"
    )

    args = parser.parse_args()

    try:
        print("=" * 80)
        print("SPOKE KNOWLEDGE GRAPH METADATA INTEGRATION DEMO")
        print("=" * 80)

        # Analyze SPOKE and register with metadata system
        schema_mapping, resource_registration = await analyze_spoke_and_register(
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password,
            sample_size=args.sample_size,
            verbose=args.verbose,
        )

        # Demonstrate mapping with the registered metadata
        await demonstrate_mapping_with_metadata(
            resource_registration=resource_registration,
            verbose=args.verbose,
        )

        # Save the resource registration if requested
        if args.output:
            # Convert to dictionary
            reg_dict = {
                "name": resource_registration.name,
                "type": resource_registration.type,
                "description": resource_registration.description,
                "config": resource_registration.config,
                "capabilities": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "confidence": c.confidence,
                    }
                    for c in resource_registration.capabilities
                ],
                "schema_mapping": resource_registration.schema_mapping,
            }

            # Determine output format
            if args.output.endswith(".json"):
                with open(args.output, "w") as f:
                    json.dump(reg_dict, f, indent=2)
            else:  # Default to YAML
                with open(args.output, "w") as f:
                    yaml.dump(reg_dict, f, sort_keys=False)

            print(f"\nResource registration written to {args.output}")

        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
