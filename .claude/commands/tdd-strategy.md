# TDD Progressive Strategy Generator

Generate a Test-Driven Development progressive mapping strategy for BiOMapper.

USAGE: `/tdd-strategy <entity_type> <source_dataset> <target_dataset>`

## Example Usage
```
/tdd-strategy proteins arivale_proteins kg2c_proteins
/tdd-strategy metabolites nightingale_nmr hmdb_reference
```

## TDD Process (MANDATORY)

### 1. CLARIFY FIRST
Ask about:
- Expected coverage per stage (e.g., 60% → 75% → 85%)
- Critical vs nice-to-have outputs
- Performance requirements
- Integration needs (Google Drive, LLM analysis)

### 2. TESTS FIRST
Generate comprehensive test suite BEFORE implementation:
```python
# tests/strategies/test_${STRATEGY_NAME}.py
def test_stage_1_achieves_expected_coverage():
    """Test direct matching achieves target coverage."""
    assert coverage >= 0.60
    
def test_progressive_improvement_authentic():
    """Test stages improve without entity duplication."""
    assert no_duplicate_entities_across_stages()
    
def test_all_outputs_generated():
    """Test complete output generation."""
    assert all_required_files_exist()
```

### 3. IMPLEMENTATION
Only after tests are written and failing:
- Create strategy YAML
- Implement required actions
- Ensure tests pass

## Strategy Template
```yaml
name: ${entity_type}_${source}_to_${target}_progressive_v1.0
description: TDD-enforced progressive mapping

parameters:
  expected_stage_1_coverage: 0.60
  expected_stage_2_coverage: 0.75
  expected_stage_3_coverage: 0.85
  
validation:
  pre_execution:
    - parameter_substitution_test
    - import_path_verification
  post_execution:
    - authentic_coverage_calculation
    - all_outputs_generated

steps:
  - name: stage_1_direct_match
    # ...
```

**CRITICAL**: Tests must exist and fail before implementation begins.