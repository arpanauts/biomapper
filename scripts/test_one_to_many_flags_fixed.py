#!/usr/bin/env python3
"""
Test script to verify the one-to-many flag bug fix in phase3_bidirectional_reconciliation.py

This script creates synthetic test data with known one-to-many relationships and verifies
that the flags are set correctly after the fix.
"""

import pandas as pd
import json
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import the phase3 script
sys.path.insert(0, str(Path(__file__).parent))

from phase3_bidirectional_reconciliation import perform_bidirectional_validation


def create_test_data():
    """Create test DataFrames with known one-to-many relationships"""
    
    # Phase 1 (forward) test data
    forward_data = [
        # One-to-one: A1 -> X1
        {"source_id": "A1", "target_id": "X1", "confidence_score": 0.9, "mapping_method": "direct"},
        
        # One-to-many source: B1 -> Y1, Y2
        {"source_id": "B1", "target_id": "Y1", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "B1", "target_id": "Y2", "confidence_score": 0.7, "mapping_method": "direct"},
        
        # Many-to-one target: C1, C2 -> Z1
        {"source_id": "C1", "target_id": "Z1", "confidence_score": 0.85, "mapping_method": "direct"},
        {"source_id": "C2", "target_id": "Z1", "confidence_score": 0.75, "mapping_method": "direct"},
        
        # Many-to-many: D1, D2 -> W1, W2
        {"source_id": "D1", "target_id": "W1", "confidence_score": 0.9, "mapping_method": "direct"},
        {"source_id": "D1", "target_id": "W2", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "D2", "target_id": "W1", "confidence_score": 0.7, "mapping_method": "direct"},
        {"source_id": "D2", "target_id": "W2", "confidence_score": 0.6, "mapping_method": "direct"},
    ]
    
    forward_df = pd.DataFrame(forward_data)
    
    # Phase 2 (reverse) test data - should match forward mappings for bidirectional validation
    reverse_data = [
        # One-to-one: X1 -> A1
        {"source_id": "X1", "target_id": "A1", "confidence_score": 0.9, "mapping_method": "direct"},
        
        # One-to-many source reverse: Y1 -> B1, Y2 -> B1
        {"source_id": "Y1", "target_id": "B1", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "Y2", "target_id": "B1", "confidence_score": 0.7, "mapping_method": "direct"},
        
        # Many-to-one target reverse: Z1 -> C1, C2
        {"source_id": "Z1", "target_id": "C1", "confidence_score": 0.85, "mapping_method": "direct"},
        {"source_id": "Z1", "target_id": "C2", "confidence_score": 0.75, "mapping_method": "direct"},
        
        # Many-to-many reverse: W1 -> D1, D2; W2 -> D1, D2
        {"source_id": "W1", "target_id": "D1", "confidence_score": 0.9, "mapping_method": "direct"},
        {"source_id": "W1", "target_id": "D2", "confidence_score": 0.7, "mapping_method": "direct"},
        {"source_id": "W2", "target_id": "D1", "confidence_score": 0.8, "mapping_method": "direct"},
        {"source_id": "W2", "target_id": "D2", "confidence_score": 0.6, "mapping_method": "direct"},
    ]
    
    reverse_df = pd.DataFrame(reverse_data)
    
    # Add required columns
    for df in [forward_df, reverse_df]:
        df['hop_count'] = 1
        df['notes'] = ""
        df['mapping_path_details_json'] = json.dumps({})
    
    return forward_df, reverse_df


def build_indices(forward_df, reverse_df):
    """Build the mapping indices needed for bidirectional validation"""
    
    # Build forward index (source -> targets)
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
    
    # Build reverse index (target -> sources)
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


def test_one_to_many_flags():
    """Test that one-to-many flags are set correctly"""
    
    print("Creating test data...")
    forward_df, reverse_df = create_test_data()
    forward_index, reverse_index = build_indices(forward_df, reverse_df)
    
    # Define column mappings
    phase1_cols = {
        'source_id': 'source_id',
        'mapped_id': 'target_id',
        'source_ontology': 'source_ontology'
    }
    
    phase2_cols = {
        'source_id': 'source_id',
        'mapped_id': 'target_id',
        'source_ontology': 'source_ontology'
    }
    
    metadata_cols = {
        'mapping_method': 'mapping_method',
        'confidence_score': 'confidence_score',
        'hop_count': 'hop_count',
        'notes': 'notes',
        'mapping_path_details_json': 'mapping_path_details_json'
    }
    
    print("Running bidirectional validation...")
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
    
    print("\nValidating flag assignments...")
    
    # Test cases
    test_cases = [
        # (source_id, expected_one_to_many_source, expected_one_to_many_target, description)
        ("A1", False, False, "One-to-one mapping"),
        ("B1", True, False, "One-to-many source (B1 maps to Y1, Y2)"),
        ("C1", False, True, "Many-to-one target (C1, C2 map to Z1)"),
        ("C2", False, True, "Many-to-one target (C1, C2 map to Z1)"),
        ("D1", True, True, "Many-to-many mapping"),
        ("D2", True, True, "Many-to-many mapping"),
    ]
    
    all_passed = True
    
    for source_id, expected_source_flag, expected_target_flag, description in test_cases:
        rows = result_df[result_df['source_id'] == source_id]
        
        if len(rows) == 0:
            print(f"❌ FAIL: No rows found for source_id={source_id}")
            all_passed = False
            continue
        
        # Check the flags for each row with this source_id
        for _, row in rows.iterrows():
            actual_source_flag = row['is_one_to_many_source']
            actual_target_flag = row['is_one_to_many_target']
            
            source_match = actual_source_flag == expected_source_flag
            target_match = actual_target_flag == expected_target_flag
            
            if source_match and target_match:
                print(f"✅ PASS: {description}")
                print(f"   Source: {source_id}, Target: {row['target_id']}")
                print(f"   is_one_to_many_source={actual_source_flag}, is_one_to_many_target={actual_target_flag}")
            else:
                print(f"❌ FAIL: {description}")
                print(f"   Source: {source_id}, Target: {row['target_id']}")
                print(f"   Expected: is_one_to_many_source={expected_source_flag}, is_one_to_many_target={expected_target_flag}")
                print(f"   Actual:   is_one_to_many_source={actual_source_flag}, is_one_to_many_target={actual_target_flag}")
                all_passed = False
    
    print("\n" + "="*60)
    
    # Check if the original bug is fixed
    print("\nChecking if original bug is fixed...")
    all_true_count = len(result_df[result_df['is_one_to_many_target'] == True])
    total_count = len(result_df)
    
    if all_true_count == total_count and total_count > 0:
        print(f"❌ BUG STILL PRESENT: All {total_count} rows have is_one_to_many_target=TRUE")
        all_passed = False
    else:
        print(f"✅ BUG FIXED: Only {all_true_count}/{total_count} rows have is_one_to_many_target=TRUE")
    
    # Show summary statistics
    print("\nFlag distribution summary:")
    print(f"is_one_to_many_source=True: {len(result_df[result_df['is_one_to_many_source'] == True])} rows")
    print(f"is_one_to_many_source=False: {len(result_df[result_df['is_one_to_many_source'] == False])} rows")
    print(f"is_one_to_many_target=True: {len(result_df[result_df['is_one_to_many_target'] == True])} rows")
    print(f"is_one_to_many_target=False: {len(result_df[result_df['is_one_to_many_target'] == False])} rows")
    
    return all_passed


if __name__ == "__main__":
    success = test_one_to_many_flags()
    
    if success:
        print("\n🎉 All tests passed! The bug has been fixed.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)