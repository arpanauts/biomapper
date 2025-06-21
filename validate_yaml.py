#!/usr/bin/env python3
"""Validate YAML syntax"""

try:
    import yaml
    
    with open('configs/mapping_strategies_config.yaml', 'r') as f:
        data = yaml.safe_load(f)
    
    print("✓ YAML syntax is valid")
    
    # Check if our specific strategy exists
    if 'entity_strategies' in data and 'protein' in data['entity_strategies']:
        if 'UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT' in data['entity_strategies']['protein']:
            strategy = data['entity_strategies']['protein']['UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT']
            print("\n✓ Found UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT strategy")
            
            # Check the updated endpoint names
            for step in strategy.get('steps', []):
                if step['step_id'] == 'S1_LOAD_UKBB_IDS':
                    endpoint = step['action']['params']['source_endpoint_name']
                    print(f"  - S1_LOAD_UKBB_IDS: source_endpoint_name = {endpoint}")
                    
                elif step['step_id'] == 'S2_LOAD_HPA_IDS':
                    endpoint = step['action']['params']['target_endpoint_name']
                    print(f"  - S2_LOAD_HPA_IDS: target_endpoint_name = {endpoint}")
                    
                elif step['step_id'] == 'S6_SAVE_RESULTS':
                    output_dir_key = step['action']['params'].get('output_dir_key')
                    print(f"  - S6_SAVE_RESULTS: output_dir_key = {output_dir_key}")
                    
except Exception as e:
    print(f"❌ YAML validation failed: {e}")
    import sys
    sys.exit(1)