"""ArangoDB implementation of the BaseArango interface."""

from typing import Any, Dict, List, Optional, Set, Tuple, cast
from pyArango.connection import Connection
from pyArango.database import Database
from pyArango.document import Document
from pyArango.theExceptions import DocumentNotFoundError

from .base_arango import (
    BaseArango,
    ArangoNode,
    ArangoEdge,
    ArangoQuery,
    ArangoResult,
)


class ArangoStore(BaseArango):
    """ArangoDB implementation of the graph store."""

    def __init__(
        self,
        username: str = "root",
        password: str = "ph",
        database: str = "spoke_human",
        host: str = "localhost",
        port: int = 8529,
    ) -> None:
        """Initialize ArangoDB connection.
        
        Args:
            username: ArangoDB username
            password: ArangoDB password
            database: Database name
            host: Database host
            port: Database port
        """
        self.username = username
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.conn: Optional[Connection] = None
        self.db: Optional[Database] = None

    async def connect(self) -> None:
        """Establish connection to ArangoDB database."""
        self.conn = Connection(
            username=self.username,
            password=self.password,
            arangoURL=f"http://{self.host}:{self.port}"
        )
        
        # Get or create database
        if not self.conn.hasDatabase(self.database):
            self.conn.createDatabase(name=self.database)
        self.db = self.conn[self.database]

        # Ensure collections exist
        if not self.db.hasCollection("Nodes"):
            self.db.createCollection(name="Nodes")
        if not self.db.hasCollection("Edges"):
            self.db.createCollection(name="Edges", className="Edges", type=3)

    async def close(self) -> None:
        """Close connection to ArangoDB database."""
        self.conn = None
        self.db = None

    def _doc_to_node(self, doc: Document) -> ArangoNode:
        """Convert ArangoDB document to ArangoNode."""
        return ArangoNode(
            id=doc["_key"],
            type=doc["type"],
            name=doc.get("name", ""),
            properties={
                k: v for k, v in doc.items()
                if k not in ["_key", "_id", "_rev", "type", "name"]
            }
        )

    def _doc_to_edge(self, doc: Document) -> ArangoEdge:
        """Convert ArangoDB document to ArangoEdge."""
        return ArangoEdge(
            source_id=doc["_from"].split("/")[1],  # Remove "Nodes/" prefix
            target_id=doc["_to"].split("/")[1],    # Remove "Nodes/" prefix
            type=doc["type"],
            properties={
                k: v for k, v in doc.items()
                if k not in ["_key", "_id", "_rev", "_from", "_to", "type"]
            }
        )

    async def get_node(self, node_id: str) -> Optional[ArangoNode]:
        """Get a node by its ID."""
        if not self.db:
            raise RuntimeError("Not connected to database")
        
        try:
            doc = self.db["Nodes"][node_id]
            return self._doc_to_node(doc)
        except DocumentNotFoundError:
            return None

    async def get_node_by_property(
        self,
        node_type: str,
        property_name: str,
        property_value: Any
    ) -> Optional[ArangoNode]:
        """Get a node by a property value."""
        if not self.db:
            raise RuntimeError("Not connected to database")

        aql = f"""
        FOR doc IN Nodes
            FILTER doc.type == @node_type
            AND doc.{property_name} == @property_value
            LIMIT 1
            RETURN doc
        """
        
        bind_vars = {
            "node_type": node_type,
            "property_value": property_value
        }
        
        cursor = self.db.AQLQuery(
            aql,
            bindVars=bind_vars,
            rawResults=True
        )
        
        if cursor:
            doc = cursor[0]
            return ArangoNode(
                id=doc["_key"],
                type=doc["type"],
                name=doc.get("name", ""),
                properties={
                    k: v for k, v in doc.items()
                    if k not in ["_key", "_id", "_rev", "type", "name"]
                }
            )
        return None

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None,
    ) -> List[Tuple[ArangoEdge, ArangoNode]]:
        """Get neighbors of a node."""
        if not self.db:
            raise RuntimeError("Not connected to database")

        # Build edge type filter
        edge_filter = ""
        if edge_types:
            edge_types_str = ", ".join([f"'{t}'" for t in edge_types])
            edge_filter = f"AND edge.type IN [{edge_types_str}]"

        # Build node type filter
        node_filter = ""
        if node_types:
            node_types_str = ", ".join([f"'{t}'" for t in node_types])
            node_filter = f"AND neighbor.type IN [{node_types_str}]"

        aql = f"""
        FOR edge IN Edges
            FILTER (edge._from == @node_id OR edge._to == @node_id)
            {edge_filter}
            LET neighbor = DOCUMENT(
                edge._from == @node_id ? edge._to : edge._from
            )
            {node_filter}
            RETURN {{edge: edge, neighbor: neighbor}}
        """

        bind_vars = {
            "node_id": f"Nodes/{node_id}"
        }

        cursor = self.db.AQLQuery(
            aql,
            bindVars=bind_vars,
            rawResults=True
        )

        results = []
        for item in cursor:
            edge = self._doc_to_edge(item["edge"])
            node = self._doc_to_node(item["neighbor"])
            results.append((edge, node))

        return results

    async def find_paths(
        self,
        query: ArangoQuery,
    ) -> ArangoResult:
        """Find paths between node types."""
        if not self.db:
            raise RuntimeError("Not connected to database")

        # Build relationship filter
        rel_filter = ""
        if query.relationship_types:
            rel_types_str = ", ".join([f"'{t}'" for t in query.relationship_types])
            rel_filter = f"AND edge.type IN [{rel_types_str}]"

        # Build property filter
        prop_filter = ""
        if query.properties:
            filters = []
            for key, value in query.properties.items():
                filters.append(f"vertex.{key} == {json.dumps(value)}")
            if filters:
                prop_filter = "AND " + " AND ".join(filters)

        aql = f"""
        FOR start IN Nodes
            FILTER start.type == @start_type
            FOR end IN Nodes
                FILTER end.type == @end_type
                FOR path IN OUTBOUND SHORTEST_PATH
                    start TO end
                    Edges
                    OPTIONS {{maxDepth: @max_depth}}
                    FILTER IS_SAME_COLLECTION("Nodes", path.vertices[*])
                    {rel_filter}
                    {prop_filter}
                    RETURN {{
                        vertices: path.vertices,
                        edges: path.edges
                    }}
        """

        bind_vars = {
            "start_type": query.start_node_type,
            "end_type": query.end_node_type,
            "max_depth": query.max_path_length
        }

        cursor = self.db.AQLQuery(
            aql,
            bindVars=bind_vars,
            rawResults=True
        )

        # Collect unique nodes and edges
        nodes_dict = {}
        edges_dict = {}
        paths = []

        for path in cursor:
            path_nodes = []
            
            # Process vertices
            for vertex in path["vertices"]:
                node = self._doc_to_node(vertex)
                nodes_dict[node.id] = node
                path_nodes.append(node.id)

            # Process edges
            for edge in path["edges"]:
                edge_obj = self._doc_to_edge(edge)
                edge_key = f"{edge_obj.source_id}-{edge_obj.target_id}"
                edges_dict[edge_key] = edge_obj

            paths.append(path_nodes)

        return ArangoResult(
            nodes=list(nodes_dict.values()),
            edges=list(edges_dict.values()),
            paths=paths
        )

    async def get_node_types(self) -> Set[str]:
        """Get all available node types."""
        if not self.db:
            raise RuntimeError("Not connected to database")

        aql = """
        RETURN UNIQUE(
            FOR doc IN Nodes
                RETURN doc.type
        )
        """
        
        cursor = self.db.AQLQuery(aql, rawResults=True)
        return set(cursor[0])

    async def get_edge_types(self) -> Set[str]:
        """Get all available edge types."""
        if not self.db:
            raise RuntimeError("Not connected to database")

        aql = """
        RETURN UNIQUE(
            FOR edge IN Edges
                RETURN edge.type
        )
        """
        
        cursor = self.db.AQLQuery(aql, rawResults=True)
        return set(cursor[0])
