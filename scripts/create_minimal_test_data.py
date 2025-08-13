#!/usr/bin/env python3
"""
Create minimal test datasets for biomapper testing on new machines.
This allows basic functionality testing without large reference files.
"""

import os
import pandas as pd
from pathlib import Path

def create_test_data():
    """Create minimal test datasets for all entity types."""
    
    # Create data directory if it doesn't exist
    data_dir = Path("data/test_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating minimal test datasets...")
    
    # 1. Test Metabolites
    metabolites_data = {
        'metabolite_id': [
            'HMDB0000001', 'HMDB0000002', 'HMDB0000005', 
            'HMDB0000008', 'HMDB0000010', 'HMDB0000011',
            'HMDB0000012', 'HMDB0000014', 'HMDB0000015', 'HMDB0000016'
        ],
        'name': [
            '1-Methylhistidine', '1,3-Diaminopropane', '2-Ketobutyric acid',
            '2-Hydroxybutyric acid', '2-Hydroxyvaleric acid', '3-Hydroxybutyric acid',
            'Deoxyuridine', 'Deoxycytidine', 'Cortexolone', 'Deoxycholic acid'
        ],
        'inchikey': [
            'BRMWTNUJHUMWMS-LURJTMIESA-N', 'XFNJVJPLKCPIBV-UHFFFAOYSA-N',
            'TYEYBOSBBBHJIV-UHFFFAOYSA-N', 'AFENDNXGAFYKQO-UHFFFAOYSA-N',
            'VOXXWSYKYCBWHO-UHFFFAOYSA-N', 'WHBMMWSBFZVSSR-UHFFFAOYSA-N',
            'MXHRCPNRJAMMIM-SHYZEUOFSA-N', 'CKTSBUTUHBMZGZ-SHYZEUOFSA-N',
            'WHBHRVVNPWVEEN-SYQHCUMBSA-N', 'KXGVEGMKQFWNSR-LLQZFEROSA-N'
        ],
        'chebi_id': [
            'CHEBI:50599', 'CHEBI:15725', 'CHEBI:30831',
            'CHEBI:1148', 'CHEBI:40443', 'CHEBI:20067',
            'CHEBI:16450', 'CHEBI:15698', 'CHEBI:16997', 'CHEBI:23614'
        ],
        'kegg_id': [
            'C01152', 'C00986', 'C00109',
            'C05984', 'C03912', 'C01089',
            'C00526', 'C00881', 'C05487', 'C04483'
        ]
    }
    
    metabolites_df = pd.DataFrame(metabolites_data)
    metabolites_df.to_csv(data_dir / "test_metabolites.tsv", sep='\t', index=False)
    print(f"  ✓ Created test_metabolites.tsv ({len(metabolites_df)} entries)")
    
    # 2. Test Proteins
    proteins_data = {
        'protein_id': [
            'P01023', 'P02763', 'P04406', 'P05067', 
            'P08238', 'P10635', 'P12345', 'O00533'
        ],
        'gene_symbol': [
            'A2M', 'ORM1', 'GAPDH', 'APP',
            'HSP90AB1', 'CYP2D6', 'TEST1', 'TEST2'
        ],
        'uniprot_accession': [
            'P01023', 'P02763', 'P04406', 'P05067',
            'P08238', 'P10635', 'P12345', 'O00533'
        ],
        'ensembl_protein': [
            'ENSP00000323929', 'ENSP00000265132', 'ENSP00000229239', 'ENSP00000284981',
            'ENSP00000360709', 'ENSP00000360608', 'ENSP00000123456', 'ENSP00000234567'
        ],
        'xrefs': [
            'UniProtKB:P01023|RefSeq:NP_000005', 'UniProtKB:P02763|RefSeq:NP_000598',
            'UniProtKB:P04406|RefSeq:NP_002037', 'UniProtKB:P05067|RefSeq:NP_000475',
            'UniProtKB:P08238|RefSeq:NP_031381', 'UniProtKB:P10635|RefSeq:NP_000097',
            'UniProtKB:P12345|TEST', 'UniProtKB:O00533|TEST'
        ]
    }
    
    proteins_df = pd.DataFrame(proteins_data)
    proteins_df.to_csv(data_dir / "test_proteins.tsv", sep='\t', index=False)
    print(f"  ✓ Created test_proteins.tsv ({len(proteins_df)} entries)")
    
    # 3. Test Chemistry/Clinical Tests
    chemistry_data = {
        'test_id': ['1', '2', '3', '4', '5'],
        'test_name': [
            'Glucose, Serum', 'Hemoglobin A1c', 'Cholesterol, Total',
            'Triglycerides', 'Creatinine, Serum'
        ],
        'loinc_code': [
            '2345-7', '4548-4', '2093-3',
            '2571-8', '2160-0'
        ],
        'vendor': [
            'LabCorp', 'Quest', 'LabCorp',
            'Quest', 'LabCorp'
        ],
        'units': [
            'mg/dL', '%', 'mg/dL',
            'mg/dL', 'mg/dL'
        ]
    }
    
    chemistry_df = pd.DataFrame(chemistry_data)
    chemistry_df.to_csv(data_dir / "test_chemistry.tsv", sep='\t', index=False)
    print(f"  ✓ Created test_chemistry.tsv ({len(chemistry_df)} entries)")
    
    # 4. Nightingale NMR Reference (minimal)
    nightingale_data = {
        'biomarker_id': ['XXL_VLDL_P', 'XL_VLDL_P', 'L_VLDL_P', 'M_VLDL_P', 'S_VLDL_P'],
        'biomarker_name': [
            'Concentration of XXL VLDL particles',
            'Concentration of XL VLDL particles', 
            'Concentration of L VLDL particles',
            'Concentration of M VLDL particles',
            'Concentration of S VLDL particles'
        ],
        'category': ['Lipoprotein', 'Lipoprotein', 'Lipoprotein', 'Lipoprotein', 'Lipoprotein'],
        'subcategory': ['VLDL', 'VLDL', 'VLDL', 'VLDL', 'VLDL'],
        'units': ['mol/L', 'mol/L', 'mol/L', 'mol/L', 'mol/L']
    }
    
    nightingale_df = pd.DataFrame(nightingale_data)
    nightingale_df.to_csv(data_dir / "nightingale_biomarkers.tsv", sep='\t', index=False)
    print(f"  ✓ Created nightingale_biomarkers.tsv ({len(nightingale_df)} entries)")
    
    # 5. SPOKE compounds reference (minimal)
    spoke_compounds_data = {
        'identifier': metabolites_data['metabolite_id'],
        'name': metabolites_data['name'],
        'chembl_id': [''] * len(metabolites_data['metabolite_id']),
        'drugbank_id': [''] * len(metabolites_data['metabolite_id']),
        'inchikey': metabolites_data['inchikey']
    }
    
    spoke_df = pd.DataFrame(spoke_compounds_data)
    spoke_df.to_csv(data_dir / "SPOKE_compounds.tsv", sep='\t', index=False)
    print(f"  ✓ Created SPOKE_compounds.tsv ({len(spoke_df)} entries)")
    
    # 6. KG2c nodes (minimal)
    kg2c_nodes_data = {
        'id': metabolites_data['metabolite_id'] + proteins_data['protein_id'],
        'name': metabolites_data['name'] + proteins_data['gene_symbol'],
        'category': ['biolink:Metabolite'] * len(metabolites_data['metabolite_id']) + 
                   ['biolink:Protein'] * len(proteins_data['protein_id']),
        'xrefs': [''] * (len(metabolites_data['metabolite_id']) + len(proteins_data['protein_id']))
    }
    
    kg2c_df = pd.DataFrame(kg2c_nodes_data)
    kg2c_df.to_csv(data_dir / "kg2c_nodes.tsv", sep='\t', index=False)
    print(f"  ✓ Created kg2c_nodes.tsv ({len(kg2c_df)} entries)")
    
    print("\nMinimal test datasets created successfully!")
    print(f"Location: {data_dir.absolute()}")
    print("\nThese datasets allow basic testing without large reference files.")
    print("For full functionality, transfer or download the complete datasets.")
    
    return data_dir

if __name__ == "__main__":
    create_test_data()