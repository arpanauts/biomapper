# Feature Specification: Fix is_one_to_many_target Flag Bug

## 1. Functional Scope

### Current Behavior (Bug)
- The `is_one_to_many_target` flag is incorrectly set to TRUE for all records in the phase3 output
- This makes it impossible to distinguish actual one-to-many target relationships from one-to-one relationships
- The bug emerged after fixing Phase 1 script to correctly generate multiple output rows for one-to-many source relationships

### Expected Behavior
- `is_one_to_many_target` should be TRUE only when a single target entity (e.g., an Arivale Protein ID) is mapped by multiple distinct source entities (e.g., multiple different UKBB Assay+UniProt combinations)
- `is_one_to_many_source` should be TRUE only when a single source entity maps to multiple distinct target entities
- `is_canonical_mapping` should correctly identify the primary/canonical mapping in many-to-many relationships

### Key Functions to Fix
1. `perform_bidirectional_validation()` in `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`
2. Related grouping and flag assignment logic

## 2. Technical Scope

### Technical Constraints
- Must maintain backward compatibility with existing output format
- Should not significantly impact performance on large datasets (100k+ mappings)
- Must work with both protein and metabolite mapping workflows

### Implementation Approach
1. **Diagnosis Phase** ✓ COMPLETE
   - Root cause identified: flags are swapped in the implementation
   - Lines 1009-1015, 1048-1054: incorrectly set `one_to_many_target` for sources with multiple targets
   - Lines 1040-1046: incorrectly set `one_to_many_source` for targets with multiple sources

2. **Fix Implementation**
   - Swap the flag assignments in 4 locations within `perform_bidirectional_validation`:
     - Line 1015: Change `one_to_many_target_col` to `one_to_many_source_col`
     - Line 1023: Change `one_to_many_source_col` to `one_to_many_target_col`
     - Line 1046: Change `one_to_many_source_col` to `one_to_many_target_col`
     - Line 1054: Change `one_to_many_target_col` to `one_to_many_source_col`
   - Add validation checks after flag assignment to ensure consistency
   - Update any related documentation or comments

3. **Validation Phase**
   - Create unit tests that verify:
     - Single source → multiple targets sets `is_one_to_many_source=True`
     - Multiple sources → single target sets `is_one_to_many_target=True`
     - One-to-one mappings have both flags as False
     - Many-to-many relationships have both flags as True
   - Test with real UKBB-Arivale data to ensure the fix resolves the original issue
   - Verify that the output file no longer has all `is_one_to_many_target=True`

### Data Structures
```python
# Expected flag combinations
# One-to-one: is_one_to_many_source=False, is_one_to_many_target=False
# One-to-many source: is_one_to_many_source=True, is_one_to_many_target=False
# One-to-many target: is_one_to_many_source=False, is_one_to_many_target=True
# Many-to-many: is_one_to_many_source=True, is_one_to_many_target=True
```

## 3. Testing Strategy

### Option A: Minimal Test Suite
- Create synthetic test data with known relationship patterns
- Test each relationship type (1:1, 1:many, many:1, many:many)
- Verify flag correctness for each pattern

**Pros:**
- Quick to implement and run
- Easy to understand and maintain
- Clear pass/fail criteria

**Cons:**
- May not catch edge cases in real data
- Doesn't test performance at scale

### Option B: Comprehensive Real-Data Testing
- Use actual UKBB-Arivale mapping outputs
- Include edge cases like composite identifiers
- Test with full dataset to ensure performance

**Pros:**
- Tests real-world scenarios
- Validates performance at scale
- Catches unexpected edge cases

**Cons:**
- Requires access to real data
- Slower to run
- More complex to set up

### Recommended Approach
Implement Option A first for rapid development and debugging, then validate with Option B before deployment.