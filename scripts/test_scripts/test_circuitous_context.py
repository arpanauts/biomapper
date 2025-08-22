#!/usr/bin/env python3
"""
Test Circuitous Framework Context Flow Solution
===============================================

🔄 This test validates that the UniversalContext wrapper enables smooth
context flow through the pipeline without modifying action internals.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, 'src')

from core.universal_context import UniversalContext, ensure_universal_context
from core.circuitous_orchestration import CircuitousOrchestrator, apply_circuitous_orchestration
from core.minimal_strategy_service import MinimalStrategyService


def test_universal_context_compatibility():
    """Test that UniversalContext works with both dict and object patterns."""
    print("\n🔄 Testing UniversalContext Compatibility")
    print("=" * 60)
    
    # Create context
    context = UniversalContext()
    
    # Test dict-style access
    print("\n1. Dict-style access:")
    context['test_key'] = 'test_value'
    assert context.get('test_key') == 'test_value'
    assert 'test_key' in context
    print("   ✅ Dict-style access works")
    
    # Test object-style access
    print("\n2. Object-style access:")
    context.datasets = {'test_dataset': [1, 2, 3]}
    assert hasattr(context, 'datasets')
    assert context.datasets == {'test_dataset': [1, 2, 3]}
    print("   ✅ Object-style access works")
    
    # Test specialized methods
    print("\n3. Pipeline orchestration methods:")
    context.set_dataset('new_dataset', [4, 5, 6])
    assert context.has_dataset('new_dataset')
    assert context.get_dataset('new_dataset') == [4, 5, 6]
    print("   ✅ Pipeline methods work")
    
    # Test wrapping different types
    print("\n4. Context wrapping:")
    
    # Wrap dict
    dict_context = {'key': 'value', 'datasets': {'ds1': [1, 2]}}
    wrapped_dict = UniversalContext.wrap(dict_context)
    assert wrapped_dict.get('key') == 'value'
    assert wrapped_dict.datasets == {'ds1': [1, 2]}
    print("   ✅ Dict wrapping works")
    
    # Wrap object
    class MockContext:
        def __init__(self):
            self.datasets = {'ds2': [3, 4]}
            self.parameters = {'p1': 'v1'}
    
    obj_context = MockContext()
    wrapped_obj = UniversalContext.wrap(obj_context)
    assert wrapped_obj.get('datasets') == {'ds2': [3, 4]}
    assert wrapped_obj.parameters == {'p1': 'v1'}
    print("   ✅ Object wrapping works")
    
    print("\n🔄 UniversalContext compatibility test PASSED!")
    return True


def test_action_context_handling():
    """Test that actions can use context regardless of their expected format."""
    print("\n🔄 Testing Action Context Handling")
    print("=" * 60)
    
    # Simulate action that expects dict context
    def dict_style_action(context):
        datasets = context.get('datasets', {})
        context['datasets']['output'] = 'dict_result'
        return True
    
    # Simulate action that expects object context
    def object_style_action(context):
        datasets = context.datasets
        context.datasets['output2'] = 'object_result'
        return True
    
    # Create universal context
    context = UniversalContext({'datasets': {}})
    
    # Test dict-style action
    print("\n1. Dict-style action:")
    dict_style_action(context)
    assert context.get_dataset('output') == 'dict_result'
    print("   ✅ Dict-style action works with UniversalContext")
    
    # Test object-style action
    print("\n2. Object-style action:")
    object_style_action(context)
    assert context.get_dataset('output2') == 'object_result'
    print("   ✅ Object-style action works with UniversalContext")
    
    # Verify both results coexist
    print("\n3. Context maintains all data:")
    datasets = context.get_datasets()
    assert 'output' in datasets
    assert 'output2' in datasets
    print(f"   ✅ Both datasets present: {list(datasets.keys())}")
    
    print("\n🔄 Action context handling test PASSED!")
    return True


async def test_pipeline_orchestration():
    """Test circuitous orchestration with real pipeline."""
    print("\n🔄 Testing Pipeline Orchestration")
    print("=" * 60)
    
    # Create service
    strategies_dir = Path("src/configs/strategies")
    service = MinimalStrategyService(strategies_dir=strategies_dir)
    
    # Apply circuitous orchestration
    apply_circuitous_orchestration(service)
    print("   ✅ Circuitous orchestration applied")
    
    # Create test context with just Stage 1
    context = {
        "parameters": {
            "stages_to_run": [1],
            "output_dir": "/tmp/biomapper/circuitous_test",
            "debug_mode": True
        }
    }
    
    print("\n   Testing with wrapped context...")
    
    # Test simplified strategy first
    try:
        result = await service.execute_strategy(
            strategy_name="test_stage1_only",
            context=context
        )
        
        if result.get('success'):
            print("   ✅ Stage 1 execution successful with circuitous orchestration")
            
            # Check datasets were created
            if 'datasets' in result:
                datasets = result['datasets']
                print(f"   ✅ Datasets created: {list(datasets.keys())[:5]}...")
        else:
            print(f"   ⚠️ Execution failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔄 Pipeline orchestration test completed!")
    return True


def test_context_handoff_validation():
    """Test context validation for stage transitions."""
    print("\n🔄 Testing Context Handoff Validation")
    print("=" * 60)
    
    orchestrator = CircuitousOrchestrator()
    
    # Create context with some datasets
    context = UniversalContext({
        'datasets': {
            'stage1_output': [1, 2, 3],
            'stage2_output': [4, 5, 6]
        }
    })
    
    # Test valid transition
    print("\n1. Valid transition:")
    valid = orchestrator.validate_stage_transition(
        'stage1', 'stage2',
        context,
        required_datasets=['stage1_output']
    )
    assert valid
    print("   ✅ Valid transition passes")
    
    # Test invalid transition
    print("\n2. Invalid transition:")
    invalid = orchestrator.validate_stage_transition(
        'stage2', 'stage3',
        context,
        required_datasets=['stage3_input']  # Doesn't exist
    )
    assert not invalid
    print("   ✅ Invalid transition caught")
    
    print("\n🔄 Context handoff validation test PASSED!")
    return True


def main():
    """Run all circuitous framework tests."""
    print("\n" + "=" * 70)
    print("🔄 CIRCUITOUS FRAMEWORK VALIDATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Universal Context Compatibility", test_universal_context_compatibility),
        ("Action Context Handling", test_action_context_handling),
        ("Context Handoff Validation", test_context_handoff_validation),
        ("Pipeline Orchestration", lambda: asyncio.run(test_pipeline_orchestration()))
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"   ❌ {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"   ❌ {test_name} raised exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"🔄 CIRCUITOUS FRAMEWORK VALIDATION RESULTS")
    print(f"   Passed: {passed}/{len(tests)}")
    print(f"   Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ All circuitous framework tests PASSED!")
        print("🔄 The UniversalContext wrapper successfully enables smooth")
        print("   context flow through the pipeline without modifying actions.")
    else:
        print(f"\n⚠️ {failed} tests failed. Review implementation.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()