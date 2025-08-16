#!/usr/bin/env python3
"""
Test the DataFrame reference fix by running the full pipeline
Expected: 99%+ match rate instead of 0.7%
"""
import asyncio
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def test_dataframe_fix():
    print("🚀 TESTING DATAFRAME REFERENCE FIX")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    print("\nExpected Results:")
    print("  - Match rate: >99% (was 0.7%)")
    print("  - Q6EMK4: Should match to NCBIGene:114990")
    print("  - Runtime: ~2 minutes")
    print("=" * 60)
    
    # Initialize service
    print("\n1. Initializing strategy service...")
    service = MinimalStrategyService(strategies_dir="configs/strategies")
    
    # Use the simple production strategy
    strategy_name = "production_simple_working"
    print(f"\n2. Running strategy: {strategy_name}")
    print("   - Arivale proteins: 1,162 unique UniProt IDs")
    print("   - KG2c entities: 350,368 proteins")
    
    # Start timer
    start_time = time.time()
    
    print("\n3. Executing pipeline (this should take ~2 minutes)...")
    
    try:
        # Run the strategy
        result = await service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name="",
            target_endpoint_name="",
            input_identifiers=[]
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ Pipeline completed in {elapsed:.1f} seconds")
        
        # Analyze results
        print("\n4. Analyzing results...")
        results_file = Path("/tmp/biomapper_results/protein_mapping_results.csv")
        
        if results_file.exists():
            df = pd.read_csv(results_file, low_memory=False)
            
            # Calculate match statistics
            total_rows = len(df)
            matched = df[df['match_status'] == 'matched']
            matched_count = len(matched)
            
            # Get unique proteins
            if 'uniprot' in df.columns:
                unique_source = df['uniprot'].nunique()
                unique_matched = matched['uniprot'].nunique() if 'uniprot' in matched.columns else 0
            else:
                unique_source = 1162  # Known value
                unique_matched = matched_count
            
            match_rate = (unique_matched / unique_source * 100) if unique_source > 0 else 0
            
            print(f"\n📊 RESULTS:")
            print(f"   Total rows: {total_rows:,}")
            print(f"   Matched rows: {matched_count:,}")
            print(f"   Unique proteins: {unique_source}")
            print(f"   Unique matched: {unique_matched}")
            print(f"   Match rate: {match_rate:.1f}%")
            
            # Check Q6EMK4 specifically
            print(f"\n🔍 Q6EMK4 Check:")
            q6_rows = df[df['uniprot'] == 'Q6EMK4'] if 'uniprot' in df.columns else pd.DataFrame()
            
            if len(q6_rows) > 0:
                q6_status = q6_rows.iloc[0]['match_status']
                print(f"   Status: {q6_status}")
                
                if q6_status == 'matched':
                    print(f"   ✅ Q6EMK4 MATCHED!")
                    if 'id' in q6_rows.columns:
                        print(f"   Target: {q6_rows.iloc[0]['id']}")
                    if 'name' in q6_rows.columns:
                        print(f"   Name: {q6_rows.iloc[0]['name']}")
                else:
                    print(f"   ❌ Q6EMK4 still showing as {q6_status}")
            else:
                print(f"   ❌ Q6EMK4 not found in results")
            
            # Verdict
            print(f"\n" + "=" * 60)
            print("🎯 VERDICT:")
            
            if match_rate > 95:
                print(f"   ✅ SUCCESS! Match rate improved from 0.7% to {match_rate:.1f}%")
                print(f"   The DataFrame reference fix WORKS!")
            elif match_rate > 70:
                print(f"   ⚠️  PARTIAL SUCCESS: {match_rate:.1f}% match rate")
                print(f"   Better than 0.7% but not the expected 99%")
            else:
                print(f"   ❌ FIX DIDN'T WORK: Still only {match_rate:.1f}% match rate")
                print(f"   The issue may be elsewhere")
            
            # Sample some matches to verify
            if matched_count > 0:
                print(f"\n📝 Sample matched proteins:")
                sample = matched.head(5)
                for _, row in sample.iterrows():
                    print(f"   - {row.get('uniprot', 'N/A')} -> {row.get('id', 'N/A')}")
            
            return match_rate > 95
            
        else:
            print(f"❌ Results file not found: {results_file}")
            return False
            
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
if __name__ == "__main__":
    print("Testing DataFrame reference fix...")
    print("This will run the full production pipeline.\n")
    
    success = asyncio.run(test_dataframe_fix())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DataFrame fix CONFIRMED! The pipeline works correctly.")
        print("\nNext steps:")
        print("1. Upload results to Google Drive")
        print("2. Apply the same fix to other actions")
        print("3. Add DataFrame safety to standardization tasks")
    else:
        print("⚠️  Fix needs more investigation")
        print("Check the debug logs for Q6EMK4 specific messages")