# Week 4 Task 4B: Pattern Extraction

## Overview

This task analyzes the implemented actions across entity types to identify common patterns that could benefit from abstraction, while being careful not to force artificial patterns that reduce code clarity or maintainability.

## Prerequisites

Before starting pattern extraction:
- ✅ All entity-specific actions implemented and tested
- ✅ Integration testing completed (Task 4A)
- ✅ Performance characteristics understood

## Pattern Analysis Approach

### 1. Evidence-Based Pattern Identification

**DO NOT** start with preconceived notions of what patterns should exist. Instead:

1. **Empirical Analysis**: Compare actual implementations side-by-side
2. **Code Metrics**: Measure code duplication and complexity
3. **Developer Experience**: Identify pain points in current structure
4. **Performance Impact**: Understand if patterns would help or hurt performance

### 2. Pattern Analysis Categories

#### A. Implementation Patterns
Analyze actual code for recurring structures:

```python
# Example pattern analysis script
def analyze_action_patterns():
    """Analyze patterns across implemented actions."""
    
    patterns_found = {
        'parameter_models': [],
        'validation_patterns': [],
        'error_handling': [],
        'context_management': [],
        'result_formatting': [],
        'testing_patterns': []
    }
    
    # Analyze each entity directory
    for entity_path in ["entities/proteins", "entities/metabolites", "entities/chemistry"]:
        actions = discover_actions(entity_path)
        
        for action in actions:
            patterns_found['parameter_models'].append(analyze_param_model(action))
            patterns_found['validation_patterns'].append(analyze_validation(action))
            # ... continue analysis
    
    return patterns_found
```

#### B. Data Flow Patterns
Map how data flows through actions:

```python
# Example data flow analysis
def analyze_data_flows():
    """Map common data transformation patterns."""
    
    flows = {
        'input_patterns': {},  # How actions receive data
        'transformation_patterns': {},  # How data is transformed
        'output_patterns': {},  # How results are returned
        'error_propagation': {}  # How errors flow through system
    }
    
    # Protein actions data flow
    protein_flows = [
        "raw_data -> extract -> normalize -> bridge -> output",
        "xrefs_field -> parse_delimiters -> extract_patterns -> validate -> dedupe",
        "uniprot_ids -> normalize_case -> remove_versions -> validate_format"
    ]
    
    # Metabolite actions data flow  
    metabolite_flows = [
        "multi_id_field -> extract_by_type -> normalize -> bridge -> enrich",
        "hmdb_variants -> normalize_padding -> validate -> standardize",
        "source_ids -> cts_translate -> fallback -> cache -> score"
    ]
    
    # Chemistry actions data flow
    chemistry_flows = [
        "test_names -> normalize -> fuzzy_match -> score -> harmonize",
        "vendor_data -> detect_patterns -> normalize -> convert_units -> validate",
        "loinc_mixed -> extract_patterns -> validate_format -> standardize"
    ]
    
    return analyze_flow_commonalities(protein_flows, metabolite_flows, chemistry_flows)
```

#### C. Testing Patterns
Identify common test structures:

```python
def analyze_testing_patterns():
    """Find patterns in test implementations."""
    
    test_patterns = {
        'setup_patterns': [],
        'mock_data_patterns': [],
        'assertion_patterns': [],
        'error_testing_patterns': []
    }
    
    # Common setup across tests
    common_setups = [
        "Mock context with datasets",
        "Create parameter models",
        "Initialize action instances",
        "Set up temporary files"
    ]
    
    # Common assertions
    common_assertions = [
        "Assert success status",
        "Validate output dataset structure", 
        "Check statistics are populated",
        "Verify error handling"
    ]
    
    return test_patterns
```

### 3. Pattern Evaluation Criteria

For each identified pattern, evaluate:

#### A. Abstraction Value
```python
def evaluate_abstraction_value(pattern):
    """Evaluate if a pattern deserves abstraction."""
    
    criteria = {
        'duplication_score': 0,      # How much code is duplicated
        'complexity_reduction': 0,   # Would abstraction simplify?
        'maintenance_benefit': 0,    # Easier to maintain?
        'performance_impact': 0,     # Performance cost/benefit
        'readability_impact': 0      # Clearer or more confusing?
    }
    
    # Score each criterion (1-10)
    if pattern.lines_duplicated > 50:
        criteria['duplication_score'] = 8
    
    if pattern.reduces_cognitive_load:
        criteria['complexity_reduction'] = 7
        
    # ... continue evaluation
    
    total_score = sum(criteria.values())
    
    # Only recommend abstraction if score > 30
    return total_score > 30, criteria
```

#### B. Entity-Specific Differences
```python
def document_entity_differences():
    """Document why entity-specific approaches are beneficial."""
    
    differences = {
        'proteins': {
            'id_complexity': 'Moderate - mainly UniProt with some gene symbols',
            'validation_rules': 'Standard 6-character format + isoforms',
            'external_services': 'UniProt API, MyGene, BioMart',
            'data_sources': 'KG2c, SPOKE, HPA, QIN, UKBB',
            'unique_challenges': 'Isoform handling, version numbers'
        },
        'metabolites': {
            'id_complexity': 'High - HMDB, InChIKey, CHEBI, KEGG, PubChem',
            'validation_rules': 'Multiple format types, padding variations',
            'external_services': 'CTS, PubChem, MetaboLights',
            'data_sources': 'Arivale, UKBB NMR, Israeli10k',
            'unique_challenges': 'Multiple ID systems, chemical similarity'
        },
        'chemistry': {
            'id_complexity': 'Variable - LOINC, vendor codes, test names',
            'validation_rules': 'Format varies by vendor and system',
            'external_services': 'Minimal - mostly internal mapping',
            'data_sources': 'Clinical labs, biobanks, health systems',
            'unique_challenges': 'Fuzzy matching primary, vendor differences'
        }
    }
    
    return differences
```

### 4. Potential Pattern Categories

#### A. Base Class Patterns (High Abstraction)

**Evaluate:** Do we need common base classes?

```python
# Potential common base class
class EntityActionBase(TypedStrategyAction):
    """Common functionality across entity actions."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.stats = ActionStatistics()
    
    def _setup_logging(self):
        """Standard logging setup."""
        pass
    
    def _validate_context(self, context: Dict) -> None:
        """Standard context validation."""
        pass
    
    def _update_statistics(self, stats: Dict) -> None:
        """Standard statistics handling."""
        pass

# EVALUATION QUESTION:
# Does this base class provide enough value to justify the abstraction?
# Or does it make entity-specific actions harder to understand?
```

#### B. Utility Function Patterns (Medium Abstraction)

**Evaluate:** Should common utilities be shared?

```python
# Potential shared utilities
def validate_input_dataset(context: Dict, key: str) -> pd.DataFrame:
    """Validate and return input dataset."""
    if key not in context.get('datasets', {}):
        raise ValueError(f"Dataset '{key}' not found")
    return context['datasets'][key].copy()

def update_context_statistics(context: Dict, action_name: str, stats: Dict) -> None:
    """Standard way to update context statistics."""
    if 'statistics' not in context:
        context['statistics'] = {}
    context['statistics'][action_name] = stats

# EVALUATION QUESTION:
# Are these utilities used enough to justify shared code?
# Or is the overhead of imports and indirection not worth it?
```

#### C. Configuration Patterns (Low Abstraction)

**Evaluate:** Should configuration handling be standardized?

```python
# Potential configuration pattern
class ActionConfig:
    """Standard action configuration handling."""
    
    def __init__(self, params: BaseModel):
        self.params = params
        self.validation_errors = []
    
    def validate_required_fields(self) -> bool:
        """Standard field validation."""
        pass
    
    def load_external_config(self, file_path: str) -> Dict:
        """Standard external config loading."""
        pass

# EVALUATION QUESTION:
# Does this add value or just add layers of indirection?
```

### 5. Anti-Pattern Identification

Document patterns that should be avoided:

```python
def identify_anti_patterns():
    """Identify patterns that reduce maintainability."""
    
    anti_patterns = {
        'forced_inheritance': {
            'description': 'Creating base classes just for the sake of it',
            'example': 'ActionBase with only __init__ method',
            'why_bad': 'Adds complexity without benefit',
            'alternative': 'Composition or utility functions'
        },
        'generic_everything': {
            'description': 'Making every method generic',
            'example': 'extract_identifiers(data, type="any")',
            'why_bad': 'Loses type safety and clarity',
            'alternative': 'Entity-specific methods'
        },
        'over_abstraction': {
            'description': 'Abstracting patterns used only 2-3 times',
            'example': 'Creating framework for 3 similar functions',
            'why_bad': 'More complex than duplicated code',
            'alternative': 'Keep simple duplication'
        }
    }
    
    return anti_patterns
```

## Analysis Methodology

### Phase 1: Code Analysis

1. **Automated Analysis**
   ```bash
   # Find duplicated code
   poetry run duplication-detector biomapper/core/strategy_actions/entities/
   
   # Complexity metrics
   poetry run radon cc biomapper/core/strategy_actions/entities/
   
   # Test coverage patterns
   poetry run pytest --cov=biomapper.core.strategy_actions.entities --cov-report=html
   ```

2. **Manual Analysis**
   - Side-by-side comparison of implementations
   - Identify recurring code blocks
   - Map data flow patterns
   - Document design decisions

### Phase 2: Pattern Classification

```python
def classify_patterns():
    """Classify identified patterns by abstraction level."""
    
    classification = {
        'beneficial_abstraction': [
            # Patterns that clearly benefit from shared code
        ],
        'questionable_abstraction': [
            # Patterns that might benefit, needs deeper analysis
        ],
        'entity_specific': [
            # Patterns that should remain entity-specific
        ],
        'anti_patterns': [
            # Patterns that should be avoided
        ]
    }
    
    return classification
```

### Phase 3: Impact Analysis

For each potential abstraction, analyze:

1. **Complexity Impact**
   - Lines of code before/after
   - Cyclomatic complexity
   - Import complexity
   - Learning curve for new developers

2. **Maintenance Impact**
   - Easier to fix bugs?
   - Easier to add features?
   - Risk of breaking multiple things?

3. **Performance Impact**
   - Runtime performance
   - Memory usage
   - Import time

4. **Testing Impact**
   - Test coverage
   - Test complexity
   - Mock requirements

## Deliverables

### 1. Pattern Analysis Report

```markdown
# Pattern Analysis Report

## Executive Summary
- Patterns analyzed: X
- Recommended for abstraction: Y
- Entity-specific patterns: Z
- Anti-patterns identified: A

## Detailed Analysis

### Beneficial Abstractions
1. **Utility Functions for Dataset Validation**
   - Code duplication: 85 lines across 12 actions
   - Abstraction benefit: High
   - Implementation complexity: Low
   - Recommendation: Create shared utilities

### Entity-Specific Patterns
1. **ID Extraction Logic**
   - Different enough between entities to warrant separate implementations
   - Abstraction would reduce clarity
   - Recommendation: Keep separate

### Anti-Patterns Identified
1. **Over-Generic Parameter Models**
   - Would reduce type safety
   - Entity-specific models are clearer
```

### 2. Refactoring Recommendations

```python
# Only implement if pattern analysis shows clear benefit
class SharedUtilities:
    """Utilities that provide clear value across entity types."""
    
    @staticmethod
    def validate_input_dataset(context: Dict, key: str) -> pd.DataFrame:
        """Only if this is used in 5+ actions exactly the same way."""
        pass
    
    @staticmethod 
    def standard_error_handling(error: Exception, action_name: str) -> None:
        """Only if error handling is identical across actions."""
        pass
```

### 3. Documentation Updates

```markdown
# Entity-Specific Design Decisions

## Why Proteins, Metabolites, and Chemistry Are Separate

### Data Complexity Differences
- **Proteins**: Moderate complexity, standardized formats
- **Metabolites**: High complexity, multiple ID systems
- **Chemistry**: Variable complexity, fuzzy matching primary

### Service Integration Differences  
- **Proteins**: Well-defined APIs (UniProt, MyGene)
- **Metabolites**: Multiple services (CTS, PubChem, vendor APIs)
- **Chemistry**: Minimal external services, internal mappings

### Performance Requirements Differences
- **Proteins**: Exact matching focus, moderate datasets
- **Metabolites**: Complex bridging, large datasets
- **Chemistry**: Fuzzy matching focus, real-time requirements
```

## Success Criteria

### Analysis Completeness
- [ ] All implemented actions analyzed
- [ ] Code duplication quantified
- [ ] Performance patterns documented
- [ ] Testing patterns identified

### Pattern Quality
- [ ] Only beneficial patterns recommended for abstraction
- [ ] Entity-specific differences well documented
- [ ] Anti-patterns identified and documented
- [ ] Clear cost/benefit analysis for each pattern

### Implementation Quality
- [ ] Abstractions (if any) reduce complexity
- [ ] No forced inheritance hierarchies
- [ ] Type safety maintained or improved
- [ ] Performance not degraded

### Documentation Quality
- [ ] Design decisions explained
- [ ] Future developers can understand rationale
- [ ] Entity-specific benefits clearly articulated
- [ ] Migration path documented (if applicable)

## Decision Framework

Use this framework for each potential abstraction:

```python
def should_abstract_pattern(pattern):
    """Decision framework for abstraction."""
    
    # Required criteria (ALL must be true)
    required = [
        pattern.used_in_at_least(5),  # Used in 5+ places
        pattern.saves_at_least_lines(30),  # Saves 30+ lines
        pattern.identical_logic(),  # Logic is truly identical
        pattern.unlikely_to_diverge()  # Won't diverge in future
    ]
    
    # Beneficial criteria (MOST should be true)  
    beneficial = [
        pattern.reduces_complexity(),
        pattern.improves_maintainability(),
        pattern.maintains_type_safety(),
        pattern.no_performance_cost(),
        pattern.improves_testability()
    ]
    
    required_met = all(required)
    beneficial_score = sum(beneficial)
    
    return required_met and beneficial_score >= 3
```

Remember: **Entity-specific code is often clearer and more maintainable than forced abstractions. Only abstract patterns that provide clear, measurable benefits.**