#!/usr/bin/env python3
"""Test different hypotheses for why Q6EMK4 fails"""

import pandas as pd
import re

print("Testing Hypotheses for Q6EMK4 Failure")
print("=" * 60)

# Hypothesis 1: String encoding issue
print("\nHypothesis 1: String Encoding Issue")
source_df = pd.read_csv(
    '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
    sep='\t', comment='#'
)
q6_rows = source_df[source_df['uniprot'] == 'Q6EMK4']
if len(q6_rows) > 0:
    q6_value = q6_rows.iloc[0]['uniprot']
    print(f"  Type: {type(q6_value)}")
    print(f"  Repr: {repr(q6_value)}")
    print(f"  Bytes: {q6_value.encode('utf-8')}")
    print(f"  Is string 'Q6EMK4': {q6_value == 'Q6EMK4'}")
    print(f"  Verdict: {'❌ ISSUE' if q6_value != 'Q6EMK4' else '✅ OK'}")
else:
    print("  ❌ Q6EMK4 not found in source!")

# Hypothesis 2: Index overwrites
print("\nHypothesis 2: Index Gets Overwritten")
target_df = pd.read_csv(
    '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
)
q6_occurrences = []
pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+(Q6EMK4)')

for idx, row in target_df.iterrows():
    xrefs = str(row.get('xrefs', ''))
    if 'Q6EMK4' in xrefs:
        q6_occurrences.append({
            'index': idx,
            'id': row['id'],
            'extracted': bool(pattern.search(xrefs))
        })

print(f"  Q6EMK4 found in {len(q6_occurrences)} rows")
if q6_occurrences:
    print(f"  All extracted correctly: {all(o['extracted'] for o in q6_occurrences)}")
    print(f"  Verdict: {'❌ Extraction fails somewhere' if not all(o['extracted'] for o in q6_occurrences) else '✅ OK'}")
else:
    print("  ❌ Q6EMK4 not found in target xrefs!")

# Hypothesis 3: Match is found but not recorded
print("\nHypothesis 3: Match Found but Not Recorded")
# This would require debugging the actual action
print("  Requires debugging the action execution")
print("  Check if match is found in _find_direct_matches")
print("  Check if match is lost in _create_merged_dataset")

# Hypothesis 4: Order-dependent bug
print("\nHypothesis 4: Order-Dependent Processing")
if len(q6_rows) > 0:
    source_idx = q6_rows.index[0]
    print(f"  Q6EMK4 is at source index: {source_idx}")
else:
    print("  Q6EMK4 not found in source")
    
ncbi_rows = target_df[target_df['id'] == 'NCBIGene:114990']
if len(ncbi_rows) > 0:
    target_idx = ncbi_rows.index[0]
    print(f"  NCBIGene:114990 is at target index: {target_idx}")
else:
    print("  NCBIGene:114990 not found in target")
    
print("  If target is processed after source fails, this could be the issue")

# Hypothesis 5: DataFrame iteration issue
print("\nHypothesis 5: DataFrame.iterrows() Issue")
print("  iterrows() returns (index, Series) pairs")
print("  If index is not reset, could cause misalignment")
source_index_type = type(source_df.index[0])
target_index_type = type(target_df.index[0])
print(f"  Source index type: {source_index_type}")
print(f"  Target index type: {target_index_type}")
print(f"  Verdict: {'❌ Index types differ' if source_index_type != target_index_type else '✅ OK'}")