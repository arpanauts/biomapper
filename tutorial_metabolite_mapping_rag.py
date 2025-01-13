
# %%

import os
from biomapper.mapping.metabolite_name_mapper import MetaboliteNameMapper

# Create mapper
mapper = MetaboliteNameMapper()

# Map a single name
result = mapper.map_single_name("glucose")
print(result)

# Map a list of names
results = mapper.map_from_names(["glucose", "cholesterol"])
print(results)

# Map from a file
df = mapper.map_from_file(
    "/home/trentleslie/github/biomapper/UKBB_NMR_Meta.tsv",
    name_column="title",
    output_path="mapped_metabolites.csv",
)

# Get mapping statistics
mappings = [
    mapper.map_single_name(name) 
    for name in df["title"].tolist()
]
mapper.print_mapping_report(mappings)

# %%

import requests
from biomapper.mapping.unichem_client import UniChemClient

def get_inchikey_from_pubchem(pubchem_id: str) -> str | None:
    """Get InChIKey from PubChem using their REST API"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{pubchem_id}/property/InChIKey/TXT"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException:
        return None


# Initialize client
client = UniChemClient()

# Example with first metabolite
hmdb_id = "HMDB01301"  # S-1-pyrroline-5-carboxylate
pubchem_id = "1196"

# Get InChIKey from PubChem first
inchikey = get_inchikey_from_pubchem(pubchem_id)
if inchikey:
    try:
        ids = client.get_compound_info_by_inchikey(inchikey)
        print(f"InChIKey: {inchikey}")
        print(f"Identifiers found via UniChem: {ids}")
    except Exception as e:
        print(f"Error with UniChem lookup: {e}")
else:
    print("Could not find InChIKey")


#%%
# arivale mapping
import pandas as pd
import requests
from time import sleep
from typing import Dict, Optional
from tqdm import tqdm
from biomapper.mapping.unichem_client import UniChemClient

def get_inchikey_from_pubchem(pubchem_id: str) -> Optional[str]:
    """Get InChIKey from PubChem using their REST API"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{pubchem_id}/property/InChIKey/TXT"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException:
        return None

def process_metabolites_file(filepath: str, output_path: str) -> None:
    """
    Process metabolites CSV file and add InChIKey column
    
    Args:
        filepath: Path to input CSV file
        output_path: Path to save augmented CSV file
    """
    # Read CSV file
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} compounds from {filepath}")
    
    # Initialize UniChem client
    client = UniChemClient()
    
    # Create new column for InChIKeys
    inchikeys: Dict[int, Optional[str]] = {}
    
    # Process each row with progress bar
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Fetching InChIKeys"):
        chemical_id = row['CHEMICAL_ID']
        
        # Skip if PubChem ID is missing
        if pd.isna(row['PUBCHEM']):
            inchikeys[chemical_id] = None
            continue
            
        # Convert PubChem ID to integer by removing decimal
        pubchem_id = str(int(row['PUBCHEM']))
        
        # Get InChIKey from PubChem
        inchikey = get_inchikey_from_pubchem(pubchem_id)
        
        # Store result
        inchikeys[chemical_id] = inchikey
        
        # Add small delay to be nice to PubChem API
        sleep(0.1)
    
    # Add InChIKey column to dataframe
    df['INCHIKEY'] = df['CHEMICAL_ID'].map(inchikeys)
    
    # Save augmented dataframe
    df.to_csv(output_path, index=False)
    print(f"\nSaved results to {output_path}")

if __name__ == "__main__":
    input_file = "arivale_metabolites.csv"
    output_file = "arivale_metabolites_with_inchikey.csv"
    process_metabolites_file(input_file, output_file)


# %%
import pandas as pd
from biomapper.mapping.unichem_client import UniChemClient

# Initialize the client
client = UniChemClient()


def analyze_metabolites(
    metabolites_df: pd.DataFrame, inchikey_column: str, dataset_name: str
) -> tuple[dict, pd.DataFrame]:
    """
    Analyze metabolites using UniChem API.

    Args:
        metabolites_df: DataFrame containing metabolites
        inchikey_column: Name of column containing InChIKeys
        dataset_name: Name of the dataset for reporting

    Returns:
        Tuple of (summary_stats, mapped_ids_df)
    """
    print(f"\nAnalyzing {dataset_name} metabolites...")

    # Get unique InChIKeys
    unique_inchikeys = pd.Series(metabolites_df[inchikey_column].unique())
    valid_inchikeys = unique_inchikeys[unique_inchikeys.notna()]

    print(f"Total unique InChIKeys: {len(unique_inchikeys)}")
    print(f"Valid InChIKeys: {len(valid_inchikeys)}")

    # Initialize results collection
    all_mappings = []

    # Process each InChIKey
    for inchikey in valid_inchikeys:
        try:
            result = client.get_compound_info_by_inchikey(inchikey)
            result["inchikey"] = inchikey
            all_mappings.append(result)
        except Exception as e:
            print(f"Error processing {inchikey}: {str(e)}")

    # Convert results to DataFrame
    mapped_df = pd.DataFrame(all_mappings)

    # Calculate summary statistics
    summary = {
        "total_compounds": len(unique_inchikeys),
        "mapped_compounds": len(mapped_df),
        "chembl_mapped": mapped_df["chembl_ids"].apply(len).sum(),
        "chebi_mapped": mapped_df["chebi_ids"].apply(len).sum(),
        "pubchem_mapped": mapped_df["pubchem_ids"].apply(len).sum(),
        "kegg_mapped": mapped_df["kegg_ids"].apply(len).sum(),
        "hmdb_mapped": mapped_df["hmdb_ids"].apply(len).sum(),
    }

    return summary, mapped_df


# Example usage:
# Load your metabolite datasets
# Note: Replace these paths with your actual file paths
arivale_metabolites = pd.read_csv(
    "/home/trentleslie/github/biomapper/arivale_metabolites.csv"
)
ukbb_metabolites = pd.read_csv("/path/to/ukbb_metabolites.csv")

# Analyze both datasets
# Note: Replace 'inchikey' with your actual column names
arivale_summary, arivale_mapped = analyze_metabolites(
    arivale_metabolites, "inchikey", "Arivale"
)
ukbb_summary, ukbb_mapped = analyze_metabolites(ukbb_metabolites, "inchikey", "UKBB")

# Compare datasets
arivale_inchikeys = set(arivale_mapped["inchikey"])
ukbb_inchikeys = set(ukbb_mapped["inchikey"])

shared_inchikeys = arivale_inchikeys & ukbb_inchikeys
unique_to_arivale = arivale_inchikeys - ukbb_inchikeys
unique_to_ukbb = ukbb_inchikeys - arivale_inchikeys

# Print comparison results
print("\nDataset Comparison:")
print(f"Shared metabolites: {len(shared_inchikeys)}")
print(f"Unique to Arivale: {len(unique_to_arivale)}")
print(f"Unique to UKBB: {len(unique_to_ukbb)}")

# Print mapping statistics
print("\nMapping Statistics:")
print("\nArivale:")
for key, value in arivale_summary.items():
    print(f"{key}: {value}")

print("\nUKBB:")
for key, value in ukbb_summary.items():
    print(f"{key}: {value}")

# Save results
output_dir = "metabolite_comparison"
os.makedirs(output_dir, exist_ok=True)

# Save mapped results
arivale_mapped.to_csv(f"{output_dir}/arivale_mapped_metabolites.csv", index=False)
ukbb_mapped.to_csv(f"{output_dir}/ukbb_mapped_metabolites.csv", index=False)

# Save comparison lists
pd.Series(list(shared_inchikeys)).to_csv(
    f"{output_dir}/shared_metabolites.csv", index=False
)
pd.Series(list(unique_to_arivale)).to_csv(
    f"{output_dir}/unique_to_arivale.csv", index=False
)
pd.Series(list(unique_to_ukbb)).to_csv(f"{output_dir}/unique_to_ukbb.csv", index=False)

# %%

if __name__ == "__main__":
    # Create mapper
    mapper = MetaboliteNameMapper()

    # Map a single name
    result = mapper.map_single_name("glucose")
    print(result)

    # Map a list of names
    results = mapper.map_from_names(["glucose", "cholesterol"])
    print(results)

    # Map from a file
    df = mapper.map_from_file(
        "/home/trentleslie/github/biomapper/UKBB_NMR_Meta.tsv",
        name_column="title",
        output_path="mapped_metabolites.csv",
    )
