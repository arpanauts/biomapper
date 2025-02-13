"""Script to explore ArangoDB data for testing."""

from pyArango.connection import Connection
import json

def main():
    """Main function to explore data."""
    # Connect to ArangoDB
    conn = Connection(
        username="root",
        password="ph",
        arangoURL="http://localhost:8529"
    )
    db = conn["spoke_human"]
    
    # Get a sample compound node
    aql = """
    FOR doc IN Nodes
        FILTER doc.type == 'Compound'
        LIMIT 1
        RETURN doc
    """
    cursor = db.AQLQuery(aql, rawResults=True)
    if cursor:
        compound = cursor[0]
        print("\nSample Compound Node:")
        print(json.dumps(compound, indent=2))
        
        # Get neighbors of this compound
        compound_id = compound["_key"]
        aql = f"""
        FOR edge IN Edges
            FILTER edge._from == 'Nodes/{compound_id}' OR edge._to == 'Nodes/{compound_id}'
            LET neighbor = DOCUMENT(
                edge._from == 'Nodes/{compound_id}' ? edge._to : edge._from
            )
            RETURN {{edge: edge, neighbor: neighbor}}
        """
        cursor = db.AQLQuery(aql, rawResults=True)
        print("\nNeighbors:")
        for item in cursor:
            print("\nEdge:", json.dumps(item["edge"], indent=2))
            print("Neighbor:", json.dumps(item["neighbor"], indent=2))
    
    # Get node types
    aql = """
    RETURN UNIQUE(
        FOR doc IN Nodes
            RETURN doc.type
    )
    """
    cursor = db.AQLQuery(aql, rawResults=True)
    print("\nNode Types:", cursor[0])
    
    # Get edge types
    aql = """
    RETURN UNIQUE(
        FOR edge IN Edges
            RETURN edge.type
    )
    """
    cursor = db.AQLQuery(aql, rawResults=True)
    print("\nEdge Types:", cursor[0])

if __name__ == "__main__":
    main()
