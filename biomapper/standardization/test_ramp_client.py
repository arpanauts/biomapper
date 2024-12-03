# test_ramp_client.py

from ramp_client import RaMPClient, RaMPAPIError
import json

def print_response(description: str, response: dict):
    """Pretty print an API response with a description"""
    print(f"\n{description}")
    print("-" * len(description))
    print(json.dumps(response, indent=2))
    print("\n")

def main():
    # Initialize the client
    print("Initializing RaMP client...")
    client = RaMPClient()

    # Test 1: Get source versions
    try:
        print("\nTesting source versions endpoint...")
        versions = client.get_source_versions()
        print_response("Source Versions:", versions)
    except RaMPAPIError as e:
        print(f"Error getting source versions: {e}")

    # Test 2: Get ID types
    try:
        print("\nTesting ID types endpoint...")
        id_types = client.get_id_types()
        print_response("ID Types:", id_types)
    except RaMPAPIError as e:
        print(f"Error getting ID types: {e}")

    # Test 3: Get chemical properties for some example metabolites
    test_metabolites = [
        "hmdb:HMDB0000064",  # Creatine
        "hmdb:HMDB0000148",  # L-Glutamic acid
    ]

    try:
        print("\nTesting chemical properties endpoint...")
        properties = client.get_chemical_properties(test_metabolites)
        print_response("Chemical Properties:", properties)
    except RaMPAPIError as e:
        print(f"Error getting chemical properties: {e}")

    # Test 4: Get pathways for these metabolites
    try:
        print("\nTesting pathways endpoint...")
        response = client.get_pathways_from_analytes(test_metabolites)
        
        # First let's see the raw response structure
        print("\nRaw Pathway Response:")
        print(json.dumps(response, indent=2))
        
        print("\nProcessed Pathway Information:")
        print("============================")
        
        if isinstance(response, dict):
            # Handle different potential response structures
            pathway_data = response.get('data') or response.get('result')
            if pathway_data:
                # Group pathways by metabolite ID
                pathways_by_metabolite = {}
                for pathway in pathway_data:
                    metabolite_id = pathway.get("inputId")
                    if metabolite_id not in pathways_by_metabolite:
                        pathways_by_metabolite[metabolite_id] = []
                    pathways_by_metabolite[metabolite_id].append(pathway)
                
                # Print grouped pathways
                for metabolite_id, pathways in pathways_by_metabolite.items():
                    print(f"\nMetabolite: {metabolite_id}")
                    if pathways:
                        print(f"Common name: {pathways[0].get('commonName', 'N/A')}")
                        print(f"Number of pathways: {len(pathways)}")
                        print("\nPathways:")
                        for i, pathway in enumerate(pathways, 1):
                            print(f"\n{i}. {pathway.get('pathwayName', 'N/A')}")
                            print(f"   Source: {pathway.get('pathwaySource', 'N/A')}")
                            print(f"   ID: {pathway.get('pathwayId', 'N/A')}")
                    print("-" * 50)
            
            # Analyze pathway statistics
            print("\nPathway Statistics:")
            print("==================")
            stats = client.analyze_pathway_stats(response)
            for metabolite_id, stat in stats.items():
                print(f"\nMetabolite: {metabolite_id}")
                print(f"Total pathways: {stat.total_pathways}")
                print("\nPathways by source:")
                for source, count in stat.pathways_by_source.items():
                    print(f"  {source}: {count}")
                
            # Find pathway overlaps
            print("\nPathway Overlaps:")
            print("================")
            overlaps = client.find_pathway_overlaps(response)
            shared_pathways = {k: v for k, v in overlaps.items() if v > 1}
            if shared_pathways:
                print("\nPathways shared between metabolites:")
                for pathway, count in shared_pathways.items():
                    print(f"- {pathway} (shared by {count} metabolites)")
            
            # Print API stats
            if "numFoundIds" in response:
                print(f"\nTotal IDs found: {response['numFoundIds'][0]}")
            if "function_call" in response:
                print(f"RaMP function: {response['function_call'][0]}")
        else:
            print("Unexpected response format")
            
    except RaMPAPIError as e:
        print(f"Error getting pathways: {e}")

if __name__ == "__main__":
    print("Starting RaMP client tests...")
    main()
    print("\nTests completed.")