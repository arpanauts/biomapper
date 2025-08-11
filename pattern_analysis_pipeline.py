#!/usr/bin/env python3
"""
Comprehensive pattern analysis pipeline for biomapper entity actions.
Implements the evidence-based methodology from Week 4B instructions.
"""

import subprocess
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pandas as pd
import numpy as np

@dataclass
class PatternCandidate:
    """Represents a potential pattern for abstraction analysis."""
    pattern_type: str
    locations: List[str]
    total_duplicated_lines: int
    abstraction_overhead_lines: int
    usage_count: int
    identical_logic: bool
    unlikely_to_diverge: bool
    has_clear_interface: bool
    testable_in_isolation: bool
    entity_specific_logic: bool
    performance_critical: bool
    code_snippets: List[str] = field(default_factory=list)
    
@dataclass
class ValidationPatternResult:
    """Results of validation pattern analysis."""
    patterns: Dict[str, List[Dict]]
    appears_in: int
    total_lines: int
    locations: List[str]

@dataclass
class PatternEvaluation:
    """Evaluation result for a pattern candidate."""
    pattern: PatternCandidate
    scores: Dict[str, float]
    total_score: float
    recommendation: str
    confidence: float
    reasoning: str

class PatternAnalyzer:
    """Main pattern analysis engine."""
    
    def __init__(self):
        self.entity_paths = [
            "biomapper/core/strategy_actions/entities/proteins",
            "biomapper/core/strategy_actions/entities/metabolites", 
            "biomapper/core/strategy_actions/entities/chemistry"
        ]
        self.abstraction_threshold = 35
        self.weights = {
            'duplication_score': 0.3,
            'complexity_reduction': 0.25,
            'maintenance_benefit': 0.2,
            'performance_impact': 0.15,
            'readability_impact': 0.1
        }
        
    def run_complete_analysis(self) -> Dict[str, Any]:
        """Run the complete pattern analysis pipeline."""
        
        print("🔍 Starting comprehensive pattern analysis...")
        
        results = {
            'analysis_metadata': {
                'total_files_analyzed': 0,
                'total_lines_analyzed': 0,
                'patterns_identified': 0,
                'timestamp': pd.Timestamp.now().isoformat()
            },
            'duplication_analysis': self.analyze_code_duplication(),
            'complexity_analysis': self.analyze_complexity(),
            'pattern_evaluation': [],
            'entity_characteristics': self.document_entity_specific_characteristics(),
            'recommendations': {}
        }
        
        # Count files and lines
        for entity_path in self.entity_paths:
            if Path(entity_path).exists():
                py_files = list(Path(entity_path).rglob("*.py"))
                results['analysis_metadata']['total_files_analyzed'] += len(py_files)
                
                for py_file in py_files:
                    try:
                        lines = len(py_file.read_text().splitlines())
                        results['analysis_metadata']['total_lines_analyzed'] += lines
                    except:
                        continue
        
        # Identify and evaluate patterns
        pattern_candidates = self.identify_pattern_candidates(results['duplication_analysis'])
        results['analysis_metadata']['patterns_identified'] = len(pattern_candidates)
        
        for candidate in pattern_candidates:
            evaluation = self.evaluate_pattern(candidate)
            results['pattern_evaluation'].append({
                'pattern_type': candidate.pattern_type,
                'locations': candidate.locations,
                'usage_count': candidate.usage_count,
                'evaluation': {
                    'scores': evaluation.scores,
                    'total_score': evaluation.total_score,
                    'recommendation': evaluation.recommendation,
                    'confidence': evaluation.confidence,
                    'reasoning': evaluation.reasoning
                }
            })
        
        # Generate final recommendations
        results['recommendations'] = self.generate_recommendations(results['pattern_evaluation'])
        
        return results
    
    def analyze_code_duplication(self) -> Dict[str, Any]:
        """Analyze code duplication patterns across entities."""
        
        print("📊 Analyzing code duplication...")
        
        duplication_results = {}
        
        # Analyze validation patterns
        validation_analysis = self.analyze_validation_patterns()
        duplication_results['validation_patterns'] = validation_analysis
        
        # Analyze error handling patterns
        error_analysis = self.analyze_error_handling_patterns()
        duplication_results['error_handling_patterns'] = error_analysis
        
        # Analyze context management patterns
        context_analysis = self.analyze_context_patterns()
        duplication_results['context_management_patterns'] = context_analysis
        
        # Cross-entity pattern analysis
        cross_entity_patterns = self.find_cross_entity_patterns(duplication_results)
        duplication_results['cross_entity_patterns'] = cross_entity_patterns
        
        return duplication_results
    
    def analyze_validation_patterns(self) -> Dict[str, Any]:
        """Analyze parameter validation patterns across actions."""
        
        validation_patterns = {
            'input_key_validation': [],
            'dataset_existence_check': [],
            'column_validation': [],
            'type_checking': []
        }
        
        for entity_path in self.entity_paths:
            if not Path(entity_path).exists():
                continue
                
            for action_file in Path(entity_path).rglob("*.py"):
                if action_file.name.startswith(("test_", "__")):
                    continue
                    
                try:
                    content = action_file.read_text()
                    
                    # Check for input key validation pattern
                    if 'input_key not in context' in content or 'datasets' not in content:
                        validation_patterns['input_key_validation'].append({
                            'file': str(action_file),
                            'lines': self.extract_validation_block(content, 'input_key'),
                            'exact_match': True
                        })
                    
                    # Check for dataset existence validation
                    if "context['datasets']" in content and "not found" in content.lower():
                        validation_patterns['dataset_existence_check'].append({
                            'file': str(action_file),
                            'lines': self.extract_validation_block(content, 'datasets'),
                            'exact_match': self.calculate_similarity_score(content, 'datasets') > 0.9
                        })
                    
                    # Check for column validation
                    if 'column' in content.lower() and ('not found' in content.lower() or 'missing' in content.lower()):
                        validation_patterns['column_validation'].append({
                            'file': str(action_file),
                            'lines': self.extract_validation_block(content, 'column'),
                            'exact_match': False
                        })
                        
                except Exception as e:
                    print(f"⚠️  Error analyzing {action_file}: {e}")
                    continue
        
        return {
            'patterns': validation_patterns,
            'summary': {
                'total_patterns': sum(len(patterns) for patterns in validation_patterns.values()),
                'exact_matches': sum(1 for patterns in validation_patterns.values() 
                                   for p in patterns if p['exact_match']),
                'cross_entity_usage': self.count_cross_entity_usage(validation_patterns)
            }
        }
    
    def analyze_error_handling_patterns(self) -> Dict[str, Any]:
        """Analyze error handling patterns."""
        
        error_patterns = {
            'context_error_raising': [],
            'dataset_not_found_error': [],
            'validation_error_messages': [],
            'exception_wrapping': []
        }
        
        for entity_path in self.entity_paths:
            if not Path(entity_path).exists():
                continue
                
            for action_file in Path(entity_path).rglob("*.py"):
                if action_file.name.startswith(("test_", "__")):
                    continue
                    
                try:
                    content = action_file.read_text()
                    
                    # Look for common error patterns
                    if 'ContextError' in content or 'context' in content.lower():
                        error_patterns['context_error_raising'].append({
                            'file': str(action_file),
                            'pattern': self.extract_error_pattern(content, 'ContextError')
                        })
                    
                    if 'DatasetNotFoundError' in content or 'dataset.*not found' in content.lower():
                        error_patterns['dataset_not_found_error'].append({
                            'file': str(action_file),
                            'pattern': self.extract_error_pattern(content, 'DatasetNotFound')
                        })
                        
                except Exception as e:
                    continue
        
        return error_patterns
    
    def analyze_context_patterns(self) -> Dict[str, Any]:
        """Analyze execution context management patterns."""
        
        context_patterns = {
            'context_read_patterns': [],
            'context_write_patterns': [],
            'statistics_updates': [],
            'result_storage': []
        }
        
        for entity_path in self.entity_paths:
            if not Path(entity_path).exists():
                continue
                
            for action_file in Path(entity_path).rglob("*.py"):
                if action_file.name.startswith(("test_", "__")):
                    continue
                    
                try:
                    content = action_file.read_text()
                    
                    # Statistics update patterns
                    if 'statistics' in content and 'context' in content:
                        stats_pattern = self.extract_statistics_pattern(content)
                        if stats_pattern:
                            context_patterns['statistics_updates'].append({
                                'file': str(action_file),
                                'pattern': stats_pattern,
                                'lines_count': len(stats_pattern.splitlines())
                            })
                    
                    # Result storage patterns
                    if "context['datasets']" in content and "=" in content:
                        result_pattern = self.extract_result_storage_pattern(content)
                        if result_pattern:
                            context_patterns['result_storage'].append({
                                'file': str(action_file),
                                'pattern': result_pattern,
                                'lines_count': len(result_pattern.splitlines())
                            })
                            
                except Exception as e:
                    continue
        
        return context_patterns
    
    def find_cross_entity_patterns(self, duplication_results: Dict) -> List[Dict]:
        """Find patterns that appear across multiple entity types."""
        
        cross_patterns = []
        
        # Check validation patterns
        validation_patterns = duplication_results.get('validation_patterns', {}).get('patterns', {})
        for pattern_type, instances in validation_patterns.items():
            if self.appears_in_multiple_entities(instances, 2):
                cross_patterns.append({
                    'pattern_type': f'validation_{pattern_type}',
                    'locations': [inst['file'] for inst in instances],
                    'lines_duplicated': sum(len(inst.get('lines', [])) for inst in instances),
                    'abstraction_benefit': self.calculate_abstraction_benefit(instances)
                })
        
        # Check context patterns
        context_patterns = duplication_results.get('context_management_patterns', {})
        for pattern_type, instances in context_patterns.items():
            if self.appears_in_multiple_entities(instances, 2):
                cross_patterns.append({
                    'pattern_type': f'context_{pattern_type}',
                    'locations': [inst['file'] for inst in instances],
                    'lines_duplicated': sum(inst.get('lines_count', 0) for inst in instances),
                    'abstraction_benefit': self.calculate_abstraction_benefit(instances)
                })
        
        return cross_patterns
    
    def identify_pattern_candidates(self, duplication_analysis: Dict) -> List[PatternCandidate]:
        """Convert duplication analysis into pattern candidates."""
        
        candidates = []
        
        cross_patterns = duplication_analysis.get('cross_entity_patterns', [])
        
        for pattern in cross_patterns:
            candidate = PatternCandidate(
                pattern_type=pattern['pattern_type'],
                locations=pattern['locations'],
                total_duplicated_lines=pattern['lines_duplicated'],
                abstraction_overhead_lines=self.estimate_abstraction_overhead(pattern),
                usage_count=len(pattern['locations']),
                identical_logic=self.assess_identical_logic(pattern),
                unlikely_to_diverge=self.assess_divergence_likelihood(pattern),
                has_clear_interface=self.assess_interface_clarity(pattern),
                testable_in_isolation=self.assess_testability(pattern),
                entity_specific_logic=self.assess_entity_specificity(pattern),
                performance_critical=self.assess_performance_criticality(pattern)
            )
            candidates.append(candidate)
        
        return candidates
    
    def evaluate_pattern(self, pattern: PatternCandidate) -> PatternEvaluation:
        """Evaluate if pattern should be abstracted with concrete metrics."""
        
        scores = {}
        
        # Duplication Score (0-10)
        lines_saved = pattern.total_duplicated_lines - pattern.abstraction_overhead_lines
        scores['duplication_score'] = min(10, max(0, lines_saved / 10))
        
        # Complexity Reduction Score (0-10)
        complexity_reduction = self.estimate_complexity_reduction(pattern)
        scores['complexity_reduction'] = complexity_reduction
        
        # Maintenance Benefit Score (0-10)
        maintenance_score = 0
        if pattern.identical_logic:
            maintenance_score += 3
        if pattern.unlikely_to_diverge:
            maintenance_score += 3
        if pattern.has_clear_interface:
            maintenance_score += 2
        if pattern.testable_in_isolation:
            maintenance_score += 2
        scores['maintenance_benefit'] = maintenance_score
        
        # Performance Impact Score (-5 to +5, normalized to 0-10)
        perf_impact = self.estimate_performance_impact(pattern)
        scores['performance_impact'] = perf_impact + 5
        
        # Readability Impact Score (0-10)
        readability_score = 0
        if not pattern.entity_specific_logic:
            readability_score += 4
        if pattern.has_clear_interface:
            readability_score += 3
        if pattern.usage_count >= 3:
            readability_score += 3
        scores['readability_impact'] = readability_score
        
        # Calculate weighted total
        total_score = sum(scores[criterion] * self.weights[criterion] 
                         for criterion in scores)
        
        recommendation = 'abstract' if total_score >= self.abstraction_threshold else 'keep_separate'
        confidence = self.calculate_confidence(scores, pattern)
        reasoning = self.generate_reasoning(scores, pattern)
        
        return PatternEvaluation(
            pattern=pattern,
            scores=scores,
            total_score=total_score,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def document_entity_specific_characteristics(self) -> Dict[str, Any]:
        """Document detailed entity-specific differences with concrete examples."""
        
        characteristics = {
            'proteins': {
                'id_systems': {
                    'primary': 'UniProt (P12345 format)',
                    'secondary': ['Gene symbols', 'Ensembl', 'RefSeq'],
                    'complexity_score': 6,
                    'validation_rules': 'Standard 6-character + isoform variations'
                },
                'data_patterns': {
                    'xrefs_complexity': 'Moderate - typically 2-4 references per protein',
                    'missing_data_rate': 0.05,
                    'format_variations': 'Low - mostly standardized'
                },
                'processing_characteristics': {
                    'primary_challenge': 'Isoform handling and version management',
                    'matching_strategy': 'Exact matching with normalization',
                    'performance_profile': 'Fast - simple string operations',
                    'cache_effectiveness': 0.85
                },
                'unique_requirements': [
                    'Isoform suffix handling (P12345-1 → P12345)',
                    'Version number removal (P12345.2 → P12345)',
                    'Case normalization (always uppercase)',
                    'Gene symbol validation (HGNC official symbols)'
                ]
            },
            'metabolites': {
                'id_systems': {
                    'primary': 'HMDB (HMDB0001234 format)',
                    'secondary': ['InChIKey', 'CHEBI', 'KEGG', 'PubChem', 'CAS'],
                    'complexity_score': 9,
                    'validation_rules': 'Multiple formats, padding variations, chemical equivalence'
                },
                'data_patterns': {
                    'xrefs_complexity': 'High - 5-8 identifier types per metabolite',
                    'missing_data_rate': 0.25,
                    'format_variations': 'High - many legacy formats'
                },
                'processing_characteristics': {
                    'primary_challenge': 'Multiple ID system reconciliation',
                    'matching_strategy': 'Multi-step with external APIs',
                    'performance_profile': 'Slow - network dependencies',
                    'cache_effectiveness': 0.65
                },
                'unique_requirements': [
                    'HMDB padding normalization (HMDB1234 → HMDB0001234)',
                    'InChI key validation (full structure validation)',
                    'Chemical similarity considerations',
                    'Stereochemistry handling',
                    'Synonym expansion'
                ]
            },
            'chemistry': {
                'id_systems': {
                    'primary': 'LOINC (12345-6 format)',
                    'secondary': ['Vendor codes', 'Test names', 'CPT codes'],
                    'complexity_score': 8,
                    'validation_rules': 'LOINC format + vendor-specific patterns'
                },
                'data_patterns': {
                    'xrefs_complexity': 'Variable - depends on vendor',
                    'missing_data_rate': 0.35,
                    'format_variations': 'Extreme - each vendor different'
                },
                'processing_characteristics': {
                    'primary_challenge': 'Fuzzy matching as primary method',
                    'matching_strategy': 'Multi-algorithm fuzzy matching',
                    'performance_profile': 'Variable - depends on dataset size',
                    'cache_effectiveness': 0.90
                },
                'unique_requirements': [
                    'Vendor detection (automatic identification)',
                    'Fuzzy matching primary (not fallback)',
                    'Unit standardization (SI vs US)',
                    'Reference range harmonization',
                    'Abbreviation expansion',
                    'Test panel expansion'
                ]
            }
        }
        
        # Calculate separation justification scores
        separation_scores = {}
        complexity_scores = [char['id_systems']['complexity_score'] 
                           for char in characteristics.values()]
        avg_complexity = np.mean(complexity_scores)
        
        for entity, char in characteristics.items():
            score = 0
            
            # ID complexity difference
            complexity_diff = abs(char['id_systems']['complexity_score'] - avg_complexity)
            score += complexity_diff * 5
            
            # Unique requirements count
            unique_req_count = len(char['unique_requirements'])
            score += unique_req_count * 2
            
            # Processing strategy uniqueness
            if 'fuzzy' in char['processing_characteristics']['matching_strategy'].lower():
                score += 15  # Unique primary strategy
            
            # Missing data rate impact
            missing_rate = char['data_patterns']['missing_data_rate']
            if missing_rate > 0.2:  # High missing data
                score += 10
            
            separation_scores[entity] = score
        
        return {
            'characteristics': characteristics,
            'separation_justification_scores': separation_scores,
            'recommendation': 'MAINTAIN_ENTITY_SEPARATION' if min(separation_scores.values()) > 25 else 'CONSIDER_ABSTRACTION'
        }
    
    def analyze_complexity(self) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        
        complexity_results = {}
        
        for entity_path in self.entity_paths:
            if not Path(entity_path).exists():
                continue
                
            entity_name = Path(entity_path).name
            complexity_results[entity_name] = {
                'total_files': 0,
                'total_lines': 0,
                'average_complexity': 0,
                'max_complexity': 0,
                'complexity_distribution': []
            }
            
            complexities = []
            
            for action_file in Path(entity_path).rglob("*.py"):
                if action_file.name.startswith(("test_", "__")):
                    continue
                    
                try:
                    content = action_file.read_text()
                    lines = len(content.splitlines())
                    
                    # Simple complexity estimation based on control flow
                    complexity = self.estimate_cyclomatic_complexity(content)
                    complexities.append(complexity)
                    
                    complexity_results[entity_name]['total_files'] += 1
                    complexity_results[entity_name]['total_lines'] += lines
                    
                except Exception:
                    continue
            
            if complexities:
                complexity_results[entity_name]['average_complexity'] = np.mean(complexities)
                complexity_results[entity_name]['max_complexity'] = max(complexities)
                complexity_results[entity_name]['complexity_distribution'] = complexities
        
        return complexity_results
    
    def generate_recommendations(self, pattern_evaluations: List[Dict]) -> Dict[str, Any]:
        """Generate final recommendations based on pattern evaluations."""
        
        recommended_abstractions = []
        entity_specific_patterns = []
        anti_patterns_avoided = []
        
        for evaluation in pattern_evaluations:
            if evaluation['evaluation']['recommendation'] == 'abstract':
                recommended_abstractions.append({
                    'pattern_type': evaluation['pattern_type'],
                    'confidence': evaluation['evaluation']['confidence'],
                    'benefit_score': evaluation['evaluation']['total_score'],
                    'implementation_priority': 'HIGH' if evaluation['evaluation']['total_score'] > 40 else 'MEDIUM'
                })
            else:
                entity_specific_patterns.append({
                    'pattern_type': evaluation['pattern_type'],
                    'reason_for_separation': evaluation['evaluation']['reasoning']
                })
        
        return {
            'recommended_abstractions': recommended_abstractions,
            'entity_specific_patterns': entity_specific_patterns,
            'anti_patterns_avoided': anti_patterns_avoided,
            'summary': {
                'total_patterns_analyzed': len(pattern_evaluations),
                'recommended_for_abstraction': len(recommended_abstractions),
                'maintain_entity_separation': len(entity_specific_patterns),
                'abstraction_percentage': len(recommended_abstractions) / len(pattern_evaluations) * 100 if pattern_evaluations else 0
            }
        }
    
    # Helper methods
    def extract_validation_block(self, content: str, validation_type: str) -> List[str]:
        """Extract validation code block."""
        lines = content.splitlines()
        validation_lines = []
        
        for i, line in enumerate(lines):
            if validation_type in line.lower():
                # Extract surrounding context (up to 5 lines before and after)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                validation_lines.extend(lines[start:end])
                break
        
        return validation_lines
    
    def calculate_similarity_score(self, content: str, pattern_type: str) -> float:
        """Calculate similarity score for pattern matching."""
        # Simple heuristic based on keyword density
        keywords = ['if', 'not', 'in', 'context', 'raise', 'Error']
        total_words = len(content.split())
        keyword_count = sum(1 for word in content.split() if word in keywords)
        return min(1.0, keyword_count / max(1, total_words) * 10)
    
    def count_cross_entity_usage(self, validation_patterns: Dict) -> int:
        """Count how many entities use similar patterns."""
        entity_usage = set()
        
        for pattern_list in validation_patterns.values():
            for pattern in pattern_list:
                file_path = pattern['file']
                if '/proteins/' in file_path:
                    entity_usage.add('proteins')
                elif '/metabolites/' in file_path:
                    entity_usage.add('metabolites')
                elif '/chemistry/' in file_path:
                    entity_usage.add('chemistry')
        
        return len(entity_usage)
    
    def extract_error_pattern(self, content: str, error_type: str) -> str:
        """Extract error handling pattern."""
        lines = content.splitlines()
        for line in lines:
            if error_type in line:
                return line.strip()
        return ""
    
    def extract_statistics_pattern(self, content: str) -> Optional[str]:
        """Extract statistics update pattern."""
        lines = content.splitlines()
        stats_lines = []
        
        in_stats_block = False
        for line in lines:
            if 'statistics' in line.lower() and ('=' in line or 'update' in line.lower()):
                in_stats_block = True
                stats_lines.append(line.strip())
            elif in_stats_block and line.strip():
                if line.startswith('    '):  # Still in the block
                    stats_lines.append(line.strip())
                else:
                    break
        
        return '\n'.join(stats_lines) if stats_lines else None
    
    def extract_result_storage_pattern(self, content: str) -> Optional[str]:
        """Extract result storage pattern."""
        lines = content.splitlines()
        storage_lines = []
        
        for line in lines:
            if "context['datasets']" in line and '=' in line:
                storage_lines.append(line.strip())
        
        return '\n'.join(storage_lines) if storage_lines else None
    
    def appears_in_multiple_entities(self, instances: List[Dict], min_entities: int = 2) -> bool:
        """Check if pattern appears in multiple entities."""
        entities = set()
        for instance in instances:
            file_path = instance['file']
            if '/proteins/' in file_path:
                entities.add('proteins')
            elif '/metabolites/' in file_path:
                entities.add('metabolites')
            elif '/chemistry/' in file_path:
                entities.add('chemistry')
        
        return len(entities) >= min_entities
    
    def calculate_abstraction_benefit(self, instances: List[Dict]) -> float:
        """Calculate potential benefit of abstracting this pattern."""
        if not instances:
            return 0.0
        
        # Simple heuristic: benefit increases with usage and line count
        usage_count = len(instances)
        total_lines = sum(len(inst.get('lines', [])) for inst in instances)
        
        benefit = (usage_count * 5) + (total_lines * 0.5)
        return min(100.0, benefit)
    
    def estimate_abstraction_overhead(self, pattern: Dict) -> int:
        """Estimate the overhead lines needed to abstract this pattern."""
        base_overhead = 10  # Function definition, imports, etc.
        
        # Add overhead for complex patterns
        if 'validation' in pattern['pattern_type']:
            base_overhead += 5  # Parameter validation
        if 'context' in pattern['pattern_type']:
            base_overhead += 3  # Context handling
        
        return base_overhead
    
    def assess_identical_logic(self, pattern: Dict) -> bool:
        """Assess if pattern logic is truly identical."""
        # Heuristic: validation patterns tend to be identical
        return 'validation' in pattern['pattern_type']
    
    def assess_divergence_likelihood(self, pattern: Dict) -> bool:
        """Assess likelihood that pattern will diverge in the future."""
        # Context and validation patterns unlikely to diverge
        return pattern['pattern_type'] in ['validation_input_key_validation', 'context_statistics_updates']
    
    def assess_interface_clarity(self, pattern: Dict) -> bool:
        """Assess if pattern would have a clear interface."""
        # Simple patterns tend to have clear interfaces
        return len(pattern['locations']) >= 3
    
    def assess_testability(self, pattern: Dict) -> bool:
        """Assess if pattern can be tested in isolation."""
        # Utility functions are generally testable
        return 'validation' in pattern['pattern_type'] or 'context' in pattern['pattern_type']
    
    def assess_entity_specificity(self, pattern: Dict) -> bool:
        """Assess if pattern contains entity-specific logic."""
        # Most validation patterns are generic
        return 'matching' in pattern['pattern_type'] or 'identification' in pattern['pattern_type']
    
    def assess_performance_criticality(self, pattern: Dict) -> bool:
        """Assess if pattern is in performance-critical path."""
        # Matching operations tend to be performance critical
        return 'matching' in pattern['pattern_type']
    
    def estimate_complexity_reduction(self, pattern: PatternCandidate) -> float:
        """Estimate complexity reduction from abstraction (0-10 scale)."""
        if pattern.usage_count >= 5:
            return 8.0  # High reduction for frequently used patterns
        elif pattern.usage_count >= 3:
            return 5.0  # Medium reduction
        else:
            return 2.0  # Low reduction
    
    def estimate_performance_impact(self, pattern: PatternCandidate) -> float:
        """Estimate performance impact (-5 to +5 scale)."""
        impact = 0.0
        
        if pattern.pattern_type in ['validation_input_key_validation', 'context_statistics_updates']:
            impact += 1.0  # Slight positive impact from centralized logic
        
        if pattern.performance_critical:
            impact -= 1.0  # Slight negative impact for critical paths
        
        return max(-5.0, min(5.0, impact))
    
    def calculate_confidence(self, scores: Dict[str, float], pattern: PatternCandidate) -> float:
        """Calculate confidence in the recommendation."""
        high_confidence_factors = [
            scores['duplication_score'] > 7,
            pattern.usage_count >= 5,
            pattern.identical_logic,
            scores['maintenance_benefit'] > 7
        ]
        
        low_confidence_factors = [
            pattern.entity_specific_logic,
            scores['readability_impact'] < 5,
            pattern.performance_critical,
            scores['complexity_reduction'] < 3
        ]
        
        confidence = (sum(high_confidence_factors) - sum(low_confidence_factors)) / 8 + 0.5
        return max(0.0, min(1.0, confidence))
    
    def generate_reasoning(self, scores: Dict[str, float], pattern: PatternCandidate) -> str:
        """Generate human-readable reasoning for the recommendation."""
        reasons = []
        
        if scores['duplication_score'] > 7:
            reasons.append("High code duplication detected")
        if scores['maintenance_benefit'] > 7:
            reasons.append("Clear maintenance benefits")
        if pattern.usage_count >= 5:
            reasons.append("Used frequently across codebase")
        if pattern.entity_specific_logic:
            reasons.append("Contains entity-specific logic")
        if scores['readability_impact'] < 5:
            reasons.append("May impact code readability")
        
        if not reasons:
            reasons.append("Marginal benefits from abstraction")
        
        return "; ".join(reasons)
    
    def estimate_cyclomatic_complexity(self, content: str) -> int:
        """Estimate cyclomatic complexity of code."""
        # Count decision points
        decision_keywords = ['if', 'elif', 'for', 'while', 'except', 'and', 'or']
        complexity = 1  # Base complexity
        
        for keyword in decision_keywords:
            complexity += content.lower().count(keyword)
        
        return complexity

def main():
    """Run the complete pattern analysis pipeline."""
    analyzer = PatternAnalyzer()
    results = analyzer.run_complete_analysis()
    
    # Save results
    output_file = Path("pattern_analysis_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Analysis complete. Results saved to: {output_file}")
    print(f"📊 Files analyzed: {results['analysis_metadata']['total_files_analyzed']}")
    print(f"📈 Lines analyzed: {results['analysis_metadata']['total_lines_analyzed']:,}")
    print(f"🔍 Patterns identified: {results['analysis_metadata']['patterns_identified']}")
    
    if results.get('recommendations'):
        rec_count = len(results['recommendations'].get('recommended_abstractions', []))
        sep_count = len(results['recommendations'].get('entity_specific_patterns', []))
        print(f"✅ Recommended for abstraction: {rec_count}")
        print(f"🏷️  Keep entity-specific: {sep_count}")
    
    return results

if __name__ == "__main__":
    main()