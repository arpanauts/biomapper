#!/usr/bin/env python3
"""
Test the fixed matching logic with UniProt extraction
"""
import asyncio
import time
import pandas as pd
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

async def test_fixed_matching():
    print("🚀 TESTING FIXED UNIPROT MATCHING")
    print("=" * 60)
    
    # Load datasets
    print("\n1. Loading datasets...")
    arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                             sep='\t', on_bad_lines='skip')
    print(f"   Arivale: {len(arivale_df)} proteins")
    
    kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
    
    # Filter to UniProtKB entries only
    kg2c_uniprot = kg2c_df[kg2c_df['id'].str.startswith('UniProtKB:', na=False)].copy()
    print(f"   KG2c (UniProtKB only): {len(kg2c_uniprot)} proteins")
    
    # Create context
    from biomapper.core.strategy_execution_context import StrategyExecutionContext
    context = StrategyExecutionContext(
        strategy_name="test",
        source_endpoint_name="",
        target_endpoint_name="",
        input_identifiers=[],
        custom_action_data={
            "datasets": {
                "arivale_proteins": arivale_df.to_dict('records'),
                "kg2c_uniprot": kg2c_uniprot.to_dict('records')
            }
        }
    )
    
    print("\n2. Running MERGE_WITH_UNIPROT_RESOLUTION...")
    
    # Get the action
    action = ACTION_REGISTRY["MERGE_WITH_UNIPROT_RESOLUTION"]()
    
    # Execute
    start = time.time()
    result = await action.execute(
        current_identifiers=[],
        current_ontology_type="proteins",
        params={
            "source_dataset_key": "arivale_proteins",
            "target_dataset_key": "kg2c_uniprot",
            "source_id_column": "uniprot",
            "target_id_column": "id",
            "target_xref_column": "xrefs",
            "composite_separator": "_",
            "use_api": False,  # Disable API for this test
            "output_key": "mapping_results"
        },
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    elapsed = time.time() - start
    
    print(f"   Completed in {elapsed:.2f} seconds")
    
    # Check results
    mapping_results = context.get_action_data("datasets", {}).get("mapping_results", [])
    print(f"\n3. Results:")
    print(f"   Total output rows: {len(mapping_results)}")
    
    # Count matches
    matched = [r for r in mapping_results if r.get('_match_type')]
    print(f"   Matched rows: {len(matched)}")
    
    if matched:
        print(f"\n   Sample matches:")
        for r in matched[:5]:
            print(f"     {r.get('source_uniprot')} -> {r.get('target_id')} (type: {r.get('_match_type')})")
    
    # Get metadata
    metadata = context.get_action_data("metadata", {}).get("mapping_results", {})
    if metadata:
        print(f"\n4. Match statistics:")
        for key, value in metadata.get('matches_by_type', {}).items():
            print(f"   {key}: {value}")
    
    return len(matched)

matches = asyncio.run(test_fixed_matching())
print(f"\n✅ Total matches found: {matches}")