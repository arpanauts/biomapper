#!/usr/bin/env python3
"""Simulate the EXACT production flow to find the bug"""

import pandas as pd
import re
from typing import Dict, List, Any

def load_dataset_identifiers(file_path: str, identifier_column: str, separator: str = '\t', comment: str = '#'):
    """Simulate LOAD_DATASET_IDENTIFIERS action"""
    df = pd.read_csv(file_path, sep=separator, comment=comment)
    # This is how the action stores data
    return df.to_dict("records")

def merge_with_uniprot_resolution(source_data: List[Dict], target_data: List[Dict]):
    """Simulate MERGE_WITH_UNIPROT_RESOLUTION action"""
    
    print("SIMULATING EXACT PRODUCTION FLOW")
    print("=" * 80)
    
    # Step 1: Convert to DataFrames (as action does)
    source_df = pd.DataFrame(source_data)
    target_df = pd.DataFrame(target_data)
    
    print(f"Source DataFrame: {len(source_df)} rows")
    print(f"Target DataFrame: {len(target_df)} rows")
    
    # Find Q6EMK4 in source
    q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
    if len(q6_source) > 0:
        q6_source_idx = q6_source.index[0]
        print(f"Q6EMK4 at source index: {q6_source_idx} (type: {type(q6_source_idx)})")
    else:
        print("Q6EMK4 NOT FOUND in source!")
        return
    
    # Step 2: Build indices (exact production logic)
    target_uniprot_to_indices = {}
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    print("\nBuilding target index...")
    for target_idx, target_row in target_df.iterrows():
        xref_value = str(target_row.get('xrefs', ''))
        if xref_value and xref_value != 'nan':
            for match in pattern.finditer(xref_value):
                uniprot_id = match.group(1)
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
    
    print(f"Built index with {len(target_uniprot_to_indices)} proteins")
    
    if 'Q6EMK4' in target_uniprot_to_indices:
        print(f"Q6EMK4 in index: YES")
    else:
        print(f"Q6EMK4 in index: NO")
        return
    
    # Step 3: Match sources
    matches = []
    print("\nMatching sources...")
    
    for source_idx, source_row in source_df.iterrows():
        source_id = str(source_row['uniprot'])
        
        if source_id in target_uniprot_to_indices:
            for target_idx, target_row in target_uniprot_to_indices[source_id]:
                match_dict = {
                    "source_idx": source_idx,
                    "target_idx": target_idx,
                    "source_id": source_id,
                    "target_id": str(target_row['id']),
                    "match_confidence": 1.0,
                }
                matches.append(match_dict)
                
                if source_id == 'Q6EMK4':
                    print(f"  Created Q6EMK4 match: source_idx={source_idx}")
    
    print(f"\nTotal matches: {len(matches)}")
    
    # Step 4: Build matched indices
    matched_source_indices = set()
    for match in matches:
        matched_source_indices.add(match["source_idx"])
    
    # Step 5: Check Q6EMK4
    if q6_source_idx in matched_source_indices:
        print(f"✅ Q6EMK4 (idx={q6_source_idx}) IS matched")
    else:
        print(f"❌ Q6EMK4 (idx={q6_source_idx}) NOT matched")
        
        # Debug
        q6_matches = [m for m in matches if m['source_id'] == 'Q6EMK4']
        if q6_matches:
            print(f"\nDEBUG: Q6EMK4 matches exist:")
            for m in q6_matches:
                print(f"  source_idx in match: {m['source_idx']} (type: {type(m['source_idx'])})")
            print(f"  Q6EMK4 actual idx: {q6_source_idx} (type: {type(q6_source_idx)})")
            print(f"  Are they equal? {q6_matches[0]['source_idx'] == q6_source_idx}")
            print(f"  Are they identical? {q6_matches[0]['source_idx'] is q6_source_idx}")
    
    # Step 6: Create output (simulate source_only assignment)
    output = []
    for source_idx, source_row in source_df.iterrows():
        if source_idx not in matched_source_indices:
            # Would be marked as source_only
            if source_row['uniprot'] == 'Q6EMK4':
                print(f"\n⚠️ Q6EMK4 would be marked as source_only!")

# Main execution
if __name__ == "__main__":
    print("Loading data as production does...")
    
    # Load source data (as LOAD_DATASET_IDENTIFIERS does)
    source_data = load_dataset_identifiers(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        'uniprot'
    )
    
    # Load target data
    target_data = load_dataset_identifiers(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv',
        'id',
        separator=','
    )
    
    # Run merge
    merge_with_uniprot_resolution(source_data, target_data)