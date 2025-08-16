"""Algorithm complexity analysis and detection tools."""

import ast
import inspect
import re
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComplexityIssue:
    """Represents a detected complexity issue in code."""
    
    file_path: str
    function_name: str
    line_number: int
    issue_type: str
    description: str
    estimated_complexity: str
    suggested_fix: str
    severity: str  # "critical", "high", "medium", "low"


class NestedLoopDetector(ast.NodeVisitor):
    """AST visitor to detect nested loops and complexity issues."""
    
    def __init__(self):
        self.loop_depth = 0
        self.nested_loops = []
        self.current_function = None
        self.iterrows_in_loop = []
        self.nested_comprehensions = []
        
    def visit_FunctionDef(self, node):
        """Track current function being analyzed."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_For(self, node):
        """Detect nested for loops."""
        self.loop_depth += 1
        
        if self.loop_depth > 1:
            # Check if it's iterating over different collections
            loop_info = {
                'function': self.current_function,
                'depth': self.loop_depth,
                'line': node.lineno,
                'outer_collection': self._extract_collection_name(node)
            }
            self.nested_loops.append(loop_info)
            
        # Check for DataFrame.iterrows() in loops
        if self._is_iterrows_call(node.iter):
            self.iterrows_in_loop.append({
                'function': self.current_function,
                'line': node.lineno,
                'depth': self.loop_depth
            })
            
        self.generic_visit(node)
        self.loop_depth -= 1
        
    def visit_ListComp(self, node):
        """Detect nested list comprehensions."""
        if self._count_generators(node) > 1:
            self.nested_comprehensions.append({
                'function': self.current_function,
                'line': node.lineno,
                'generators': self._count_generators(node)
            })
        self.generic_visit(node)
        
    def _extract_collection_name(self, node) -> str:
        """Extract the name of the collection being iterated over."""
        if isinstance(node.iter, ast.Name):
            return node.iter.id
        elif isinstance(node.iter, ast.Attribute):
            return ast.unparse(node.iter)
        elif isinstance(node.iter, ast.Call):
            return ast.unparse(node.iter)
        return "unknown"
        
    def _is_iterrows_call(self, node) -> bool:
        """Check if node is a DataFrame.iterrows() call."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == 'iterrows'
        return False
        
    def _count_generators(self, node) -> int:
        """Count number of generators in a comprehension."""
        count = 0
        for generator in node.generators:
            count += 1
            # Check for nested comprehensions within
            if hasattr(generator.iter, 'generators'):
                count += self._count_generators(generator.iter)
        return count


class ComplexityChecker:
    """Analyzes code for algorithmic complexity issues."""
    
    def __init__(self):
        self.optimization_patterns = {
            'nested_loop_matching': {
                'pattern': r'for .+ in .+:\s+for .+ in .+:\s+if .+ == .+:',
                'suggestion': 'Use dictionary indexing for O(1) lookups instead of nested loops',
                'example': self._get_indexing_example()
            },
            'iterrows_nested': {
                'pattern': r'\.iterrows\(\).*\.iterrows\(\)',
                'suggestion': 'Avoid nested iterrows(). Use vectorized operations or indexing',
                'example': self._get_vectorized_example()
            },
            'repeated_lookups': {
                'pattern': r'for .+ in .+:\s+.+\[.+\]',
                'suggestion': 'Cache lookups outside the loop or use dictionary comprehension',
                'example': self._get_caching_example()
            }
        }
        
    def analyze_function(self, func: Callable) -> Dict[str, Any]:
        """Analyze a function for complexity issues."""
        source = inspect.getsource(func)
        tree = ast.parse(source)
        
        detector = NestedLoopDetector()
        detector.visit(tree)
        
        analysis = {
            'function_name': func.__name__,
            'nested_loops': detector.nested_loops,
            'iterrows_usage': detector.iterrows_in_loop,
            'nested_comprehensions': detector.nested_comprehensions,
            'estimated_complexity': self._estimate_complexity_from_ast(tree),
            'issues': []
        }
        
        # Generate issues
        for loop in detector.nested_loops:
            if loop['depth'] > 2:
                analysis['issues'].append(ComplexityIssue(
                    file_path=inspect.getfile(func),
                    function_name=func.__name__,
                    line_number=loop['line'],
                    issue_type='nested_loops',
                    description=f"Nested loops at depth {loop['depth']}",
                    estimated_complexity='O(n^' + str(loop['depth']) + ')',
                    suggested_fix='Use indexing or hashing for better performance',
                    severity='critical' if loop['depth'] > 2 else 'high'
                ))
                
        for iterrows in detector.iterrows_in_loop:
            if iterrows['depth'] > 1:
                analysis['issues'].append(ComplexityIssue(
                    file_path=inspect.getfile(func),
                    function_name=func.__name__,
                    line_number=iterrows['line'],
                    issue_type='iterrows_in_nested_loop',
                    description='DataFrame.iterrows() in nested loop',
                    estimated_complexity='O(n*m) or worse',
                    suggested_fix='Use vectorized operations or build an index',
                    severity='critical'
                ))
                
        return analysis
        
    def detect_nested_loops(self, code: str) -> List[Dict[str, Any]]:
        """Find nested loops that iterate over different collections."""
        try:
            tree = ast.parse(code)
            detector = NestedLoopDetector()
            detector.visit(tree)
            
            issues = []
            for loop in detector.nested_loops:
                issues.append({
                    'line': loop['line'],
                    'depth': loop['depth'],
                    'function': loop.get('function', 'module-level'),
                    'severity': 'critical' if loop['depth'] > 2 else 'high'
                })
                
            return issues
        except SyntaxError as e:
            return [{'error': str(e)}]
            
    def suggest_optimization(self, pattern: str) -> str:
        """Suggest optimization for common patterns."""
        for key, opt_pattern in self.optimization_patterns.items():
            if re.search(opt_pattern['pattern'], pattern, re.MULTILINE | re.DOTALL):
                return f"{opt_pattern['suggestion']}\n\nExample:\n{opt_pattern['example']}"
                
        return "Consider using more efficient data structures or algorithms"
        
    def estimate_complexity(self, func: Callable, sample_sizes: Dict[str, int]) -> Dict[str, Any]:
        """Estimate runtime complexity for given data sizes."""
        source = inspect.getsource(func)
        tree = ast.parse(source)
        detector = NestedLoopDetector()
        detector.visit(tree)
        
        max_depth = max([loop['depth'] for loop in detector.nested_loops], default=1)
        
        # Estimate operations
        if max_depth == 1:
            complexity = 'O(n)'
            estimated_ops = sample_sizes.get('n', 1000)
        elif max_depth == 2:
            complexity = 'O(n*m)'
            estimated_ops = sample_sizes.get('n', 1000) * sample_sizes.get('m', 1000)
        else:
            complexity = f'O(n^{max_depth})'
            estimated_ops = sample_sizes.get('n', 1000) ** max_depth
            
        return {
            'complexity': complexity,
            'estimated_operations': estimated_ops,
            'estimated_time_seconds': estimated_ops / 1_000_000,  # Assume 1M ops/sec
            'warning': 'Critical performance issue' if estimated_ops > 1_000_000_000 else None
        }
        
    def analyze_file(self, file_path: Path) -> List[ComplexityIssue]:
        """Analyze an entire file for complexity issues."""
        issues = []
        
        with open(file_path, 'r') as f:
            code = f.read()
            
        try:
            tree = ast.parse(code)
            detector = NestedLoopDetector()
            detector.visit(tree)
            
            # Check for nested loops
            for loop in detector.nested_loops:
                if loop['depth'] >= 2:
                    issues.append(ComplexityIssue(
                        file_path=str(file_path),
                        function_name=loop.get('function', 'module-level'),
                        line_number=loop['line'],
                        issue_type='nested_loops',
                        description=f"Nested loops at depth {loop['depth']}",
                        estimated_complexity=f"O(n^{loop['depth']})",
                        suggested_fix=self._get_fix_for_depth(loop['depth']),
                        severity='critical' if loop['depth'] > 2 else 'high'
                    ))
                    
            # Check for iterrows in loops
            for iterrows in detector.iterrows_in_loop:
                if iterrows['depth'] >= 1:
                    issues.append(ComplexityIssue(
                        file_path=str(file_path),
                        function_name=iterrows.get('function', 'module-level'),
                        line_number=iterrows['line'],
                        issue_type='iterrows_usage',
                        description='DataFrame.iterrows() in loop - inefficient',
                        estimated_complexity='O(n*m)' if iterrows['depth'] > 1 else 'O(n)',
                        suggested_fix='Use vectorized operations or .apply()',
                        severity='high' if iterrows['depth'] > 1 else 'medium'
                    ))
                    
        except SyntaxError:
            pass  # Skip files with syntax errors
            
        return issues
        
    def _estimate_complexity_from_ast(self, tree: ast.AST) -> str:
        """Estimate complexity from AST analysis."""
        detector = NestedLoopDetector()
        detector.visit(tree)
        
        max_depth = max([loop['depth'] for loop in detector.nested_loops], default=0)
        
        if max_depth == 0:
            return 'O(1) or O(n)'
        elif max_depth == 1:
            return 'O(n)'
        elif max_depth == 2:
            return 'O(n*m)'
        else:
            return f'O(n^{max_depth})'
            
    def _get_fix_for_depth(self, depth: int) -> str:
        """Get suggested fix based on nesting depth."""
        if depth == 2:
            return "Use dictionary/set for O(1) lookups or sorted merge for O(n log n)"
        elif depth == 3:
            return "Refactor algorithm - consider indexing, hashing, or dynamic programming"
        else:
            return "Critical: Algorithm needs complete redesign. Consider different approach"
            
    def _get_indexing_example(self) -> str:
        """Example of using indexing instead of nested loops."""
        return '''# Before: O(n*m)
for item1 in list1:
    for item2 in list2:
        if item1['id'] == item2['id']:
            process(item1, item2)

# After: O(n+m)
index = {item['id']: item for item in list2}
for item1 in list1:
    if item1['id'] in index:
        process(item1, index[item1['id']])'''
        
    def _get_vectorized_example(self) -> str:
        """Example of vectorized operations."""
        return '''# Before: Using iterrows()
for idx, row in df.iterrows():
    df.loc[idx, 'new_col'] = row['col1'] * 2

# After: Vectorized
df['new_col'] = df['col1'] * 2'''
        
    def _get_caching_example(self) -> str:
        """Example of caching lookups."""
        return '''# Before: Repeated lookups
for item in items:
    value = expensive_lookup[item['key']]
    process(value)

# After: Cache result
cache = {item['key']: expensive_lookup[item['key']] for item in items}
for item in items:
    process(cache[item['key']])'''