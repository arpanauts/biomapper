#!/usr/bin/env python3
"""
Comprehensive parameter audit script for biomapper actions.
Scans all action files and identifies non-standard parameter naming.
"""

import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

class ParameterAuditor:
    """Audits parameter naming across all biomapper actions."""
    
    # Standard naming conventions
    STANDARD_NAMES = {
        'input_dataset': 'input_key',
        'output_dataset': 'output_key',
        'source_dataset': 'source_key',
        'target_dataset': 'target_key',
        'input_file': 'file_path',
        'output_file': 'output_path',
        'identifier_column': 'identifier_column',
        'dataset_name': 'dataset_name',
        'merge_column': 'merge_column',
        'threshold': 'threshold',
        'description': 'description',
    }
    
    # Patterns to identify parameter types
    PATTERNS = {
        'input_dataset': [
            r'input[_-]?key', r'dataset[_-]?key', r'input[_-]?context[_-]?key',
            r'source[_-]?dataset[_-]?key', r'input[_-]?dataset', r'dataset1[_-]?key'
        ],
        'output_dataset': [
            r'output[_-]?key', r'output[_-]?context[_-]?key', r'result[_-]?key',
            r'output[_-]?dataset[_-]?key', r'output[_-]?dataset'
        ],
        'source_dataset': [
            r'source[_-]?key', r'source[_-]?dataset', r'from[_-]?dataset'
        ],
        'target_dataset': [
            r'target[_-]?key', r'target[_-]?dataset', r'to[_-]?dataset'
        ],
        'input_file': [
            r'file[_-]?path', r'input[_-]?file', r'input[_-]?path',
            r'filepath', r'filename', r'csv[_-]?path', r'tsv[_-]?path'
        ],
        'output_file': [
            r'output[_-]?path', r'output[_-]?file', r'output[_-]?filepath',
            r'export[_-]?path', r'save[_-]?path', r'output[_-]?filename'
        ],
    }
    
    def __init__(self):
        self.audit_results = {
            'total_files': 0,
            'total_params': 0,
            'non_standard_params': 0,
            'param_variations': defaultdict(set),
            'files': {},
            'summary': {},
            'recommendations': []
        }
        
    def find_python_files(self, directory: str) -> List[Path]:
        """Find all Python files in the directory."""
        path = Path(directory)
        return list(path.rglob("*.py"))
    
    def extract_pydantic_params(self, file_path: str) -> Dict[str, List[Dict]]:
        """Extract Pydantic model parameters from a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                print(f"Syntax error in {file_path}: {e}")
                return {}
        
        results = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a Pydantic model (inherits from BaseModel)
                if any(self._is_basemodel(base) for base in node.bases):
                    class_name = node.name
                    params = self._extract_fields(node)
                    if params:
                        results[class_name] = params
        
        return results
    
    def _is_basemodel(self, base) -> bool:
        """Check if a base class is BaseModel."""
        if isinstance(base, ast.Name):
            return base.id == 'BaseModel'
        elif isinstance(base, ast.Attribute):
            return base.attr == 'BaseModel'
        return False
    
    def _extract_fields(self, class_node: ast.ClassDef) -> List[Dict]:
        """Extract field definitions from a class."""
        fields = []
        
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                field_name = node.target.id
                field_info = {
                    'name': field_name,
                    'type': self._get_type_str(node.annotation),
                    'has_default': node.value is not None,
                    'is_field': False
                }
                
                # Check if it's a Field() call
                if node.value and isinstance(node.value, ast.Call):
                    if self._is_field_call(node.value):
                        field_info['is_field'] = True
                        field_info['field_args'] = self._extract_field_args(node.value)
                
                fields.append(field_info)
        
        return fields
    
    def _get_type_str(self, annotation) -> str:
        """Convert AST annotation to string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Attribute):
            return f"{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            return "Optional/List/etc"
        return "Unknown"
    
    def _is_field_call(self, node: ast.Call) -> bool:
        """Check if a call is Field()."""
        if isinstance(node.func, ast.Name):
            return node.func.id == 'Field'
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == 'Field'
        return False
    
    def _extract_field_args(self, call_node: ast.Call) -> Dict:
        """Extract arguments from Field() call."""
        args = {}
        
        # Extract positional arguments
        if call_node.args:
            args['default'] = 'Ellipsis' if isinstance(call_node.args[0], ast.Constant) and call_node.args[0].value == ... else 'value'
        
        # Extract keyword arguments
        for keyword in call_node.keywords:
            if keyword.arg:
                args[keyword.arg] = self._ast_to_value(keyword.value)
        
        return args
    
    def _ast_to_value(self, node):
        """Convert AST node to Python value."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self._ast_to_value(elt) for elt in node.elts]
        return str(type(node).__name__)
    
    def categorize_parameter(self, param_name: str) -> Optional[str]:
        """Categorize a parameter based on its name."""
        param_lower = param_name.lower()
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.match(f"^{pattern}$", param_lower):
                    return category
        
        return None
    
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file."""
        models = self.extract_pydantic_params(str(file_path))
        
        file_analysis = {
            'path': str(file_path.relative_to(Path.cwd())),
            'models': {},
            'non_standard_count': 0,
            'total_params': 0
        }
        
        for model_name, params in models.items():
            model_analysis = {
                'params': [],
                'non_standard': []
            }
            
            for param in params:
                param_name = param['name']
                category = self.categorize_parameter(param_name)
                
                param_info = {
                    'name': param_name,
                    'type': param['type'],
                    'category': category,
                    'is_standard': False,
                    'suggested_name': None
                }
                
                if category:
                    standard_name = self.STANDARD_NAMES.get(category)
                    if standard_name and param_name != standard_name:
                        param_info['is_standard'] = False
                        param_info['suggested_name'] = standard_name
                        model_analysis['non_standard'].append(param_info)
                        file_analysis['non_standard_count'] += 1
                        
                        # Track variations
                        self.audit_results['param_variations'][category].add(param_name)
                    elif standard_name and param_name == standard_name:
                        param_info['is_standard'] = True
                
                model_analysis['params'].append(param_info)
                file_analysis['total_params'] += 1
            
            file_analysis['models'][model_name] = model_analysis
        
        return file_analysis
    
    def run_audit(self, directory: str):
        """Run the complete audit."""
        print(f"Starting parameter audit in: {directory}")
        
        files = self.find_python_files(directory)
        print(f"Found {len(files)} Python files")
        
        for file_path in files:
            if '__pycache__' in str(file_path):
                continue
                
            analysis = self.analyze_file(file_path)
            if analysis['models']:  # Only include files with models
                self.audit_results['files'][str(file_path)] = analysis
                self.audit_results['total_files'] += 1
                self.audit_results['total_params'] += analysis['total_params']
                self.audit_results['non_standard_params'] += analysis['non_standard_count']
        
        # Generate summary
        self._generate_summary()
        
        # Generate recommendations
        self._generate_recommendations()
        
        print(f"Audit complete. Analyzed {self.audit_results['total_files']} files")
        print(f"Total parameters: {self.audit_results['total_params']}")
        print(f"Non-standard parameters: {self.audit_results['non_standard_params']}")
    
    def _generate_summary(self):
        """Generate audit summary."""
        summary = {}
        
        for category, variations in self.audit_results['param_variations'].items():
            standard = self.STANDARD_NAMES.get(category, 'unknown')
            summary[category] = {
                'standard_name': standard,
                'variations_found': sorted(list(variations)),
                'variation_count': len(variations)
            }
        
        self.audit_results['summary'] = summary
    
    def _generate_recommendations(self):
        """Generate recommendations for standardization."""
        recommendations = []
        
        for category, info in self.audit_results['summary'].items():
            if info['variation_count'] > 1:
                recommendations.append({
                    'category': category,
                    'recommendation': f"Standardize all {category} parameters to '{info['standard_name']}'",
                    'current_variations': info['variations_found'],
                    'files_affected': self._count_affected_files(category)
                })
        
        self.audit_results['recommendations'] = recommendations
    
    def _count_affected_files(self, category: str) -> int:
        """Count files affected by a category's non-standard naming."""
        count = 0
        variations = self.audit_results['param_variations'][category]
        
        for file_data in self.audit_results['files'].values():
            for model_data in file_data['models'].values():
                for param in model_data['non_standard']:
                    if param['category'] == category:
                        count += 1
                        break
        
        return count
    
    def save_report(self, output_path: str):
        """Save the audit report to JSON."""
        # Convert sets to lists for JSON serialization
        report = self.audit_results.copy()
        report['param_variations'] = {
            k: sorted(list(v)) for k, v in report['param_variations'].items()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Audit report saved to: {output_path}")


def main():
    """Run the parameter audit."""
    auditor = ParameterAuditor()
    
    # Audit the strategy_actions directory
    actions_dir = "/home/ubuntu/biomapper/biomapper/core/strategy_actions"
    auditor.run_audit(actions_dir)
    
    # Create audits directory if it doesn't exist
    os.makedirs("/home/ubuntu/biomapper/audits", exist_ok=True)
    
    # Save the report
    auditor.save_report("/home/ubuntu/biomapper/audits/parameter_audit.json")
    
    # Print summary
    print("\n=== AUDIT SUMMARY ===")
    print(f"Files with models: {auditor.audit_results['total_files']}")
    print(f"Total parameters: {auditor.audit_results['total_params']}")
    print(f"Non-standard parameters: {auditor.audit_results['non_standard_params']}")
    
    print("\n=== TOP RECOMMENDATIONS ===")
    for rec in auditor.audit_results['recommendations'][:5]:
        print(f"- {rec['recommendation']}")
        print(f"  Current variations: {', '.join(rec['current_variations'])}")
        print(f"  Files affected: {rec['files_affected']}")


if __name__ == "__main__":
    main()