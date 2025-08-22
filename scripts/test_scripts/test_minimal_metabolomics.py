#!/usr/bin/env python3
"""
Minimal test of metabolomics pipeline - Stages 1-2 only, no external dependencies.
This establishes a baseline for what works without APIs or expensive features.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

# Disable expensive features
os.environ['STAGE_3_ENABLED'] = 'false'  # No RampDB API
os.environ['STAGE_4_ENABLED'] = 'false'  # No HMDB VectorRAG
os.environ['ENABLE_LLM_ANALYSIS'] = 'false'  # No LLM
os.environ['ENABLE_DRIVE_SYNC'] = 'false'  # No Google Drive
os.environ['ENABLE_VISUALIZATIONS'] = 'false'  # Skip for now

# Set output directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_dir = f'/tmp/metabolomics_minimal_test_{timestamp}'
os.environ['OUTPUT_DIR'] = output_dir

print("=" * 60)
print("MINIMAL METABOLOMICS PIPELINE TEST")
print("=" * 60)
print(f"Testing Stages 1-2 only (no external APIs)")
print(f"Output: {output_dir}")
print("=" * 60)

try:
    from client.client_v2 import BiomapperClient
    
    print("\n1. Initializing client...")
    client = BiomapperClient()
    print("   ✅ Client initialized")
    
    print("\n2. Running minimal pipeline...")
    print("   Stage 1: Nightingale Bridge (direct ID matching)")
    print("   Stage 2: Fuzzy String Match (algorithmic)")
    print("   Stage 3: DISABLED (RampDB API)")
    print("   Stage 4: DISABLED (HMDB VectorRAG)")
    
    result = client.run("metabolomics_progressive_production")
    
    if result:
        print("\n   ✅ Pipeline completed!")
        
        # Check for output files
        output_path = Path(output_dir)
        if output_path.exists():
            files = list(output_path.glob("*.tsv"))
            print(f"\n3. Generated {len(files)} output files:")
            for f in files:
                size = f.stat().st_size / 1024
                print(f"   - {f.name} ({size:.1f} KB)")
            
            # Try to get coverage stats
            matched_file = output_path / "matched_metabolites_v3.0.tsv"
            if matched_file.exists():
                with open(matched_file) as f:
                    matched_count = len(f.readlines()) - 1  # Subtract header
                
                # Arivale has ~1351 metabolites
                coverage = (matched_count / 1351) * 100
                
                print(f"\n4. Coverage Statistics:")
                print(f"   Matched: {matched_count} metabolites")
                print(f"   Coverage: {coverage:.1f}%")
                print(f"   (Stages 1-2 only, no API calls)")
                
                print("\n" + "=" * 60)
                print("BASELINE ESTABLISHED")
                print("=" * 60)
                print(f"Minimal coverage (Stages 1-2): {coverage:.1f}%")
                print("This is what works WITHOUT:")
                print("  - RampDB API access")
                print("  - HMDB vector database")
                print("  - LLM analysis")
                print("  - Google Drive sync")
                
                if coverage > 50:
                    print("\n✅ Good baseline coverage!")
                else:
                    print("\n⚠️ Low baseline - may need Stage 3-4 for viability")
            else:
                print("\n⚠️ No matched metabolites file found")
        else:
            print(f"\n⚠️ Output directory not created: {output_dir}")
    else:
        print("\n❌ Pipeline failed")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()