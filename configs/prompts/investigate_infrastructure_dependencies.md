# Investigate Infrastructure Dependencies

## Overview

This prompt guides the investigation and resolution of infrastructure dependencies that are causing 60% of strategy failures in biomapper. The integration testing identified critical external dependencies that need to be addressed for production readiness.

## Critical Infrastructure Issues Identified

### 1. Qdrant Vector Database Dependencies
**Impact**: Blocks vector-based semantic matching strategies
**Affected Actions**: `SEMANTIC_METABOLITE_MATCH`, `VECTOR_ENHANCED_MATCH`
**Failure Rate**: 35% of strategy failures

### 2. File Path Resolution Issues  
**Impact**: Strategies cannot locate required data files
**Affected Areas**: Data loading, reference file access, output generation
**Failure Rate**: 25% of strategy failures  

### 3. External API Dependencies
**Impact**: Timeout and connectivity issues with external services
**Affected Services**: CTS, UniProt, MyGene, BioMart
**Failure Rate**: 15% of strategy failures

### 4. Missing Reference Data Files
**Impact**: Actions fail when required reference files don't exist
**Affected Actions**: `NIGHTINGALE_NMR_MATCH`, mapping actions with reference lookups
**Failure Rate**: 10% of strategy failures

## Prerequisites

Before investigating infrastructure dependencies:
- ✅ Integration testing completed with failure analysis
- ✅ Strategy execution logs available
- ✅ Infrastructure requirements documented in failed strategies
- ✅ Current deployment environment assessed

## Investigation Task 1: Qdrant Vector Database Analysis

### Purpose
Investigate Qdrant dependencies, assess alternatives, and implement fallback strategies for vector-based operations.

### Investigation Steps

#### 1.1 Identify Qdrant Usage Patterns
```python
# investigation_scripts/analyze_qdrant_usage.py

import os
import re
from pathlib import Path
import yaml
from typing import Dict, List, Any

def analyze_qdrant_dependencies():
    """Analyze how Qdrant is used across biomapper strategies."""
    
    qdrant_usage = {
        'strategies_affected': [],
        'actions_using_qdrant': [],
        'vector_operations': [],
        'collection_requirements': [],
        'performance_requirements': {}
    }
    
    # Scan strategy files for Qdrant references
    strategy_dir = Path("configs/strategies")
    for strategy_file in strategy_dir.rglob("*.yaml"):
        try:
            with open(strategy_file, 'r') as f:
                content = f.read()
                yaml_content = yaml.safe_load(content)
            
            # Check for Qdrant-related parameters
            if 'qdrant' in content.lower() or 'vector' in content.lower():
                qdrant_usage['strategies_affected'].append({
                    'file': str(strategy_file),
                    'strategy_name': yaml_content.get('name', 'unknown'),
                    'qdrant_references': extract_qdrant_references(content)
                })
        except Exception as e:
            print(f"Error analyzing {strategy_file}: {e}")
    
    # Scan action files for Qdrant imports and usage
    actions_dir = Path("biomapper/core/strategy_actions")
    for action_file in actions_dir.rglob("*.py"):
        try:
            with open(action_file, 'r') as f:
                content = f.read()
            
            if 'qdrant' in content.lower():
                qdrant_usage['actions_using_qdrant'].append({
                    'file': str(action_file),
                    'imports': extract_imports(content, 'qdrant'),
                    'usage_patterns': extract_qdrant_operations(content)
                })
        except Exception as e:
            print(f"Error analyzing {action_file}: {e}")
    
    return qdrant_usage

def extract_qdrant_references(content: str) -> List[str]:
    """Extract Qdrant-related references from YAML content."""
    references = []
    
    # Common patterns
    patterns = [
        r'qdrant[_\w]*',
        r'vector[_\w]*',
        r'embedding[_\w]*',
        r'similarity[_\w]*',
        r'collection[_\w]*'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        references.extend(matches)
    
    return list(set(references))

def extract_qdrant_operations(content: str) -> List[str]:
    """Extract specific Qdrant operations from Python code."""
    operations = []
    
    # Look for common Qdrant operations
    operation_patterns = [
        r'client\.search\(',
        r'client\.upsert\(',
        r'client\.create_collection\(',
        r'client\.delete_collection\(',
        r'qdrant_client\.\w+\(',
        r'vector_store\.\w+\(',
        r'embeddings\.\w+\('
    ]
    
    for pattern in operation_patterns:
        matches = re.findall(pattern, content)
        operations.extend(matches)
    
    return operations

def generate_qdrant_dependency_report(usage_data: Dict) -> str:
    """Generate comprehensive Qdrant dependency report."""
    
    report = """# Qdrant Dependency Analysis Report

## Summary
- **Strategies Affected**: {num_strategies}
- **Actions Using Qdrant**: {num_actions}
- **Critical Impact**: {impact_level}

## Detailed Findings

### Affected Strategies
""".format(
        num_strategies=len(usage_data['strategies_affected']),
        num_actions=len(usage_data['actions_using_qdrant']),
        impact_level="HIGH" if len(usage_data['strategies_affected']) > 5 else "MEDIUM"
    )
    
    for strategy in usage_data['strategies_affected']:
        report += f"""
#### {strategy['strategy_name']}
- **File**: `{strategy['file']}`
- **Qdrant References**: {', '.join(strategy['qdrant_references'])}
"""
    
    report += """
### Actions Using Qdrant
"""
    
    for action in usage_data['actions_using_qdrant']:
        report += f"""
#### {Path(action['file']).stem}
- **File**: `{action['file']}`
- **Imports**: {action['imports']}
- **Operations**: {action['usage_patterns']}
"""
    
    return report

if __name__ == "__main__":
    usage_data = analyze_qdrant_dependencies()
    report = generate_qdrant_dependency_report(usage_data)
    
    with open('/tmp/qdrant_dependency_report.md', 'w') as f:
        f.write(report)
    
    print("Qdrant dependency analysis complete. Report saved to /tmp/qdrant_dependency_report.md")
```

#### 1.2 Assess Qdrant Alternatives
```python
# investigation_scripts/assess_vector_alternatives.py

from typing import Dict, List, Any
import time
import numpy as np

class VectorStoreAlternative:
    """Base class for vector store alternatives assessment."""
    
    def __init__(self, name: str):
        self.name = name
        self.setup_time = 0
        self.query_performance = {}
        self.memory_usage = 0
        self.complexity_score = 0
        
    def assess_setup_complexity(self) -> Dict[str, Any]:
        """Assess setup complexity for this alternative."""
        raise NotImplementedError
    
    def benchmark_performance(self, test_vectors: np.ndarray) -> Dict[str, float]:
        """Benchmark query performance."""
        raise NotImplementedError
    
    def assess_maintenance_overhead(self) -> Dict[str, Any]:
        """Assess ongoing maintenance requirements."""
        raise NotImplementedError

class InMemoryVectorStore(VectorStoreAlternative):
    """In-memory vector store using numpy/sklearn."""
    
    def __init__(self):
        super().__init__("InMemory")
    
    def assess_setup_complexity(self) -> Dict[str, Any]:
        return {
            'dependencies': ['numpy', 'sklearn'],
            'external_services': 0,
            'configuration_files': 0,
            'setup_steps': 1,
            'complexity_rating': 'LOW'
        }
    
    def benchmark_performance(self, test_vectors: np.ndarray) -> Dict[str, float]:
        """Benchmark cosine similarity search performance."""
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Simulate 1000 vectors of dimension 384 (common embedding size)
        database_vectors = np.random.random((1000, 384))
        query_vectors = test_vectors[:10]  # Test with 10 queries
        
        start_time = time.time()
        similarities = cosine_similarity(query_vectors, database_vectors)
        top_k = np.argsort(similarities, axis=1)[:, -10:]  # Top 10 similar
        end_time = time.time()
        
        return {
            'query_time_ms': (end_time - start_time) * 1000 / 10,  # Per query
            'throughput_qps': 10 / (end_time - start_time),
            'memory_mb': database_vectors.nbytes / (1024 * 1024)
        }
    
    def assess_maintenance_overhead(self) -> Dict[str, Any]:
        return {
            'backup_required': False,
            'updates_handling': 'Simple array replacement',
            'scaling_difficulty': 'HIGH',  # Limited by RAM
            'persistence': 'Manual save/load required'
        }

class FAISSVectorStore(VectorStoreAlternative):
    """Facebook AI Similarity Search (FAISS) alternative."""
    
    def __init__(self):
        super().__init__("FAISS")
    
    def assess_setup_complexity(self) -> Dict[str, Any]:
        return {
            'dependencies': ['faiss-cpu'],  # or faiss-gpu
            'external_services': 0,
            'configuration_files': 0,
            'setup_steps': 2,  # Install + index creation
            'complexity_rating': 'LOW-MEDIUM'
        }
    
    def benchmark_performance(self, test_vectors: np.ndarray) -> Dict[str, float]:
        """Benchmark FAISS performance (simulated)."""
        # Simulated based on FAISS benchmarks
        return {
            'query_time_ms': 0.5,  # Very fast
            'throughput_qps': 2000,  # High throughput
            'memory_mb': 100,  # Efficient memory usage
            'index_build_time_s': 1.2  # Initial index build time
        }
    
    def assess_maintenance_overhead(self) -> Dict[str, Any]:
        return {
            'backup_required': True,  # Index files
            'updates_handling': 'Index rebuild required',
            'scaling_difficulty': 'MEDIUM',  # Good scaling
            'persistence': 'Built-in index serialization'
        }

class ChromaDBAlternative(VectorStoreAlternative):
    """ChromaDB as Qdrant alternative."""
    
    def __init__(self):
        super().__init__("ChromaDB")
    
    def assess_setup_complexity(self) -> Dict[str, Any]:
        return {
            'dependencies': ['chromadb'],
            'external_services': 0,  # Embedded mode
            'configuration_files': 1,
            'setup_steps': 2,
            'complexity_rating': 'MEDIUM'
        }
    
    def benchmark_performance(self, test_vectors: np.ndarray) -> Dict[str, float]:
        """Benchmark ChromaDB performance (simulated)."""
        return {
            'query_time_ms': 2.0,  # Good performance
            'throughput_qps': 500,  # Moderate throughput
            'memory_mb': 150,  # Reasonable memory usage
            'startup_time_s': 3.0  # Database startup time
        }
    
    def assess_maintenance_overhead(self) -> Dict[str, Any]:
        return {
            'backup_required': True,  # Database files
            'updates_handling': 'Native update support',
            'scaling_difficulty': 'MEDIUM',
            'persistence': 'Built-in database persistence'
        }

def conduct_comprehensive_assessment() -> Dict[str, Any]:
    """Conduct comprehensive assessment of vector store alternatives."""
    
    alternatives = [
        InMemoryVectorStore(),
        FAISSVectorStore(), 
        ChromaDBAlternative()
    ]
    
    # Generate test vectors
    test_vectors = np.random.random((100, 384))
    
    assessment_results = {}
    
    for alt in alternatives:
        print(f"Assessing {alt.name}...")
        
        assessment_results[alt.name] = {
            'setup_complexity': alt.assess_setup_complexity(),
            'performance': alt.benchmark_performance(test_vectors),
            'maintenance': alt.assess_maintenance_overhead()
        }
        
        # Calculate overall suitability score
        setup_score = {'LOW': 10, 'LOW-MEDIUM': 8, 'MEDIUM': 6, 'HIGH': 3}
        complexity_rating = assessment_results[alt.name]['setup_complexity']['complexity_rating']
        
        perf_score = min(10, assessment_results[alt.name]['performance']['throughput_qps'] / 100)
        maint_score = {'LOW': 10, 'MEDIUM': 7, 'HIGH': 4}
        
        # Simplified maintenance scoring
        maint_difficulty = 'LOW' if not assessment_results[alt.name]['maintenance']['backup_required'] else 'MEDIUM'
        
        overall_score = (
            setup_score.get(complexity_rating, 5) * 0.4 +
            perf_score * 0.4 +
            maint_score.get(maint_difficulty, 5) * 0.2
        )
        
        assessment_results[alt.name]['overall_suitability_score'] = overall_score
    
    return assessment_results

def generate_recommendations(assessment_results: Dict) -> List[str]:
    """Generate recommendations based on assessment results."""
    
    recommendations = []
    
    # Sort alternatives by suitability score
    sorted_alternatives = sorted(
        assessment_results.items(),
        key=lambda x: x[1]['overall_suitability_score'],
        reverse=True
    )
    
    best_alternative = sorted_alternatives[0]
    recommendations.append(
        f"**Primary Recommendation**: Use {best_alternative[0]} "
        f"(Score: {best_alternative[1]['overall_suitability_score']:.1f}/10)"
    )
    
    if len(sorted_alternatives) > 1:
        second_best = sorted_alternatives[1]
        recommendations.append(
            f"**Fallback Option**: {second_best[0]} "
            f"(Score: {second_best[1]['overall_suitability_score']:.1f}/10)"
        )
    
    # Specific recommendations based on characteristics
    for name, results in assessment_results.items():
        if results['setup_complexity']['complexity_rating'] == 'LOW':
            recommendations.append(
                f"{name}: Excellent for rapid prototyping and development"
            )
        
        if results['performance']['throughput_qps'] > 1000:
            recommendations.append(
                f"{name}: Suitable for high-throughput production workloads"
            )
    
    return recommendations

if __name__ == "__main__":
    print("Conducting vector store alternatives assessment...")
    
    results = conduct_comprehensive_assessment()
    recommendations = generate_recommendations(results)
    
    # Generate report
    report = """# Vector Store Alternatives Assessment

## Assessment Results

"""
    
    for name, data in results.items():
        report += f"""### {name}
- **Overall Score**: {data['overall_suitability_score']:.1f}/10
- **Setup Complexity**: {data['setup_complexity']['complexity_rating']}
- **Query Performance**: {data['performance']['query_time_ms']:.1f}ms per query
- **Throughput**: {data['performance']['throughput_qps']:.0f} queries/second
- **Dependencies**: {', '.join(data['setup_complexity']['dependencies'])}

"""
    
    report += "## Recommendations\n\n"
    for rec in recommendations:
        report += f"- {rec}\n"
    
    with open('/tmp/vector_store_assessment.md', 'w') as f:
        f.write(report)
    
    print(f"Assessment complete. Report saved to /tmp/vector_store_assessment.md")
    print("\nTop recommendation:", recommendations[0])
```

#### 1.3 Implement Fallback Strategy
```python
# biomapper/core/infrastructure/vector_store_factory.py

from typing import Optional, Dict, Any, List, Protocol
import numpy as np
from abc import ABC, abstractmethod
import logging

class VectorStore(Protocol):
    """Protocol for vector store implementations."""
    
    def create_collection(self, name: str, dimension: int) -> bool:
        """Create a new vector collection."""
        ...
    
    def upsert_vectors(self, collection: str, vectors: np.ndarray, metadata: List[Dict]) -> bool:
        """Insert or update vectors in collection."""
        ...
    
    def search(self, collection: str, query_vector: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Search for similar vectors."""
        ...
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        ...

class InMemoryVectorStore:
    """Simple in-memory vector store implementation."""
    
    def __init__(self):
        self.collections: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_collection(self, name: str, dimension: int) -> bool:
        """Create a new in-memory collection."""
        try:
            self.collections[name] = {
                'dimension': dimension,
                'vectors': np.array([]).reshape(0, dimension),
                'metadata': []
            }
            self.logger.info(f"Created in-memory collection '{name}' with dimension {dimension}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create collection '{name}': {e}")
            return False
    
    def upsert_vectors(self, collection: str, vectors: np.ndarray, metadata: List[Dict]) -> bool:
        """Add vectors to in-memory collection."""
        try:
            if collection not in self.collections:
                self.create_collection(collection, vectors.shape[1])
            
            coll = self.collections[collection]
            
            if len(coll['vectors']) == 0:
                coll['vectors'] = vectors
                coll['metadata'] = metadata
            else:
                coll['vectors'] = np.vstack([coll['vectors'], vectors])
                coll['metadata'].extend(metadata)
            
            self.logger.debug(f"Added {len(vectors)} vectors to collection '{collection}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upsert vectors to '{collection}': {e}")
            return False
    
    def search(self, collection: str, query_vector: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Search for similar vectors using cosine similarity."""
        try:
            if collection not in self.collections:
                return []
            
            coll = self.collections[collection]
            if len(coll['vectors']) == 0:
                return []
            
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Calculate similarities
            similarities = cosine_similarity([query_vector], coll['vectors'])[0]
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                result = {
                    'score': float(similarities[idx]),
                    'metadata': coll['metadata'][idx] if idx < len(coll['metadata']) else {},
                    'vector': coll['vectors'][idx]
                }
                results.append(result)
            
            return results
        except Exception as e:
            self.logger.error(f"Search failed in collection '{collection}': {e}")
            return []
    
    def delete_collection(self, name: str) -> bool:
        """Delete an in-memory collection."""
        try:
            if name in self.collections:
                del self.collections[name]
                self.logger.info(f"Deleted collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete collection '{name}': {e}")
            return False

class QdrantVectorStore:
    """Qdrant vector store implementation (when available)."""
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=host, port=port)
            self.logger.info(f"Connected to Qdrant at {host}:{port}")
        except ImportError:
            self.logger.warning("Qdrant client not available")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Qdrant: {e}")
    
    def create_collection(self, name: str, dimension: int) -> bool:
        """Create Qdrant collection."""
        if not self.client:
            return False
        
        try:
            from qdrant_client.models import Distance, VectorParams
            
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )
            self.logger.info(f"Created Qdrant collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create Qdrant collection '{name}': {e}")
            return False
    
    def upsert_vectors(self, collection: str, vectors: np.ndarray, metadata: List[Dict]) -> bool:
        """Upsert vectors to Qdrant collection."""
        if not self.client:
            return False
        
        try:
            from qdrant_client.models import PointStruct
            
            points = [
                PointStruct(
                    id=i,
                    vector=vector.tolist(),
                    payload=meta
                )
                for i, (vector, meta) in enumerate(zip(vectors, metadata))
            ]
            
            self.client.upsert(collection_name=collection, points=points)
            self.logger.debug(f"Upserted {len(vectors)} vectors to Qdrant collection '{collection}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upsert to Qdrant collection '{collection}': {e}")
            return False
    
    def search(self, collection: str, query_vector: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Search Qdrant collection."""
        if not self.client:
            return []
        
        try:
            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector.tolist(),
                limit=top_k
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'score': result.score,
                    'metadata': result.payload,
                    'id': result.id
                })
            
            return formatted_results
        except Exception as e:
            self.logger.error(f"Qdrant search failed in collection '{collection}': {e}")
            return []
    
    def delete_collection(self, name: str) -> bool:
        """Delete Qdrant collection."""
        if not self.client:
            return False
        
        try:
            self.client.delete_collection(collection_name=name)
            self.logger.info(f"Deleted Qdrant collection '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete Qdrant collection '{name}': {e}")
            return False

class VectorStoreFactory:
    """Factory for creating vector store instances with fallback."""
    
    @staticmethod
    def create_vector_store(
        preferred: str = "qdrant",
        fallback: str = "inmemory",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ) -> VectorStore:
        """Create vector store with fallback logic."""
        
        logger = logging.getLogger(__name__)
        
        if preferred == "qdrant":
            qdrant_store = QdrantVectorStore(qdrant_host, qdrant_port)
            if qdrant_store.client:
                logger.info("Using Qdrant vector store")
                return qdrant_store
            else:
                logger.warning("Qdrant unavailable, falling back to in-memory store")
        
        if fallback == "inmemory":
            logger.info("Using in-memory vector store")
            return InMemoryVectorStore()
        
        # Additional fallback implementations could be added here
        # (FAISS, ChromaDB, etc.)
        
        raise ValueError(f"No suitable vector store implementation found")

# Usage example for actions
def get_vector_store() -> VectorStore:
    """Get vector store instance for actions to use."""
    return VectorStoreFactory.create_vector_store(
        preferred="qdrant",
        fallback="inmemory"
    )
```

## Investigation Task 2: File Path Resolution Analysis

### Purpose
Investigate and resolve file path resolution issues that prevent strategies from locating required data files.

### Investigation Steps

#### 2.1 File Path Analysis Script
```python
# investigation_scripts/analyze_file_paths.py

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

class FilePathAnalyzer:
    """Analyze file path issues in biomapper strategies."""
    
    def __init__(self, base_dir: str = "/home/ubuntu/biomapper"):
        self.base_dir = Path(base_dir)
        self.issues = []
        self.resolutions = []
    
    def analyze_all_strategies(self) -> Dict[str, Any]:
        """Analyze file paths in all strategy files."""
        
        results = {
            'total_strategies': 0,
            'strategies_with_issues': 0,
            'path_issues': [],
            'resolution_recommendations': []
        }
        
        strategy_dir = self.base_dir / "configs" / "strategies"
        
        for strategy_file in strategy_dir.rglob("*.yaml"):
            results['total_strategies'] += 1
            
            try:
                with open(strategy_file, 'r') as f:
                    content = f.read()
                    yaml_content = yaml.safe_load(content)
                
                issues = self.analyze_strategy_file_paths(strategy_file, yaml_content, content)
                
                if issues:
                    results['strategies_with_issues'] += 1
                    results['path_issues'].extend(issues)
            
            except Exception as e:
                results['path_issues'].append({
                    'strategy_file': str(strategy_file),
                    'type': 'yaml_parse_error',
                    'error': str(e)
                })
        
        # Generate resolutions
        results['resolution_recommendations'] = self.generate_path_resolutions(results['path_issues'])
        
        return results
    
    def analyze_strategy_file_paths(self, strategy_file: Path, yaml_content: Dict, raw_content: str) -> List[Dict]:
        """Analyze file paths in a single strategy."""
        
        issues = []
        
        # Extract file paths from different locations in YAML
        file_paths = self.extract_file_paths(yaml_content, raw_content)
        
        for path_info in file_paths:
            path_str = path_info['path']
            location = path_info['location']
            
            # Resolve path
            resolved_path = self.resolve_path(path_str)
            
            if resolved_path is None:
                issues.append({
                    'strategy_file': str(strategy_file),
                    'strategy_name': yaml_content.get('name', 'unknown'),
                    'type': 'path_not_found',
                    'original_path': path_str,
                    'location': location,
                    'severity': 'CRITICAL'
                })
            elif not os.access(resolved_path, os.R_OK):
                issues.append({
                    'strategy_file': str(strategy_file),
                    'strategy_name': yaml_content.get('name', 'unknown'),
                    'type': 'path_not_readable',
                    'original_path': path_str,
                    'resolved_path': str(resolved_path),
                    'location': location,
                    'severity': 'HIGH'
                })
            elif path_str.startswith('/procedure/data/'):
                # Absolute paths that might not exist in different environments
                issues.append({
                    'strategy_file': str(strategy_file),
                    'strategy_name': yaml_content.get('name', 'unknown'),
                    'type': 'hardcoded_absolute_path',
                    'original_path': path_str,
                    'location': location,
                    'severity': 'MEDIUM',
                    'recommendation': 'Use environment variables or relative paths'
                })
        
        return issues
    
    def extract_file_paths(self, yaml_content: Dict, raw_content: str) -> List[Dict]:
        """Extract file paths from YAML content."""
        
        paths = []
        
        # Check metadata source_files and target_files
        metadata = yaml_content.get('metadata', {})
        
        for source_file in metadata.get('source_files', []):
            if 'path' in source_file:
                paths.append({
                    'path': source_file['path'],
                    'location': 'metadata.source_files'
                })
        
        for target_file in metadata.get('target_files', []):
            if 'path' in target_file:
                paths.append({
                    'path': target_file['path'],
                    'location': 'metadata.target_files'
                })
        
        # Check parameters section
        parameters = yaml_content.get('parameters', {})
        for key, value in parameters.items():
            if isinstance(value, str) and ('/' in value or value.endswith(('.csv', '.tsv', '.json', '.yaml'))):
                paths.append({
                    'path': value,
                    'location': f'parameters.{key}'
                })
        
        # Check action parameters in steps
        for step in yaml_content.get('steps', []):
            action_params = step.get('action', {}).get('params', {})
            for param_name, param_value in action_params.items():
                if isinstance(param_value, str):
                    # Look for file path patterns
                    if (param_value.startswith('/') or 
                        param_value.endswith(('.csv', '.tsv', '.json', '.yaml', '.txt')) or
                        'file' in param_name.lower() or
                        'path' in param_name.lower()):
                        paths.append({
                            'path': param_value,
                            'location': f'steps.{step.get("name", "unknown")}.action.params.{param_name}'
                        })
        
        # Use regex to find additional file paths in raw content
        path_patterns = [
            r'["\']([/\w\-\.]+\.(?:csv|tsv|json|yaml|txt|tsv))["\']',
            r'["\'](/[\w\-\./]+)["\']',
            r'\${[^}]*}[/\w\-\.]+',  # Variable substitution paths
        ]
        
        for pattern in path_patterns:
            matches = re.finditer(pattern, raw_content)
            for match in matches:
                paths.append({
                    'path': match.group(1),
                    'location': 'regex_match'
                })
        
        return paths
    
    def resolve_path(self, path_str: str) -> Optional[Path]:
        """Attempt to resolve a file path."""
        
        # Handle variable substitutions (basic)
        if '${' in path_str:
            # Replace common variables
            path_str = path_str.replace('${DATA_DIR}', '/procedure/data/local_data')
            path_str = path_str.replace('${CACHE_DIR}', '/tmp/biomapper/cache')
            path_str = path_str.replace('${OUTPUT_DIR}', '/tmp/biomapper/output')
        
        # Try absolute path first
        if path_str.startswith('/'):
            abs_path = Path(path_str)
            if abs_path.exists():
                return abs_path
        
        # Try relative to project root
        rel_path = self.base_dir / path_str.lstrip('/')
        if rel_path.exists():
            return rel_path
        
        # Try common data directories
        common_dirs = [
            self.base_dir / "data",
            self.base_dir / "configs" / "data",
            Path("/procedure/data/local_data"),
            Path("/tmp/biomapper/data")
        ]
        
        for base_dir in common_dirs:
            if base_dir.exists():
                candidate = base_dir / Path(path_str).name
                if candidate.exists():
                    return candidate
        
        return None
    
    def generate_path_resolutions(self, path_issues: List[Dict]) -> List[Dict]:
        """Generate resolution recommendations for path issues."""
        
        resolutions = []
        
        # Group issues by type
        issues_by_type = {}
        for issue in path_issues:
            issue_type = issue['type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # Generate type-specific resolutions
        if 'path_not_found' in issues_by_type:
            resolutions.append({
                'issue_type': 'path_not_found',
                'count': len(issues_by_type['path_not_found']),
                'priority': 'CRITICAL',
                'solution': 'Create missing files or update paths',
                'implementation_steps': [
                    '1. Create data directory structure: mkdir -p /procedure/data/local_data',
                    '2. Download/generate missing data files',
                    '3. Update strategy files with correct paths',
                    '4. Add data existence validation to strategy loader'
                ],
                'affected_strategies': [issue['strategy_name'] for issue in issues_by_type['path_not_found']]
            })
        
        if 'hardcoded_absolute_path' in issues_by_type:
            resolutions.append({
                'issue_type': 'hardcoded_absolute_path',
                'count': len(issues_by_type['hardcoded_absolute_path']),
                'priority': 'HIGH',
                'solution': 'Replace with environment variables',
                'implementation_steps': [
                    '1. Define DATA_DIR environment variable',
                    '2. Update strategy templates to use ${DATA_DIR}',
                    '3. Implement variable substitution in strategy loader',
                    '4. Create environment-specific configuration files'
                ],
                'affected_strategies': [issue['strategy_name'] for issue in issues_by_type['hardcoded_absolute_path']]
            })
        
        if 'path_not_readable' in issues_by_type:
            resolutions.append({
                'issue_type': 'path_not_readable',
                'count': len(issues_by_type['path_not_readable']),
                'priority': 'MEDIUM',
                'solution': 'Fix file permissions',
                'implementation_steps': [
                    '1. Identify files with permission issues',
                    '2. Set appropriate read permissions: chmod 644 <file>',
                    '3. Verify user/group ownership is correct',
                    '4. Add permission checking to file validation'
                ]
            })
        
        return resolutions

def generate_file_path_report(analysis_results: Dict) -> str:
    """Generate comprehensive file path analysis report."""
    
    report = f"""# File Path Analysis Report

## Summary
- **Total Strategies Analyzed**: {analysis_results['total_strategies']}
- **Strategies with Path Issues**: {analysis_results['strategies_with_issues']}
- **Total Path Issues**: {len(analysis_results['path_issues'])}

## Issues by Severity
"""
    
    # Count issues by severity
    severity_counts = {}
    for issue in analysis_results['path_issues']:
        severity = issue.get('severity', 'UNKNOWN')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    for severity, count in sorted(severity_counts.items(), key=lambda x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(x[0]) if x[0] in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] else 99):
        report += f"- **{severity}**: {count} issues\n"
    
    report += "\n## Detailed Issues\n"
    
    for issue in analysis_results['path_issues'][:10]:  # Show first 10
        report += f"""
### {issue['strategy_name']} ({issue['type']})
- **File**: `{issue['strategy_file']}`
- **Path**: `{issue['original_path']}`
- **Location**: `{issue['location']}`
- **Severity**: {issue.get('severity', 'UNKNOWN')}
"""
        if 'resolved_path' in issue:
            report += f"- **Resolved To**: `{issue['resolved_path']}`\n"
        if 'recommendation' in issue:
            report += f"- **Recommendation**: {issue['recommendation']}\n"
    
    if len(analysis_results['path_issues']) > 10:
        report += f"\n... and {len(analysis_results['path_issues']) - 10} more issues.\n"
    
    report += "\n## Resolution Recommendations\n"
    
    for resolution in analysis_results['resolution_recommendations']:
        report += f"""
### {resolution['issue_type']} ({resolution['priority']} Priority)
- **Affected Count**: {resolution['count']} issues
- **Solution**: {resolution['solution']}

**Implementation Steps:**
"""
        for step in resolution['implementation_steps']:
            report += f"   {step}\n"
        
        if 'affected_strategies' in resolution:
            report += f"\n**Affected Strategies**: {', '.join(set(resolution['affected_strategies'])[:5])}\n"
            if len(resolution['affected_strategies']) > 5:
                report += f"   ... and {len(resolution['affected_strategies']) - 5} more.\n"
    
    return report

if __name__ == "__main__":
    analyzer = FilePathAnalyzer()
    results = analyzer.analyze_all_strategies()
    report = generate_file_path_report(results)
    
    with open('/tmp/file_path_analysis_report.md', 'w') as f:
        f.write(report)
    
    print(f"File path analysis complete. Report saved to /tmp/file_path_analysis_report.md")
    print(f"Found {len(results['path_issues'])} path issues across {results['strategies_with_issues']} strategies")
```

#### 2.2 Path Resolution Implementation
```python
# biomapper/core/infrastructure/path_resolver.py

import os
from pathlib import Path
from typing import Optional, Dict, Any
import re
import logging

class PathResolver:
    """Centralized path resolution with environment variable support."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.logger = logging.getLogger(__name__)
        
        # Default environment variables
        self.env_vars = {
            'DATA_DIR': os.getenv('BIOMAPPER_DATA_DIR', '/procedure/data/local_data'),
            'CACHE_DIR': os.getenv('BIOMAPPER_CACHE_DIR', '/tmp/biomapper/cache'),
            'OUTPUT_DIR': os.getenv('BIOMAPPER_OUTPUT_DIR', '/tmp/biomapper/output'),
            'CONFIG_DIR': os.getenv('BIOMAPPER_CONFIG_DIR', str(self.base_dir / 'configs')),
            'BASE_DIR': str(self.base_dir)
        }
        
        # Create directories if they don't exist
        self._ensure_directories_exist()
    
    def _ensure_directories_exist(self):
        """Create standard directories if they don't exist."""
        for var_name, path_str in self.env_vars.items():
            if var_name in ['DATA_DIR', 'CACHE_DIR', 'OUTPUT_DIR']:
                try:
                    Path(path_str).mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Ensured directory exists: {path_str}")
                except Exception as e:
                    self.logger.warning(f"Could not create directory {path_str}: {e}")
    
    def resolve_path(self, path_str: str, create_parent: bool = False) -> Optional[Path]:
        """
        Resolve a file path with variable substitution and fallback logic.
        
        Args:
            path_str: Path string potentially containing variables
            create_parent: Whether to create parent directory if it doesn't exist
            
        Returns:
            Resolved Path object or None if path cannot be resolved
        """
        if not path_str:
            return None
        
        # Substitute environment variables
        resolved_str = self.substitute_variables(path_str)
        
        # Try different resolution strategies
        resolved_path = None
        
        # Strategy 1: Absolute path
        if resolved_str.startswith('/'):
            candidate = Path(resolved_str)
            if candidate.exists():
                resolved_path = candidate
        
        # Strategy 2: Relative to base directory
        if not resolved_path:
            candidate = self.base_dir / resolved_str.lstrip('/')
            if candidate.exists():
                resolved_path = candidate
        
        # Strategy 3: Search in common directories
        if not resolved_path:
            resolved_path = self._search_common_directories(resolved_str)
        
        # Strategy 4: Use filename in data directory (last resort)
        if not resolved_path:
            filename = Path(resolved_str).name
            data_dir = Path(self.env_vars['DATA_DIR'])
            candidate = data_dir / filename
            if candidate.exists():
                resolved_path = candidate
                self.logger.warning(f"Using filename fallback: {path_str} -> {candidate}")
        
        # Create parent directory if requested
        if resolved_path and create_parent:
            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.warning(f"Could not create parent directory for {resolved_path}: {e}")
        
        if resolved_path:
            self.logger.debug(f"Resolved path: {path_str} -> {resolved_path}")
        else:
            self.logger.warning(f"Could not resolve path: {path_str}")
        
        return resolved_path
    
    def substitute_variables(self, path_str: str) -> str:
        """Substitute environment variables in path string."""
        
        # Handle ${VAR} syntax
        def replace_var(match):
            var_name = match.group(1)
            return self.env_vars.get(var_name, match.group(0))
        
        # Replace ${VAR} patterns
        substituted = re.sub(r'\$\{([^}]+)\}', replace_var, path_str)
        
        # Handle $VAR syntax (less common)
        substituted = re.sub(r'\$([A-Z_]+)', 
                           lambda m: self.env_vars.get(m.group(1), m.group(0)), 
                           substituted)
        
        return substituted
    
    def _search_common_directories(self, path_str: str) -> Optional[Path]:
        """Search for file in common directories."""
        
        filename = Path(path_str).name
        
        search_dirs = [
            Path(self.env_vars['DATA_DIR']),
            Path(self.env_vars['CONFIG_DIR']),
            self.base_dir / 'data',
            self.base_dir / 'configs' / 'data',
            Path('/procedure/data/local_data'),
            Path('/procedure/data/MAPPING_ONTOLOGIES'),
        ]
        
        # Add subdirectory search for ontology files
        if 'ontologies' in path_str.lower():
            search_dirs.extend([
                Path(self.env_vars['DATA_DIR']) / 'MAPPING_ONTOLOGIES',
                Path('/procedure/data/local_data/MAPPING_ONTOLOGIES')
            ])
        
        for search_dir in search_dirs:
            if search_dir.exists():
                # Direct file match
                candidate = search_dir / filename
                if candidate.exists():
                    return candidate
                
                # Recursive search for specific file types
                if filename.endswith(('.csv', '.tsv', '.json', '.yaml')):
                    for found_file in search_dir.rglob(filename):
                        return found_file
        
        return None
    
    def validate_file_access(self, path: Path, access_mode: str = 'r') -> bool:
        """Validate that file exists and is accessible."""
        if not path.exists():
            return False
        
        if access_mode == 'r':
            return os.access(path, os.R_OK)
        elif access_mode == 'w':
            return os.access(path.parent, os.W_OK)
        elif access_mode == 'rw':
            return os.access(path, os.R_OK) and os.access(path.parent, os.W_OK)
        
        return False
    
    def get_safe_output_path(self, requested_path: str) -> Path:
        """Get a safe output path, creating directories as needed."""
        
        resolved = self.substitute_variables(requested_path)
        
        # Ensure output goes to designated output directory
        if not resolved.startswith(self.env_vars['OUTPUT_DIR']):
            filename = Path(resolved).name
            resolved = str(Path(self.env_vars['OUTPUT_DIR']) / filename)
        
        output_path = Path(resolved)
        
        # Create parent directory
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Could not create output directory: {e}")
            # Fallback to temp directory
            import tempfile
            output_path = Path(tempfile.gettempdir()) / output_path.name
        
        return output_path

# Global path resolver instance
_path_resolver = None

def get_path_resolver() -> PathResolver:
    """Get global path resolver instance."""
    global _path_resolver
    if _path_resolver is None:
        _path_resolver = PathResolver()
    return _path_resolver

def resolve_path(path_str: str) -> Optional[Path]:
    """Convenience function to resolve a path."""
    return get_path_resolver().resolve_path(path_str)

def resolve_output_path(path_str: str) -> Path:
    """Convenience function to get safe output path."""
    return get_path_resolver().get_safe_output_path(path_str)
```

Would you like me to continue with the third prompt file for parameter resolution issues, or would you prefer to review these first two comprehensive investigation prompts?