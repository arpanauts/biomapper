#!/usr/bin/env python3
"""Analyze the actual production results to understand the issue"""

import pandas as pd
import os

results_path = '/tmp/biomapper_results/protein_mapping_results.csv'

if os.path.exists(results_path):
    # Load results
    results_df = pd.read_csv(results_path, low_memory=False)
    
    print("PRODUCTION RESULTS ANALYSIS")
    print("=" * 60)
    
    # Overall statistics
    print(f"Total rows: {len(results_df)}")
    
    # Match status distribution
    print("\nMatch Status Distribution:")
    status_counts = results_df['match_status'].value_counts()
    for status, count in status_counts.items():
        percent = (count / len(results_df)) * 100
        print(f"  {status}: {count} ({percent:.1f}%)")
    
    # Find Q6EMK4 specifically
    q6_results = results_df[results_df['uniprot'] == 'Q6EMK4']
    
    print(f"\nQ6EMK4 Analysis:")
    print(f"  Found in results: {len(q6_results) > 0}")
    
    if len(q6_results) > 0:
        q6_row = q6_results.iloc[0]
        print(f"  Row number in results: {q6_results.index[0]}")
        print(f"  Original source row: {q6_row.get('_row_number_source', 'N/A')}")
        
        # Check all Q6EMK4 fields
        print("\n  Q6EMK4 Row Details:")
        important_cols = ['uniprot', 'match_status', 'match_type', 'match_confidence', 
                         'match_value', 'api_resolved', '_row_number_source']
        for col in important_cols:
            if col in q6_row.index:
                print(f"    {col}: {q6_row[col]}")
        
        # Check if there are any matched proteins around Q6EMK4
        print("\n  Neighboring Proteins (same source area):")
        if '_row_number_source' in results_df.columns:
            source_row = q6_row['_row_number_source']
            if pd.notna(source_row):
                nearby = results_df[
                    (results_df['_row_number_source'] >= source_row - 5) &
                    (results_df['_row_number_source'] <= source_row + 5)
                ]
                for idx, row in nearby.iterrows():
                    print(f"    Row {row['_row_number_source']}: {row['uniprot']} -> {row['match_status']}")
    
    # Check for any weird patterns
    print("\n" + "=" * 60)
    print("CHECKING FOR PATTERNS:")
    
    # Are there other proteins that should match but don't?
    source_only = results_df[results_df['match_status'] == 'source_only']
    print(f"\nTotal 'source_only' proteins: {len(source_only)}")
    
    # Sample some source_only proteins
    print("\nSample of 'source_only' proteins:")
    for idx, row in source_only.head(10).iterrows():
        print(f"  {row['uniprot']}: {row.get('gene_name', 'N/A')}")
    
    # Check if Q6EMK4 appears multiple times
    q6_all = results_df[results_df['uniprot'].str.contains('Q6EMK4', na=False)]
    print(f"\nAll rows containing 'Q6EMK4': {len(q6_all)}")
    
else:
    print(f"Results file not found at {results_path}")
    print("Cannot analyze production results")