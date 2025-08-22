#!/usr/bin/env python3
"""
Simple test of metabolomics actions to verify the pipeline components work.
"""
import os
import sys
import pandas as pd
from pathlib import Path

# Setup paths
sys.path.insert(0, 'src')
os.chdir('/home/ubuntu/biomapper')

def test_action_imports():
    """Test that our metabolomics actions can be imported."""
    print("Testing action imports...")
    
    try:
        # Test HMDB Vector Match Action
        from actions.entities.metabolites.matching.hmdb_vector_match import HMDBVectorMatchAction
        print("✅ HMDB Vector Match action imported successfully")
        
        # Test other metabolite actions
        from actions.entities.metabolites.identification.nightingale_bridge import NightingaleBridgeAction
        print("✅ Nightingale Bridge action imported successfully")
        
        from actions.entities.metabolites.matching.fuzzy_string_match import MetaboliteFuzzyStringMatch
        print("✅ Fuzzy String Match action imported successfully")
        
        from actions.entities.metabolites.matching.rampdb_bridge import MetaboliteRampdbBridge
        print("✅ RampDB Bridge action imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_data_loading():
    """Test that we can load the metabolomics data."""
    print("\nTesting data loading...")
    
    arivale_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv"
    ukbb_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv"
    
    try:
        if os.path.exists(arivale_file):
            arivale_df = pd.read_csv(arivale_file, sep='\t')
            print(f"✅ Arivale data loaded: {len(arivale_df)} metabolites")
            print(f"   Columns: {list(arivale_df.columns)[:5]}...")
        else:
            print(f"⚠️ Arivale file not found: {arivale_file}")
            
        if os.path.exists(ukbb_file):
            ukbb_df = pd.read_csv(ukbb_file, sep='\t')
            print(f"✅ UKBB data loaded: {len(ukbb_df)} metabolites")
            print(f"   Columns: {list(ukbb_df.columns)[:5]}...")
        else:
            print(f"⚠️ UKBB file not found: {ukbb_file}")
            
        return True
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        return False

def test_qdrant_availability():
    """Test if Qdrant collection is available."""
    print("\nTesting Qdrant availability...")
    
    qdrant_path = "/home/ubuntu/biomapper/data/qdrant_storage"
    hmdb_collection = f"{qdrant_path}/collections/hmdb_metabolites"
    
    if os.path.exists(hmdb_collection):
        print(f"✅ HMDB Qdrant collection found at: {hmdb_collection}")
        
        # Check if we can import qdrant_client
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(path=qdrant_path)
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]
            print(f"✅ Qdrant client works. Collections: {collection_names}")
            return True
        except ImportError:
            print("⚠️ Qdrant client not installed")
            return False
        except Exception as e:
            print(f"⚠️ Qdrant connection error: {e}")
            return False
    else:
        print(f"❌ HMDB collection not found: {hmdb_collection}")
        return False

def test_strategy_file():
    """Test that our strategy file is valid."""
    print("\nTesting strategy file...")
    
    strategy_file = "src/configs/strategies/experimental/metabolomics_progressive_production.yaml"
    
    try:
        import yaml
        with open(strategy_file, 'r') as f:
            strategy = yaml.safe_load(f)
        
        print(f"✅ Strategy file loaded: {strategy['name']}")
        print(f"   Description: {strategy['description'][:100]}...")
        print(f"   Steps: {len(strategy['steps'])}")
        
        # Check for key parameters
        params = strategy.get('parameters', {})
        print(f"   Parameters: file_path={params.get('file_path', 'NOT_SET')}")
        print(f"   Parameters: directory_path={params.get('directory_path', 'NOT_SET')}")
        print(f"   Parameters: stage_4_enabled={params.get('stage_4_enabled', 'NOT_SET')}")
        
        return True
    except Exception as e:
        print(f"❌ Strategy file error: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("METABOLOMICS PROGRESSIVE PIPELINE - COMPONENT TEST")
    print("="*60)
    
    results = []
    results.append(test_action_imports())
    results.append(test_data_loading())
    results.append(test_qdrant_availability())
    results.append(test_strategy_file())
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All component tests passed! Pipeline components are ready.")
    elif passed >= total - 1:
        print("✅ Most components working. Minor issues may exist.")
    else:
        print("⚠️ Some components have issues. Check logs above.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)