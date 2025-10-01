#!/usr/bin/env python3
"""
Proto-action: Load Kraken 1.0.0 reference data for metabolite mapping
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - no context/parameters
KRAKEN_CHEMICALS_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
KRAKEN_METABOLITES_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_metabolites.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def load_kraken_nodes(file_path, node_type):
    """Load and validate Kraken node file"""
    print(f"Loading {node_type} nodes from {file_path}...")

    try:
        # Try CSV format first (Kraken 1.0.0 uses CSV)
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_csv(file_path, sep='\t')

        print(f"  Loaded {len(df)} {node_type} nodes")
        print(f"  Columns: {list(df.columns)}")

        # Show sample data - including xrefs if present
        print(f"  Sample {node_type} nodes:")
        display_cols = ['id', 'name'] if 'name' in df.columns else list(df.columns)[:3]
        if 'xrefs' in df.columns:
            display_cols.append('xrefs')
        print(df[display_cols].head(3).to_string())

        # Check if xrefs column exists
        if 'xrefs' in df.columns:
            # Analyze xrefs content
            xrefs_non_null = df['xrefs'].notna().sum()
            print(f"  Nodes with xrefs: {xrefs_non_null}/{len(df)} ({xrefs_non_null/len(df)*100:.1f}%)")

            # Show sample xrefs
            sample_xrefs = df[df['xrefs'].notna()]['xrefs'].head(2).tolist()
            if sample_xrefs:
                print(f"  Sample xrefs content:")
                for xref in sample_xrefs[:2]:
                    print(f"    {xref[:100]}..." if len(str(xref)) > 100 else f"    {xref}")

        return df

    except FileNotFoundError:
        print(f"  ERROR: File not found: {file_path}")
        # Check what files are available
        directory = Path(file_path).parent
        if directory.exists():
            print(f"  Available files in {directory}:")
            for file in directory.glob("*.tsv"):
                print(f"    {file}")
        return None
    except Exception as e:
        print(f"  ERROR loading {node_type} nodes: {e}")
        return None

def main():
    print("Loading Kraken 1.0.0 reference data for metabolite mapping...")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load Kraken chemicals (includes ChEBI nodes)
    chemicals_df = load_kraken_nodes(KRAKEN_CHEMICALS_FILE, "chemicals")
    if chemicals_df is not None:
        # Filter for ChEBI nodes only
        chebi_nodes = chemicals_df[chemicals_df['id'].str.startswith('CHEBI:', na=False)].copy()
        print(f"  Found {len(chebi_nodes)} ChEBI nodes in chemicals")

        if len(chebi_nodes) > 0:
            # Save ChEBI reference WITH xrefs column preserved
            chebi_output = OUTPUT_DIR / "kraken_chebi.tsv"
            chebi_nodes.to_csv(chebi_output, sep='\t', index=False)
            print(f"  Saved ChEBI nodes to {chebi_output} (with xrefs column)")

            # Analyze ChEBI ID formats
            sample_ids = chebi_nodes['id'].head(10).tolist()
            print(f"  Sample ChEBI IDs: {sample_ids}")

            # Check for ChEBI IDs in xrefs
            if 'xrefs' in chebi_nodes.columns:
                xref_chebi_count = chebi_nodes['xrefs'].str.contains('CHEBI:', na=False).sum()
                print(f"  Nodes with CHEBI in xrefs: {xref_chebi_count}")

    print()

    # Load Kraken metabolites (may include HMDB nodes)
    metabolites_df = load_kraken_nodes(KRAKEN_METABOLITES_FILE, "metabolites")
    if metabolites_df is not None:
        # Filter for HMDB nodes if they exist
        hmdb_nodes = metabolites_df[metabolites_df['id'].str.startswith('HMDB:', na=False)].copy()
        print(f"  Found {len(hmdb_nodes)} HMDB nodes in metabolites")

        if len(hmdb_nodes) > 0:
            # Save HMDB reference WITH xrefs column preserved
            hmdb_output = OUTPUT_DIR / "kraken_hmdb.tsv"
            hmdb_nodes.to_csv(hmdb_output, sep='\t', index=False)
            print(f"  Saved HMDB nodes to {hmdb_output} (with xrefs column)")

            # Analyze HMDB ID formats
            sample_ids = hmdb_nodes['id'].head(10).tolist()
            print(f"  Sample HMDB IDs: {sample_ids}")

            # Check for HMDB IDs in xrefs
            if 'xrefs' in hmdb_nodes.columns:
                xref_hmdb_count = hmdb_nodes['xrefs'].str.contains('HMDB:', na=False).sum()
                print(f"  Nodes with HMDB in xrefs: {xref_hmdb_count}")

        # Also check for other metabolite identifiers that might be useful
        all_ids = metabolites_df['id'].str[:6].value_counts().head(10)
        print(f"  Metabolite ID prefixes: {dict(all_ids)}")

    print()

    # Summary
    total_nodes = 0
    print("SUMMARY:")
    if chemicals_df is not None:
        total_nodes += len(chemicals_df)
        print(f"  - Total chemical nodes loaded: {len(chemicals_df)}")
        if 'chebi_nodes' in locals():
            print(f"  - ChEBI nodes available: {len(chebi_nodes)}")

    if metabolites_df is not None:
        total_nodes += len(metabolites_df)
        print(f"  - Total metabolite nodes loaded: {len(metabolites_df)}")
        if 'hmdb_nodes' in locals():
            print(f"  - HMDB nodes available: {len(hmdb_nodes)}")

    print(f"  - Total reference nodes: {total_nodes}")
    print(f"  - Ready for ID mapping!")

if __name__ == "__main__":
    main()