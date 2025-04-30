"""
SPOKE Knowledge Graph Adapter for Biomapper Resource Metadata System.

This module provides an adapter for interacting with the SPOKE knowledge graph,
following the ResourceAdapter and KnowledgeGraphClient protocols.
"""

import time
import logging
import asyncio
from typing import Dict, List, Any, Optional

from arango import ArangoClient
from arango.database import Database

from biomapper.mapping.metadata.interfaces import (
    BaseResourceAdapter,
    KnowledgeGraphClient,
)

logger = logging.getLogger(__name__)


class SpokeClient:
    """
    Client for interacting with the SPOKE knowledge graph.

    This class implements the KnowledgeGraphClient protocol for SPOKE.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SPOKE client.

        Args:
            config: Configuration dictionary with keys:
                - host: ArangoDB host
                - port: ArangoDB port
                - db_name: Database name
                - username: ArangoDB username
                - password: ArangoDB password
        """
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 8529)
        self.db_name = config.get("db_name", "spoke")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.client = None
        self.db = None

    async def connect(self) -> bool:
        """
        Connect to SPOKE ArangoDB instance.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Connect to ArangoDB, run in thread to avoid blocking
            return await asyncio.to_thread(self._connect_sync)
        except Exception as e:
            logger.error(f"Error connecting to SPOKE: {e}")
            return False

    def _connect_sync(self) -> bool:
        """Synchronous implementation of connect."""
        self.client = ArangoClient(host=f"http://{self.host}:{self.port}")
        self.db = self.client.db(
            self.db_name, username=self.username, password=self.password
        )
        return self.db is not None

    async def get_entity(
        self, identifier: str, entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an entity by identifier and type.

        Args:
            identifier: Entity identifier
            entity_type: Entity type (e.g., 'Compound', 'Gene', 'Protein')

        Returns:
            Entity data, or None if not found
        """
        if not self.db:
            if not await self.connect():
                return None

        # Execute in a thread to avoid blocking the event loop
        return await asyncio.to_thread(self._get_entity_sync, identifier, entity_type)

    def _get_entity_sync(
        self, identifier: str, entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """Synchronous implementation of get_entity."""
        try:
            # Determine how to search for the entity based on entity_type
            aql_filters = []
            if entity_type.lower() == "compound":
                # Check multiple identifier types for compounds
                aql_filters = [
                    "node.type == 'Compound'",
                    f"(node.properties.chebi == '{identifier}' OR "
                    + f"node.properties.hmdb == '{identifier}' OR "
                    + f"node.properties.pubchem == '{identifier}' OR "
                    + f"node.properties.drugbank == '{identifier}' OR "
                    + f"node.properties.inchikey == '{identifier}')",
                ]
            elif entity_type.lower() == "gene":
                aql_filters = [
                    "node.type == 'Gene'",
                    f"(node.properties.entrez == '{identifier}' OR "
                    + f"node.name == '{identifier}')",
                ]
            elif entity_type.lower() == "protein":
                aql_filters = [
                    "node.type == 'Protein'",
                    f"node.properties.uniprot == '{identifier}'",
                ]
            elif entity_type.lower() == "disease":
                aql_filters = [
                    "node.type == 'Disease'",
                    f"(node.properties.mondo == '{identifier}' OR "
                    + f"node.properties.doid == '{identifier}' OR "
                    + f"node.properties.mesh == '{identifier}')",
                ]
            else:
                # Generic approach for other entity types
                aql_filters = [
                    f"node.type == '{entity_type}'",
                    f"node.name == '{identifier}'",
                ]

            # Build and execute AQL query
            aql = f"""
            FOR node IN Nodes
              FILTER {" AND ".join(aql_filters)}
              RETURN {{
                id: node._key,
                type: node.type,
                name: node.name,
                properties: node.properties
              }}
            """

            cursor = self.db.aql.execute(aql)
            results = list(cursor)

            return results[0] if results else None

        except Exception as e:
            logger.error(f"Error retrieving entity from SPOKE: {e}")
            return None

    async def map_identifier(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """
        Map an identifier from source_type to target_type.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type

        Returns:
            List of target identifiers with confidence scores
        """
        if not self.db:
            if not await self.connect():
                return []

        # Execute in a thread to avoid blocking the event loop
        return await asyncio.to_thread(
            self._map_identifier_sync, source_id, source_type, target_type
        )

    def _map_identifier_sync(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """Synchronous implementation of map_identifier."""
        try:
            # Handle different mapping scenarios

            # Case 1: Same entity, different identifier types
            if self._is_same_entity_mapping(source_type, target_type):
                return self._map_within_entity(source_id, source_type, target_type)

            # Case 2: Different entities with relationship
            else:
                return self._map_between_entities(source_id, source_type, target_type)

        except Exception as e:
            logger.error(f"Error mapping identifier in SPOKE: {e}")
            return []

    def _is_same_entity_mapping(self, source_type: str, target_type: str) -> bool:
        """Determine if source and target are different identifiers for the same entity type."""
        # Check if these are different identifier types for the same entity

        # Compound identifiers
        compound_identifiers = {
            "chebi",
            "hmdb",
            "pubchem",
            "drugbank",
            "inchikey",
            "compound_name",
        }
        if source_type in compound_identifiers and target_type in compound_identifiers:
            return True

        # Gene identifiers
        gene_identifiers = {"entrez", "gene_symbol", "ensembl", "hgnc"}
        if source_type in gene_identifiers and target_type in gene_identifiers:
            return True

        # Protein identifiers
        protein_identifiers = {"uniprot", "pdb", "interpro"}
        if source_type in protein_identifiers and target_type in protein_identifiers:
            return True

        # Disease identifiers
        disease_identifiers = {"mondo", "doid", "mesh", "omim", "disgenet"}
        if source_type in disease_identifiers and target_type in disease_identifiers:
            return True

        return False

    def _map_within_entity(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """Map between different identifier types within the same entity."""
        entity_type = self._get_entity_type_for_identifier(source_type)
        if not entity_type:
            return []

        # Get property field for source and target types
        source_prop = self._get_property_field(source_type)
        target_prop = self._get_property_field(target_type)

        if not source_prop or not target_prop:
            return []

        # Build AQL query
        aql = f"""
        FOR node IN Nodes
          FILTER node.type == '{entity_type}'
            AND node.properties.{source_prop} == '{source_id}'
            AND node.properties.{target_prop} != null
          RETURN {{
            target_id: node.properties.{target_prop},
            confidence: 1.0,
            source: 'spoke_direct'
          }}
        """

        cursor = self.db.aql.execute(aql)
        results = list(cursor)

        # For compound names, handle differently
        if source_type == "compound_name" or target_type == "compound_name":
            if source_type == "compound_name":
                # Search by name
                aql = f"""
                FOR node IN Nodes
                  FILTER node.type == 'Compound'
                    AND node.name == '{source_id}'
                    AND node.properties.{target_prop} != null
                  RETURN {{
                    target_id: node.properties.{target_prop},
                    confidence: 0.9,
                    source: 'spoke_name_match'
                  }}
                """
            else:
                # Return name as target
                aql = f"""
                FOR node IN Nodes
                  FILTER node.type == 'Compound'
                    AND node.properties.{source_prop} == '{source_id}'
                  RETURN {{
                    target_id: node.name,
                    confidence: 0.9,
                    source: 'spoke_name_match'
                  }}
                """

            cursor = self.db.aql.execute(aql)
            results.extend(list(cursor))

        return results

    def _map_between_entities(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """Map between different entity types using graph relationships."""
        source_entity = self._get_entity_type_for_identifier(source_type)
        target_entity = self._get_entity_type_for_identifier(target_type)

        if not source_entity or not target_entity:
            return []

        source_prop = self._get_property_field(source_type)
        target_prop = self._get_property_field(target_type)

        if not source_prop:
            # Try using the name for matching
            if source_type.endswith("_name"):
                source_prop = "name"
            else:
                return []

        if not target_prop:
            # Try using the name for matching
            if target_type.endswith("_name"):
                target_prop = "name"
            else:
                return []

        # Find paths between entities
        # This is a simplified query, a real implementation would need to handle
        # different relationship types and path lengths
        aql = f"""
        FOR source IN Nodes
          FILTER source.type == '{source_entity}'
            AND source.{"name" if source_prop == "name" else "properties." + source_prop} == '{source_id}'
          
          FOR target IN 1..2 OUTBOUND source Edges
            FILTER target.type == '{target_entity}'
              AND target.{"name" if target_prop == "name" else "properties." + target_prop} != null
              
            LET edge = (
              FOR e IN Edges
                FILTER e._from == source._id AND e._to == target._id
                LIMIT 1
                RETURN e
            )[0]
            
            RETURN {{
              target_id: target.{"name" if target_prop == "name" else "properties." + target_prop},
              confidence: 0.8,
              source: 'spoke_relationship',
              relationship: edge.label
            }}
        """

        cursor = self.db.aql.execute(aql)
        results = list(cursor)

        return results

    def _get_entity_type_for_identifier(self, identifier_type: str) -> Optional[str]:
        """Get SPOKE entity type for a given identifier type."""
        # Map identifier types to SPOKE entity types
        mappings = {
            # Compound identifiers
            "chebi": "Compound",
            "hmdb": "Compound",
            "pubchem": "Compound",
            "drugbank": "Compound",
            "inchikey": "Compound",
            "compound_name": "Compound",
            # Gene identifiers
            "entrez": "Gene",
            "gene_symbol": "Gene",
            "ensembl": "Gene",
            "hgnc": "Gene",
            # Protein identifiers
            "uniprot": "Protein",
            "pdb": "Protein",
            "interpro": "Protein",
            # Disease identifiers
            "mondo": "Disease",
            "doid": "Disease",
            "mesh": "Disease",
            "omim": "Disease",
            "disgenet": "Disease",
            # Pathway identifiers
            "reactome": "Pathway",
            "kegg": "Pathway",
            "go": "Pathway",
        }

        return mappings.get(identifier_type.lower())

    def _get_property_field(self, identifier_type: str) -> Optional[str]:
        """Get the property field name in SPOKE for a given identifier type."""
        # Map identifier types to SPOKE property fields
        mappings = {
            "chebi": "chebi",
            "hmdb": "hmdb",
            "pubchem": "pubchem",
            "drugbank": "drugbank",
            "inchikey": "inchikey",
            "entrez": "entrez",
            "gene_symbol": "symbol",
            "ensembl": "ensembl",
            "uniprot": "uniprot",
            "pdb": "pdb",
            "mondo": "mondo",
            "doid": "doid",
            "mesh": "mesh",
            "omim": "omim",
            "reactome": "reactome",
            "kegg": "kegg",
        }

        return mappings.get(identifier_type.lower())

    def get_supported_entity_types(self) -> List[str]:
        """
        Get the entity types supported by SPOKE.

        Returns:
            List of supported entity types
        """
        return [
            "Compound",
            "Gene",
            "Protein",
            "Disease",
            "Pathway",
            "Anatomy",
            "Food",
            "Symptom",
        ]


class SpokeResourceAdapter(BaseResourceAdapter):
    """
    Adapter for the SPOKE knowledge graph.

    This adapter provides access to the SPOKE knowledge graph,
    allowing for mapping operations using graph-based approaches.
    """

    def __init__(self, config: Dict[str, Any], name: str = "spoke_graph"):
        """
        Initialize the SPOKE adapter.

        Args:
            config: Configuration dictionary for SPOKE connection
            name: Name of the resource (default: "spoke_graph")
        """
        super().__init__(config, name)
        self.spoke_client = SpokeClient(config)

    async def connect(self) -> bool:
        """
        Connect to the SPOKE knowledge graph.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        connected = await self.spoke_client.connect()
        self.is_connected = connected
        return connected

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Map an entity using the SPOKE knowledge graph.

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

        return await self.spoke_client.map_identifier(
            source_id, source_type, target_type
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this resource.

        Returns:
            Dictionary describing the resource's capabilities
        """
        return {
            "name": self.name,
            "type": "graph",
            "supports_batch": False,
            "supports_async": True,
            "max_batch_size": 1,
            "supports_relationships": True,
            "entity_types": self.spoke_client.get_supported_entity_types(),
        }
