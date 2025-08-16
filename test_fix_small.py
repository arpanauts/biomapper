#!/usr/bin/env python3
"""Test the fix with a small subset of data"""

import pandas as pd
import asyncio
import logging

logging.basicConfig(level=logging.WARNING)

async def test_small():
    """Test with small dataset"""
    
    # Load just the rows around Q6EMK4
    source_df = pd.read_csv(
        '/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv',
        sep='\t', comment='#'
    )
    
    # Get Q6EMK4 and neighbors
    q6_idx = source_df[source_df['uniprot'] == 'Q6EMK4'].index[0]
    test_source = source_df.iloc[q6_idx-10:q6_idx+10].to_dict('records')
    
    # Load relevant target rows
    target_df = pd.read_csv(
        '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'
    )
    
    # Get rows that might match our test proteins
    test_proteins = [row['uniprot'] for row in test_source]
    mask = target_df['xrefs'].apply(lambda x: any(p in str(x) for p in test_proteins) if pd.notna(x) else False)
    test_target = target_df[mask].to_dict('records')
    
    print(f"Test data: {len(test_source)} source rows, {len(test_target)} target rows")
    
    # Set up context
    context = type('Context', (), {
        'datasets': {
            'source': test_source,
            'target': test_target
        },
        'get_action_data': lambda self, key, default: getattr(self, key, default),
        'set_action_data': lambda self, key, value: setattr(self, key, value)
    })()
    
    # Set up params
    params = type('Params', (), {
        'source_dataset_key': 'source',
        'target_dataset_key': 'target',
        'source_id_column': 'uniprot',
        'target_id_column': 'id',
        'target_xref_column': 'xrefs',
        'output_key': 'merged',
        'composite_separator': '||',
        'confidence_threshold': 0.6,
        'use_api': False
    })()
    
    # Get the action
    from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
    action_class = ACTION_REGISTRY.get('MERGE_WITH_UNIPROT_RESOLUTION')
    if not action_class:
        print("❌ Action not found in registry")
        return
    action = action_class()
    
    # Run the action
    print("Running merge action...")
    result = await action.execute(params.__dict__, context)
    
    # Check results
    if hasattr(context, 'datasets') and 'merged' in context.datasets:
        merged = context.datasets['merged']
        
        # Find Q6EMK4
        for row in merged:
            if row.get('uniprot') == 'Q6EMK4':
                status = row.get('match_status')
                if status == 'matched':
                    print(f"✅ Q6EMK4: FIXED! Now matches correctly")
                else:
                    print(f"❌ Q6EMK4: Still broken, status = {status}")
                return
        
        print("❌ Q6EMK4: Not found in results")
    else:
        print("❌ No merged dataset created")

if __name__ == "__main__":
    asyncio.run(test_small())