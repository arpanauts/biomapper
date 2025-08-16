#!/usr/bin/env python3
"""
Debug specifically why Q6EMK4 doesn't match
"""
import pandas as pd
import re
import asyncio
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import MergeWithUniprotResolution, MergeWithUniprotResolutionParams
from biomapper.core.adapters import ContextAdapter

async def debug_q6emk4():
    print("🔍 DEBUGGING Q6EMK4 SPECIFIC ISSUE")
    print("=" * 60)
    
    # Load the actual datasets using BiologicalFileLoader
    print("\n1. Loading actual datasets...")
    from biomapper.core.standards import BiologicalFileLoader
    
    arivale_df = BiologicalFileLoader.load_tsv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        auto_detect=True,
        validate=True
    )
    kg2c_df = BiologicalFileLoader.load_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv',
        auto_detect=True,
        validate=True
    )
    
    # Filter to just Q6EMK4 for testing
    print("\n2. Filtering to Q6EMK4 for focused testing...")
    test_arivale = arivale_df[arivale_df['uniprot'] == 'Q6EMK4'].copy()
    print(f"   Test Arivale: {len(test_arivale)} rows")
    print(f"   Q6EMK4 at index: {test_arivale.index[0]}")
    
    # Get the specific KG2c row we know has Q6EMK4
    test_kg2c = kg2c_df[kg2c_df['id'] == 'NCBIGene:114990'].copy()
    print(f"   Test KG2c: {len(test_kg2c)} rows")
    print(f"   NCBIGene:114990 at index: {test_kg2c.index[0]}")
    print(f"   xrefs: {test_kg2c.iloc[0]['xrefs'][:100]}...")
    
    # Add a few more KG2c rows for context
    additional_kg2c = kg2c_df.head(10)
    test_kg2c = pd.concat([test_kg2c, additional_kg2c]).drop_duplicates()
    print(f"   Total test KG2c rows: {len(test_kg2c)}")
    
    # Create context with test data
    context = ContextAdapter()
    context.set_action_data("datasets", {
        "test_arivale": test_arivale.to_dict('records'),
        "test_kg2c": test_kg2c.to_dict('records')
    })
    
    # Create params
    params = MergeWithUniprotResolutionParams(
        source_dataset_key="test_arivale",
        target_dataset_key="test_kg2c",
        source_id_column="uniprot",
        target_id_column="id",
        target_xref_column="xrefs",
        output_key="test_results",
        use_api=False,  # No API for testing
        confidence_threshold=0.0
    )
    
    # Run the action
    print("\n3. Running MergeWithUniprotResolution action...")
    action = MergeWithUniprotResolution()
    
    # Add some debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    result = await action.execute(params.model_dump(), context)
    
    # Check results
    print("\n4. Checking results...")
    datasets = context.get_action_data("datasets", {})
    test_results = datasets.get("test_results", [])
    
    print(f"   Total result rows: {len(test_results)}")
    
    # Find Q6EMK4 in results
    q6_results = [r for r in test_results if r.get('uniprot') == 'Q6EMK4']
    print(f"   Q6EMK4 rows: {len(q6_results)}")
    
    if q6_results:
        result = q6_results[0]
        print(f"\n   Q6EMK4 result:")
        print(f"     match_status: {result.get('match_status')}")
        print(f"     match_type: {result.get('match_type')}")
        print(f"     target_id: {result.get('id')}")
        print(f"     target_name: {result.get('name')}")
        
        if result.get('match_status') == 'matched':
            print("     ✅ Q6EMK4 matched successfully!")
        else:
            print("     ❌ Q6EMK4 NOT matched!")
            
            # Debug: Manually check the index
            print("\n5. Manual index check...")
            uniprot_pattern = re.compile(r'(?:UniProtKB|uniprot|UniProt)[:\s]+([A-Z][0-9][A-Z0-9]{3}[0-9](?:-\d+)?)')
            xrefs = test_kg2c.iloc[0]['xrefs']
            matches = uniprot_pattern.findall(xrefs)
            print(f"   UniProt IDs in NCBIGene:114990 xrefs: {matches}")
            print(f"   Q6EMK4 in extracted IDs: {'Q6EMK4' in matches}")
    
    print("\n" + "=" * 60)

# Run the debug
asyncio.run(debug_q6emk4())