#!/usr/bin/env python3
"""Test with actual production data for Q6EMK4 and neighbors"""

import pandas as pd
import re
from typing import List, Dict, Any

def test_real_q6emk4():
    """Test with the actual Q6EMK4 data from production"""
    
    print("TESTING WITH REAL Q6EMK4 DATA")
    print("=" * 80)
    
    # Load real data
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    # Get Q6EMK4 and neighbors from source
    q6_idx = source_df[source_df['uniprot'] == 'Q6EMK4'].index[0]
    test_source = source_df.iloc[q6_idx-2:q6_idx+3].copy()
    test_source = test_source.reset_index(drop=True)  # Reset index to 0-based
    
    print("Test source proteins:")
    for idx, row in test_source.iterrows():
        print(f"  {idx}: {row['uniprot']}")
    
    # Get relevant target rows (those that contain our test proteins)
    test_proteins = test_source['uniprot'].tolist()
    relevant_target_indices = []
    
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    for idx, row in target_df.iterrows():
        xrefs = str(row.get('xrefs', ''))
        if xrefs and xrefs != 'nan':
            extracted = pattern.findall(xrefs)
            for protein in test_proteins:
                if protein in extracted:
                    relevant_target_indices.append(idx)
                    break
    
    test_target = target_df.iloc[relevant_target_indices].copy()
    test_target = test_target.reset_index(drop=True)
    
    print(f"\nFound {len(test_target)} relevant target rows")
    
    # Now run the matching logic
    matches = []
    target_uniprot_to_indices = {}
    
    # Build index from test target
    for target_idx, target_row in test_target.iterrows():
        xref_value = str(target_row.get('xrefs', ''))
        if xref_value and xref_value != 'nan':
            for match in pattern.finditer(xref_value):
                uniprot_id = match.group(1)
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
    
    print(f"\nBuilt index with {len(target_uniprot_to_indices)} UniProt IDs")
    print(f"Q6EMK4 in index: {'Q6EMK4' in target_uniprot_to_indices}")
    
    # Match source proteins
    for source_idx, source_row in test_source.iterrows():
        source_id = str(source_row['uniprot'])
        
        if source_id in target_uniprot_to_indices:
            for target_idx, target_row in target_uniprot_to_indices[source_id]:
                matches.append({
                    "source_idx": source_idx,
                    "target_idx": target_idx,
                    "source_id": source_id,
                    "target_id": str(target_row['id']),
                    "match_confidence": 1.0,
                })
                print(f"  Match: {source_id} (src_idx={source_idx}) -> {target_row['id']}")
    
    # Check matched indices
    matched_source_indices = set()
    for match in matches:
        matched_source_indices.add(match["source_idx"])
    
    print(f"\nMatched source indices: {matched_source_indices}")
    
    # Check status for each
    print("\nFinal status:")
    for source_idx, source_row in test_source.iterrows():
        if source_idx in matched_source_indices:
            status = "matched"
        else:
            status = "source_only"
        print(f"  {source_row['uniprot']}: {status}")
    
    # Special check for Q6EMK4
    q6_in_test = test_source[test_source['uniprot'] == 'Q6EMK4']
    if len(q6_in_test) > 0:
        q6_test_idx = q6_in_test.index[0]
        if q6_test_idx in matched_source_indices:
            print(f"\n✅ Q6EMK4 MATCHED in test (index {q6_test_idx})")
        else:
            print(f"\n❌ Q6EMK4 NOT MATCHED in test (index {q6_test_idx})")
            print(f"   Q6EMK4 in target index: {'Q6EMK4' in target_uniprot_to_indices}")
            if 'Q6EMK4' in target_uniprot_to_indices:
                print(f"   Q6EMK4 target matches: {target_uniprot_to_indices['Q6EMK4']}")

test_real_q6emk4()