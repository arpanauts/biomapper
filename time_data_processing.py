#!/usr/bin/env python3
"""
Simple timing test to measure core data processing speed
"""
import time
import pandas as pd
from datetime import datetime

def time_operation(name, func):
    """Time an operation and print results"""
    print(f"\n⏱️  Testing: {name}")
    print("-" * 40)
    start = time.time()
    result = func()
    elapsed = time.time() - start
    print(f"✅ Completed in {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
    return result, elapsed

def load_arivale():
    """Load Arivale dataset"""
    df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv', sep='\t')
    print(f"   Loaded {len(df)} Arivale proteins")
    return df

def load_kg2c():
    """Load KG2c dataset"""
    df = pd.read_csv('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv')
    print(f"   Loaded {len(df)} KG2c entities")
    return df

def process_uniprot_matching(arivale_df, kg2c_df):
    """Simulate UniProt matching"""
    print(f"   Processing {len(arivale_df)} x {len(kg2c_df)} comparisons")
    
    # Get unique identifiers
    arivale_ids = set(arivale_df['uniprot'].dropna().unique())
    
    # Simulate extraction from xrefs (this is what takes time)
    kg2c_extracted = []
    for idx, row in kg2c_df.iterrows():
        if idx % 10000 == 0:
            print(f"   Processed {idx}/{len(kg2c_df)} rows...", end='\r')
        
        # Simulate extraction logic
        xref = str(row.get('equivalent_identifiers', ''))
        if 'UniProtKB' in xref:
            kg2c_extracted.append(row)
    
    print(f"\n   Found {len(kg2c_extracted)} KG2c entries with UniProt refs")
    
    # Simulate matching
    matches = 0
    for aid in arivale_ids:
        for kg2c_entry in kg2c_extracted[:1000]:  # Limit for timing test
            if str(aid) in str(kg2c_entry):
                matches += 1
                break
    
    print(f"   Matched {matches} proteins")
    return matches

def main():
    print("🚀 TIMING TEST FOR BIOMAPPER DATA PROCESSING")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    print("=" * 60)
    
    total_time = 0
    
    # Time each operation
    arivale_df, t1 = time_operation("Load Arivale Data", load_arivale)
    total_time += t1
    
    kg2c_df, t2 = time_operation("Load KG2c Data", load_kg2c)
    total_time += t2
    
    # Estimate full processing time
    print("\n⚡ Quick matching test (subset)...")
    start = time.time()
    sample_kg2c = kg2c_df.head(10000)  # Test with 10K rows
    process_uniprot_matching(arivale_df, sample_kg2c)
    sample_time = time.time() - start
    
    # Extrapolate to full dataset
    full_estimate = sample_time * (len(kg2c_df) / 10000)
    
    print("\n" + "=" * 60)
    print("📊 TIMING ANALYSIS")
    print("=" * 60)
    print(f"Data loading time: {t1 + t2:.2f} seconds")
    print(f"Sample processing (10K): {sample_time:.2f} seconds")
    print(f"Estimated full processing: {full_estimate:.2f} seconds ({full_estimate/60:.1f} minutes)")
    print(f"Add Google Drive upload: ~60 seconds")
    print("-" * 40)
    total_estimate = t1 + t2 + full_estimate + 60
    print(f"TOTAL ESTIMATED TIME: {total_estimate:.0f} seconds ({total_estimate/60:.1f} minutes)")
    
    print("\n💡 RECOMMENDED TIMEOUT SETTINGS:")
    print(f"  Minimum: {int(total_estimate * 1.5)} seconds ({total_estimate * 1.5/60:.1f} minutes)")
    print(f"  Recommended: {int(total_estimate * 2)} seconds ({total_estimate * 2/60:.1f} minutes)")
    print(f"  Safe: {int(total_estimate * 3)} seconds ({total_estimate * 3/60:.1f} minutes)")

if __name__ == "__main__":
    main()