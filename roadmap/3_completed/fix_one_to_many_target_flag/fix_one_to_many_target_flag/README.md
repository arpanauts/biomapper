# Feature: Fix is_one_to_many_target Flag Bug

## Goal

Investigate and resolve the bug in Phase 3 bidirectional reconciliation where the `is_one_to_many_target` flag is incorrectly set to TRUE for all records, ensuring accurate identification of one-to-many relationships in both source and target directions.

## Key Requirements

- Identify the specific logic error in the `perform_bidirectional_validation` function in `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`
- Fix the calculation of `is_one_to_many_target` flag to correctly identify only true one-to-many target relationships
- Ensure the bug fix doesn't introduce new issues with related flags (`is_one_to_many_source` and `is_canonical_mapping`)
- Validate the fix with real-world data containing known one-to-many relationships
- Update tests to explicitly verify the correctness of these flags
- Document the flag calculation logic to prevent similar issues in the future

## Target Audience

- Developers working on the biomapper project
- Users relying on accurate one-to-many relationship identification for protein and metabolite mappings
- Data scientists using the output for downstream analysis

## Open Questions

- ~~Is the bug specifically in the grouping logic or in the flag assignment logic?~~ **RESOLVED**: The bug is in the flag assignment logic - the flags are swapped.
- Are there edge cases in the current implementation that need special handling?
- Should we add additional validation checks to prevent similar issues in the future?
- What is the performance impact of the corrected logic on large datasets?

## Root Cause Identified

The bug has been traced to swapped flag assignments in `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`:
- `is_one_to_many_target` is incorrectly set when a SOURCE has multiple TARGETS
- `is_one_to_many_source` is incorrectly set when a TARGET has multiple SOURCES
- The fix requires swapping these assignments in 4 locations (lines 1015, 1023, 1046, 1054)