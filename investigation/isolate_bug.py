#!/usr/bin/env python3
"""Isolate the exact bug causing Q6EMK4 to fail"""

import pandas as pd
import re
from typing import Dict, List, Any, Tuple

def simulate_production_bug():
    """Reproduce the exact bug from production"""
    
    print("ISOLATING THE BUG")
    print("=" * 80)
    
    # Load FULL datasets (not samples)
    print("Loading full datasets...")
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    print(f"Source: {len(source_df)} rows")
    print(f"Target: {len(target_df)} rows")
    
    # Find Q6EMK4 source index
    q6_source_idx = source_df[source_df['uniprot'] == 'Q6EMK4'].index[0]
    print(f"\nQ6EMK4 at source index: {q6_source_idx}")
    
    # Build index EXACTLY as production does
    print("\nBuilding indices...")
    target_uniprot_to_indices = {}
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    # FIRST LOOP - Build index
    for target_idx, target_row in target_df.iterrows():
        xref_value = str(target_row.get('xrefs', ''))
        if xref_value and xref_value != 'nan':
            for match in pattern.finditer(xref_value):
                uniprot_id = match.group(1)
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                # POTENTIAL BUG: Storing row reference
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
    
    print(f"Index built with {len(target_uniprot_to_indices)} proteins")
    
    # Check Q6EMK4 in index
    if 'Q6EMK4' in target_uniprot_to_indices:
        q6_entries = target_uniprot_to_indices['Q6EMK4']
        print(f"\nQ6EMK4 in index with {len(q6_entries)} entries")
        for idx, row in q6_entries:
            print(f"  Entry: idx={idx}, id={row['id']}")
    else:
        print("\n❌ Q6EMK4 NOT IN INDEX!")
        return
    
    # SECOND LOOP - Build composite index (simulating production)
    print("\nBuilding composite index...")
    target_composite_parts = {}
    for target_idx, target_row in target_df.iterrows():
        target_id = str(target_row['id'])
        if '||' in target_id:
            parts = target_id.split('||')
            for part in parts:
                if part not in target_composite_parts:
                    target_composite_parts[part] = []
                target_composite_parts[part].append((target_idx, target_id, target_row))
    
    print(f"Composite index built with {len(target_composite_parts)} parts")
    
    # Now check if Q6EMK4 entry is still valid
    print("\nChecking Q6EMK4 after second loop...")
    if 'Q6EMK4' in target_uniprot_to_indices:
        q6_entries = target_uniprot_to_indices['Q6EMK4']
        print(f"Q6EMK4 still in index with {len(q6_entries)} entries")
        for idx, row in q6_entries:
            try:
                # Try to access the row data
                test_id = row['id']
                print(f"  ✅ Entry valid: idx={idx}, id={test_id}")
            except Exception as e:
                print(f"  ❌ Entry corrupted: idx={idx}, error={e}")
    
    # THIRD LOOP - Match sources
    print("\nMatching sources...")
    matches = []
    
    for source_idx, source_row in source_df.iterrows():
        source_id = str(source_row['uniprot'])
        
        if source_id == 'Q6EMK4':
            print(f"\nProcessing Q6EMK4 at source_idx={source_idx}")
            
        if source_id in target_uniprot_to_indices:
            for target_idx, target_row in target_uniprot_to_indices[source_id]:
                try:
                    match_dict = {
                        "source_idx": source_idx,
                        "target_idx": target_idx,
                        "source_id": source_id,
                        "target_id": str(target_row['id']),
                        "match_confidence": 1.0,
                    }
                    matches.append(match_dict)
                    
                    if source_id == 'Q6EMK4':
                        print(f"  ✅ Created match for Q6EMK4")
                except Exception as e:
                    if source_id == 'Q6EMK4':
                        print(f"  ❌ Failed to create match: {e}")
    
    print(f"\nTotal matches created: {len(matches)}")
    
    # Check if Q6EMK4 is in matches
    q6_matches = [m for m in matches if m['source_id'] == 'Q6EMK4']
    print(f"Q6EMK4 matches: {len(q6_matches)}")
    
    # Now simulate the merge logic
    print("\n" + "=" * 80)
    print("SIMULATING MERGE LOGIC")
    
    # Filter by confidence
    all_matches = []
    for match in matches:
        if match["match_confidence"] >= 0.6:
            all_matches.append(match)
    
    print(f"Filtered matches: {len(all_matches)}")
    
    # Build matched indices
    matched_source_indices = set()
    for match in all_matches:
        matched_source_indices.add(match["source_idx"])
    
    print(f"Matched source indices: {len(matched_source_indices)}")
    
    # Check Q6EMK4
    if q6_source_idx in matched_source_indices:
        print(f"✅ Q6EMK4 (idx={q6_source_idx}) IS IN matched_source_indices")
    else:
        print(f"❌ Q6EMK4 (idx={q6_source_idx}) NOT IN matched_source_indices")
        
        # Debug why
        print("\nDEBUGGING:")
        q6_match_indices = [m['source_idx'] for m in all_matches if m['source_id'] == 'Q6EMK4']
        print(f"  Q6EMK4 match indices: {q6_match_indices}")
        print(f"  Q6EMK4 actual index: {q6_source_idx}")
        print(f"  Type of Q6EMK4 actual: {type(q6_source_idx)}")
        if q6_match_indices:
            print(f"  Type of match index: {type(q6_match_indices[0])}")

if __name__ == "__main__":
    simulate_production_bug()