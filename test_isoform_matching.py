#!/usr/bin/env python3
"""
Test the improved matching with isoform stripping
"""
import asyncio
import time
import pandas as pd
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

async def test_improved_matching():
    print("🚀 TESTING IMPROVED UNIPROT MATCHING (WITH ISOFORM STRIPPING)")
    print("=" * 60)
    
    # Load datasets
    print("\n1. Loading datasets...")
    arivale_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', 
                             sep='\t', comment='#')
    print(f"   Arivale: {len(arivale_df)} proteins")
    print(f"   Unique UniProt IDs: {arivale_df['uniprot'].nunique()}")
    
    kg2c_df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
    
    # Filter to UniProtKB entries only for efficiency
    kg2c_uniprot = kg2c_df[kg2c_df['id'].str.startswith('UniProtKB:', na=False)].copy()
    print(f"   KG2c (UniProtKB only): {len(kg2c_uniprot)} proteins")
    
    # Create context as a simple dict
    context = {
        "custom_action_data": {
            "datasets": {
                "arivale_proteins": arivale_df.to_dict('records'),
                "kg2c_uniprot": kg2c_uniprot.to_dict('records')
            }
        }
    }
    
    print("\n2. Running MERGE_WITH_UNIPROT_RESOLUTION with isoform stripping...")
    
    # Get the action
    action = ACTION_REGISTRY["MERGE_WITH_UNIPROT_RESOLUTION"]()
    
    # Execute with correct signature
    start = time.time()
    result = await action.execute(
        [],  # current_identifiers
        "proteins",  # current_ontology_type
        {
            "source_dataset_key": "arivale_proteins",
            "target_dataset_key": "kg2c_uniprot",
            "source_id_column": "uniprot",
            "target_id_column": "id",
            "target_xref_column": "xrefs",
            "composite_separator": "_",
            "use_api": False,  # Disable API for this test
            "output_key": "mapping_results"
        },
        None,  # source_endpoint
        None,  # target_endpoint
        context
    )
    
    elapsed = time.time() - start
    
    print(f"   Completed in {elapsed:.2f} seconds")
    
    # Check results
    mapping_results = context.get("custom_action_data", {}).get("datasets", {}).get("mapping_results", [])
    print(f"\n3. Results:")
    print(f"   Total output rows: {len(mapping_results)}")
    
    # Count matches
    matched = [r for r in mapping_results if r.get('match_status') == 'matched']
    print(f"   Matched rows: {len(matched)}")
    
    # Count unique source IDs that matched
    unique_matched_source = set(r.get('uniprot') for r in matched if r.get('uniprot'))
    total_source = arivale_df['uniprot'].nunique()
    print(f"   Unique Arivale proteins matched: {len(unique_matched_source)}/{total_source}")
    print(f"   Match rate: {len(unique_matched_source)/total_source*100:.1f}%")
    
    if matched:
        print(f"\n   Sample matches:")
        for r in matched[:10]:
            source_id = r.get('uniprot', 'N/A')
            target_id = r.get('id', 'N/A')
            match_type = r.get('match_type', 'N/A')
            print(f"     {source_id} -> {target_id} (type: {match_type})")
    
    # Get metadata
    metadata = context.get("custom_action_data", {}).get("metadata", {}).get("mapping_results", {})
    if metadata:
        print(f"\n4. Match statistics:")
        for key, value in metadata.get('matches_by_type', {}).items():
            if value > 0:
                print(f"   {key}: {value}")
    
    print(f"\n✅ SUCCESS: {len(unique_matched_source)}/{total_source} proteins matched ({len(unique_matched_source)/total_source*100:.1f}%)")
    
    return len(matched)

matches = asyncio.run(test_improved_matching())