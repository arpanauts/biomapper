"""Tutorial demonstrating the usage of the MetaboAnalystClient."""

from biomapper.mapping.clients.metaboanalyst_client import MetaboAnalystClient


def print_result(result):
    """Print details of a mapping result."""
    print(f"\nInput: {result.input_id}")
    if result.match_found:
        print(f"  Name: {result.name}")
        print(f"  HMDB ID: {result.hmdb_id}")
        print(f"  PubChem ID: {result.pubchem_id}")
        print(f"  ChEBI ID: {result.chebi_id}")
        print(f"  KEGG ID: {result.kegg_id}")
        print(f"  METLIN ID: {result.metlin_id}")
    else:
        print("  No match found")


def main():
    """Demonstrate MetaboAnalyst compound mapping."""
    print("MetaboAnalyst Compound Mapping Tutorial")
    print("--------------------------------------")

    # Initialize the client
    client = MetaboAnalystClient()

    # Example 1: Map compounds by name
    print("\nExample 1: Map compounds by name")
    print("-" * 40)
    compounds = [
        "1,3-Diaminopropane",
        "2-Ketobutyric acid",
        "2-Hydroxybutyric acid",
        "Glucose",
    ]

    try:
        results = client.map_compounds(compounds, input_type="name")

        # Print the results
        for result in results:
            print_result(result)
    except Exception as e:
        print(f"Error mapping compounds: {e}")

    # Example 2: Map compounds by HMDB ID
    print("\nExample 2: Map compounds by HMDB ID")
    print("-" * 40)
    hmdb_ids = ["HMDB0000002", "HMDB0000122", "HMDB0001847"]

    try:
        results = client.map_compounds(hmdb_ids, input_type="hmdb")

        # Print the results
        for result in results:
            print_result(result)
    except Exception as e:
        print(f"Error mapping HMDB IDs: {e}")

    # Example 3: Map compounds by ChEBI ID
    print("\nExample 3: Map compounds by ChEBI ID")
    print("-" * 40)
    chebi_ids = ["15725", "17234", "27732"]

    try:
        results = client.map_compounds(chebi_ids, input_type="chebi")

        # Print the results
        for result in results:
            print_result(result)
    except Exception as e:
        print(f"Error mapping ChEBI IDs: {e}")


if __name__ == "__main__":
    main()
