#!/usr/bin/env python3
"""Create a minimal test case to reproduce the bug"""

import pandas as pd
import re
from typing import List, Dict, Any, Tuple

def find_direct_matches_minimal(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """Minimal reproduction of the matching logic"""
    matches = []
    
    print("Building target index...")
    # Build target UniProt index from xrefs
    target_uniprot_to_indices = {}
    pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
    
    for target_idx, target_row in target_df.iterrows():
        xref_value = str(target_row.get('xrefs', ''))
        if xref_value and xref_value != 'nan':
            for match in pattern.finditer(xref_value):
                uniprot_id = match.group(1)
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append((target_idx, target_row))
                
    print(f"  Built index with {len(target_uniprot_to_indices)} UniProt IDs")
    
    # Match source proteins
    print("\nMatching source proteins...")
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
                print(f"  Created match: {source_id} (idx={source_idx}) -> {target_row['id']} (idx={target_idx})")
    
    return matches

def create_merged_dataset_minimal(
    source_df: pd.DataFrame,
    matches: List[Dict[str, Any]],
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Minimal reproduction of the merge logic"""
    
    # Filter matches by confidence
    confidence_threshold = 0.6
    all_matches = []
    for match in matches:
        if match["match_confidence"] >= confidence_threshold:
            all_matches.append(match)
    
    print(f"\nFiltered matches: {len(all_matches)} passed confidence threshold")
    
    # Build matched indices
    matched_source_indices = set()
    for match in all_matches:
        source_idx = match["source_idx"]
        matched_source_indices.add(source_idx)
        print(f"  Added source_idx {source_idx} (type: {type(source_idx)}) to matched set")
    
    print(f"\nMatched source indices: {matched_source_indices}")
    
    # Check each source row
    results = []
    stats = {"matched": 0, "source_only": 0}
    
    for source_idx, source_row in source_df.iterrows():
        if source_idx in matched_source_indices:
            status = "matched"
            stats["matched"] += 1
        else:
            status = "source_only"
            stats["source_only"] += 1
        
        results.append({
            "uniprot": source_row["uniprot"],
            "match_status": status,
            "source_idx": source_idx,
            "idx_in_matched": source_idx in matched_source_indices
        })
    
    return pd.DataFrame(results), stats

# Test with minimal data
print("MINIMAL TEST CASE")
print("=" * 80)

# Create minimal source (including Q6EMK4 and a few others)
source_data = pd.DataFrame({
    'uniprot': ['Q6EMK4', 'P12345', 'O00533', 'P99999']
})

# Create minimal target with these proteins in xrefs
target_data = pd.DataFrame({
    'id': ['NCBIGene:114990', 'NCBIGene:12345', 'NCBIGene:533', 'NCBIGene:99999'],
    'name': ['VASN', 'TEST1', 'TEST2', 'NOTHERE'],
    'xrefs': [
        'ENSEMBL:ENSG00000168140||PR:Q6EMK4||UniProtKB:Q6EMK4',
        'UniProtKB:P12345||KEGG:K12345',
        'UniProtKB:O00533-1||UniProtKB:O00533',  # Has isoform
        'UniProtKB:X99999'  # Different protein
    ]
})

print("Source data:")
print(source_data)
print("\nTarget data:")
print(target_data[['id', 'xrefs']])

# Run matching
matches = find_direct_matches_minimal(source_data, target_data)

print(f"\nTotal matches found: {len(matches)}")

# Run merge
results, stats = create_merged_dataset_minimal(source_data, matches)

print(f"\nFinal statistics: {stats}")
print("\nFinal results:")
print(results)

# Check Q6EMK4 specifically
q6_result = results[results['uniprot'] == 'Q6EMK4']
if len(q6_result) > 0:
    status = q6_result.iloc[0]['match_status']
    print(f"\n{'✅' if status == 'matched' else '❌'} Q6EMK4 status: {status}")