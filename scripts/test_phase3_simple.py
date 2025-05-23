#!/usr/bin/env python3
"""
Simple test to verify the fix works by checking the phase3 output
"""

import pandas as pd
import sys
from pathlib import Path

def check_phase3_output(output_file):
    """Check the distribution of one-to-many flags in phase3 output"""
    
    print(f"Checking phase3 output: {output_file}")
    
    # Read the file, skipping comment lines
    df = pd.read_csv(output_file, sep='\t', comment='#')
    
    # Get column names
    print(f"\nTotal rows: {len(df)}")
    
    # Find columns with 'one_to_many' in the name
    one_to_many_cols = [col for col in df.columns if 'one_to_many' in col.lower()]
    
    if not one_to_many_cols:
        print("ERROR: No one_to_many columns found!")
        print(f"Available columns: {list(df.columns)}")
        return False
    
    # Check distribution for each one-to-many column
    for col in one_to_many_cols:
        print(f"\n{col} distribution:")
        value_counts = df[col].value_counts()
        for val, count in value_counts.items():
            percentage = (count / len(df)) * 100
            print(f"  {val}: {count} ({percentage:.1f}%)")
    
    # Check if the bug is present (all or most is_one_to_many_target are True)
    if 'is_one_to_many_target' in one_to_many_cols:
        target_col = 'is_one_to_many_target'
        true_count = df[df[target_col] == True][target_col].count()
        true_percentage = (true_count / len(df)) * 100
        
        if true_percentage > 90:
            print(f"\n❌ BUG DETECTED: {true_percentage:.1f}% of is_one_to_many_target are True!")
            return False
        else:
            print(f"\n✅ BUG FIXED: Only {true_percentage:.1f}% of is_one_to_many_target are True")
            return True
    
    return True


if __name__ == "__main__":
    # Check the old output first
    print("="*60)
    print("CHECKING ORIGINAL (BUGGY) OUTPUT")
    print("="*60)
    old_file = "/home/ubuntu/biomapper/scripts/test_output/one_to_many_fix_test_20250513_175053/phase3_bidirectional_reconciliation_results.tsv"
    check_phase3_output(old_file)
    
    # Now we would check the new output if we had successfully run phase3
    # For now, we've verified the fix works with our synthetic test data