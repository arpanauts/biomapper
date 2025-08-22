# Progressive Mapping Development Guide with Test-Driven Development

## A TDD-First Collaborative Framework for Biological Data Harmonization with Claude Code Agents

### Table of Contents
1. [Progressive Mapping Framework Overview](#progressive-mapping-framework-overview)
2. [Test-Driven Development Philosophy](#test-driven-development-philosophy)
3. [Standard Progressive Stages by Entity Type](#standard-progressive-stages-by-entity-type)
4. [TDD-Based Collaborative Action Development Process](#tdd-based-collaborative-action-development-process)
5. [Standard Action Types for Progressive Mapping](#standard-action-types-for-progressive-mapping)
6. [TDD Development Workflow Template](#tdd-development-workflow-template)
7. [Progressive Statistics Standard](#progressive-statistics-standard)
8. [Testing Progressive Strategies](#testing-progressive-strategies)
9. [TDD Collaboration Checkpoints](#tdd-collaboration-checkpoints)

---

## Progressive Mapping Framework Overview

The **Progressive Mapping Framework** is biomapper's standardized approach to biological data harmonization, designed to maximize mapping coverage through staged, incremental improvements.

### Core Philosophy

- **Waterfall Approach**: Each stage builds upon previous results, attempting to map only the remaining unmapped items
- **Cumulative Improvement**: Statistics track both stage-specific and cumulative performance
- **Confidence Scoring**: Each mapping has an associated confidence score based on the method used
- **Entity Flexibility**: The framework adapts to different biological data types while maintaining consistent patterns

### Universal Pattern

```
Initial Dataset (100%)
    ↓
Stage 1: High-confidence direct matching (e.g., 65%)
    ↓ (35% remaining)
Stage 2: Extended matching techniques (e.g., +10% = 75% cumulative)
    ↓ (25% remaining)
Stage 3: Advanced/fuzzy matching (e.g., +10% = 85% cumulative)
    ↓ (15% remaining)
Final: Unmapped items documented for manual review
```

---

## Test-Driven Development Philosophy

### Core TDD Principles for Progressive Mapping

The Progressive Mapping Framework **REQUIRES** Test-Driven Development (TDD) as its foundation. Every action, every stage, and every enhancement must follow the RED-GREEN-REFACTOR cycle.

### The TDD Cycle for Progressive Actions

```
RED Phase (Write Failing Tests First)
    ↓
    - Define expected coverage for each stage
    - Write tests for confidence scores
    - Create tests for unmapped pattern handling
    - Set performance benchmarks in tests
    ↓
GREEN Phase (Minimal Implementation)
    ↓
    - Implement just enough to pass tests
    - No premature optimization
    - Focus on correctness over elegance
    ↓
REFACTOR Phase (Improve While Green)
    ↓
    - Optimize algorithms
    - Extract shared components
    - Enhance error handling
    - Maintain all tests passing
```

### TDD Rules for Progressive Mapping

1. **NO CODE WITHOUT TESTS**: Never write implementation code before tests
2. **PROGRESSIVE TEST COVERAGE**: Each stage must have independent test coverage
3. **CUMULATIVE VALIDATION**: Tests must verify cumulative improvements
4. **PERFORMANCE ASSERTIONS**: Include execution time and memory tests
5. **EDGE CASE PRIORITY**: Write edge case tests before happy path tests

### Progressive TDD Pattern

```python
# ALWAYS START WITH TESTS for each progressive stage

class TestProgressiveProteinMapping:
    """TDD tests for progressive protein mapping pipeline."""
    
    def test_stage_1_coverage_expectation(self):
        """Stage 1 MUST achieve 65% coverage with confidence 1.0"""
        # This test MUST be written BEFORE implementing Stage 1
        test_data = generate_test_proteins(100)
        result = execute_stage_1_direct_match(test_data)
        
        assert result.coverage >= 0.65, "Stage 1 must achieve 65% minimum"
        assert result.confidence == 1.0, "Direct matches must have perfect confidence"
        assert result.execution_time < 1.0, "Stage 1 must complete in <1 second"
    
    def test_stage_2_incremental_improvement(self):
        """Stage 2 MUST improve on Stage 1's unmapped items"""
        # This test MUST exist BEFORE Stage 2 implementation
        stage_1_result = execute_stage_1_direct_match(test_data)
        unmapped_from_stage_1 = stage_1_result.unmapped
        
        stage_2_result = execute_stage_2_composite(unmapped_from_stage_1)
        
        assert stage_2_result.new_matches > 0, "Stage 2 must find new matches"
        assert stage_2_result.confidence >= 0.95, "Composite matches need high confidence"
        assert stage_2_result.only_processes_unmapped, "Stage 2 must not reprocess Stage 1 matches"
    
    def test_progressive_cumulative_tracking(self):
        """Progressive stats MUST track cumulative improvements"""
        # Write this test FIRST to define statistics structure
        pipeline_result = execute_full_progressive_pipeline(test_data)
        
        assert pipeline_result.stats["stages"][1]["cumulative_matched"] > 0
        assert pipeline_result.stats["stages"][2]["cumulative_matched"] >= \
               pipeline_result.stats["stages"][1]["cumulative_matched"]
        assert pipeline_result.stats["stages"][3]["cumulative_matched"] >= \
               pipeline_result.stats["stages"][2]["cumulative_matched"]
```

### TDD Test Hierarchy for Progressive Mapping

```
1. Expectation Tests (Write First)
   ├── Coverage expectations per stage
   ├── Confidence score requirements
   ├── Performance benchmarks
   └── Statistics structure validation

2. Behavior Tests (Write Second)
   ├── Stage isolation (no reprocessing)
   ├── Incremental improvement validation
   ├── Unmapped pattern capture
   └── Error handling per stage

3. Integration Tests (Write Third)
   ├── Full pipeline execution
   ├── Cumulative statistics tracking
   ├── Cross-stage data flow
   └── Final reporting accuracy

4. Edge Case Tests (Write Throughout)
   ├── Empty datasets
   ├── Single item datasets
   ├── Malformed identifiers
   ├── API failures/timeouts
   └── Memory constraints
```

---

## Standard Progressive Stages by Entity Type

### Proteins
**Target Coverage: ~80%**

| Stage | Method | Expected Coverage | Confidence |
|-------|--------|------------------|------------|
| 1 | Direct UniProt matching | 65% | 1.0 |
| 2 | Composite identifier parsing | +0-5% (65-70% cumulative) | 0.95 |
| 3 | Historical/deprecated ID resolution | +10-15% (75-80% cumulative) | 0.85 |

**Key Challenges:**
- Isoform handling (P12345-1)
- Version numbers (P12345.2)
- Multiple identifiers per entry

### Metabolites
**Target Coverage: 85%+**

| Stage | Method | Expected Coverage | Confidence |
|-------|--------|------------------|------------|
| 1 | Direct HMDB/InChIKey matching | 40-50% | 1.0 |
| 2 | RampDB cross-reference expansion | +15-20% (55-70% cumulative) | 0.9 |
| 3 | HMDB FastEmbed VectorRAG + LLM | +10-15% (70-85% cumulative) | 0.85 |
| 4 | Semantic similarity matching | +5% (75-90% cumulative) | 0.75 |

**Key Challenges:**
- Synonym variations
- Structural isomers
- Vendor-specific naming

### Chemistry/Clinical Tests
**Target Coverage: ~70%**

| Stage | Method | Expected Coverage | Confidence |
|-------|--------|------------------|------------|
| 1 | Direct LOINC code matching | 30-40% | 1.0 |
| 2 | Fuzzy test name matching | +20-25% (50-65% cumulative) | 0.85 |
| 3 | Vendor-specific harmonization | +5-10% (60-75% cumulative) | 0.8 |

**Key Challenges:**
- High naming variability
- Vendor-specific formats
- Unit conversions

---

## TDD-Based Collaborative Action Development Process

### Pre-Implementation Test Definition Framework

When developing a new action type, Claude Code agents should engage in TDD-focused structured dialogue with users:

#### 1. Test-First Purpose & Scope Definition

**Claude asks:**
```
"Before we write ANY code for [ACTION_NAME], let's define the tests:

1. What specific behavior should we test for?
   - Expected coverage percentage?
   - Confidence score requirements?
   - Performance benchmarks?

2. What edge cases must we handle?
   - Empty datasets?
   - Malformed identifiers?
   - API failures?

3. How will we know the action is successful?
   - What assertions define success?
   - What metrics prove improvement?
   - What validates correctness?"
```

**User provides:**
- Specific test scenarios and expected outcomes
- Performance requirements as test assertions
- Edge cases that must pass

**Claude responds:**
```python
# I'll write these tests FIRST:
def test_action_achieves_expected_coverage():
    """Test that action achieves X% coverage as specified."""
    assert result.coverage >= 0.X

def test_action_handles_edge_cases():
    """Test edge case handling."""
    assert handles_empty_dataset_gracefully()
    assert handles_malformed_ids_correctly()

def test_action_meets_performance_requirements():
    """Test performance benchmarks."""
    assert execution_time < X_seconds
    assert memory_usage < X_MB
```

#### 2. TDD Input/Output Test Specifications

**Claude asks:**
```
"Let's write tests for the input/output interface:

1. What should the tests validate about inputs?
   - Required columns present?
   - Data type correctness?
   - Value range validation?

2. What should the tests assert about outputs?
   - New columns added correctly?
   - Original data preserved?
   - Statistics updated properly?

3. What error conditions should tests verify?
   - Missing required fields?
   - Invalid data types?
   - Null/NaN handling?"
```

**User provides:**
- Test cases for valid and invalid inputs
- Expected output structure assertions
- Error scenario expectations

**Claude creates test suite:**
```python
class TestActionInputOutput:
    def test_validates_required_columns(self):
        """Test fails if required columns missing."""
        with pytest.raises(ValidationError):
            action.execute(missing_column_data)
    
    def test_preserves_original_data(self):
        """Test that original columns remain unchanged."""
        result = action.execute(test_data)
        assert_dataframes_equal(result[original_cols], test_data[original_cols])
    
    def test_adds_expected_output_columns(self):
        """Test that new columns are added correctly."""
        result = action.execute(test_data)
        assert "confidence_score" in result.columns
        assert "match_type" in result.columns
```

#### 3. TDD Behavioral Test Decisions

**Claude asks:**
```
"Now let's define behavioral tests:

1. How should we test confidence scoring?
   - Test cases for each confidence tier?
   - Boundary condition tests?
   - Score distribution validation?

2. How should we test matching logic?
   - Known match/no-match pairs?
   - Ambiguous case handling?
   - Multiple match scenarios?

3. How should we test progressive improvement?
   - Verify only unmapped items processed?
   - Confirm no regression on previous matches?
   - Validate cumulative statistics?"
```

**User provides:**
- Test data with known outcomes
- Confidence score expectations
- Progressive improvement criteria

#### 4. TDD Implementation Approach

**Claude proposes:**
```
"Based on TDD methodology, here's our development approach:

RED Phase (Immediate - Write All Tests First):
- Write comprehensive test suite
- Define all expected behaviors
- Include edge cases and performance tests
- Verify ALL tests fail (proving they're testing something)

GREEN Phase - Stub Implementation (30 minutes):
- Minimal code to make basic tests pass
- Mock external dependencies
- Return hardcoded successful results
- Get to "all tests green" quickly

GREEN Phase - Basic Implementation (Next session):
- Replace mocks with real logic
- Implement core algorithm
- Handle common cases
- Maintain all tests passing

REFACTOR Phase - Full Implementation (Final session):
- Optimize performance
- Add advanced features
- Enhance error handling
- Extract reusable components
- Keep all tests green

Shall we start by writing the complete test suite?"
```

### TDD Collaboration Pattern

```python
# STEP 1: Claude and User collaborate to write tests FIRST

# Claude: "Let's define what success looks like in test form:"
def test_progressive_stage_success_criteria():
    """Define success criteria as executable tests."""
    
    # User: "Stage 1 should achieve 65% coverage"
    assert stage_1_result.coverage >= 0.65
    
    # User: "Stage 2 should add 10% more coverage"
    assert stage_2_result.cumulative_coverage >= 0.75
    
    # User: "Full pipeline should complete in under 1 minute"
    assert pipeline_result.total_time < 60

# STEP 2: Run tests to verify they fail
# Claude: "Running tests to confirm RED phase..."
# Expected: All tests fail (this is good!)

# STEP 3: Write minimal implementation
# Claude: "Now I'll write just enough code to pass..."

# STEP 4: Verify tests pass
# Claude: "Tests are GREEN! Now we can refactor safely."
```

---

## Standard Action Types for Progressive Mapping

### Visualization Actions

#### GENERATE_MAPPING_VISUALIZATIONS
**Purpose**: Create visual representations of mapping performance

**Key Decisions to Discuss:**
- Chart types (waterfall, confidence distribution, pie charts)
- Statistical summaries to include
- Export formats (PNG, SVG, PDF)
- Color schemes for different match types

**Standard Outputs:**
- Waterfall chart showing progressive improvements
- Confidence score distribution histogram
- Match type breakdown pie chart
- Summary statistics TSV

### Analysis Actions

#### GENERATE_LLM_ANALYSIS
**Purpose**: Provide intelligent insights and recommendations

**Key Decisions to Discuss:**
- Template-based vs API-based generation
- Analysis depth (summary, detailed, recommendations)
- LLM provider choice (Claude, GPT, local)
- Output format (markdown, HTML, JSON)

**Standard Outputs:**
- Executive summary
- Stage-by-stage analysis
- Unmapped pattern identification
- Improvement recommendations
- Mermaid flowchart of mapping process

### Statistics Actions

#### CALCULATE_PROGRESSIVE_STATS
**Purpose**: Track detailed metrics across stages

**Key Decisions to Discuss:**
- Metrics to track per stage
- Aggregation methods
- Performance benchmarks
- Export formats

**Standard Metrics:**
- Total processed
- Stage-specific matches
- Cumulative matches
- Confidence distributions
- Processing times
- Memory usage

---

## TDD Development Workflow Template

### TDD Session Structure

```markdown
## TDD Action Development Session: [ACTION_NAME]
Date: [YYYY-MM-DD]
Entity Type: [Proteins/Metabolites/Chemistry]
Stage: [1/2/3/etc]
TDD Phase: [RED/GREEN/REFACTOR]

### 1. Test Requirements Definition (15-20 minutes) - RED PHASE START

**Claude**: "Before writing ANY code, let's define our tests for [ACTION_NAME]. I'll help you write comprehensive tests that define exactly what this action should do."

**Test Categories to Define:**
1. Coverage expectations (what % improvement?)
2. Confidence score requirements
3. Performance benchmarks
4. Edge case handling
5. Progressive improvement validation

**Claude writes test file:**
```python
# tests/test_[action_name].py
# WRITTEN BEFORE ANY IMPLEMENTATION CODE

import pytest
from biomapper.testing.base import ProgressiveActionTestBase

class Test[ActionName](ProgressiveActionTestBase):
    
    @pytest.fixture
    def expected_coverage(self):
        """Define expected coverage for this stage."""
        return 0.65  # User-specified expectation
    
    def test_achieves_expected_coverage(self, test_data, expected_coverage):
        """Test that action achieves expected coverage."""
        result = execute_action(test_data)
        assert result.coverage >= expected_coverage
        assert result.confidence_scores.mean() >= 0.95
    
    def test_only_processes_unmapped_items(self, staged_data):
        """Test that action only processes unmapped items from previous stage."""
        result = execute_action(staged_data.unmapped_only)
        assert result.did_not_reprocess_mapped_items()
    
    def test_handles_empty_dataset(self):
        """Test graceful handling of empty input."""
        result = execute_action(pd.DataFrame())
        assert result.success == True
        assert result.matched_count == 0
    
    def test_performance_requirements(self, large_test_data):
        """Test that action meets performance requirements."""
        with Timer() as timer:
            result = execute_action(large_test_data)
        
        assert timer.elapsed < 5.0  # Must complete in 5 seconds
        assert peak_memory_usage() < 500_000_000  # Less than 500MB
```

**User confirms test expectations**

### 2. Run Tests to Confirm RED Phase (5 minutes)

**Claude**: "Let's run our tests to confirm they all fail (RED phase):"

```bash
poetry run pytest tests/test_[action_name].py -xvs
```

**Expected Output:**
```
FAILED test_achieves_expected_coverage - AttributeError: execute_action not found
FAILED test_only_processes_unmapped_items - AttributeError: execute_action not found
FAILED test_handles_empty_dataset - AttributeError: execute_action not found
FAILED test_performance_requirements - AttributeError: execute_action not found

4 failed - This is perfect! RED phase confirmed.
```

### 3. Minimal Implementation Plan (5 minutes) - GREEN PHASE START

**Claude**: "Now I'll write JUST enough code to make tests pass:

```python
# Step 1: Stub that passes basic tests
def execute_action(data):
    return ActionResult(
        coverage=0.65,  # Hardcoded to pass test
        confidence_scores=pd.Series([0.95]),
        success=True,
        matched_count=len(data) * 0.65
    )

# Step 2: Basic implementation (next iteration)
# Step 3: Full implementation (final iteration)
```

Which tests should we make pass first?"

### 4. Test-Driven Development (20-30 minutes)

**Development Cycle:**
```
For each test:
1. Run single test → See it fail
2. Write minimal code → Make it pass
3. Run all tests → Ensure no regression
4. Refactor if needed → Keep tests green
```

**Claude's TDD approach:**
```python
# Iteration 1: Make test_handles_empty_dataset pass
if data.empty:
    return ActionResult(success=True, matched_count=0)

# Run: poetry run pytest tests/test_[action_name].py::test_handles_empty_dataset
# ✓ PASSED

# Iteration 2: Make test_achieves_expected_coverage pass
matches = identify_matches(data)
coverage = len(matches) / len(data)
return ActionResult(coverage=coverage, ...)

# Run: poetry run pytest tests/test_[action_name].py::test_achieves_expected_coverage
# ✓ PASSED

# Continue for each test...
```

### 5. Continuous Test Validation (Throughout)

**Claude**: "After each code change, I'm running tests:

```bash
# Run specific test being worked on
poetry run pytest tests/test_[action_name].py::test_specific -xvs

# Run all tests for this action
poetry run pytest tests/test_[action_name].py -xvs

# Run integration tests if applicable
poetry run pytest tests/integration/ -xvs
```

Current test status:
- ✓ test_handles_empty_dataset (PASSING)
- ✓ test_achieves_expected_coverage (PASSING)
- ⚠ test_only_processes_unmapped_items (IN PROGRESS)
- ✗ test_performance_requirements (NOT YET IMPLEMENTED)"

### 6. REFACTOR Phase Planning (5 minutes)

**Claude**: "All tests are GREEN! Now we can safely refactor:

Refactoring opportunities (with tests protecting us):
- [ ] Extract matching algorithm to shared component
- [ ] Optimize performance bottlenecks
- [ ] Improve error messages
- [ ] Add comprehensive logging
- [ ] Extract magic numbers to constants

After each refactor:
1. Run tests → Confirm still GREEN
2. Measure performance → Verify improvements
3. Check code coverage → Ensure comprehensive

Next session focus:
- Replace stub implementations with real logic
- Add more edge case tests
- Performance optimization
```

### 7. TDD Metrics Review (5 minutes)

**Session Metrics:**
- Tests Written: [X]
- Tests Passing: [Y/X]
- Code Coverage: [Z%]
- TDD Cycles Completed: [N]
- Performance Benchmarks Met: [Yes/No]

**TDD Success Criteria:**
✓ All tests written before implementation
✓ RED phase confirmed before coding
✓ Incremental GREEN achievements
✓ No test regressions during development
✓ REFACTOR only with GREEN tests
```

---

## Progressive Statistics Standard

### Required Context Structure

All progressive mapping strategies must maintain this statistics structure:

```python
context["progressive_stats"] = {
    # Overall metrics
    "total_processed": 10000,
    "strategy_name": "prot_arv_to_kg2c_progressive",
    "entity_type": "protein",
    "start_time": "2025-01-18T10:00:00",
    "end_time": "2025-01-18T10:00:13",
    
    # Stage-by-stage tracking
    "stages": {
        1: {
            "name": "direct_match",
            "method": "Direct UniProt ID matching",
            "matched": 6500,
            "new_matches": 6500,  # Same as matched for stage 1
            "cumulative_matched": 6500,
            "confidence_avg": 1.0,
            "confidence_min": 1.0,
            "confidence_max": 1.0,
            "computation_time": "0.5s",
            "memory_peak_mb": 125.3
        },
        2: {
            "name": "composite_expansion",
            "method": "Composite identifier parsing",
            "matched": 0,  # No new matches in this example
            "new_matches": 0,
            "cumulative_matched": 6500,  # Same as stage 1
            "confidence_avg": 0.95,
            "confidence_min": 0.95,
            "confidence_max": 0.95,
            "computation_time": "0.2s",
            "memory_peak_mb": 130.1
        },
        3: {
            "name": "historical_resolution",
            "method": "Historical/deprecated ID lookup",
            "matched": 1500,
            "new_matches": 1500,
            "cumulative_matched": 8000,  # 6500 + 1500
            "confidence_avg": 0.85,
            "confidence_min": 0.8,
            "confidence_max": 0.9,
            "computation_time": "12.3s",
            "memory_peak_mb": 245.7
        }
    },
    
    # Final summary
    "final_match_rate": 0.80,  # 8000/10000
    "total_matched": 8000,
    "total_unmapped": 2000,
    "total_time": "13.0s",
    
    # Match type distribution
    "match_type_distribution": {
        "direct": 6500,
        "composite": 0,
        "historical": 1500,
        "unmapped": 2000
    },
    
    # Unmapped analysis
    "unmapped_analysis": {
        "patterns_identified": [
            "Obsolete identifiers (800)",
            "Non-standard formats (600)",
            "Missing from reference (600)"
        ],
        "recommendations": [
            "Update reference database",
            "Add regex patterns for non-standard formats",
            "Consider manual curation for obsolete IDs"
        ]
    }
}
```

### Tracking Implementation

Each stage should update statistics:

```python
# In each action's execute method
def update_stage_stats(context, stage_num, stage_name, new_matches):
    if "progressive_stats" not in context:
        context["progressive_stats"] = {"stages": {}}
    
    prev_cumulative = 0
    if stage_num > 1 and (stage_num - 1) in context["progressive_stats"]["stages"]:
        prev_cumulative = context["progressive_stats"]["stages"][stage_num - 1]["cumulative_matched"]
    
    context["progressive_stats"]["stages"][stage_num] = {
        "name": stage_name,
        "matched": new_matches,
        "new_matches": new_matches,
        "cumulative_matched": prev_cumulative + new_matches,
        # ... other metrics
    }
```

---

## Testing Progressive Strategies with TDD

### TDD-First Three-Level Testing Framework

#### TDD Principle: Write Tests Before Each Level

```python
# MANDATORY: Write these test structures BEFORE implementing ANY stage

class TDDProgressiveTestStructure:
    """Define test structure before implementation."""
    
    def write_tests_first(self):
        """This method MUST be called before writing any action code."""
        self.write_level_1_unit_tests()
        self.write_level_2_integration_tests()
        self.write_level_3_production_tests()
        self.verify_all_tests_fail()  # Confirm RED phase
```

#### Level 1: TDD Unit Tests (Per Stage)
**TDD Rule**: Write these tests BEFORE implementing the stage
**Duration**: <1 second per test
**Data Size**: 5-10 records
**Focus**: Individual stage functionality

```python
# WRITE THIS TEST FIRST (before stage implementation)
class TestStage1DirectMatch:
    """TDD tests for Stage 1 - written BEFORE implementation."""
    
    def test_expected_coverage_stage_1(self):
        """Define Stage 1 coverage expectation."""
        # This test MUST fail initially (RED phase)
        test_data = generate_test_proteins(10)
        result = execute_stage_1_direct_match(test_data)
        
        # Assertions that define success
        assert result.matched_count >= 6  # Expect 60%+ matches
        assert result.confidence_scores.all() == 1.0  # Perfect confidence
        assert result.execution_time < 0.1  # Must be fast
        
    def test_stage_1_identifier_patterns(self):
        """Test specific identifier patterns."""
        # Define expected behavior for known patterns
        test_cases = [
            ("P12345", True, 1.0),  # Standard UniProt
            ("Q6EMK4", True, 1.0),  # Edge case protein
            ("INVALID", False, 0.0),  # Invalid format
            ("", False, 0.0),  # Empty string
        ]
        
        for identifier, should_match, expected_confidence in test_cases:
            result = stage_1_match_single(identifier)
            assert result.matched == should_match
            assert result.confidence == expected_confidence
    
    def test_stage_1_only_direct_matches(self):
        """Ensure Stage 1 only performs direct matching."""
        # Test that fuzzy/semantic matching is NOT attempted
        similar_but_not_exact = "P12345-1"  # Isoform
        result = stage_1_match_single(similar_but_not_exact)
        assert result.matched == False  # Stage 1 should not match isoforms
```

#### Level 2: TDD Integration Tests (Full Pipeline)
**TDD Rule**: Write these tests BEFORE connecting stages
**Duration**: <10 seconds
**Data Size**: 100-1000 records
**Focus**: Stage progression and statistics

```python
# WRITE THIS TEST FIRST (before pipeline integration)
class TestProgressivePipelineIntegration:
    """TDD tests for pipeline integration - written BEFORE connecting stages."""
    
    def test_progressive_improvement_pattern(self):
        """Define expected progressive improvement."""
        # This test MUST fail initially
        test_data = generate_test_proteins(1000)
        
        # Define expected behavior BEFORE implementation
        stage_1_result = execute_stage_1(test_data)
        stage_2_result = execute_stage_2(stage_1_result.unmapped)
        stage_3_result = execute_stage_3(stage_2_result.unmapped)
        
        # Progressive improvement assertions
        assert stage_1_result.coverage >= 0.65
        assert stage_2_result.new_matches > 0  # Must find some new matches
        assert stage_3_result.new_matches > 0  # Must find more matches
        
        # Cumulative improvement
        total_coverage = (
            stage_1_result.matched_count +
            stage_2_result.matched_count +
            stage_3_result.matched_count
        ) / len(test_data)
        assert total_coverage >= 0.75  # Target 75%+ total
    
    def test_no_duplicate_processing(self):
        """Ensure items are not processed multiple times."""
        # Critical test to prevent reprocessing
        test_data = generate_test_proteins(100)
        pipeline_result = execute_progressive_pipeline(test_data)
        
        # Count total processing attempts
        total_processed = sum(
            stage["items_processed"] 
            for stage in pipeline_result.stages.values()
        )
        assert total_processed == len(test_data)  # Each item processed once
    
    def test_statistics_accumulation(self):
        """Test that statistics accumulate correctly."""
        # Define expected statistics structure
        result = execute_progressive_pipeline(test_data)
        stats = result.context["progressive_stats"]
        
        # Validate statistics structure
        assert stats["stages"][1]["cumulative_matched"] > 0
        assert stats["stages"][2]["cumulative_matched"] >= \
               stats["stages"][1]["cumulative_matched"]
        assert stats["stages"][3]["cumulative_matched"] >= \
               stats["stages"][2]["cumulative_matched"]
        
        # Validate final statistics
        assert stats["final_match_rate"] == \
               stats["total_matched"] / stats["total_processed"]
```

#### Level 3: TDD Production Subset Tests
**TDD Rule**: Write these tests with real data patterns FIRST
**Duration**: <60 seconds
**Data Size**: 5000+ records
**Focus**: Real-world performance and edge cases

```python
# WRITE THIS TEST FIRST (using production data patterns)
class TestProgressiveProductionScenarios:
    """TDD tests for production scenarios - written with real patterns."""
    
    @pytest.fixture
    def production_edge_cases(self):
        """Define known production edge cases upfront."""
        return [
            "Q6EMK4",  # Known problematic identifier
            "P12345-1",  # Isoform
            "O00533.2",  # Version number
            "UniProtKB:P42336",  # With prefix
            None,  # Missing value
            "",  # Empty string
        ]
    
    def test_production_coverage_targets(self):
        """Test against production coverage expectations."""
        # Use real production data subset
        prod_data = load_production_subset("arivale_proteins", 5000)
        result = execute_progressive_pipeline(prod_data)
        
        # Production-calibrated expectations
        assert result.final_match_rate >= 0.78  # Real-world target
        assert result.stages[1]["coverage"] >= 0.63  # Stage 1 reality
        assert result.stages[2]["coverage"] >= 0.05  # Stage 2 increment
        assert result.stages[3]["coverage"] >= 0.10  # Stage 3 increment
    
    def test_handles_all_edge_cases(self, production_edge_cases):
        """Ensure all known edge cases are handled."""
        for edge_case in production_edge_cases:
            result = execute_progressive_pipeline([{"id": edge_case}])
            assert result.success == True  # Must not crash
            assert result.error_count == 0  # Must handle gracefully
    
    def test_production_performance_requirements(self):
        """Test real-world performance constraints."""
        prod_data = load_production_subset("large_dataset", 10000)
        
        with Timer() as timer:
            result = execute_progressive_pipeline(prod_data)
        
        # Production performance requirements
        assert timer.elapsed < 60  # Must complete in 1 minute
        assert peak_memory_usage() < 1_000_000_000  # Less than 1GB
        assert result.stages[1]["execution_time"] < 1.0  # Stage 1 fast
        assert result.stages[3]["execution_time"] < 30.0  # Stage 3 reasonable
```

### TDD Performance Benchmarking

Define performance tests BEFORE optimization:

```python
class TDDProgressivePerformanceTest:
    """Performance tests written BEFORE optimization."""
    
    def test_stage_performance_requirements(self):
        """Define performance requirements upfront."""
        # These tests MUST be written first
        performance_requirements = {
            1: {"max_time": 1.0, "max_memory_mb": 100},
            2: {"max_time": 5.0, "max_memory_mb": 200},
            3: {"max_time": 30.0, "max_memory_mb": 500},
        }
        
        for stage_num, requirements in performance_requirements.items():
            with PerformanceMonitor() as monitor:
                result = execute_stage(stage_num, test_data)
            
            assert monitor.execution_time < requirements["max_time"]
            assert monitor.peak_memory_mb < requirements["max_memory_mb"]
            assert result.matches_per_second > 1000  # Throughput requirement
    
    def test_scalability_requirements(self):
        """Test that performance scales linearly."""
        # Test with increasing data sizes
        for size in [100, 1000, 10000]:
            with Timer() as timer:
                execute_progressive_pipeline(generate_test_data(size))
            
            time_per_record = timer.elapsed / size
            assert time_per_record < 0.01  # Max 10ms per record
```

### TDD Test Execution Strategy

```bash
# 1. Write all tests first (RED phase)
poetry run pytest tests/ --collect-only  # Verify tests exist

# 2. Run tests to confirm failures
poetry run pytest tests/ -xvs  # All should fail (good!)

# 3. Implement incrementally (GREEN phase)
# After each small implementation:
poetry run pytest tests/test_specific.py -xvs

# 4. Run full test suite frequently
poetry run pytest tests/ --tb=short

# 5. Check test coverage
poetry run pytest --cov=biomapper --cov-report=html

# 6. Run performance tests
poetry run pytest tests/performance/ --benchmark-only

# 7. Continuous integration
poetry run pytest tests/ --junit-xml=report.xml
```

---

## TDD Collaboration Checkpoints

### Before ANY Implementation (TDD RED Phase)

✅ **TDD Test Definition Checklist:**
- [ ] **ALL tests written BEFORE code** (mandatory)
- [ ] Coverage expectation tests defined for each stage
- [ ] Confidence score requirement tests written
- [ ] Performance benchmark tests created
- [ ] Edge case tests documented
- [ ] Integration tests for stage transitions planned
- [ ] All tests confirmed to FAIL (RED phase verified)

✅ **Test Coverage Planning:**
- [ ] Unit tests for each stage (Level 1)
- [ ] Integration tests for pipeline (Level 2)
- [ ] Production subset tests (Level 3)
- [ ] Performance tests defined
- [ ] Memory usage tests included

### During TDD Development (GREEN Phase)

✅ **TDD Implementation Checkpoints:**

**After Writing Each Test (RED):**
- [ ] Test fails as expected
- [ ] Failure message is informative
- [ ] Test validates correct behavior
- [ ] Test is independent of other tests

**After Minimal Implementation (GREEN):**
- [ ] Specific test now passes
- [ ] No other tests broken (no regression)
- [ ] Implementation is minimal (no gold-plating)
- [ ] Code only does what test requires

**After Each Refactor (REFACTOR):**
- [ ] All tests still pass
- [ ] Performance improved or code cleaner
- [ ] No new functionality added
- [ ] Test coverage maintained or improved

### TDD Cycle Tracking

✅ **Per-Session TDD Metrics:**
```
Session: [Date/Time]
Tests Written First: [X]
Tests Passing: [Y/X]
TDD Cycles Completed: [N]
Code Coverage: [Z%]
RED→GREEN Time: [Minutes]
Refactoring Count: [R]
```

### After TDD Implementation

✅ **TDD Validation Checklist:**
- [ ] All tests written before code (verified via git history)
- [ ] 100% of defined tests passing
- [ ] Code coverage >= 85%
- [ ] Performance tests all passing
- [ ] Edge cases all handled
- [ ] No untested code paths

✅ **TDD Quality Metrics:**
- [ ] Test-to-code ratio > 1:1
- [ ] All assertions meaningful (no trivial tests)
- [ ] Tests document behavior clearly
- [ ] Tests serve as usage examples
- [ ] Tests catch regressions effectively

### TDD Continuous Improvement

**TDD Retrospective Questions:**
1. Were all tests truly written first? Any exceptions?
2. Which tests caught the most bugs during development?
3. Are there missing test scenarios discovered during implementation?
4. How many TDD cycles were completed per feature?
5. What refactoring opportunities were enabled by tests?

**Test Evolution Tracking:**
```python
# Track how tests evolved during development
class TDDEvolutionMetrics:
    initial_tests_written = 50
    tests_added_during_dev = 5  # Should be minimal
    tests_modified = 12  # Refined based on learning
    tests_deleted = 0  # Should be rare
    final_test_count = 55
    coverage_progression = [45%, 67%, 85%, 92%]  # Over time
```

### TDD Anti-Pattern Detection

⚠️ **Warning Signs (TDD Violations):**
- [ ] Code written before tests
- [ ] Tests written to match existing code
- [ ] Tests that never failed (not testing anything)
- [ ] Tests coupled to implementation details
- [ ] Tests that are harder to write than the code
- [ ] Skipped tests without justification

✅ **TDD Best Practices Achieved:**
- [ ] Tests define behavior, not implementation
- [ ] Each test has a single assertion focus
- [ ] Test names describe expected behavior
- [ ] Tests are fast and independent
- [ ] Tests enable confident refactoring
- [ ] Tests serve as living documentation

---

## Example TDD Development Session

### TDD Development of GENERATE_LLM_ANALYSIS Action

**Claude**: "I'm ready to develop the GENERATE_LLM_ANALYSIS action using strict TDD methodology. Before writing ANY code, let's define our tests:

### Step 1: Define Test Requirements (RED Phase)

**Claude**: "First, let's write comprehensive tests that define exactly what this action should do:

```python
# tests/test_generate_llm_analysis.py
# WRITTEN BEFORE ANY IMPLEMENTATION

import pytest
from pathlib import Path

class TestGenerateLLMAnalysis:
    '''TDD tests for LLM analysis action - ALL WRITTEN FIRST'''
    
    def test_produces_markdown_report(self, progressive_stats):
        '''Test that action produces a markdown report file.'''
        # This test MUST fail initially
        result = execute_llm_analysis(progressive_stats)
        
        assert result.success == True
        assert result.output_file.endswith('.md')
        assert Path(result.output_file).exists()
        
    def test_report_contains_required_sections(self, progressive_stats):
        '''Test that report contains all required sections.'''
        result = execute_llm_analysis(progressive_stats)
        content = Path(result.output_file).read_text()
        
        # Required sections
        assert '## Executive Summary' in content
        assert '## Stage-by-Stage Analysis' in content
        assert '## Unmapped Pattern Analysis' in content
        assert '## Recommendations' in content
        assert '```mermaid' in content  # Flowchart
        
    def test_analyzes_unmapped_patterns(self, progressive_stats):
        '''Test that unmapped patterns are correctly identified.'''
        # Add known unmapped patterns to test data
        progressive_stats['unmapped_identifiers'] = [
            'OBSOLETE_001', 'OBSOLETE_002',  # Obsolete pattern
            'P12345_HUMAN', 'Q67890_MOUSE',  # Species suffix pattern
            'temp_id_001', 'temp_id_002'  # Temporary ID pattern
        ]
        
        result = execute_llm_analysis(progressive_stats)
        analysis = result.pattern_analysis
        
        assert 'obsolete' in analysis['patterns_detected']
        assert 'species_suffix' in analysis['patterns_detected']
        assert 'temporary_ids' in analysis['patterns_detected']
        
    def test_generates_actionable_recommendations(self, progressive_stats):
        '''Test that recommendations are specific and actionable.'''
        result = execute_llm_analysis(progressive_stats)
        
        assert len(result.recommendations) > 0
        for rec in result.recommendations:
            assert rec['action'] in ['add_stage', 'modify_stage', 'update_reference']
            assert rec['expected_improvement'] > 0
            assert rec['confidence'] > 0
            
    def test_performance_requirements(self, large_progressive_stats):
        '''Test that analysis completes within time limits.'''
        import time
        start = time.time()
        
        result = execute_llm_analysis(large_progressive_stats)
        
        elapsed = time.time() - start
        assert elapsed < 5.0  # Must complete in 5 seconds
        assert result.success == True
```

**User**: "These tests look good. I want to ensure it also tracks which stages contributed most to the final coverage."

**Claude**: "Excellent point! Let me add that test:

```python
    def test_stage_contribution_analysis(self, progressive_stats):
        '''Test that report analyzes each stage's contribution.'''
        result = execute_llm_analysis(progressive_stats)
        
        assert 'stage_contributions' in result.analysis
        total_contribution = sum(
            stage['contribution_percent'] 
            for stage in result.analysis['stage_contributions']
        )
        assert abs(total_contribution - 100.0) < 0.01  # Should sum to 100%
```

### Step 2: Confirm RED Phase

**Claude**: "Let's run our tests to confirm they all fail:

```bash
poetry run pytest tests/test_generate_llm_analysis.py -xvs
```

**Output:**
```
FAILED test_produces_markdown_report - NameError: name 'execute_llm_analysis' is not defined
FAILED test_report_contains_required_sections - NameError: name 'execute_llm_analysis' is not defined
... (all tests fail)

6 tests failed ✓ Perfect! RED phase confirmed.
```

### Step 3: Minimal Implementation (GREEN Phase)

**Claude**: "Now I'll write JUST enough code to make tests pass, one at a time:

```python
# biomapper/actions/reports/generate_llm_analysis.py
# MINIMAL IMPLEMENTATION - Just enough to pass tests

from pathlib import Path
from typing import Dict, Any
import json

def execute_llm_analysis(progressive_stats: Dict[str, Any]) -> AnalysisResult:
    '''Minimal implementation to pass first test.'''
    
    # Test 1: Produce markdown report
    output_file = '/tmp/analysis.md'
    Path(output_file).write_text('# Analysis Report\n')
    
    return AnalysisResult(
        success=True,
        output_file=output_file
    )
```

**Run first test:**
```bash
poetry run pytest tests/test_generate_llm_analysis.py::test_produces_markdown_report -xvs
```

✓ PASSED - First test green!

**Claude**: "Now let's make the second test pass:

```python
def execute_llm_analysis(progressive_stats: Dict[str, Any]) -> AnalysisResult:
    '''Implementation for required sections test.'''
    
    # Generate report with required sections
    report = []
    report.append('# Progressive Mapping Analysis\n')
    report.append('## Executive Summary\n')
    report.append('Summary content here.\n')
    report.append('## Stage-by-Stage Analysis\n')
    report.append('Stage analysis here.\n')
    report.append('## Unmapped Pattern Analysis\n')
    report.append('Pattern analysis here.\n')
    report.append('## Recommendations\n')
    report.append('Recommendations here.\n')
    report.append('```mermaid\ngraph TD\nA-->B\n```\n')
    
    output_file = '/tmp/analysis.md'
    Path(output_file).write_text('\\n'.join(report))
    
    return AnalysisResult(
        success=True,
        output_file=output_file
    )
```

**Continue this process for each test...**

### Step 4: Refactor (REFACTOR Phase)

**Claude**: "All tests are GREEN! Now we can safely refactor:

```python
# REFACTORED VERSION - Clean, maintainable, fully tested

class LLMAnalysisGenerator:
    '''Generate analysis reports for progressive mapping results.'''
    
    def __init__(self, template_engine='jinja2'):
        self.template_engine = template_engine
        self.pattern_detector = UnmappedPatternDetector()
        self.recommendation_engine = RecommendationEngine()
        
    def generate_analysis(self, progressive_stats: Dict) -> AnalysisResult:
        '''Generate comprehensive analysis report.'''
        
        # All functionality proven by tests
        patterns = self.pattern_detector.analyze(
            progressive_stats.get('unmapped_identifiers', [])
        )
        
        recommendations = self.recommendation_engine.generate(
            patterns, progressive_stats
        )
        
        report = self.render_report(
            stats=progressive_stats,
            patterns=patterns,
            recommendations=recommendations
        )
        
        output_path = self.save_report(report)
        
        return AnalysisResult(
            success=True,
            output_file=str(output_path),
            pattern_analysis={'patterns_detected': patterns},
            recommendations=recommendations,
            analysis={'stage_contributions': self.calculate_contributions(progressive_stats)}
        )
```

**Run all tests after refactoring:**
```bash
poetry run pytest tests/test_generate_llm_analysis.py -xvs
```

✓ All 6 tests still PASSING! Refactoring successful.

### Step 5: TDD Metrics Review

**Session Metrics:**
- Tests Written First: 6
- Tests Passing: 6/6
- Code Coverage: 94%
- TDD Cycles Completed: 6
- RED→GREEN Time: 45 minutes
- Refactoring Count: 3

**User**: "Excellent! The TDD approach caught several edge cases I hadn't considered. Let's continue with the next action..."

---

## Conclusion

This Progressive Mapping Development Guide establishes a collaborative framework for developing biological data harmonization strategies with Claude Code agents. By following this structured approach:

1. **Consistency**: All entity types follow the same progressive pattern
2. **Collaboration**: Clear communication between developer and agent
3. **Quality**: Staged implementation ensures robust solutions
4. **Metrics**: Comprehensive tracking enables continuous improvement
5. **Flexibility**: Framework adapts to different biological data types

The progressive mapping approach, combined with collaborative development, ensures biomapper strategies achieve maximum coverage while maintaining high confidence in mapping results.

---

## Appendix: Quick Reference

### Stage Naming Convention
- Stage 1: `direct_match`
- Stage 2: `extended_match` or `composite_expansion`
- Stage 3: `advanced_match` or `historical_resolution`
- Stage 4+: `[method]_match`

### Confidence Score Ranges
- 1.0: Perfect direct match
- 0.9-0.99: High confidence (minor transformations)
- 0.8-0.89: Good confidence (fuzzy matching)
- 0.7-0.79: Moderate confidence (semantic/vector matching)
- <0.7: Low confidence (requires review)

### Standard File Outputs
- `waterfall_chart.png`: Progressive improvement visualization
- `confidence_distribution.png`: Score distribution histogram
- `match_type_breakdown.png`: Pie chart of match types
- `mapping_statistics.tsv`: Detailed metrics
- `mapping_summary.txt`: Human-readable summary
- `mapping_report.json`: Complete structured data
- `llm_analysis.md`: AI-generated insights and recommendations

### Performance Targets
- Stage 1: <1 second for 10,000 records
- Stage 2: <5 seconds for 10,000 records
- Stage 3: <30 seconds for 10,000 records
- Memory: <500MB for 100,000 records
- Full pipeline: <1 minute for 10,000 records