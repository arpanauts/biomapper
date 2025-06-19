"""ArangoDB-based knowledge graph analyzer implementation.

This module provides an implementation of the KnowledgeGraphAnalyzer protocol
specifically for ArangoDB-based knowledge graphs, including SPOKE.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from arango import ArangoClient

from biomapper.core.graph_analyzer import (
    IdentifierConfidence,
    KnowledgeGraphAnalyzer,
    NodeTypeMetadata,
    RelationshipMetadata,
)
from biomapper.spoke.client import SPOKEConfig


logger = logging.getLogger(__name__)


class ArangoDBGraphAnalyzer(KnowledgeGraphAnalyzer):
    """Analyzer implementation for ArangoDB-based knowledge graphs.

    This analyzer works with ArangoDB databases and is specifically
    optimized for exploring SPOKE and similar knowledge graphs.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8529,
        username: str = "root",
        password: str = "password",
        database: str = "spoke",
        use_ssl: bool = False,
        sample_size: int = 5,
    ):
        """Initialize the ArangoDB graph analyzer.

        Args:
            host: ArangoDB host
            port: ArangoDB port
            username: ArangoDB username
            password: ArangoDB password
            database: ArangoDB database name
            use_ssl: Whether to use SSL for connection
            sample_size: Default sample size for data exploration
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.use_ssl = use_ssl
        self.sample_size = sample_size
        self._db = None
        self._ontology_patterns = self._compile_ontology_patterns()

    async def connect(self) -> None:
        """Connect to the ArangoDB database."""
        if self._db is not None:
            return

        # Create a connection to ArangoDB
        protocol = "https" if self.use_ssl else "http"
        url = f"{protocol}://{self.host}:{self.port}"

        # This will be run in a thread pool since arango client is synchronous
        def _connect():
            client = ArangoClient(hosts=url)
            db = client.db(
                self.database,
                username=self.username,
                password=self.password,
            )
            return db

        self._db = await asyncio.to_thread(_connect)
        logger.info(f"Connected to ArangoDB at {url}, database: {self.database}")

    async def disconnect(self) -> None:
        """Disconnect from the ArangoDB database."""
        self._db = None

    async def discover_node_types(self) -> Dict[str, NodeTypeMetadata]:
        """Discover node types and their properties.

        For SPOKE-style ArangoDB databases, this typically requires examining
        the 'Nodes' collection and analyzing the 'type' field.

        Returns:
            Dictionary mapping node type names to their metadata
        """
        await self.connect()

        # This will be different depending on the ArangoDB schema
        # For SPOKE, we typically have a 'Nodes' collection with a 'type' field
        # For other ArangoDB graphs, each node type might be its own collection

        # Check if this is a SPOKE-style database with a 'Nodes' collection
        collections = await asyncio.to_thread(
            lambda: [
                c["name"]
                for c in self._db.collections()
                if not c["name"].startswith("_")
            ]
        )

        node_types = {}

        if "Nodes" in collections:
            # SPOKE-style database with a single 'Nodes' collection
            # Node types are stored in the 'type' field
            aql_query = """
                FOR doc IN Nodes
                COLLECT type = doc.type
                WITH COUNT INTO count
                RETURN {
                    type: type,
                    count: count
                }
            """

            cursor = await asyncio.to_thread(lambda: self._db.aql.execute(aql_query))
            results = await asyncio.to_thread(lambda: [doc for doc in cursor])

            for result in results:
                node_type = result["type"]
                node_types[node_type] = NodeTypeMetadata(
                    name=node_type,
                    count=result["count"],
                )

                # Get sample node to analyze properties
                samples = await self.sample_node_data(node_type)
                if samples:
                    properties = {}
                    sample_values = {}

                    # Analyze the first sample to get property types
                    sample = samples[0]
                    for key, value in sample.items():
                        if key not in ("_id", "_key", "_rev"):
                            properties[key] = type(value).__name__

                            # For properties that are dicts, analyze their structure
                            if isinstance(value, dict):
                                for subkey, subvalue in value.items():
                                    prop_path = f"{key}.{subkey}"
                                    properties[prop_path] = type(subvalue).__name__

                    # Collect sample values for each property
                    for sample in samples:
                        for key, value in sample.items():
                            if key not in ("_id", "_key", "_rev"):
                                if key not in sample_values:
                                    sample_values[key] = []

                                # Only add if the value is a simple type and not already in the list
                                if (
                                    isinstance(value, (str, int, float, bool))
                                    and value not in sample_values[key]
                                ):
                                    sample_values[key].append(value)

                                # For properties that are dicts, collect samples for each subkey
                                if isinstance(value, dict):
                                    for subkey, subvalue in value.items():
                                        prop_path = f"{key}.{subkey}"
                                        if prop_path not in sample_values:
                                            sample_values[prop_path] = []

                                        if (
                                            isinstance(
                                                subvalue, (str, int, float, bool)
                                            )
                                            and subvalue not in sample_values[prop_path]
                                        ):
                                            sample_values[prop_path].append(subvalue)

                    node_types[node_type].properties = properties
                    node_types[node_type].sample_values = sample_values
        else:
            # Standard ArangoDB database where each node type is its own collection
            # For document collections, we'll treat them as node types
            for collection in collections:
                collection_data = await asyncio.to_thread(
                    lambda: self._db.collection(collection)
                )
                collection_info = await asyncio.to_thread(
                    lambda: collection_data.properties()
                )

                # Check if this is a document collection (type 2)
                if collection_info["type"] == 2:  # Document collection
                    count = await asyncio.to_thread(lambda: collection_data.count())
                    node_types[collection] = NodeTypeMetadata(
                        name=collection,
                        count=count,
                    )

                    # Get sample documents to analyze properties
                    samples = await asyncio.to_thread(
                        lambda: [
                            doc for doc in collection_data.all(limit=self.sample_size)
                        ]
                    )

                    if samples:
                        properties = {}
                        sample_values = {}

                        # Analyze the first sample to get property types
                        sample = samples[0]
                        for key, value in sample.items():
                            if key not in ("_id", "_key", "_rev"):
                                properties[key] = type(value).__name__

                        # Collect sample values for each property
                        for sample in samples:
                            for key, value in sample.items():
                                if key not in ("_id", "_key", "_rev"):
                                    if key not in sample_values:
                                        sample_values[key] = []

                                    # Only add if the value is a simple type and not already in the list
                                    if (
                                        isinstance(value, (str, int, float, bool))
                                        and value not in sample_values[key]
                                    ):
                                        sample_values[key].append(value)

                        node_types[collection].properties = properties
                        node_types[collection].sample_values = sample_values

        return node_types

    async def discover_relationship_types(self) -> Dict[str, RelationshipMetadata]:
        """Discover relationship types between nodes.

        For SPOKE-style ArangoDB databases, this typically requires examining
        the 'Edges' collection and analyzing the 'label' field.

        Returns:
            Dictionary mapping relationship type names to their metadata
        """
        await self.connect()

        # Check if this is a SPOKE-style database with an 'Edges' collection
        collections = await asyncio.to_thread(
            lambda: [
                c["name"]
                for c in self._db.collections()
                if not c["name"].startswith("_")
            ]
        )

        relationship_types = {}

        if "Edges" in collections:
            # SPOKE-style database with a single 'Edges' collection
            # Relationship types are stored in the 'label' field
            aql_query = """
                FOR edge IN Edges
                COLLECT label = edge.label
                WITH COUNT INTO count
                RETURN {
                    label: label,
                    count: count
                }
            """

            cursor = await asyncio.to_thread(lambda: self._db.aql.execute(aql_query))
            results = await asyncio.to_thread(lambda: [doc for doc in cursor])

            for result in results:
                relationship_type = result["label"]
                relationship_types[relationship_type] = RelationshipMetadata(
                    name=relationship_type,
                    count=result["count"],
                )

                # Get sample relationships to analyze properties
                aql_query = f"""
                    FOR edge IN Edges
                    FILTER edge.label == "{relationship_type}"
                    LIMIT {self.sample_size}
                    RETURN {{
                        _from: edge._from,
                        _to: edge._to,
                        label: edge.label,
                        properties: edge.properties
                    }}
                """

                cursor = await asyncio.to_thread(
                    lambda: self._db.aql.execute(aql_query)
                )
                samples = await asyncio.to_thread(lambda: [doc for doc in cursor])

                if samples:
                    properties = {}
                    source_node_types = set()
                    target_node_types = set()
                    sample_sources = []
                    sample_targets = []

                    for sample in samples:
                        # For SPOKE, we need to extract the node type from the _from and _to IDs
                        source_id = sample["_from"]
                        target_id = sample["_to"]

                        # Add to sample lists
                        if source_id not in sample_sources:
                            sample_sources.append(source_id)
                        if target_id not in sample_targets:
                            sample_targets.append(target_id)

                        # Get node types for source and target
                        source_node_type = await self._get_node_type_for_id(source_id)
                        target_node_type = await self._get_node_type_for_id(target_id)

                        if source_node_type:
                            source_node_types.add(source_node_type)
                        if target_node_type:
                            target_node_types.add(target_node_type)

                        # Analyze properties
                        if "properties" in sample and isinstance(
                            sample["properties"], dict
                        ):
                            for key, value in sample["properties"].items():
                                properties[key] = type(value).__name__

                    relationship_types[relationship_type].properties = properties
                    relationship_types[
                        relationship_type
                    ].source_node_types = source_node_types
                    relationship_types[
                        relationship_type
                    ].target_node_types = target_node_types
                    relationship_types[
                        relationship_type
                    ].sample_sources = sample_sources
                    relationship_types[
                        relationship_type
                    ].sample_targets = sample_targets
        else:
            # Standard ArangoDB database where edge collections represent relationship types
            for collection in collections:
                collection_data = await asyncio.to_thread(
                    lambda: self._db.collection(collection)
                )
                collection_info = await asyncio.to_thread(
                    lambda: collection_data.properties()
                )

                # Check if this is an edge collection (type 3)
                if collection_info["type"] == 3:  # Edge collection
                    count = await asyncio.to_thread(lambda: collection_data.count())
                    relationship_types[collection] = RelationshipMetadata(
                        name=collection,
                        count=count,
                    )

                    # Get sample edges to analyze properties
                    samples = await asyncio.to_thread(
                        lambda: [
                            doc for doc in collection_data.all(limit=self.sample_size)
                        ]
                    )

                    if samples:
                        properties = {}
                        source_node_types = set()
                        target_node_types = set()
                        sample_sources = []
                        sample_targets = []

                        for sample in samples:
                            # Extract source and target
                            source_id = sample["_from"]
                            target_id = sample["_to"]

                            # Add to sample lists
                            if source_id not in sample_sources:
                                sample_sources.append(source_id)
                            if target_id not in sample_targets:
                                sample_targets.append(target_id)

                            # Extract collection names from IDs
                            source_collection = (
                                source_id.split("/")[0] if "/" in source_id else None
                            )
                            target_collection = (
                                target_id.split("/")[0] if "/" in target_id else None
                            )

                            if source_collection:
                                source_node_types.add(source_collection)
                            if target_collection:
                                target_node_types.add(target_collection)

                            # Analyze properties
                            for key, value in sample.items():
                                if key not in ("_id", "_key", "_rev", "_from", "_to"):
                                    properties[key] = type(value).__name__

                        relationship_types[collection].properties = properties
                        relationship_types[
                            collection
                        ].source_node_types = source_node_types
                        relationship_types[
                            collection
                        ].target_node_types = target_node_types
                        relationship_types[collection].sample_sources = sample_sources
                        relationship_types[collection].sample_targets = sample_targets

        return relationship_types

    async def identify_ontology_fields(
        self,
    ) -> Dict[str, List[Tuple[str, IdentifierConfidence]]]:
        """Identify fields that likely contain ontology identifiers.

        This method analyzes the properties and sample values of node types
        to identify fields that likely contain ontology identifiers.

        Returns:
            Dictionary mapping node type names to lists of (field_name, confidence) tuples
        """
        node_types = await self.discover_node_types()
        results = {}

        for node_type_name, metadata in node_types.items():
            field_confidences = []

            # Check field names first
            for field_name in metadata.properties:
                confidence = self._assess_field_name_confidence(field_name)
                if confidence != IdentifierConfidence.LOW:
                    field_confidences.append((field_name, confidence))

            # Then check sample values for patterns
            for field_name, samples in metadata.sample_values.items():
                if any(isinstance(sample, str) for sample in samples):
                    confidence = self._assess_sample_values_confidence(samples)
                    if confidence != IdentifierConfidence.LOW:
                        # Only add if not already added with higher confidence
                        existing = next(
                            (c for f, c in field_confidences if f == field_name), None
                        )
                        if existing is None or existing == IdentifierConfidence.LOW:
                            field_confidences.append((field_name, confidence))

            if field_confidences:
                results[node_type_name] = field_confidences

        return results

    async def sample_node_data(
        self, node_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get sample data for a specific node type.

        Args:
            node_type: The node type to sample
            limit: Maximum number of samples to return

        Returns:
            List of node data dictionaries
        """
        await self.connect()

        # Check if this is a SPOKE-style database
        collections = await asyncio.to_thread(
            lambda: [
                c["name"]
                for c in self._db.collections()
                if not c["name"].startswith("_")
            ]
        )

        samples = []

        if "Nodes" in collections:
            # SPOKE-style database
            aql_query = f"""
                FOR doc IN Nodes
                FILTER doc.type == "{node_type}"
                LIMIT {limit}
                RETURN doc
            """

            cursor = await asyncio.to_thread(lambda: self._db.aql.execute(aql_query))
            samples = await asyncio.to_thread(lambda: [doc for doc in cursor])
        elif node_type in collections:
            # Standard ArangoDB database where each node type is its own collection
            collection_data = await asyncio.to_thread(
                lambda: self._db.collection(node_type)
            )
            samples = await asyncio.to_thread(
                lambda: [doc for doc in collection_data.all(limit=limit)]
            )

        return samples

    async def sample_relationship_data(
        self, relationship_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get sample data for a specific relationship type.

        Args:
            relationship_type: The relationship type to sample
            limit: Maximum number of samples to return

        Returns:
            List of relationship data dictionaries
        """
        await self.connect()

        # Check if this is a SPOKE-style database
        collections = await asyncio.to_thread(
            lambda: [
                c["name"]
                for c in self._db.collections()
                if not c["name"].startswith("_")
            ]
        )

        samples = []

        if "Edges" in collections:
            # SPOKE-style database
            aql_query = f"""
                FOR edge IN Edges
                FILTER edge.label == "{relationship_type}"
                LIMIT {limit}
                RETURN edge
            """

            cursor = await asyncio.to_thread(lambda: self._db.aql.execute(aql_query))
            samples = await asyncio.to_thread(lambda: [doc for doc in cursor])
        elif relationship_type in collections:
            # Standard ArangoDB database where each relationship type is its own collection
            collection_data = await asyncio.to_thread(
                lambda: self._db.collection(relationship_type)
            )
            samples = await asyncio.to_thread(
                lambda: [doc for doc in collection_data.all(limit=limit)]
            )

        return samples

    async def _get_node_type_for_id(self, node_id: str) -> Optional[str]:
        """Get the node type for a given node ID.

        For SPOKE-style databases, we need to query the Nodes collection.
        For standard ArangoDB databases, the collection name is the node type.

        Args:
            node_id: The ID of the node

        Returns:
            Node type or None if not found
        """
        if "/" not in node_id:
            return None

        collection, key = node_id.split("/")

        # Check if this is a SPOKE-style database
        collections = await asyncio.to_thread(
            lambda: [
                c["name"]
                for c in self._db.collections()
                if not c["name"].startswith("_")
            ]
        )

        if "Nodes" in collections and collection == "Nodes":
            # SPOKE-style database, need to query the node
            aql_query = f"""
                FOR doc IN Nodes
                FILTER doc._key == "{key}"
                RETURN doc.type
            """

            cursor = await asyncio.to_thread(lambda: self._db.aql.execute(aql_query))
            results = await asyncio.to_thread(lambda: [doc for doc in cursor])
            return results[0] if results else None
        else:
            # Standard ArangoDB database, collection name is the node type
            return collection

    def _assess_field_name_confidence(self, field_name: str) -> IdentifierConfidence:
        """Assess confidence that a field name contains ontology identifiers.

        Args:
            field_name: The field name to analyze

        Returns:
            Confidence level
        """
        # Extract the last part of the field path
        parts = field_name.split(".")
        name = parts[-1].lower()

        # Check for common identifier field names
        high_confidence_patterns = [
            r"id$",
            r"^id_",
            "identifier",
            "accession",
            "chebi",
            "hmdb",
            "pubchem",
            "inchikey",
            "inchi",
            "smiles",
            "kegg",
            "uniprot",
            "ensembl",
            "gene_symbol",
            "symbol",
            "mondo",
            "doid",
            "mesh",
            "drugbank",
            "cas",
            "unii",
            "rxnorm",
            "ndc",
        ]

        medium_confidence_patterns = [
            "code",
            "reference",
            "external",
            "database",
            "ontology",
        ]

        # Check high confidence patterns
        for pattern in high_confidence_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return IdentifierConfidence.HIGH

        # Check medium confidence patterns
        for pattern in medium_confidence_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return IdentifierConfidence.MEDIUM

        return IdentifierConfidence.LOW

    def _assess_sample_values_confidence(
        self, samples: List[Any]
    ) -> IdentifierConfidence:
        """Assess confidence that sample values match ontology identifier patterns.

        Args:
            samples: List of sample values

        Returns:
            Confidence level
        """
        # Convert samples to strings and filter out None values
        str_samples = [str(s) for s in samples if s is not None]
        if not str_samples:
            return IdentifierConfidence.LOW

        # Count matches for each pattern
        matches = {}
        for pattern_name, pattern in self._ontology_patterns.items():
            match_count = sum(1 for s in str_samples if pattern.match(s))
            if match_count > 0:
                matches[pattern_name] = match_count / len(str_samples)

        # If any pattern matches more than 50% of samples, high confidence
        if any(ratio >= 0.5 for ratio in matches.values()):
            return IdentifierConfidence.HIGH

        # If any pattern matches at all, medium confidence
        if matches:
            return IdentifierConfidence.MEDIUM

        return IdentifierConfidence.LOW

    def _compile_ontology_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for ontology identifiers.

        Returns:
            Dictionary of compiled patterns
        """
        patterns = {
            "chebi": r"^CHEBI:\d+$",
            "hmdb": r"^HMDB\d+$",
            "pubchem": r"^CID\d+$",
            "inchikey": r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$",
            "uniprot": r"^[A-Z\d]{6,10}$",
            "ensembl": r"^ENS[A-Z]*\d+$",
            "kegg": r"^C\d{5}$",
            "drugbank": r"^DB\d{5}$",
            "cas": r"^\d{1,7}-\d{2}-\d$",
            "mesh": r"^[A-Z]\d{6}$",
            "mondo": r"^MONDO:\d{7}$",
            "doid": r"^DOID:\d+$",
            "unii": r"^[A-Z0-9]{10}$",
        }

        return {name: re.compile(pattern) for name, pattern in patterns.items()}


class SPOKEGraphAnalyzer(ArangoDBGraphAnalyzer):
    """Specialized analyzer for SPOKE knowledge graph.

    This is a convenience class that pre-configures the ArangoDBGraphAnalyzer
    for the SPOKE schema.
    """

    def __init__(
        self,
        config: Optional[SPOKEConfig] = None,
        sample_size: int = 5,
    ):
        """Initialize the SPOKE graph analyzer.

        Args:
            config: SPOKE configuration
            sample_size: Default sample size for data exploration
        """
        if config is None:
            config = SPOKEConfig(
                host="localhost",
                port=8529,
                database="spoke23_human",
            )

        super().__init__(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            database=config.database,
            use_ssl=config.use_ssl,
            sample_size=sample_size,
        )
