#!/usr/bin/env python3
"""Verify the match statistics more carefully"""

import asyncio
import pandas as pd
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import (
    MergeWithUniprotResolutionAction,
    MergeWithUniprotResolutionParams
)
from biomapper.core.models.execution_context import StrategyExecutionContext

async def verify_stats():
    # Load datasets
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    # Create context
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
    
    # Create params WITH xref column
    params = MergeWithUniprotResolutionParams(
        source_dataset_key="source_proteins",
        target_dataset_key="target_proteins",
        source_id_column="uniprot",
        target_id_column="id",
        target_xref_column="xrefs",  # THE FIX
        output_key="merged_proteins",
        composite_separator="||",
        confidence_threshold=0.6,
        use_api=False
    )
    
    # Execute
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
    
    print("MATCH STATISTICS VERIFICATION")
    print("=" * 80)
    
    # Source statistics
    unique_source = source_df['uniprot'].dropna().nunique()
    print(f"Unique source proteins: {unique_source}")
    
    # Count matched source proteins
    matched_df = pd.DataFrame(merged_data)
    matched_source = matched_df[matched_df['match_status'] == 'matched']['uniprot'].nunique()
    print(f"Matched source proteins: {matched_source}")
    
    # Count by match type
    source_only = matched_df[matched_df['match_status'] == 'source_only']['uniprot'].nunique()
    print(f"Source-only proteins: {source_only}")
    
    # True match rate
    true_match_rate = (matched_source / unique_source) * 100
    print(f"\nTrue match rate: {true_match_rate:.1f}% ({matched_source}/{unique_source})")
    
    # Check some specific proteins
    test_proteins = ['Q6EMK4', 'P04083', 'P15692', 'P02749', 'P01042']
    print(f"\nSample protein statuses:")
    for protein in test_proteins:
        rows = matched_df[matched_df['uniprot'] == protein]
        if not rows.empty:
            status = rows.iloc[0]['match_status']
            print(f"  {protein}: {status}")
    
    # Match type breakdown
    print(f"\nMatch types:")
    print(f"  Direct matches: {metadata['matches_by_type']['direct']}")
    print(f"  Composite matches: {metadata['matches_by_type']['composite']}")
    print(f"  Historical matches: {metadata['matches_by_type']['historical']}")
    
    return true_match_rate

if __name__ == "__main__":
    match_rate = asyncio.run(verify_stats())
    print(f"\n{'✅' if match_rate > 90 else '❌'} Final match rate: {match_rate:.1f}%")