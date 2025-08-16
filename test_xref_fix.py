#!/usr/bin/env python3
"""Test the target_xref_column fix end-to-end"""

import asyncio
import pandas as pd
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import (
    MergeWithUniprotResolutionAction,
    MergeWithUniprotResolutionParams
)
from biomapper.core.models.execution_context import StrategyExecutionContext

async def test_xref_fix():
    print("TESTING XREF FIX END-TO-END")
    print("=" * 80)
    
    # Load the actual production data
    print("Loading datasets...")
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    print(f"Source: {len(source_df)} rows")
    print(f"Target: {len(target_df)} rows")
    
    # Check Q6EMK4 is present
    q6_in_source = 'Q6EMK4' in source_df['uniprot'].values
    q6_in_target = any(target_df['xrefs'].str.contains('Q6EMK4', na=False))
    print(f"\nQ6EMK4 in source: {q6_in_source}")
    print(f"Q6EMK4 in target xrefs: {q6_in_target}")
    
    # Create execution context
    context = StrategyExecutionContext(
        initial_identifier="",
        current_identifier="",
        ontology_type="protein",
        custom_action_data={}
    )
    context.set_action_data("datasets", {
        "source_proteins": source_df.to_dict('records'),
        "target_proteins": target_df.to_dict('records')
    })
    
    # Create params WITH target_xref_column
    params = MergeWithUniprotResolutionParams(
        source_dataset_key="source_proteins",
        target_dataset_key="target_proteins",
        source_id_column="uniprot",
        target_id_column="id",
        target_xref_column="xrefs",  # THIS IS THE FIX!
        output_key="merged_proteins",
        composite_separator="||",
        confidence_threshold=0.6,
        use_api=False
    )
    
    print(f"\nParams include target_xref_column: {params.target_xref_column}")
    
    # Execute the action
    print("\nExecuting merge action...")
    action = MergeWithUniprotResolutionAction()
    
    result = await action.execute_typed(
        current_identifiers=[],
        current_ontology_type="protein",
        params=params,
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    # Get results
    merged_data = context.get_action_data("datasets")["merged_proteins"]
    metadata = context.get_action_data("metadata")["merged_proteins"]
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print(f"Total merged rows: {len(merged_data)}")
    print(f"Match statistics: {metadata['matches_by_type']}")
    
    # Calculate match rate
    total_matches = sum(metadata['matches_by_type'].values())
    unique_source = metadata['unique_source_ids']
    match_rate = (total_matches / unique_source) * 100 if unique_source > 0 else 0
    
    print(f"\nMatch rate: {match_rate:.1f}% ({total_matches}/{unique_source})")
    
    # Check Q6EMK4 specifically
    print("\n" + "=" * 80)
    print("Q6EMK4 STATUS:")
    
    q6_rows = [row for row in merged_data if row.get('uniprot') == 'Q6EMK4']
    if q6_rows:
        for row in q6_rows:
            print(f"  Match status: {row['match_status']}")
            print(f"  Match type: {row.get('match_type', 'N/A')}")
            print(f"  Match value: {row.get('match_value', 'N/A')}")
            if row['match_status'] == 'matched':
                print(f"  ✅ Q6EMK4 successfully matched!")
            else:
                print(f"  ❌ Q6EMK4 is {row['match_status']}")
    else:
        print("  ❌ Q6EMK4 not found in results!")
    
    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT:")
    
    if match_rate > 90:
        print(f"✅ SUCCESS: Match rate improved to {match_rate:.1f}%")
    else:
        print(f"❌ FAILURE: Match rate still low at {match_rate:.1f}%")
    
    q6_matched = any(row.get('match_status') == 'matched' for row in q6_rows)
    if q6_matched:
        print("✅ SUCCESS: Q6EMK4 is now matching!")
    else:
        print("❌ FAILURE: Q6EMK4 still not matching")
    
    return match_rate, q6_matched

if __name__ == "__main__":
    match_rate, q6_matched = asyncio.run(test_xref_fix())
    
    # Exit with appropriate code
    if match_rate > 90 and q6_matched:
        print("\n🎉 Fix verified successfully!")
        exit(0)
    else:
        print("\n❌ Fix did not work as expected")
        exit(1)