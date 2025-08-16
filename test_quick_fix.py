#!/usr/bin/env python3
"""
Quick test to verify the DataFrame reference fix
"""
import asyncio
import pandas as pd
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import MergeWithUniprotResolutionAction
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import MergeWithUniprotResolutionParams

async def test_quick():
    print("Testing DataFrame reference fix...")
    
    # Create test data
    source_data = [
        {"uniprot": "Q6EMK4", "name": "Vasorin"},
        {"uniprot": "P12345", "name": "Test protein"}
    ]
    
    # Create target data with xrefs
    target_data = [
        {"id": "NCBIGene:114990", "name": "VASN", "xrefs": "UniProtKB:Q6EMK4,PR:Q6EMK4"},
        {"id": "UniProtKB:P12345", "name": "Another protein", "xrefs": ""}
    ]
    
    # Create action
    action = MergeWithUniprotResolutionAction()
    
    # Create params - note target_xref_column is now Optional
    params = MergeWithUniprotResolutionParams(
        source_dataset_key="source",
        target_dataset_key="target",
        source_id_column="uniprot",
        target_id_column="id",
        target_xref_column="xrefs",  # This should work now
        output_key="merged"
    )
    
    # Create context
    class MockContext:
        def __init__(self):
            self.custom_action_data = {
                "datasets": {
                    "source": source_data,
                    "target": target_data
                }
            }
        
        def get_action_data(self, key, default=None):
            return self.custom_action_data.get(key, default)
        
        def set_action_data(self, key, value):
            self.custom_action_data[key] = value
    
    context = MockContext()
    
    # Execute
    result = await action.execute_typed(
        current_identifiers=[],
        current_ontology_type="protein",
        params=params,
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    # Check results
    merged = context.custom_action_data["datasets"]["merged"]
    print(f"\nResults: {len(merged)} rows")
    
    # Check Q6EMK4
    q6_rows = [r for r in merged if r.get("uniprot") == "Q6EMK4"]
    if q6_rows:
        row = q6_rows[0]
        print(f"Q6EMK4 status: {row.get('match_status')}")
        if row.get('match_status') == 'matched':
            print("✅ Q6EMK4 matched successfully!")
            print(f"   Matched to: {row.get('id')}")
        else:
            print("❌ Q6EMK4 not matched")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_quick())