#!/usr/bin/env python3
"""
Script to fix all YAML strategy files to use correct format and real data paths.
"""

import yaml
import os
from pathlib import Path

# Define the data path mappings
DATA_PATHS = {
    'arivale': '/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv',
    'hpa': '/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv',
    'ukbb': '/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv',
    'qin': '/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/qin_osps.csv',
    'kg2c': '/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv',
    'spoke': '/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_protein.csv'
}

# Define column mappings
COLUMN_MAPPINGS = {
    'arivale': 'uniprot',
    'hpa': 'uniprot',
    'ukbb': 'UniProt',
    'qin': 'uniprot',
    'kg2c': 'id',
    'spoke': 'identifier'
}

def fix_strategy_file(file_path):
    """Fix a single strategy file."""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Extract strategy from wrapper if needed
    if 'strategy' in data:
        strategy = data['strategy']
        steps = data.get('steps', [])
    else:
        strategy = data
        steps = data.get('steps', [])
    
    # Fix the format
    fixed_strategy = {
        'name': strategy['name'].replace(' ', '_').replace('to', 'TO').upper(),
        'description': strategy['description'],
        'steps': []
    }
    
    # Fix each step
    for step in steps:
        fixed_step = {
            'name': step['name'],
            'action': {
                'type': step['action']['type'],
                'params': {}
            }
        }
        
        # Fix parameters
        params = step['action']['params']
        new_params = {}
        
        for key, value in params.items():
            if key == 'file_path':
                # Update file paths to real data
                if 'arivale' in str(value):
                    new_params[key] = DATA_PATHS['arivale']
                elif 'hpa' in str(value):
                    new_params[key] = DATA_PATHS['hpa']
                elif 'ukbb' in str(value):
                    new_params[key] = DATA_PATHS['ukbb']
                elif 'qin' in str(value):
                    new_params[key] = DATA_PATHS['qin']
                elif 'kg2c' in str(value):
                    new_params[key] = DATA_PATHS['kg2c']
                elif 'spoke' in str(value):
                    new_params[key] = DATA_PATHS['spoke']
                else:
                    new_params[key] = value
            elif key == 'output_dir':
                new_params[key] = '/home/ubuntu/biomapper/data/results'
            elif key in ['source_key', 'target_key']:
                # These are old parameter names, convert to new ones
                if key == 'source_key':
                    new_params['source_dataset_key'] = value
                elif key == 'target_key':
                    new_params['target_dataset_key'] = value
            elif key in ['source_identifier_column', 'target_identifier_column']:
                # These are old parameter names, convert to new ones
                if key == 'source_identifier_column':
                    new_params['source_id_column'] = value
                elif key == 'target_identifier_column':
                    new_params['target_id_column'] = value
            else:
                new_params[key] = value
        
        fixed_step['action']['params'] = new_params
        fixed_strategy['steps'].append(fixed_step)
    
    # Write the fixed strategy
    with open(file_path, 'w') as f:
        yaml.dump(fixed_strategy, f, default_flow_style=False, indent=2)
    
    print(f"Fixed {file_path} -> {fixed_strategy['name']}")

def main():
    """Fix all strategy files."""
    configs_dir = Path('/home/ubuntu/biomapper/configs')
    
    strategy_files = [
        'arivale_ukbb_mapping.yaml',
        'hpa_qin_mapping.yaml',
        'hpa_spoke_mapping.yaml',
        'ukbb_kg2c_mapping.yaml',
        'ukbb_qin_mapping.yaml',
        'ukbb_spoke_mapping.yaml'
    ]
    
    for file_name in strategy_files:
        file_path = configs_dir / file_name
        if file_path.exists():
            fix_strategy_file(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == '__main__':
    main()