#!/usr/bin/env python3
"""Compare why Q6EMK4 works in tests but not in production"""

import pandas as pd
import os

# Check if production results exist
results_path = '/tmp/biomapper_results/protein_mapping_results.csv'
if not os.path.exists(results_path):
    print(f"Production results not found at {results_path}")
    print("Please run production pipeline first to generate results")
    print("\nCreating minimal test comparison instead...")
else:
    # Load production results
    results_df = pd.read_csv(results_path, low_memory=False)
    
    # Find Q6EMK4
    q6_results = results_df[results_df['uniprot'] == 'Q6EMK4']
    
    print("Production Results for Q6EMK4:")
    print(f"  Rows: {len(q6_results)}")
    if len(q6_results) > 0:
        row = q6_results.iloc[0]
        print(f"  match_status: {row['match_status']}")
        print(f"  match_type: {row.get('match_type', 'N/A')}")
        
        # Check all columns
        print("\n  All columns with values:")
        for col in row.index:
            if pd.notna(row[col]):
                print(f"    {col}: {row[col]}")
    
    # Check if there's something special about the production data
    print("\n" + "="*60)
    print("Checking for Data Anomalies:")
    
    # Check if Q6EMK4 appears multiple times
    q6_count = (results_df['uniprot'] == 'Q6EMK4').sum()
    print(f"  Q6EMK4 appears {q6_count} times in results")
    
    # Check if there are any successful matches around row 80
    if len(results_df) > 82:
        nearby_matches = results_df.iloc[78:83]
        print(f"\n  Rows near Q6EMK4 (78-82):")
        for idx, row in nearby_matches.iterrows():
            print(f"    Row {idx}: {row['uniprot']} -> {row['match_status']}")

# Now run a minimal test that SHOULD work
print("\n" + "="*60)
print("Running Minimal Test:")

# Create minimal datasets
test_source = pd.DataFrame({'uniprot': ['Q6EMK4']})
test_target = pd.DataFrame({
    'id': ['NCBIGene:114990'],
    'xrefs': ['UniProtKB:Q6EMK4']
})

print(f"  Source: {test_source.to_dict()}")
print(f"  Target: {test_target.to_dict()}")

# Simulate matching
if 'Q6EMK4' in ['Q6EMK4']:  # Trivial but shows it should work
    print("  ✅ Match SHOULD work")
else:
    print("  ❌ Something is wrong with the test")