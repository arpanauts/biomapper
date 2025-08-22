#!/usr/bin/env python3
"""Test each metabolomics pipeline action independently to verify interfaces."""

import asyncio
import json
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add src to path
sys.path.insert(0, '/home/ubuntu/biomapper/src')

# Import the actions we need to test
from actions.registry import ACTION_REGISTRY


async def test_stage1_nightingale():
    """Test Stage 1: METABOLITE_NIGHTINGALE_BRIDGE action."""
    print("\n" + "="*70)
    print("TESTING STAGE 1: NIGHTINGALE BRIDGE")
    print("="*70)
    
    try:
        # Get the action class
        if "METABOLITE_NIGHTINGALE_BRIDGE" not in ACTION_REGISTRY:
            print("❌ METABOLITE_NIGHTINGALE_BRIDGE not registered!")
            return None
            
        action_class = ACTION_REGISTRY["METABOLITE_NIGHTINGALE_BRIDGE"]
        action = action_class()
        
        # Create minimal test context
        context = {
            "datasets": {
                "arivale_data": [
                    {"identifier": "Total cholesterol", "name": "Total cholesterol"},
                    {"identifier": "LDL cholesterol", "name": "LDL cholesterol"},
                    {"identifier": "HDL cholesterol", "name": "HDL cholesterol"},
                    {"identifier": "Triglycerides", "name": "Triglycerides"},
                    {"identifier": "Glucose", "name": "Glucose"},
                ],
                "reference_data": [
                    {"identifier": "Total cholesterol", "title": "Total cholesterol"},
                    {"identifier": "LDL-C", "title": "LDL cholesterol"},
                    {"identifier": "HDL-C", "title": "HDL cholesterol"},
                ]
            }
        }
        
        # Test parameters
        params = {
            "input_key": "arivale_data",
            "reference_key": "reference_data",
            "output_key": "stage_1_matched",
            "unmatched_key": "stage_1_unmatched",
            "threshold": 0.7
        }
        
        # Execute the action
        print("Executing METABOLITE_NIGHTINGALE_BRIDGE...")
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="metabolite",
            action_params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        # Analyze results
        if result:
            print("✅ Stage 1 executed successfully!")
            if "details" in result:
                print(f"Details: {json.dumps(result['details'], indent=2)}")
            
            # Check if datasets were updated
            if "stage_1_matched" in context["datasets"]:
                matched = context["datasets"]["stage_1_matched"]
                print(f"Matched: {len(matched)} metabolites")
                
            if "stage_1_unmatched" in context["datasets"]:
                unmatched = context["datasets"]["stage_1_unmatched"]
                print(f"Unmatched: {len(unmatched)} metabolites")
                
            return result
        else:
            print("❌ Stage 1 returned no result")
            return None
            
    except Exception as e:
        print(f"❌ Stage 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_stage2_fuzzy():
    """Test Stage 2: METABOLITE_FUZZY_STRING_MATCH action."""
    print("\n" + "="*70)
    print("TESTING STAGE 2: FUZZY STRING MATCH")
    print("="*70)
    
    try:
        if "METABOLITE_FUZZY_STRING_MATCH" not in ACTION_REGISTRY:
            print("❌ METABOLITE_FUZZY_STRING_MATCH not registered!")
            return None
            
        action_class = ACTION_REGISTRY["METABOLITE_FUZZY_STRING_MATCH"]
        action = action_class()
        
        # Create test context with Stage 1 unmapped format
        context = {
            "datasets": {
                "nightingale_unmapped": [
                    {"name": "Glucose", "for_stage": 2, "reason": "no_direct_match"},
                    {"name": "Insulin", "for_stage": 2, "reason": "no_direct_match"},
                    {"name": "C-reactive protein", "for_stage": 2, "reason": "no_direct_match"},
                ],
                "reference_metabolites": [
                    {"name": "Glucose, serum", "id": "GLUC"},
                    {"name": "Insulin, fasting", "id": "INS"},
                    {"name": "C-reactive protein (CRP)", "id": "CRP"},
                ]
            }
        }
        
        params = {
            "unmapped_key": "nightingale_unmapped",
            "reference_key": "reference_metabolites",
            "output_key": "fuzzy_matched",
            "final_unmapped_key": "fuzzy_unmapped",
            "fuzzy_threshold": 85.0
        }
        
        print("Executing METABOLITE_FUZZY_STRING_MATCH...")
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="metabolite",
            action_params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        if result:
            print("✅ Stage 2 executed successfully!")
            if isinstance(result, dict):
                if "success" in result:
                    print(f"Success: {result.get('success')}")
                if "total_matches" in result:
                    print(f"Matches: {result.get('total_matches')}")
            return result
        else:
            print("❌ Stage 2 returned no result")
            return None
            
    except Exception as e:
        print(f"❌ Stage 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_stage3_rampdb():
    """Test Stage 3: METABOLITE_RAMPDB_BRIDGE action."""
    print("\n" + "="*70)
    print("TESTING STAGE 3: RAMPDB BRIDGE")
    print("="*70)
    
    try:
        if "METABOLITE_RAMPDB_BRIDGE" not in ACTION_REGISTRY:
            print("❌ METABOLITE_RAMPDB_BRIDGE not registered!")
            return None
            
        action_class = ACTION_REGISTRY["METABOLITE_RAMPDB_BRIDGE"]
        action = action_class()
        
        # Test context with Stage 2 unmapped format
        context = {
            "datasets": {
                "fuzzy_unmapped": [
                    {"name": "Acetylcarnitine", "for_stage": 3, "reason": "no_fuzzy_match"},
                    {"name": "Phosphatidylcholine", "for_stage": 3, "reason": "no_fuzzy_match"},
                ]
            }
        }
        
        params = {
            "unmapped_key": "fuzzy_unmapped",
            "output_key": "rampdb_matched",
            "final_unmapped_key": "rampdb_unmapped",
            "confidence_threshold": 0.8,
            "batch_size": 10
        }
        
        print("Executing METABOLITE_RAMPDB_BRIDGE...")
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="metabolite",
            action_params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        if result:
            print("✅ Stage 3 executed (may have no matches due to mock data)")
            return result
        else:
            print("❌ Stage 3 returned no result")
            return None
            
    except Exception as e:
        print(f"❌ Stage 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_stage4_hmdb():
    """Test Stage 4: HMDB_VECTOR_MATCH action."""
    print("\n" + "="*70)
    print("TESTING STAGE 4: HMDB VECTOR MATCH")
    print("="*70)
    
    try:
        if "HMDB_VECTOR_MATCH" not in ACTION_REGISTRY:
            print("❌ HMDB_VECTOR_MATCH not registered!")
            return None
            
        action_class = ACTION_REGISTRY["HMDB_VECTOR_MATCH"]
        action = action_class()
        
        # Test context with Stage 3 unmapped format
        context = {
            "datasets": {
                "stage_4_input": [
                    {"BIOCHEMICAL_NAME": "Unknown metabolite 1", "for_stage": 4},
                    {"BIOCHEMICAL_NAME": "Unknown metabolite 2", "for_stage": 4},
                ]
            }
        }
        
        params = {
            "input_key": "stage_4_input",
            "output_key": "stage_4_matched",
            "unmatched_key": "stage_4_unmatched",
            "threshold": 0.75,
            "use_qdrant": False,  # Disable for testing
            "enable_llm_validation": False  # Disable for testing
        }
        
        print("Executing HMDB_VECTOR_MATCH...")
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="metabolite",
            action_params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        if result:
            print("✅ Stage 4 executed (may fail due to vector DB requirements)")
            return result
        else:
            print("❌ Stage 4 returned no result")
            return None
            
    except Exception as e:
        print(f"❌ Stage 4 failed: {e}")
        print("Note: This is expected if Qdrant is not configured")
        return None


async def test_all_stages():
    """Test all stages independently."""
    print("="*70)
    print("METABOLOMICS PIPELINE - INDIVIDUAL ACTION TESTS")
    print("="*70)
    
    results = {}
    
    # Test each stage
    results["stage1"] = await test_stage1_nightingale()
    results["stage2"] = await test_stage2_fuzzy()
    results["stage3"] = await test_stage3_rampdb()
    results["stage4"] = await test_stage4_hmdb()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for stage, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{stage}: {status}")
    
    # Check which actions are registered
    print("\n" + "="*70)
    print("REGISTERED METABOLITE ACTIONS")
    print("="*70)
    metabolite_actions = [k for k in ACTION_REGISTRY.keys() if 'METABOLITE' in k]
    for action in metabolite_actions:
        print(f"  - {action}")
    
    return results


if __name__ == "__main__":
    # Run all tests
    results = asyncio.run(test_all_stages())
    
    # Exit with appropriate code
    all_passed = all(r is not None for r in results.values())
    exit(0 if all_passed else 1)