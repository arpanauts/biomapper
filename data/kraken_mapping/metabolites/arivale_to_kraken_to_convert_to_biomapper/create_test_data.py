#!/usr/bin/env python3
"""
Create minimal test data from Kraken files to test the pipeline
"""
import pandas as pd
from pathlib import Path

# Direct file paths
KRAKEN_CHEMICALS_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_chemicals.csv"
KRAKEN_METABOLITES_FILE = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kraken_1.0.0_ontologies/kraken_1.0.0_metabolites.csv"
OUTPUT_DIR = Path(__file__).parent / "data"

def create_sample_data():
    """Create small sample datasets for testing."""
    print("Creating sample Kraken data for testing...")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Sample some chemicals with relevant identifiers
    print("Sampling chemicals with HMDB/ChEBI/PubChem identifiers...")

    # Create sample data manually with known identifiers that match Arivale format
    sample_chemicals = [
        {
            'id': 'HMDB:HMDB01301',
            'name': 'S-1-pyrroline-5-carboxylate',
            'category': 'biolink:SmallMolecule',
            'description': 'Sample metabolite',
            'xrefs': 'HMDB:HMDB01301||PUBCHEM.COMPOUND:1196||CHEBI:58066'
        },
        {
            'id': 'HMDB:HMDB01257',
            'name': 'Spermidine',
            'category': 'biolink:SmallMolecule',
            'description': 'Sample metabolite',
            'xrefs': 'HMDB:HMDB01257||PUBCHEM.COMPOUND:1102||CHEBI:16610'
        },
        {
            'id': 'HMDB:HMDB00699',
            'name': '1-methylnicotinamide',
            'category': 'biolink:SmallMolecule',
            'description': 'Sample metabolite',
            'xrefs': 'HMDB:HMDB00699||PUBCHEM.COMPOUND:457||CHEBI:17205'
        },
        {
            'id': 'PUBCHEM:1196',
            'name': 'Chemical from PubChem',
            'category': 'biolink:ChemicalEntity',
            'description': 'Sample chemical',
            'xrefs': 'PUBCHEM.COMPOUND:1196||CHEBI:58066'
        },
        {
            'id': 'CHEBI:16610',
            'name': 'Chemical from ChEBI',
            'category': 'biolink:ChemicalEntity',
            'description': 'Sample chemical',
            'xrefs': 'CHEBI:16610||PUBCHEM.COMPOUND:1102'
        }
    ]

    sample_metabolites = [
        {
            'id': 'HMDB:HMDB01301',
            'name': 'S-1-pyrroline-5-carboxylate metabolite',
            'category': 'biolink:SmallMolecule',
            'description': 'Sample metabolite entry',
            'xrefs': 'HMDB:HMDB01301||PUBCHEM.COMPOUND:1196'
        },
        {
            'id': 'HMDB:HMDB01257',
            'name': 'Spermidine metabolite',
            'category': 'biolink:SmallMolecule',
            'description': 'Sample metabolite entry',
            'xrefs': 'HMDB:HMDB01257||PUBCHEM.COMPOUND:1102'
        }
    ]

    # Save sample data
    chemicals_df = pd.DataFrame(sample_chemicals)
    metabolites_df = pd.DataFrame(sample_metabolites)

    chemicals_file = OUTPUT_DIR / "sample_kraken_chemicals.csv"
    metabolites_file = OUTPUT_DIR / "sample_kraken_metabolites.csv"

    chemicals_df.to_csv(chemicals_file, index=False)
    metabolites_df.to_csv(metabolites_file, index=False)

    print(f"Created sample chemicals: {chemicals_file} ({len(chemicals_df)} entries)")
    print(f"Created sample metabolites: {metabolites_file} ({len(metabolites_df)} entries)")

    # Show the sample data
    print("\nSample chemicals:")
    print(chemicals_df.to_string())
    print("\nSample metabolites:")
    print(metabolites_df.to_string())

if __name__ == "__main__":
    create_sample_data()