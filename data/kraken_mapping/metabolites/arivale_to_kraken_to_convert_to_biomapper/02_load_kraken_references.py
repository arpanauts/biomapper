#!/usr/bin/env python3
"""
Proto-action: Load and prepare Kraken metabolite/chemical reference data
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
import re
from pathlib import Path

# Direct file paths - no context/parameters
KRAKEN_CHEMICALS_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
KRAKEN_METABOLITES_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_metabolites.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def extract_identifiers_from_xrefs(xrefs_str):
    """Extract HMDB, ChEBI, and PubChem identifiers from xrefs field."""
    if pd.isna(xrefs_str) or not isinstance(xrefs_str, str):
        return {'hmdb_ids': [], 'chebi_ids': [], 'pubchem_ids': []}

    # Regex patterns for different identifier types
    hmdb_pattern = re.compile(r'HMDB:(HMDB\d+)')
    chebi_pattern = re.compile(r'CHEBI:(\d+)')
    pubchem_pattern = re.compile(r'PUBCHEM\.COMPOUND:(\d+)')

    # Extract all matches
    hmdb_ids = hmdb_pattern.findall(xrefs_str)
    chebi_ids = chebi_pattern.findall(xrefs_str)
    pubchem_ids = pubchem_pattern.findall(xrefs_str)

    return {
        'hmdb_ids': hmdb_ids,
        'chebi_ids': chebi_ids,
        'pubchem_ids': pubchem_ids
    }

def prepare_kraken_for_mapping(df, entity_type):
    """Prepare Kraken data for mapping by extracting relevant identifiers."""
    # Extract identifiers from xrefs
    df['extracted_ids'] = df['xrefs'].apply(extract_identifiers_from_xrefs)

    # Create separate rows for each identifier type
    rows_for_hmdb = []
    rows_for_chebi = []
    rows_for_pubchem = []

    for idx, row in df.iterrows():
        extracted = row['extracted_ids']

        # Create HMDB mapping records
        for hmdb_id in extracted['hmdb_ids']:
            rows_for_hmdb.append({
                'kraken_id': row['id'],
                'kraken_name': row['name'],
                'kraken_category': row['category'],
                'kraken_description': row.get('description', ''),
                'entity_type': entity_type,
                'mapping_type': 'hmdb',
                'identifier': hmdb_id
            })

        # Create ChEBI mapping records
        for chebi_id in extracted['chebi_ids']:
            rows_for_chebi.append({
                'kraken_id': row['id'],
                'kraken_name': row['name'],
                'kraken_category': row['category'],
                'kraken_description': row.get('description', ''),
                'entity_type': entity_type,
                'mapping_type': 'chebi',
                'identifier': f"CHEBI:{chebi_id}"
            })

        # Create PubChem mapping records
        for pubchem_id in extracted['pubchem_ids']:
            rows_for_pubchem.append({
                'kraken_id': row['id'],
                'kraken_name': row['name'],
                'kraken_category': row['category'],
                'kraken_description': row.get('description', ''),
                'entity_type': entity_type,
                'mapping_type': 'pubchem',
                'identifier': pubchem_id
            })

    # Combine all mapping records
    all_mapping_rows = rows_for_hmdb + rows_for_chebi + rows_for_pubchem

    if all_mapping_rows:
        return pd.DataFrame(all_mapping_rows)
    else:
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=[
            'kraken_id', 'kraken_name', 'kraken_category', 'kraken_description',
            'entity_type', 'mapping_type', 'identifier'
        ])

def main():
    """Load and prepare Kraken reference data for metabolite mapping."""
    print("Loading Kraken reference data...")

    # Load Kraken chemicals with optimized settings
    print(f"Loading chemicals from: {KRAKEN_CHEMICALS_FILE}")
    chemicals_df = pd.read_csv(KRAKEN_CHEMICALS_FILE, low_memory=False, dtype={'id': str, 'name': str, 'category': str})
    print(f"Loaded {len(chemicals_df)} chemical entities")

    # Load Kraken metabolites with optimized settings
    print(f"Loading metabolites from: {KRAKEN_METABOLITES_FILE}")
    metabolites_df = pd.read_csv(KRAKEN_METABOLITES_FILE, low_memory=False, dtype={'id': str, 'name': str, 'category': str})
    print(f"Loaded {len(metabolites_df)} metabolite entities")

    # Prepare mapping tables
    print("\nExtracting identifiers from xrefs...")

    chemicals_mapping = prepare_kraken_for_mapping(chemicals_df, 'chemical')
    metabolites_mapping = prepare_kraken_for_mapping(metabolites_df, 'metabolite')

    # Combine all mappings
    all_mappings = pd.concat([chemicals_mapping, metabolites_mapping], ignore_index=True)

    print(f"\nKraken Mapping Summary:")
    print(f"Total mapping records: {len(all_mappings)}")

    # Break down by mapping type
    if len(all_mappings) > 0:
        mapping_counts = all_mappings['mapping_type'].value_counts()
        for mapping_type, count in mapping_counts.items():
            print(f"{mapping_type.upper()} mappings: {count}")

        # Break down by entity type
        entity_counts = all_mappings['entity_type'].value_counts()
        for entity_type, count in entity_counts.items():
            print(f"{entity_type.title()} entities: {count}")

    # Save mapping data by type for efficient joining
    OUTPUT_DIR.mkdir(exist_ok=True)

    if len(all_mappings) > 0:
        # Save HMDB mappings
        hmdb_mappings = all_mappings[all_mappings['mapping_type'] == 'hmdb'].copy()
        if len(hmdb_mappings) > 0:
            hmdb_file = OUTPUT_DIR / "kraken_hmdb_mappings.tsv"
            hmdb_mappings.to_csv(hmdb_file, sep='\t', index=False)
            print(f"Saved {len(hmdb_mappings)} HMDB mappings to: {hmdb_file}")

        # Save ChEBI mappings
        chebi_mappings = all_mappings[all_mappings['mapping_type'] == 'chebi'].copy()
        if len(chebi_mappings) > 0:
            chebi_file = OUTPUT_DIR / "kraken_chebi_mappings.tsv"
            chebi_mappings.to_csv(chebi_file, sep='\t', index=False)
            print(f"Saved {len(chebi_mappings)} ChEBI mappings to: {chebi_file}")

        # Save PubChem mappings
        pubchem_mappings = all_mappings[all_mappings['mapping_type'] == 'pubchem'].copy()
        if len(pubchem_mappings) > 0:
            pubchem_file = OUTPUT_DIR / "kraken_pubchem_mappings.tsv"
            pubchem_mappings.to_csv(pubchem_file, sep='\t', index=False)
            print(f"Saved {len(pubchem_mappings)} PubChem mappings to: {pubchem_file}")

        # Save all mappings combined
        all_file = OUTPUT_DIR / "kraken_all_mappings.tsv"
        all_mappings.to_csv(all_file, sep='\t', index=False)
        print(f"Saved all mappings to: {all_file}")

        # Show sample of HMDB mappings
        if len(hmdb_mappings) > 0:
            print(f"\nSample HMDB mappings:")
            print(hmdb_mappings.head(3).to_string())
    else:
        print("No mappings found in Kraken reference data!")

if __name__ == "__main__":
    main()