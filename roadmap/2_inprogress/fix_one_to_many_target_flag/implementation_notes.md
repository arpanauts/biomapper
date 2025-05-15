# Implementation Notes: Fix is_one_to_many_target Flag Bug

## Date: 2025-05-15

### Progress:

- Identified critical issue with `is_one_to_many_target` flag in Phase 3 reconciliation output
- Bug confirmed: the flag is incorrectly set to TRUE for all records in the output
- Initial analysis suggests the issue is in the `perform_bidirectional_validation` function of `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`
- Created task list for systematically addressing the issue

### Key Insights from Conversation:

1. **Root Issue**: The one-to-many fix for Phase 1 mapping script (`/home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py`) was implemented correctly:
   - Now properly generates multiple rows when a source UniProt ID maps to multiple Arivale target IDs
   - This prevents data loss at the initial mapping stage

2. **Current Bug**: The issue appears in the Phase 3 reconciliation script's (`/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`) flag calculation:
   - The `is_one_to_many_target` flag is being set to TRUE for all records
   - This incorrectly suggests that every target is mapped by multiple sources
   - This compromises the reliability of canonical mapping selection

3. **Flag Definitions**:
   - `is_one_to_many_source`: Should be TRUE if a single source entity maps to multiple target entities
   - `is_one_to_many_target`: Should be TRUE if a single target entity is mapped by multiple source entities

### Next Steps:

1. Examine the exact implementation of the `perform_bidirectional_validation` function
2. Identify where/how the `is_one_to_many_target` flag is calculated
3. Compare with the calculation of `is_one_to_many_source` for clues
4. Fix the logic to correctly identify only true one-to-many target relationships

### Challenges Encountered:

- Complex reconciliation logic makes it difficult to isolate the specific issue
- Fix must ensure consistency across all three key flags (`is_one_to_many_source`, `is_one_to_many_target`, `is_canonical_mapping`)
- Need to ensure fix works with the existing one-to-many handling in Phase 1
