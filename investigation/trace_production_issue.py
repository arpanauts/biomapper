#!/usr/bin/env python3
"""Trace exactly what happens to Q6EMK4 in the production pipeline"""

import pandas as pd
import re

# Simulate the exact production logic
def simulate_production_matching():
    print("SIMULATING PRODUCTION MATCHING LOGIC")
    print("=" * 60)
    
    # Load datasets exactly as production does
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    # Parameters (from production)
    source_id_column = 'uniprot'
    target_id_column = 'id'
    target_xref_column = 'xrefs'
    confidence_threshold = 0.6
    
    # Step 1: Build target indices (exact production logic)
    target_uniprot_to_indices = {}
    
    for target_idx, target_row in target_df.iterrows():
        # Process xrefs column
        xref_value = str(target_row.get(target_xref_column, ''))
        if xref_value and xref_value != 'nan':
            # Extract UniProt IDs from xrefs
            uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
            for match in uniprot_pattern.finditer(xref_value):
                uniprot_id = match.group(1)
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
    
    print(f"Built target index with {len(target_uniprot_to_indices)} UniProt IDs")
    print(f"Q6EMK4 in index: {'Q6EMK4' in target_uniprot_to_indices}")
    
    if 'Q6EMK4' in target_uniprot_to_indices:
        print(f"Q6EMK4 maps to {len(target_uniprot_to_indices['Q6EMK4'])} target rows")
    
    # Step 2: Find Q6EMK4 in source
    q6_source = source_df[source_df[source_id_column] == 'Q6EMK4']
    if len(q6_source) > 0:
        source_idx = q6_source.index[0]
        print(f"\nQ6EMK4 found in source at index: {source_idx}")
        
        # Step 3: Simulate matching logic
        matches = []
        source_row = q6_source.iloc[0]
        source_id = str(source_row[source_id_column])
        
        print(f"Source ID: '{source_id}'")
        print(f"Checking if '{source_id}' in target_uniprot_to_indices...")
        
        # This is the exact logic from production
        if source_id in target_uniprot_to_indices:
            print(f"  ✅ MATCH FOUND!")
            for target_idx, target_row in target_uniprot_to_indices[source_id]:
                match = {
                    "source_idx": source_idx,
                    "target_idx": target_idx,
                    "source_id": source_id,
                    "target_id": str(target_row[target_id_column]),
                    "match_value": source_id,
                    "match_type": "direct",
                    "match_confidence": 1.0,
                    "api_resolved": False,
                }
                matches.append(match)
                print(f"  Created match: source_idx={source_idx}, target_idx={target_idx}")
                print(f"  Match confidence: {match['match_confidence']}")
        else:
            print(f"  ❌ NO MATCH FOUND")
        
        # Step 4: Filter by confidence
        print(f"\nFiltering matches by confidence >= {confidence_threshold}")
        filtered_matches = []
        for match in matches:
            if match["match_confidence"] >= confidence_threshold:
                filtered_matches.append(match)
                print(f"  ✅ Match passed filter (confidence={match['match_confidence']})")
            else:
                print(f"  ❌ Match failed filter (confidence={match['match_confidence']})")
        
        # Step 5: Check if source_idx is in matched set
        matched_source_indices = set()
        for match in filtered_matches:
            matched_source_indices.add(match["source_idx"])
        
        print(f"\nMatched source indices: {matched_source_indices}")
        print(f"Is Q6EMK4 (idx={source_idx}) matched? {source_idx in matched_source_indices}")
        
        if source_idx not in matched_source_indices:
            print("\n⚠️ Q6EMK4 would be marked as 'source_only'!")
        else:
            print("\n✅ Q6EMK4 should be properly matched!")
            
        # Step 6: Check for potential issues
        print("\n" + "=" * 60)
        print("CHECKING FOR POTENTIAL ISSUES:")
        
        # Issue 1: Index type mismatch
        print(f"\n1. Index type check:")
        print(f"   source_idx type: {type(source_idx)}")
        if filtered_matches:
            print(f"   match source_idx type: {type(filtered_matches[0]['source_idx'])}")
        
        # Issue 2: Multiple Q6EMK4 entries
        q6_count = (source_df[source_id_column] == 'Q6EMK4').sum()
        print(f"\n2. Duplicate check:")
        print(f"   Q6EMK4 appears {q6_count} time(s) in source")
        
        # Issue 3: DataFrame iteration behavior
        print(f"\n3. DataFrame iteration:")
        print(f"   iterrows() returns index as-is")
        print(f"   source_df.index type: {type(source_df.index)}")
        print(f"   target_df.index type: {type(target_df.index)}")
        
    else:
        print("Q6EMK4 not found in source!")

if __name__ == "__main__":
    simulate_production_matching()