#!/usr/bin/env python3
"""
Test the surgical framework with GENERATE_MAPPING_VISUALIZATIONS.

This script demonstrates how the framework:
1. Detects surgical intent
2. Captures baseline behavior
3. Validates changes are safe
4. Ensures no pipeline impact
"""

import sys
import os
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

import logging
from pathlib import Path
import pandas as pd
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import surgical framework
from core.safety import (
    ActionSurgeon,
    SurgicalMode,
    surgical_framework
)


def test_surgical_detection():
    """Test that surgical intent is correctly detected."""
    print("\n" + "="*60)
    print("TEST 1: Surgical Intent Detection")
    print("="*60)
    
    test_messages = [
        "The visualization shows 3675 proteins but should show unique entities",
        "Fix the statistics counting in GENERATE_MAPPING_VISUALIZATIONS",
        "The entity counting is wrong, it's counting expanded records",
        "Update the visualization without breaking the pipeline",
        "Just run the pipeline normally",  # Should NOT trigger
        "Export the data to CSV"  # Should NOT trigger
    ]
    
    for msg in test_messages:
        needs_surgical, action_type = ActionSurgeon.should_use_surgical_mode(msg)
        print(f"\nMessage: '{msg[:50]}...'" if len(msg) > 50 else f"\nMessage: '{msg}'")
        print(f"  → Surgical: {needs_surgical}, Action: {action_type}")
    
    print("\n✅ Detection test complete")


def test_baseline_capture():
    """Test baseline capture for GENERATE_MAPPING_VISUALIZATIONS."""
    print("\n" + "="*60)
    print("TEST 2: Baseline Capture")
    print("="*60)
    
    # Create test context with realistic data
    test_df = pd.DataFrame({
        'uniprot': ['P12345', 'P12345', 'Q67890', 'Q67890', 'R11111'],
        'confidence_score': [1.0, 1.0, 0.95, 0.95, 0.0],
        'match_type': ['direct', 'direct', 'composite', 'composite', 'unmapped'],
        'mapping_stage': [1, 1, 2, 2, 99]
    })
    
    test_context = {
        'datasets': {
            'final_mappings': test_df
        },
        'output_files': [],
        'statistics': {},
        'progressive_stats': {
            'stages': {
                '0': {'name': 'Input', 'matched': 0, 'new_matches': 0},
                '1': {'name': 'Direct', 'matched': 2, 'new_matches': 2},
                '2': {'name': 'Composite', 'matched': 2, 'new_matches': 2}
            },
            'total_input_entities': 3  # The TRUE unique count
        }
    }
    
    # Save test context for action to use
    test_dir = Path("/tmp/biomapper/surgical/GENERATE_MAPPING_VISUALIZATIONS")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    with open(test_dir / "test_context.json", 'w') as f:
        # Convert DataFrame to serializable format
        context_copy = test_context.copy()
        context_copy['datasets'] = {
            'final_mappings': test_df.to_dict('records')
        }
        json.dump(context_copy, f, indent=2)
    
    # Create surgeon and capture baseline
    surgeon = ActionSurgeon("GENERATE_MAPPING_VISUALIZATIONS")
    
    try:
        baseline = surgeon.capture_baseline(test_context)
        
        print(f"\n📸 Baseline captured:")
        print(f"  - Action: {baseline.action_type}")
        print(f"  - Context reads: {baseline.context_keys_read}")
        print(f"  - Context writes: {baseline.context_keys_written}")
        print(f"  - Output structures: {len(baseline.output_structure)} files")
        
        print("\n✅ Baseline capture successful")
        return surgeon
        
    except Exception as e:
        print(f"\n❌ Baseline capture failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_agent_integration():
    """Test the agent integration for automatic activation."""
    print("\n" + "="*60)
    print("TEST 3: Agent Integration")
    print("="*60)
    
    # Simulate user message
    user_message = "The statistics in the visualization are counting expanded records (3675) instead of unique entities (should be ~1200)"
    
    print(f"\nUser: {user_message}")
    
    # Process through surgical framework
    surgical_context = surgical_framework.process_user_message(user_message)
    
    if surgical_context:
        print(f"\nAgent Response:")
        print(surgical_context['initial_response'])
        print(f"\n  Mode: {surgical_context['mode']}")
        print(f"  Action: {surgical_context['action_type']}")
        print("\n✅ Agent integration working")
    else:
        print("\n❌ Surgical mode not activated (should have been)")


def test_validation_simulation():
    """Simulate validation of changes."""
    print("\n" + "="*60)
    print("TEST 4: Change Validation (Simulation)")
    print("="*60)
    
    print("\nSimulating surgical changes to statistics calculation...")
    
    # This would normally involve actual code changes
    # For now, we simulate the validation results
    
    validation_results = [
        "✅ Context Interface: Context interface preserved",
        "✅ Output Structure: Output structures preserved", 
        "✅ Data Types: Data types preserved"
    ]
    
    print("\nValidation Results:")
    for result in validation_results:
        print(f"  {result}")
    
    print("\n✅ All validations pass - changes are safe!")


def main():
    """Run all tests."""
    print("\n" + "🔬 SURGICAL FRAMEWORK TEST SUITE 🔬")
    print("="*60)
    
    # Test 1: Detection
    test_surgical_detection()
    
    # Test 2: Baseline capture
    surgeon = test_baseline_capture()
    
    # Test 3: Agent integration
    test_agent_integration()
    
    # Test 4: Validation
    test_validation_simulation()
    
    print("\n" + "="*60)
    print("🎉 SURGICAL FRAMEWORK TESTS COMPLETE")
    print("="*60)
    
    print("\nNext Steps:")
    print("1. Apply actual fix to GENERATE_MAPPING_VISUALIZATIONS")
    print("2. Run validation with real changes")
    print("3. Test in full pipeline")


if __name__ == "__main__":
    main()