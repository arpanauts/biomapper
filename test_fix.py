#!/usr/bin/env python3
"""Test if the fix resolves the Q6EMK4 issue"""

import asyncio
from biomapper.core.minimal_strategy_service import MinimalStrategyService
import logging

logging.basicConfig(level=logging.INFO)

async def test_fix():
    """Test the fix with production pipeline"""
    
    # Create simple test strategy
    strategy = {
        "name": "test_q6emk4_fix",
        "description": "Test if Q6EMK4 now matches correctly",
        "steps": [
            {
                "name": "load_source",
                "action": {
                    "type": "LOAD_DATASET_IDENTIFIERS",
                    "params": {
                        "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
                        "identifier_column": "uniprot",
                        "output_key": "source_proteins",
                        "separator": "\t",
                        "comment": "#"
                    }
                }
            },
            {
                "name": "load_target",
                "action": {
                    "type": "LOAD_DATASET_IDENTIFIERS",
                    "params": {
                        "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv",
                        "identifier_column": "id",
                        "output_key": "target_proteins",
                        "separator": ","
                    }
                }
            },
            {
                "name": "merge",
                "action": {
                    "type": "MERGE_WITH_UNIPROT_RESOLUTION",
                    "params": {
                        "source_dataset_key": "source_proteins",
                        "target_dataset_key": "target_proteins",
                        "source_id_column": "uniprot",
                        "target_id_column": "id",
                        "target_xref_column": "xrefs",
                        "output_key": "merged_proteins",
                        "composite_separator": "||",
                        "confidence_threshold": 0.6,
                        "use_api": False
                    }
                }
            }
        ]
    }
    
    # Run strategy
    service = MinimalStrategyService(strategies_dir="/tmp")
    context = await service.execute_strategy(strategy)
    
    # Check results
    if "merged_proteins" in context.datasets:
        merged = context.datasets["merged_proteins"]
        
        # Count match statuses
        status_counts = {}
        q6_found = False
        
        for row in merged:
            status = row.get('match_status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if row.get('uniprot') == 'Q6EMK4':
                q6_found = True
                q6_status = status
        
        # Calculate percentages
        total = len(merged)
        print(f"\nRESULTS SUMMARY:")
        print(f"Total rows: {total}")
        for status, count in status_counts.items():
            pct = (count / total) * 100
            print(f"  {status}: {count} ({pct:.1f}%)")
        
        # Check Q6EMK4
        if q6_found:
            if q6_status == 'matched':
                print(f"\n✅ Q6EMK4: FIXED! Now shows as '{q6_status}'")
            else:
                print(f"\n❌ Q6EMK4: Still broken, shows as '{q6_status}'")
        else:
            print(f"\n❌ Q6EMK4: Not found in results")
        
        # Check overall match rate
        matched = status_counts.get('matched', 0)
        source_only = status_counts.get('source_only', 0)
        
        # We know there are ~1162 unique source proteins
        unique_source_proteins = 1162  # Approximate from our analysis
        match_rate = (matched / unique_source_proteins) * 100 if matched > 0 else 0
        
        print(f"\nMATCH RATE:")
        print(f"  Matched proteins: {matched}")
        print(f"  Source-only proteins: {source_only}")
        print(f"  Estimated match rate: {match_rate:.1f}%")
        
        if match_rate > 90:
            print(f"\n✅ OVERALL: Match rate looks good!")
        else:
            print(f"\n❌ OVERALL: Match rate still too low")

if __name__ == "__main__":
    asyncio.run(test_fix())