#!/usr/bin/env python3
"""
Debug script to understand how the flags are being set
"""

import pandas as pd
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from phase3_bidirectional_reconciliation import perform_bidirectional_validation


def create_simple_test():
    """Create a very simple test case"""
    
    # Forward: B1 -> Y1, Y2 (one-to-many source)
    forward_data = [
        {"source_id": "B1", "target_id": "Y1", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "B1", "target_id": "Y2", "confidence_score": 0.7, "mapping_method": "direct"},
    ]
    
    # Reverse: Y1 -> B1, Y2 -> B1
    reverse_data = [
        {"source_id": "Y1", "target_id": "B1", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "Y2", "target_id": "B1", "confidence_score": 0.7, "mapping_method": "direct"},
    ]
    
    forward_df = pd.DataFrame(forward_data)
    reverse_df = pd.DataFrame(reverse_data)
    
    # Add required columns
    for df in [forward_df, reverse_df]:
        df['hop_count'] = 1
        df['notes'] = ""
        df['mapping_path_details_json'] = json.dumps({})
    
    return forward_df, reverse_df


def build_indices(forward_df, reverse_df):
    """Build the mapping indices"""
    
    forward_index = {}
    for _, row in forward_df.iterrows():
        source_id = row['source_id']
        if source_id not in forward_index:
            forward_index[source_id] = []
        forward_index[source_id].append({
            'mapping_step_1_target_arivale_protein_id': row['target_id'],
            'mapping_method': row['mapping_method'],
            'confidence_score': row['confidence_score']
        })
    
    reverse_index = {}
    for _, row in reverse_df.iterrows():
        source_id = row['source_id']
        if source_id not in reverse_index:
            reverse_index[source_id] = []
        reverse_index[source_id].append({
            'ukbb_id': row['target_id'],
            'mapping_method': row['mapping_method'],
            'confidence_score': row['confidence_score']
        })
    
    return forward_index, reverse_index


def debug_flags():
    """Debug the flag setting logic"""
    
    print("Creating simple test case: B1 -> Y1, Y2")
    forward_df, reverse_df = create_simple_test()
    forward_index, reverse_index = build_indices(forward_df, reverse_df)
    
    # Column mappings
    phase1_cols = {'source_id': 'source_id', 'mapped_id': 'target_id', 'source_ontology': 'source_ontology'}
    phase2_cols = {'source_id': 'source_id', 'mapped_id': 'target_id', 'source_ontology': 'source_ontology'}
    metadata_cols = {
        'mapping_method': 'mapping_method',
        'confidence_score': 'confidence_score',
        'hop_count': 'hop_count',
        'notes': 'notes',
        'mapping_path_details_json': 'mapping_path_details_json'
    }
    
    print("\nRunning validation...")
    result_df = perform_bidirectional_validation(
        forward_df=forward_df,
        reverse_df=reverse_df,
        ukbb_to_arivale_index=forward_index,
        arivale_to_ukbb_index=reverse_index,
        phase1_input_cols=phase1_cols,
        phase2_input_cols=phase2_cols,
        standard_metadata_cols=metadata_cols,
        support_one_to_many=True
    )
    
    print("\nResult DataFrame:")
    print(result_df[['source_id', 'target_id', 'is_one_to_many_source', 'is_one_to_many_target', 
                    'all_forward_mapped_target_ids', 'all_reverse_mapped_source_ids']])
    
    print("\nExpected:")
    print("- B1 -> Y1: is_one_to_many_source=True (B1 maps to Y1,Y2), is_one_to_many_target=False")
    print("- B1 -> Y2: is_one_to_many_source=True (B1 maps to Y1,Y2), is_one_to_many_target=False")
    
    print("\nActual:")
    for _, row in result_df.iterrows():
        print(f"- {row['source_id']} -> {row['target_id']}: "
              f"is_one_to_many_source={row['is_one_to_many_source']}, "
              f"is_one_to_many_target={row['is_one_to_many_target']}")
        print(f"  all_forward_mapped_target_ids: {row['all_forward_mapped_target_ids']}")
        print(f"  all_reverse_mapped_source_ids: {row['all_reverse_mapped_source_ids']}")


if __name__ == "__main__":
    debug_flags()