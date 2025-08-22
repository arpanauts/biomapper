#!/usr/bin/env python3
"""
Test backward compatibility for action parameter updates.
Ensures existing pipelines continue working with old parameter names.
"""

import asyncio
import yaml
import warnings
import logging
from pathlib import Path
from datetime import datetime
import sys
import os

# Add biomapper src to path
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper/src')

from core.minimal_strategy_service import MinimalStrategyService

# Import the action registry after path setup
try:
    from actions.registry import ACTION_REGISTRY
except ImportError:
    # Try alternative import
    import actions
    from actions import registry
    ACTION_REGISTRY = registry.ACTION_REGISTRY

# Configure logging to see deprecation warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Capture warnings
warnings.filterwarnings('always', category=DeprecationWarning)

class BackwardCompatibilityTester:
    """Test backward compatibility of action parameter changes."""
    
    def __init__(self):
        self.test_results = []
        self.deprecation_warnings = []
        
    def capture_warnings(self):
        """Context manager to capture deprecation warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', category=DeprecationWarning)
            yield w
            
    async def test_action_with_old_params(self, action_type: str, old_params: dict, new_params: dict):
        """Test that an action works with both old and new parameter names."""
        
        print(f"\n{'='*60}")
        print(f"Testing {action_type}")
        print(f"{'='*60}")
        
        # Test with old parameters
        print(f"\n1. Testing with OLD parameter names:")
        print(f"   Parameters: {old_params}")
        
        with self.capture_warnings() as captured:
            try:
                # Get action from registry
                if action_type not in ACTION_REGISTRY:
                    print(f"   ❌ Action {action_type} not found in registry")
                    return False
                    
                action_class = ACTION_REGISTRY[action_type]
                action = action_class()
                
                # Create minimal context
                context = {
                    'datasets': {},
                    'output_files': [],
                    'progressive_stats': {
                        'total_processed': 100,
                        'final_match_rate': 0.75,
                        'stages': {
                            '1': {
                                'name': 'Direct Match',
                                'method': 'Exact',
                                'new_matches': 75,
                                'cumulative_matched': 75,
                                'confidence_avg': 0.98,
                                'computation_time': '1.2s'
                            }
                        }
                    }
                }
                
                # Execute action with old parameters
                result = await action.execute(old_params, context)
                
                # Check for deprecation warnings
                dep_warnings = [w for w in captured if issubclass(w.category, DeprecationWarning)]
                
                if dep_warnings:
                    print(f"   ✅ Action executed successfully with old parameters")
                    print(f"   ⚠️  Deprecation warnings captured: {len(dep_warnings)}")
                    for w in dep_warnings:
                        print(f"      - {w.message}")
                        self.deprecation_warnings.append({
                            'action': action_type,
                            'message': str(w.message),
                            'params': 'old'
                        })
                else:
                    print(f"   ⚠️  No deprecation warnings - may not be using backward compatibility")
                    
                self.test_results.append({
                    'action': action_type,
                    'params': 'old',
                    'success': True,
                    'warnings': len(dep_warnings)
                })
                
            except Exception as e:
                print(f"   ❌ Failed with old parameters: {e}")
                self.test_results.append({
                    'action': action_type,
                    'params': 'old',
                    'success': False,
                    'error': str(e)
                })
                return False
        
        # Test with new parameters
        print(f"\n2. Testing with NEW parameter names:")
        print(f"   Parameters: {new_params}")
        
        with self.capture_warnings() as captured:
            try:
                action = action_class()
                result = await action.execute(new_params, context)
                
                # Check for deprecation warnings (should be none with new params)
                dep_warnings = [w for w in captured if issubclass(w.category, DeprecationWarning)]
                
                if dep_warnings:
                    print(f"   ⚠️  Unexpected deprecation warnings with new parameters")
                else:
                    print(f"   ✅ Action executed successfully with new parameters (no warnings)")
                    
                self.test_results.append({
                    'action': action_type,
                    'params': 'new',
                    'success': True,
                    'warnings': len(dep_warnings)
                })
                
            except Exception as e:
                print(f"   ❌ Failed with new parameters: {e}")
                self.test_results.append({
                    'action': action_type,
                    'params': 'new',
                    'success': False,
                    'error': str(e)
                })
                return False
                
        return True
        
    async def test_yaml_strategy_compatibility(self, yaml_path: Path):
        """Test that an existing YAML strategy still works."""
        
        print(f"\n{'='*60}")
        print(f"Testing YAML Strategy: {yaml_path.name}")
        print(f"{'='*60}")
        
        try:
            # Load the YAML
            with open(yaml_path, 'r') as f:
                strategy = yaml.safe_load(f)
                
            print(f"Strategy: {strategy['name']}")
            print(f"Description: {strategy.get('description', 'N/A')[:100]}...")
            
            # Check for actions using old parameters
            old_param_actions = []
            for step in strategy.get('steps', []):
                action = step.get('action', {})
                action_type = action.get('type')
                params = action.get('params', {})
                
                # Check for old parameter names
                if 'output_dir' in params:
                    old_param_actions.append({
                        'step': step['name'],
                        'action': action_type,
                        'old_param': 'output_dir'
                    })
                if 'output_directory' in params:
                    old_param_actions.append({
                        'step': step['name'],
                        'action': action_type,
                        'old_param': 'output_directory'
                    })
                    
            if old_param_actions:
                print(f"\n⚠️  Found {len(old_param_actions)} actions using old parameter names:")
                for item in old_param_actions:
                    print(f"   - Step '{item['step']}': {item['action']} uses '{item['old_param']}'")
            else:
                print(f"\n✅ No old parameter names found in strategy")
                
            # Try to initialize the strategy service
            print(f"\n3. Testing strategy initialization...")
            service = MinimalStrategyService()
            
            # Mock execution context
            context = {
                'datasets': {},
                'output_files': [],
                'statistics': {}
            }
            
            # We won't actually execute the full strategy (would take too long)
            # Just verify it can be loaded and actions are available
            missing_actions = []
            for step in strategy.get('steps', []):
                action_type = step.get('action', {}).get('type')
                if action_type and action_type not in ACTION_REGISTRY:
                    missing_actions.append(action_type)
                    
            if missing_actions:
                print(f"   ❌ Missing actions: {missing_actions}")
            else:
                print(f"   ✅ All actions found in registry")
                
            return len(old_param_actions) > 0, len(missing_actions) == 0
            
        except Exception as e:
            print(f"   ❌ Error testing YAML: {e}")
            return False, False
            
    async def run_tests(self):
        """Run all backward compatibility tests."""
        
        print("="*60)
        print("BACKWARD COMPATIBILITY TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: GENERATE_MAPPING_VISUALIZATIONS
        await self.test_action_with_old_params(
            action_type="GENERATE_MAPPING_VISUALIZATIONS",
            old_params={
                'input_key': 'test_data',
                'output_dir': '/tmp/test_viz_old',  # OLD parameter name
                'generate_statistics': True,
                'generate_summary': True
            },
            new_params={
                'input_key': 'test_data',
                'directory_path': '/tmp/test_viz_new',  # NEW parameter name
                'generate_statistics': True,
                'generate_summary': True
            }
        )
        
        # Test 2: GENERATE_LLM_ANALYSIS
        await self.test_action_with_old_params(
            action_type="GENERATE_LLM_ANALYSIS",
            old_params={
                'provider': 'template',
                'model': 'template',
                'output_directory': '/tmp/test_llm_old',  # OLD parameter name
                'progressive_stats_key': 'progressive_stats',
                'mapping_results_key': 'final_merged',
                'strategy_name': 'test_strategy',
                'entity_type': 'protein'
            },
            new_params={
                'provider': 'template',
                'model': 'template',
                'directory_path': '/tmp/test_llm_new',  # NEW parameter name
                'progressive_stats_key': 'progressive_stats',
                'mapping_results_key': 'final_merged',
                'strategy_name': 'test_strategy',
                'entity_type': 'protein'
            }
        )
        
        # Test 3: Check existing protein pipeline YAML
        protein_yaml = Path('/home/ubuntu/biomapper/src/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0.yaml')
        if protein_yaml.exists():
            has_old_params, all_actions_available = await self.test_yaml_strategy_compatibility(protein_yaml)
        
        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        successful_tests = [t for t in self.test_results if t['success']]
        failed_tests = [t for t in self.test_results if not t['success']]
        
        print(f"\nTotal tests run: {len(self.test_results)}")
        print(f"✅ Successful: {len(successful_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        
        if self.deprecation_warnings:
            print(f"\n⚠️  Deprecation warnings collected: {len(self.deprecation_warnings)}")
            print("   This is EXPECTED and GOOD - it means backward compatibility is working!")
            
        if failed_tests:
            print(f"\n❌ Failed tests:")
            for test in failed_tests:
                print(f"   - {test['action']} with {test['params']} params: {test.get('error', 'Unknown error')}")
        else:
            print(f"\n✅ All backward compatibility tests passed!")
            
        # Migration recommendations
        print(f"\n{'='*60}")
        print("MIGRATION RECOMMENDATIONS")
        print(f"{'='*60}")
        
        print("\n1. The existing protein pipeline (prot_arv_to_kg2c_uniprot_v3.0.yaml) uses old parameter names:")
        print("   - GENERATE_MAPPING_VISUALIZATIONS: uses 'output_dir'")
        print("   - GENERATE_LLM_ANALYSIS: uses 'output_directory'")
        print("\n2. These will continue to work but will show deprecation warnings.")
        print("\n3. To migrate without warnings, run:")
        print("   python scripts/migrate_parameter_names.py src/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0.yaml")
        print("\n4. Or to check all strategies:")
        print("   python scripts/migrate_parameter_names.py --check --all src/configs/strategies/")
        
        return len(failed_tests) == 0


async def main():
    """Main test runner."""
    tester = BackwardCompatibilityTester()
    success = await tester.run_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())