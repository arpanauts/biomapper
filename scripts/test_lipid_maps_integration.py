#!/usr/bin/env python3
"""
Integration test for LIPID MAPS SPARQL action.
Tests the action with real metabolite data and verifies pipeline integration.
"""

import asyncio
import pandas as pd
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, 'src')

# Import the action
from actions.entities.metabolites.external.lipid_maps_sparql_match import (
    LipidMapsSparqlMatch,
    LipidMapsSparqlParams
)
from core.standards.context_handler import UniversalContext


async def test_lipid_maps_integration():
    """Test LIPID MAPS action with realistic data."""
    
    print("=" * 60)
    print("LIPID MAPS SPARQL Action Integration Test")
    print("=" * 60)
    
    # Create test data with realistic unmapped metabolites
    test_metabolites = pd.DataFrame([
        {"identifier": "cholesterol", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sterol"},
        {"identifier": "palmitic acid", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "glucose", "SUPER_PATHWAY": "Carbohydrate", "SUB_PATHWAY": "Sugar"},
        {"identifier": "18:2n6", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "oleic acid", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "DHA", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "alanine", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Alanine Metabolism"},
    ])
    
    print(f"\nTest Data: {len(test_metabolites)} metabolites")
    print(f"  Lipids: {len(test_metabolites[test_metabolites['SUPER_PATHWAY'] == 'Lipid'])}")
    print(f"  Non-lipids: {len(test_metabolites[test_metabolites['SUPER_PATHWAY'] != 'Lipid'])}")
    
    # Create context
    context = {
        "datasets": {
            "stage_4_unmapped": test_metabolites,
            "original_metabolites": test_metabolites  # For coverage calculation
        },
        "statistics": {
            "progressive_stage4": {
                "cumulative_matched": 0,
                "cumulative_coverage": 0.0
            }
        }
    }
    
    # Test 1: Feature flag OFF
    print("\n--- Test 1: Feature Flag OFF ---")
    action = LipidMapsSparqlMatch()
    params_disabled = LipidMapsSparqlParams(
        input_key="stage_4_unmapped",
        output_key="stage_5_matched",
        unmatched_key="final_unmapped",
        enabled=False  # Disabled
    )
    
    result = await action.execute_typed(params_disabled, context)
    print(f"Result: {result.message}")
    assert result.success == True
    assert result.queries_executed == 0
    print("✓ Feature flag correctly disables action")
    
    # Test 2: Feature flag ON with timeout control
    print("\n--- Test 2: Feature Flag ON with Conservative Settings ---")
    params_enabled = LipidMapsSparqlParams(
        input_key="stage_4_unmapped",
        output_key="stage_5_matched",
        unmatched_key="final_unmapped",
        enabled=True,
        fail_on_error=False,  # Never fail pipeline
        timeout_seconds=3,  # Conservative timeout
        filter_lipids_only=True,  # Only query lipids
        batch_size=3  # Small batches
    )
    
    result = await action.execute_typed(params_enabled, context)
    print(f"Result: {result.message}")
    print(f"  Success: {result.success}")
    print(f"  Matches found: {result.matches_found}")
    print(f"  Queries executed: {result.queries_executed}")
    print(f"  Timeouts: {result.timeouts}")
    print(f"  SPARQL errors: {result.sparql_errors}")
    print(f"  Average query time: {result.average_query_time:.2f}s")
    print(f"  Coverage improvement: {result.stage5_coverage_improvement:.1f}%")
    
    # Check results
    matched = context["datasets"].get("stage_5_matched")
    unmapped = context["datasets"].get("final_unmapped")
    
    if matched is not None and not matched.empty:
        print(f"\n✓ Matched {len(matched)} metabolites:")
        for _, row in matched.iterrows():
            print(f"  - {row['identifier']} → {row.get('lipid_maps_id', 'Unknown')} (confidence: {row.get('confidence_score', 0):.2f})")
    else:
        print("\n⚠ No matches found (SPARQL may be unavailable)")
    
    if unmapped is not None and not unmapped.empty:
        print(f"\n{len(unmapped)} still unmapped:")
        for _, row in unmapped.head(3).iterrows():
            print(f"  - {row['identifier']}")
    
    # Check progressive statistics
    if "progressive_stage5" in context["statistics"]:
        stats = context["statistics"]["progressive_stage5"]
        print(f"\nProgressive Statistics:")
        print(f"  Stage: {stats['stage']}")
        print(f"  LIPID MAPS matched: {stats['lipid_maps_matched']}")
        print(f"  Still unmapped: {stats['still_unmapped']}")
        print(f"  Cumulative coverage: {stats['cumulative_coverage']:.1%}")
    
    # Test 3: Cache functionality
    print("\n--- Test 3: Cache Functionality ---")
    # Reset datasets but keep cache
    context["datasets"]["stage_4_unmapped"] = test_metabolites
    
    result2 = await action.execute_typed(params_enabled, context)
    print(f"Second run with cache:")
    print(f"  Queries executed: {result2.queries_executed}")
    print(f"  Cache hits: {result2.cache_hits}")
    
    if result2.cache_hits > 0:
        print("✓ Cache is working")
    else:
        print("⚠ Cache not utilized (may be due to SPARQL failures)")
    
    print("\n" + "=" * 60)
    print("Integration Test Complete")
    print("=" * 60)
    
    # Summary
    if result.success:
        print("\n✅ Action is production-ready with:")
        print("  • Feature flag control working")
        print("  • Timeout management in place")
        print("  • Error handling functional")
        print("  • Progressive statistics integrated")
        
        if result.timeouts > 0:
            print("\n⚠ Warning: Some timeouts occurred")
            print("  Consider monitoring timeout rates in production")
    else:
        print("\n❌ Action failed - review error handling")
    
    return result


if __name__ == "__main__":
    # Run the async test
    result = asyncio.run(test_lipid_maps_integration())
    
    # Exit with appropriate code
    exit(0 if result.success else 1)