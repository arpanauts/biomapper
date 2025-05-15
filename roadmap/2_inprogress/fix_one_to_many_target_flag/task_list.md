# Task List: Fix is_one_to_many_target Flag Bug

## Investigation Tasks

1. [ ] Examine the `perform_bidirectional_validation` function in `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py` to locate the logic that sets the `is_one_to_many_target` flag
2. [ ] Run test cases with known one-to-many relationships to reproduce the issue where all `is_one_to_many_target` values are TRUE
3. [ ] Identify the specific logical error in the flag calculation
4. [ ] Compare with the `is_one_to_many_source` flag calculation to understand differences and potential issues
5. [ ] Document the current behavior and root cause of the issue

## Implementation Tasks

6. [ ] Create a fix for the `is_one_to_many_target` flag calculation logic
7. [ ] Ensure the fix preserves correct behavior for `is_one_to_many_source`
8. [ ] Verify the fix works with the changes previously made to handle one-to-many relationships in the Phase 1 mapping script (`/home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py`)
9. [ ] Update any related logic for `is_canonical_mapping` if necessary
10. [ ] Refactor any redundant or overly complex code in the process

## Testing Tasks

11. [ ] Create test cases that validate both one-to-many and many-to-one relationships
12. [ ] Test with real UKBB and Arivale data to ensure correct flag assignment
13. [ ] Verify that `is_one_to_many_target` is only TRUE when a target is mapped by multiple sources
14. [ ] Verify that `is_one_to_many_source` is only TRUE when a source maps to multiple targets
15. [ ] Validate that canonical mappings are correctly identified

## Documentation Tasks

16. [ ] Update code comments to clearly explain the flag calculation logic
17. [ ] Document the fix in implementation notes
18. [ ] Update any relevant technical documentation, particularly regarding one-to-many relationship handling
19. [ ] Consider adding explicit validation checks in the code to catch similar issues in the future
20. [ ] Prepare a summary of the fix for the next status update
