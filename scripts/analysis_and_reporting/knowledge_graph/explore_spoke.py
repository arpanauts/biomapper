#!/usr/bin/env python
"""
Explore the SPOKE database structure and create documentation for future RAG/LLM approaches.

This script connects to the SPOKE ArangoDB instance, extracts schema information,
and creates a structured documentation resource.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from arango import ArangoClient

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def connect_to_spoke(
    host="localhost",
    port=8529,
    username="root",
    password="ph",
    database="spoke23_human",
):
    """Connect to the SPOKE ArangoDB instance.

    Args:
        host: ArangoDB host
        port: ArangoDB port
        username: ArangoDB username
        password: ArangoDB password
        database: SPOKE database name

    Returns:
        tuple: ArangoDB client and database instance
    """
    # Create a connection to the ArangoDB server
    client = ArangoClient(hosts=f"http://{host}:{port}")

    # Connect to the system database
    sys_db = client.db("_system", username=username, password=password)

    # Check if the SPOKE database exists
    if not sys_db.has_database(database):
        available_dbs = sys_db.databases()
        print(f"Database '{database}' not found. Available databases: {available_dbs}")

        # Try to use the first available database if the specified one doesn't exist
        if len(available_dbs) > 1:  # Skip _system
            database = [db for db in available_dbs if db != "_system"][0]
            print(f"Using database '{database}' instead.")

    # Connect to the SPOKE database
    db = client.db(database, username=username, password=password)
    print(f"Connected to ArangoDB at {host}:{port}, database: {database}")

    return client, db


def get_database_structure(db):
    """Extract the database structure.

    Args:
        db: ArangoDB database instance

    Returns:
        dict: Database structure information
    """
    structure = {
        "collections": {},
        "graphs": {},
        "database_info": {},
    }

    # Get database information
    structure["database_info"] = {
        "name": db.name,
        "version": db.version(),
        "properties": db.properties(),
    }

    # Get all collections
    collections = db.collections()
    structure["collection_summary"] = {
        "total": len(collections),
        "document_collections": len(
            [c for c in collections if c["type"] == 2 and not c["name"].startswith("_")]
        ),
        "edge_collections": len(
            [c for c in collections if c["type"] == 3 and not c["name"].startswith("_")]
        ),
        "system_collections": len(
            [c for c in collections if c["name"].startswith("_")]
        ),
    }

    # Process each collection
    for collection in collections:
        collection_name = collection["name"]

        # Skip system collections
        if collection_name.startswith("_"):
            continue

        # Get collection
        col = db.collection(collection_name)

        # Get collection properties
        properties = col.properties()

        # Get collection statistics
        stats = col.statistics()

        # Sample documents
        sample_size = min(5, stats["count"])
        samples = list(col.random(sample_size)) if sample_size > 0 else []

        # Extract schema from samples
        schema = extract_schema_from_samples(samples)

        # Store collection information
        structure["collections"][collection_name] = {
            "type": "edge" if properties["type"] == 3 else "document",
            "properties": properties,
            "statistics": stats,
            "schema": schema,
            "sample_documents": samples,
        }

    # Get all graphs
    graphs = db.graphs()
    structure["graph_summary"] = {
        "total": len(graphs),
    }

    # Process each graph
    for graph in graphs:
        graph_name = graph["name"]

        # Get graph
        g = db.graph(graph_name)

        # Get graph properties
        properties = g.properties()

        # Get edge definitions
        edge_definitions = properties["edgeDefinitions"]

        # Store graph information
        structure["graphs"][graph_name] = {
            "properties": properties,
            "edge_definitions": edge_definitions,
            "vertex_collections": g.vertex_collections(),
            "edge_collections": [e["collection"] for e in edge_definitions],
        }

    return structure


def extract_schema_from_samples(samples):
    """Extract schema information from sample documents.

    Args:
        samples: List of sample documents

    Returns:
        dict: Schema information
    """
    if not samples:
        return {"fields": {}}

    field_types = defaultdict(list)

    # Process each sample
    for sample in samples:
        for field, value in sample.items():
            # Skip system fields
            if field.startswith("_"):
                continue

            # Get value type
            value_type = type(value).__name__
            field_types[field].append(value_type)

    # Calculate field statistics
    fields = {}
    for field, types in field_types.items():
        type_counter = Counter(types)
        most_common_type = type_counter.most_common(1)[0][0]

        fields[field] = {
            "type": most_common_type,
            "present_in_samples": len(types),
            "total_samples": len(samples),
            "presence_ratio": round(len(types) / len(samples), 2),
            "type_distribution": dict(type_counter),
        }

    return {"fields": fields}


def analyze_spoke_structure(structure):
    """Analyze the SPOKE database structure.

    Args:
        structure: Database structure information

    Returns:
        dict: Analysis results
    """
    analysis = {
        "overview": {
            "database_name": structure["database_info"]["name"],
            "total_collections": structure["collection_summary"]["total"],
            "document_collections": structure["collection_summary"][
                "document_collections"
            ],
            "edge_collections": structure["collection_summary"]["edge_collections"],
            "total_graphs": structure["graph_summary"]["total"],
        },
        "node_types": {},
        "edge_types": {},
        "entity_id_patterns": {},
        "common_properties": defaultdict(list),
    }

    # Analyze document collections (nodes)
    for name, collection in structure["collections"].items():
        if collection["type"] == "document":
            # Count documents
            doc_count = collection["statistics"]["count"]

            # Collect field names
            fields = list(collection["schema"]["fields"].keys())

            # Check for name and identifier fields
            id_fields = [
                f
                for f in fields
                if f in ("id", "identifier", "uuid", "name", "identifier")
            ]

            # Collect common properties
            for field in fields:
                analysis["common_properties"][field].append(name)

            # Store node type information
            analysis["node_types"][name] = {
                "count": doc_count,
                "fields": fields,
                "id_fields": id_fields,
            }

            # Try to extract ID patterns if samples exist
            if collection["sample_documents"]:
                id_patterns = extract_id_patterns(collection["sample_documents"])
                if id_patterns:
                    analysis["entity_id_patterns"][name] = id_patterns

        # Analyze edge collections
        elif collection["type"] == "edge":
            # Count edges
            edge_count = collection["statistics"]["count"]

            # Collect field names (excluding _from, _to)
            fields = [
                f
                for f in collection["schema"]["fields"].keys()
                if f not in ("_from", "_to")
            ]

            # Store edge type information
            analysis["edge_types"][name] = {
                "count": edge_count,
                "fields": fields,
            }

            # Try to determine connection patterns from samples
            if collection["sample_documents"]:
                connections = analyze_edge_connections(collection["sample_documents"])
                analysis["edge_types"][name]["connections"] = connections

    # Convert defaultdict to regular dict
    analysis["common_properties"] = dict(analysis["common_properties"])

    # Sort common properties by frequency
    for prop, collections in analysis["common_properties"].items():
        analysis["common_properties"][prop] = {
            "collections": collections,
            "frequency": len(collections),
        }

    # Sort common properties by frequency
    analysis["common_properties"] = {
        k: v
        for k, v in sorted(
            analysis["common_properties"].items(),
            key=lambda item: item[1]["frequency"],
            reverse=True,
        )
    }

    return analysis


def extract_id_patterns(samples):
    """Extract ID patterns from sample documents.

    Args:
        samples: List of sample documents

    Returns:
        dict: ID pattern information
    """
    patterns = {}

    # Common ID field names to check
    id_fields = ["id", "identifier", "uuid", "_id", "_key", "name"]

    # Check each sample
    for sample in samples:
        for field in id_fields:
            if field in sample and isinstance(sample[field], str):
                # Get ID value
                id_value = sample[field]

                # Skip empty values
                if not id_value:
                    continue

                # Initialize pattern for this field if not exists
                if field not in patterns:
                    patterns[field] = {
                        "examples": [],
                        "prefixes": Counter(),
                        "contains_colon": 0,
                        "contains_dash": 0,
                    }

                # Add example if we have fewer than 5
                if (
                    len(patterns[field]["examples"]) < 5
                    and id_value not in patterns[field]["examples"]
                ):
                    patterns[field]["examples"].append(id_value)

                # Check for prefix (e.g., CHEBI:12345)
                if ":" in id_value:
                    patterns[field]["contains_colon"] += 1
                    prefix = id_value.split(":")[0]
                    patterns[field]["prefixes"][prefix] += 1

                # Check for dash (e.g., HMDB-00001)
                if "-" in id_value:
                    patterns[field]["contains_dash"] += 1

    # Format results
    for field, pattern in patterns.items():
        # Convert counters to dictionaries
        pattern["prefixes"] = dict(pattern["prefixes"].most_common())

        # Calculate percentages
        total = len(pattern["examples"])
        if total > 0:
            pattern["has_colon_percent"] = round(
                pattern["contains_colon"] / total * 100, 1
            )
            pattern["has_dash_percent"] = round(
                pattern["contains_dash"] / total * 100, 1
            )

    return patterns


def analyze_edge_connections(samples):
    """Analyze edge connections from sample documents.

    Args:
        samples: List of sample edge documents

    Returns:
        dict: Edge connection information
    """
    connections = {
        "from_collections": Counter(),
        "to_collections": Counter(),
        "patterns": Counter(),
    }

    # Check each sample
    for sample in samples:
        if "_from" in sample and "_to" in sample:
            # Get from and to values
            from_value = sample["_from"]
            to_value = sample["_to"]

            # Extract collection names
            if "/" in from_value:
                from_collection = from_value.split("/")[0]
                connections["from_collections"][from_collection] += 1

            if "/" in to_value:
                to_collection = to_value.split("/")[0]
                connections["to_collections"][to_collection] += 1

            # Record pattern
            if "/" in from_value and "/" in to_value:
                pattern = f"{from_value.split('/')[0]} -> {to_value.split('/')[0]}"
                connections["patterns"][pattern] += 1

    # Convert counters to dictionaries
    connections["from_collections"] = dict(
        connections["from_collections"].most_common()
    )
    connections["to_collections"] = dict(connections["to_collections"].most_common())
    connections["patterns"] = dict(connections["patterns"].most_common())

    return connections


def generate_documentation(structure, analysis):
    """Generate documentation for the SPOKE database.

    Args:
        structure: Database structure information
        analysis: Analysis results

    Returns:
        str: Markdown documentation
    """
    # Initialize markdown
    md = ["# SPOKE Database Structure Documentation", ""]

    # Overview
    md.extend(
        [
            "## Overview",
            "",
            f"Database: **{analysis['overview']['database_name']}**",
            "",
            "| Metric | Count |",
            "| ------ | ----- |",
            f"| Document Collections (Node Types) | {analysis['overview']['document_collections']} |",
            f"| Edge Collections (Relationship Types) | {analysis['overview']['edge_collections']} |",
            f"| Graphs | {analysis['overview']['total_graphs']} |",
            "",
        ]
    )

    # Document collections (Node Types)
    md.extend(
        [
            "## Node Types",
            "",
            "| Collection Name | Entity Count | ID Fields | Sample Properties |",
            "| -------------- | ------------ | --------- | ----------------- |",
        ]
    )

    for name, info in sorted(
        analysis["node_types"].items(), key=lambda x: x[1]["count"], reverse=True
    ):
        # Get sample properties (top 5)
        sample_props = ", ".join(list(info["fields"])[:5])
        id_fields = ", ".join(info["id_fields"]) if info["id_fields"] else "None"

        md.append(f"| {name} | {info['count']:,} | {id_fields} | {sample_props} |")

    md.append("")

    # Edge collections (Relationship Types)
    md.extend(
        [
            "## Edge Types",
            "",
            "| Collection Name | Relationship Count | Primary Connections | Sample Properties |",
            "| -------------- | ------------------ | ------------------ | ----------------- |",
        ]
    )

    for name, info in sorted(
        analysis["edge_types"].items(), key=lambda x: x[1]["count"], reverse=True
    ):
        # Get sample properties (top 5)
        sample_props = (
            ", ".join(info["fields"][:5]) if len(info["fields"]) > 0 else "None"
        )

        # Get primary connections (top 2)
        connections = ""
        if "connections" in info and "patterns" in info["connections"]:
            patterns = list(info["connections"]["patterns"].keys())
            if patterns:
                connections = ", ".join(patterns[:2])

        md.append(f"| {name} | {info['count']:,} | {connections} | {sample_props} |")

    md.append("")

    # ID patterns
    if analysis["entity_id_patterns"]:
        md.extend(
            [
                "## Entity Identifier Patterns",
                "",
            ]
        )

        for collection, patterns in analysis["entity_id_patterns"].items():
            md.extend(
                [
                    f"### {collection}",
                    "",
                ]
            )

            for field, pattern in patterns.items():
                md.extend(
                    [
                        f"**{field}** field patterns:",
                        "",
                        f"- Examples: {', '.join(pattern['examples'])}",
                        "",
                    ]
                )

                if "prefixes" in pattern and pattern["prefixes"]:
                    md.extend(
                        [
                            "- Prefixes:",
                            "",
                        ]
                    )

                    for prefix, count in pattern["prefixes"].items():
                        md.append(f"  - `{prefix}:` ({count} occurrences)")

                    md.append("")

    # Common properties across collections
    md.extend(
        [
            "## Common Properties Across Collections",
            "",
            "| Property | Frequency | Collections |",
            "| -------- | --------- | ----------- |",
        ]
    )

    # Show top 20 most common properties
    for prop, info in list(analysis["common_properties"].items())[:20]:
        collections = ", ".join(info["collections"][:5])
        if len(info["collections"]) > 5:
            collections += f" and {len(info['collections']) - 5} more"

        md.append(f"| {prop} | {info['frequency']} | {collections} |")

    md.append("")

    # Graphs
    if structure["graphs"]:
        md.extend(
            [
                "## Knowledge Graphs",
                "",
            ]
        )

        for name, graph in structure["graphs"].items():
            md.extend(
                [
                    f"### {name}",
                    "",
                    f"- Vertex Collections: {', '.join(graph['vertex_collections'])}",
                    f"- Edge Collections: {', '.join(graph['edge_collections'])}",
                    "",
                    "#### Edge Definitions:",
                    "",
                ]
            )

            for edge_def in graph["properties"]["edgeDefinitions"]:
                md.extend(
                    [
                        f"- **{edge_def['collection']}**:",
                        f"  - From: {', '.join(edge_def['from'])}",
                        f"  - To: {', '.join(edge_def['to'])}",
                        "",
                    ]
                )

    # Integration guidance for RAG/LLM
    md.extend(
        [
            "## Integration Guidance for RAG/LLM",
            "",
            "### Entity Type Mapping",
            "",
            "When integrating with the SQLite mapping cache or other systems, use the following type mapping:",
            "",
            "```python",
            "spoke_to_cache_type_map = {",
        ]
    )

    # Generate type mapping based on node types
    for node_type in sorted(analysis["node_types"].keys()):
        # Generate snake_case version for cache
        cache_type = node_type.lower()
        md.append(f'    "{node_type}": "{cache_type}",')

    md.extend(
        [
            "}",
            "```",
            "",
            "### Entity ID Formats",
            "",
            "SPOKE uses the following ID formats for different entity types:",
            "",
        ]
    )

    # List ID formats based on patterns
    for collection, patterns in analysis["entity_id_patterns"].items():
        for field, pattern in patterns.items():
            if "examples" in pattern and pattern["examples"]:
                md.extend(
                    [
                        f"- **{collection}**: `{pattern['examples'][0]}` (using `{field}` field)",
                    ]
                )

    md.extend(
        [
            "",
            "### Relationship Types",
            "",
            "When querying for relationships between entities, consider the following edge collections:",
            "",
        ]
    )

    # List top relationships by count
    for name, info in sorted(
        analysis["edge_types"].items(), key=lambda x: x[1]["count"], reverse=True
    )[:10]:
        connections = ""
        if "connections" in info and "patterns" in info["connections"]:
            patterns = list(info["connections"]["patterns"].keys())
            if patterns:
                connections = f" ({patterns[0]})"

        md.append(f"- **{name}**{connections}: {info['count']:,} relationships")

    md.append("")

    return "\n".join(md)


def main():
    """Main function."""
    # Connect to SPOKE database
    client, db = connect_to_spoke()

    # Extract database structure
    print("Extracting database structure...")
    structure = get_database_structure(db)

    # Analyze structure
    print("Analyzing database structure...")
    analysis = analyze_spoke_structure(structure)

    # Generate documentation
    print("Generating documentation...")
    documentation = generate_documentation(structure, analysis)

    # Save JSON structure for further analysis
    output_dir = Path("docs/spoke")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full structure (excluding sample documents to reduce size)
    structure_simplified = structure.copy()
    for collection in structure_simplified["collections"].values():
        collection[
            "sample_documents"
        ] = f"{len(collection['sample_documents'])} samples (removed to reduce file size)"

    with open(output_dir / "spoke_structure.json", "w") as f:
        json.dump(structure_simplified, f, indent=2)

    # Save analysis
    with open(output_dir / "spoke_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    # Save documentation
    with open(output_dir / "spoke_database.md", "w") as f:
        f.write(documentation)

    print(f"Documentation saved to {output_dir / 'spoke_database.md'}")
    print(f"Analysis JSON saved to {output_dir / 'spoke_analysis.json'}")
    print(f"Structure JSON saved to {output_dir / 'spoke_structure.json'}")


if __name__ == "__main__":
    main()
