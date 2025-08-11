#!/usr/bin/env python3
"""
Manual pattern analysis for detailed examination of specific code patterns.
This complements the automated analysis with human-guided pattern recognition.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import difflib

def analyze_dataset_validation_patterns():
    """Analyze dataset validation patterns across all actions."""
    
    patterns = {
        'input_validation_check': [],
        'dataset_key_check': [],  
        'empty_dataset_handling': [],
        'column_existence_check': [],
        'result_storage': []
    }
    
    action_files = list(Path("biomapper/core/strategy_actions/entities").rglob("*.py"))
    
    for file_path in action_files:
        if file_path.name.startswith(("test_", "__")):
            continue
            
        try:
            content = file_path.read_text()
            
            # Pattern 1: Input validation check
            if 'if params.input_key not in context["datasets"]' in content:
                patterns['input_validation_check'].append({
                    'file': str(file_path),
                    'pattern': 'if params.input_key not in context["datasets"]',
                    'entity': get_entity_from_path(file_path)
                })
            
            # Pattern 2: Dataset key existence check
            dataset_key_patterns = re.findall(
                r'if.*not in context\["datasets"\]', content
            )
            if dataset_key_patterns:
                patterns['dataset_key_check'].append({
                    'file': str(file_path),
                    'patterns': dataset_key_patterns,
                    'entity': get_entity_from_path(file_path)
                })
            
            # Pattern 3: Empty dataset handling
            if 'if.*\.empty:' in content and 'df' in content:
                patterns['empty_dataset_handling'].append({
                    'file': str(file_path),
                    'pattern': 'empty dataset check',
                    'entity': get_entity_from_path(file_path)
                })
            
            # Pattern 4: Column existence validation
            column_checks = re.findall(
                r'if.*column.*not in.*\.columns', content, re.IGNORECASE
            )
            if column_checks:
                patterns['column_existence_check'].append({
                    'file': str(file_path),
                    'patterns': column_checks,
                    'entity': get_entity_from_path(file_path)
                })
            
            # Pattern 5: Result storage
            result_storage = re.findall(
                r'context\["datasets"\]\[.*\] = .*', content
            )
            if result_storage:
                patterns['result_storage'].append({
                    'file': str(file_path),
                    'patterns': result_storage,
                    'entity': get_entity_from_path(file_path)
                })
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    return patterns

def analyze_statistics_patterns():
    """Analyze statistics update patterns."""
    
    patterns = {
        'statistics_initialization': [],
        'statistics_updates': [],
        'statistics_storage': []
    }
    
    action_files = list(Path("biomapper/core/strategy_actions/entities").rglob("*.py"))
    
    for file_path in action_files:
        if file_path.name.startswith(("test_", "__")):
            continue
            
        try:
            content = file_path.read_text()
            
            # Statistics initialization
            if 'if "statistics" not in context' in content:
                patterns['statistics_initialization'].append({
                    'file': str(file_path),
                    'entity': get_entity_from_path(file_path)
                })
            
            # Statistics updates - find all context["statistics"] assignments
            stats_updates = re.findall(
                r'context\["statistics"\].*=.*', content
            )
            if stats_updates:
                patterns['statistics_updates'].append({
                    'file': str(file_path),
                    'count': len(stats_updates),
                    'patterns': stats_updates[:3],  # First 3 examples
                    'entity': get_entity_from_path(file_path)
                })
            
        except Exception:
            continue
    
    return patterns

def analyze_parameter_patterns():
    """Analyze parameter definition patterns."""
    
    patterns = {
        'input_key_params': [],
        'output_key_params': [],
        'column_params': [],
        'boolean_flags': []
    }
    
    action_files = list(Path("biomapper/core/strategy_actions/entities").rglob("*.py"))
    
    for file_path in action_files:
        if file_path.name.startswith(("test_", "__")):
            continue
            
        try:
            content = file_path.read_text()
            
            # Input key parameters
            if 'input_key: str = Field' in content:
                input_key_match = re.search(
                    r'input_key: str = Field\([^)]+\)', content
                )
                if input_key_match:
                    patterns['input_key_params'].append({
                        'file': str(file_path),
                        'pattern': input_key_match.group(0),
                        'entity': get_entity_from_path(file_path)
                    })
            
            # Output key parameters
            if 'output_key: str = Field' in content:
                output_key_match = re.search(
                    r'output_key: str = Field\([^)]+\)', content
                )
                if output_key_match:
                    patterns['output_key_params'].append({
                        'file': str(file_path),
                        'pattern': output_key_match.group(0),
                        'entity': get_entity_from_path(file_path)
                    })
            
            # Column parameters
            column_params = re.findall(
                r'\w*column\w*: str = Field\([^)]+\)', content
            )
            if column_params:
                patterns['column_params'].append({
                    'file': str(file_path),
                    'patterns': column_params,
                    'count': len(column_params),
                    'entity': get_entity_from_path(file_path)
                })
            
        except Exception:
            continue
    
    return patterns

def analyze_error_handling_patterns():
    """Analyze error handling patterns."""
    
    patterns = {
        'key_error_handling': [],
        'validation_errors': [],
        'exception_patterns': []
    }
    
    action_files = list(Path("biomapper/core/strategy_actions/entities").rglob("*.py"))
    
    for file_path in action_files:
        if file_path.name.startswith(("test_", "__")):
            continue
            
        try:
            content = file_path.read_text()
            
            # KeyError patterns
            key_errors = re.findall(
                r'raise KeyError\([^)]+\)', content
            )
            if key_errors:
                patterns['key_error_handling'].append({
                    'file': str(file_path),
                    'patterns': key_errors,
                    'entity': get_entity_from_path(file_path)
                })
            
            # Try/except blocks
            try_blocks = re.findall(
                r'try:\s*\n.*?except.*?:', content, re.DOTALL
            )
            if try_blocks:
                patterns['exception_patterns'].append({
                    'file': str(file_path),
                    'count': len(try_blocks),
                    'entity': get_entity_from_path(file_path)
                })
            
        except Exception:
            continue
    
    return patterns

def get_entity_from_path(file_path: Path) -> str:
    """Extract entity type from file path."""
    parts = file_path.parts
    if 'proteins' in parts:
        return 'proteins'
    elif 'metabolites' in parts:
        return 'metabolites'
    elif 'chemistry' in parts:
        return 'chemistry'
    else:
        return 'unknown'

def calculate_pattern_similarity(pattern1: str, pattern2: str) -> float:
    """Calculate similarity between two code patterns."""
    return difflib.SequenceMatcher(None, pattern1, pattern2).ratio()

def identify_beneficial_abstractions(all_patterns: Dict) -> List[Dict]:
    """Identify patterns that would benefit from abstraction."""
    
    beneficial = []
    
    # Analyze dataset validation patterns
    dataset_patterns = all_patterns.get('dataset_validation', {})
    
    # Input validation check - appears in multiple entities
    input_checks = dataset_patterns.get('input_validation_check', [])
    if len(input_checks) >= 3:
        entities = set(p['entity'] for p in input_checks)
        if len(entities) >= 2:  # Cross-entity usage
            beneficial.append({
                'pattern_name': 'dataset_input_validation',
                'usage_count': len(input_checks),
                'cross_entity_usage': len(entities),
                'entities': list(entities),
                'files': [p['file'] for p in input_checks],
                'abstraction_type': 'utility_function',
                'benefit_score': len(input_checks) * 3 + len(entities) * 5,
                'example_code': input_checks[0]['pattern'] if input_checks else '',
                'recommendation': 'HIGH' if len(input_checks) > 4 and len(entities) >= 3 else 'MEDIUM'
            })
    
    # Statistics patterns
    stats_patterns = all_patterns.get('statistics', {})
    stats_init = stats_patterns.get('statistics_initialization', [])
    if len(stats_init) >= 3:
        entities = set(p['entity'] for p in stats_init)
        beneficial.append({
            'pattern_name': 'statistics_initialization',
            'usage_count': len(stats_init),
            'cross_entity_usage': len(entities),
            'entities': list(entities),
            'files': [p['file'] for p in stats_init],
            'abstraction_type': 'utility_function',
            'benefit_score': len(stats_init) * 2 + len(entities) * 3,
            'recommendation': 'MEDIUM'
        })
    
    # Parameter patterns
    param_patterns = all_patterns.get('parameters', {})
    input_key_params = param_patterns.get('input_key_params', [])
    if len(input_key_params) >= 4:
        # Check similarity of parameter definitions
        similarities = []
        for i in range(len(input_key_params)):
            for j in range(i + 1, len(input_key_params)):
                sim = calculate_pattern_similarity(
                    input_key_params[i]['pattern'], 
                    input_key_params[j]['pattern']
                )
                similarities.append(sim)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        if avg_similarity > 0.8:  # High similarity
            beneficial.append({
                'pattern_name': 'input_key_parameter_definition',
                'usage_count': len(input_key_params),
                'cross_entity_usage': len(set(p['entity'] for p in input_key_params)),
                'average_similarity': avg_similarity,
                'abstraction_type': 'shared_parameter_base',
                'benefit_score': len(input_key_params) * 2 + (avg_similarity * 10),
                'recommendation': 'LOW'  # Parameter sharing can reduce type safety
            })
    
    return beneficial

def identify_entity_specific_patterns(all_patterns: Dict) -> Dict[str, List[Dict]]:
    """Identify patterns that should remain entity-specific."""
    
    entity_specific = {
        'proteins': [],
        'metabolites': [],
        'chemistry': []
    }
    
    # Look for patterns that are used within one entity but not across entities
    for pattern_category, patterns in all_patterns.items():
        for pattern_type, instances in patterns.items():
            if isinstance(instances, list) and instances:
                entity_usage = defaultdict(int)
                for instance in instances:
                    entity = instance.get('entity', 'unknown')
                    entity_usage[entity] += 1
                
                # If pattern is heavily used in one entity but not others
                for entity, count in entity_usage.items():
                    if count >= 3 and entity != 'unknown':
                        # Check if it's truly entity-specific (not used much in others)
                        other_usage = sum(c for e, c in entity_usage.items() if e != entity)
                        if other_usage <= 1:  # Very low usage in other entities
                            entity_specific[entity].append({
                                'pattern_name': f"{pattern_category}_{pattern_type}",
                                'usage_in_entity': count,
                                'usage_in_others': other_usage,
                                'specificity_ratio': count / max(1, other_usage),
                                'files': [i.get('file', '') for i in instances if i.get('entity') == entity],
                                'reason': f"Heavy usage in {entity} ({count}x) vs minimal elsewhere ({other_usage}x)"
                            })
    
    return entity_specific

def main():
    """Run comprehensive manual pattern analysis."""
    
    print("🔍 Starting manual pattern analysis...")
    
    # Analyze different pattern categories
    dataset_patterns = analyze_dataset_validation_patterns()
    statistics_patterns = analyze_statistics_patterns()
    parameter_patterns = analyze_parameter_patterns()
    error_patterns = analyze_error_handling_patterns()
    
    all_patterns = {
        'dataset_validation': dataset_patterns,
        'statistics': statistics_patterns,
        'parameters': parameter_patterns,
        'error_handling': error_patterns
    }
    
    print("📊 Pattern analysis results:")
    print(f"  Dataset validation patterns: {sum(len(p) for p in dataset_patterns.values())}")
    print(f"  Statistics patterns: {sum(len(p) for p in statistics_patterns.values())}")
    print(f"  Parameter patterns: {sum(len(p) for p in parameter_patterns.values())}")
    print(f"  Error handling patterns: {sum(len(p) for p in error_patterns.values())}")
    
    # Identify beneficial abstractions
    beneficial_abstractions = identify_beneficial_abstractions(all_patterns)
    
    print(f"\n✅ Beneficial abstractions identified: {len(beneficial_abstractions)}")
    for abstraction in beneficial_abstractions:
        print(f"  - {abstraction['pattern_name']}: {abstraction['usage_count']} usages across {abstraction['cross_entity_usage']} entities")
        print(f"    Recommendation: {abstraction['recommendation']}, Score: {abstraction['benefit_score']}")
    
    # Identify entity-specific patterns
    entity_specific = identify_entity_specific_patterns(all_patterns)
    
    print(f"\n🏷️  Entity-specific patterns:")
    for entity, patterns in entity_specific.items():
        if patterns:
            print(f"  {entity}: {len(patterns)} entity-specific patterns")
            for pattern in patterns[:3]:  # Show first 3
                print(f"    - {pattern['pattern_name']}: {pattern['usage_in_entity']}x in {entity}, {pattern['usage_in_others']}x elsewhere")
    
    # Save detailed results
    import json
    results = {
        'all_patterns': all_patterns,
        'beneficial_abstractions': beneficial_abstractions,
        'entity_specific_patterns': entity_specific,
        'summary': {
            'total_patterns_found': sum(sum(len(p) for p in cat.values()) for cat in all_patterns.values()),
            'beneficial_abstractions_count': len(beneficial_abstractions),
            'high_priority_abstractions': len([a for a in beneficial_abstractions if a['recommendation'] == 'HIGH']),
            'entity_specific_count': sum(len(patterns) for patterns in entity_specific.values())
        }
    }
    
    with open('manual_pattern_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Manual analysis complete. Results saved to manual_pattern_analysis_results.json")
    print(f"📈 Summary: {results['summary']['total_patterns_found']} patterns found")
    print(f"🎯 {results['summary']['beneficial_abstractions_count']} beneficial abstractions identified")
    print(f"🏷️  {results['summary']['entity_specific_count']} entity-specific patterns")
    
    return results

if __name__ == "__main__":
    main()