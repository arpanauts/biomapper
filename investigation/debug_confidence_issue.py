#!/usr/bin/env python3
"""Debug why Q6EMK4 match might have low confidence"""

import pandas as pd
import re

# Load datasets
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)

target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)

# Find Q6EMK4 in source
q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_source) > 0:
    source_idx = q6_source.index[0]
    source_row = q6_source.iloc[0]
    
    print("Q6EMK4 in Source:")
    print(f"  Index: {source_idx}")
    print(f"  UniProt: {source_row['uniprot']}")
    print(f"  Gene Name: {source_row.get('gene_name', 'N/A')}")
    
    # Find Q6EMK4 in target xrefs
    print("\nQ6EMK4 in Target:")
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    matches_found = []
    for target_idx, target_row in target_df.iterrows():
        xrefs = str(target_row.get('xrefs', ''))
        if 'Q6EMK4' in xrefs:
            # Extract UniProt IDs
            extracted = pattern.findall(xrefs)
            if 'Q6EMK4' in extracted:
                print(f"  Target Index: {target_idx}")
                print(f"  Target ID: {target_row['id']}")
                print(f"  Target Name: {target_row['name']}")
                
                # Calculate what the confidence would be
                # The action uses simple match_type to confidence mapping:
                # - direct: 1.0
                # - composite: 0.8
                # - historical: 0.6
                
                # Since Q6EMK4 is extracted from xrefs, not a direct ID match,
                # it would be a "direct" match (extracted ID matches source ID exactly)
                print(f"  Expected match_type: direct")
                print(f"  Expected confidence: 1.0")
                
                # But let's check if there's something special
                print(f"\n  Full xrefs field (first 200 chars):")
                print(f"    {xrefs[:200]}")
                
                matches_found.append({
                    'target_idx': target_idx,
                    'target_id': target_row['id'],
                    'extracted': extracted
                })
    
    print(f"\nTotal matches found: {len(matches_found)}")
    
    # Check default confidence threshold
    print("\nDefault confidence threshold in action: 0.6")
    print("Since Q6EMK4 would get confidence 1.0 (direct match), it should pass the threshold.")
    print("\nPossible issues:")
    print("1. The match is found but not added to direct_matches list")
    print("2. The source_idx is incorrect when creating the match")
    print("3. There's a bug in the indexing logic")
else:
    print("Q6EMK4 not found in source dataset!")