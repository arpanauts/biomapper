#!/usr/bin/env python3
"""Trace Q6EMK4 through the entire pipeline step by step"""

import pandas as pd
import re
import json
from datetime import datetime

class Q6EMK4Tracer:
    def __init__(self):
        self.trace = []
        
    def log(self, step: str, details: dict):
        """Log each step of processing"""
        self.trace.append({
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'details': details
        })
        print(f"[{step}] {details}")
    
    def run_trace(self):
        """Simulate the exact pipeline processing"""
        
        # Step 1: Load source data
        self.log("load_source", {"file": "proteomics_metadata.tsv"})
        source_df = pd.read_csv(
            '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
            sep='\t', comment='#'
        )
        
        # Find Q6EMK4 row
        q6_source = source_df[source_df['uniprot'] == 'Q6EMK4']
        self.log("find_in_source", {
            "found": len(q6_source) > 0,
            "index": q6_source.index[0] if len(q6_source) > 0 else None
        })
        
        # Step 2: Load target data
        self.log("load_target", {"file": "kg2c_proteins.csv"})
        target_df = pd.read_csv(
            '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
        )
        
        # Step 3: Build index (simulate action logic)
        self.log("build_index", {"starting": True})
        target_uniprot_to_indices = {}
        
        # Process all rows to build complete index
        for target_idx, target_row in target_df.iterrows():
            # Process id column
            target_id = str(target_row['id'])
            if target_id.startswith('UniProtKB:'):
                uniprot_id = target_id.replace('UniProtKB:', '')
                if uniprot_id not in target_uniprot_to_indices:
                    target_uniprot_to_indices[uniprot_id] = []
                target_uniprot_to_indices[uniprot_id].append(target_idx)
            
            # Process xrefs column
            xref_value = str(target_row.get('xrefs', ''))
            if xref_value and xref_value != 'nan':
                pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
                for match in pattern.finditer(xref_value):
                    uniprot_id = match.group(1)
                    if uniprot_id not in target_uniprot_to_indices:
                        target_uniprot_to_indices[uniprot_id] = []
                    target_uniprot_to_indices[uniprot_id].append(target_idx)
                    
                    # Check if this is Q6EMK4
                    if uniprot_id == 'Q6EMK4':
                        self.log("indexed_q6emk4", {
                            "from_row": target_idx,
                            "target_id": target_id,
                            "extracted_from": "xrefs"
                        })
        
        self.log("index_complete", {
            "total_keys": len(target_uniprot_to_indices),
            "has_q6emk4": 'Q6EMK4' in target_uniprot_to_indices
        })
        
        # Step 4: Attempt matching
        self.log("matching", {"starting": True})
        
        if len(q6_source) > 0:
            source_id = str(q6_source.iloc[0]['uniprot'])
            
            if source_id in target_uniprot_to_indices:
                matches = target_uniprot_to_indices[source_id]
                self.log("match_found", {
                    "source_id": source_id,
                    "num_matches": len(matches),
                    "target_indices": matches[:5]  # First 5
                })
                
                # Get details of matches
                for idx in matches[:3]:
                    target_row = target_df.iloc[idx]
                    self.log("match_detail", {
                        "target_idx": idx,
                        "target_id": target_row['id'],
                        "target_name": target_row['name']
                    })
            else:
                self.log("no_match", {"source_id": source_id})
        
        # Save trace
        with open('q6emk4_trace.json', 'w') as f:
            json.dump(self.trace, f, indent=2)
        print(f"\nTrace saved to q6emk4_trace.json")

tracer = Q6EMK4Tracer()
tracer.run_trace()