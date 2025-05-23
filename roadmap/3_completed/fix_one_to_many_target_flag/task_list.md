# Task List: Fix is_one_to_many_target Flag Bug

## Implementation Tasks

### 1. Code Changes
- [x] Open `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`
- [x] Fix line 1015: Change `one_to_many_target_col` to `one_to_many_source_col`
- [x] Fix line 1023: Change `one_to_many_source_col` to `one_to_many_target_col` 
- [x] Fix line 1046: Change `one_to_many_source_col` to `one_to_many_target_col`
- [x] Fix line 1054: Change `one_to_many_target_col` to `one_to_many_source_col`
- [x] Add comment above each fix explaining the correct logic
- [x] Fix additional locations found during testing (lines 581, 609, 942)

### 2. Testing
- [x] Create test script `test_one_to_many_flags_fixed.py` with test cases for:
  - [x] One-to-one mapping (both flags FALSE)
  - [x] One-to-many source (source flag TRUE, target flag FALSE)
  - [x] One-to-many target (source flag FALSE, target flag TRUE)
  - [x] Many-to-many mapping (both flags TRUE)
- [x] Run test script to verify the fix works correctly
- [x] Test with real UKBB-Arivale data to confirm the bug is resolved

### 3. Validation
- [x] Run the fixed script on existing test data from `/home/ubuntu/biomapper/scripts/test_output/`
- [x] Verify that `is_one_to_many_target` is no longer TRUE for all records
- [x] Check that the flag distributions make logical sense
- [x] Compare output file sizes to ensure no unexpected changes

### 4. Documentation
- [x] Update any inline comments in the code to clarify flag meanings
- [x] Create or update implementation notes documenting the fix
- [ ] Prepare summary for the completion stage

## Success Criteria
- All test cases pass
- Real data no longer shows all `is_one_to_many_target=TRUE`
- Flag assignments correctly represent the actual relationships
- No regression in other functionality