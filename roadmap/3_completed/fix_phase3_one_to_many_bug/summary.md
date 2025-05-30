# Summary: Fix Phase 3 One-To-Many Bug

A bug in `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py` was fixed, where the `is_one_to_many_target` flag was incorrectly set to TRUE for all records. The issue stemmed from the count-based logic for determining one-to-many relationships, which did not properly exclude rows with NULL source or target IDs.

The fix involved modifying the `perform_bidirectional_validation` function to:
1.  Create a `valid_mapping_df` by filtering out rows with missing source or target IDs.
2.  Calculate mapping counts (`source_id_counts`, `target_id_counts`) using this filtered DataFrame.
3.  Explicitly skip rows with NULL IDs during the flag-setting process.
4.  Use the `valid_mapping_df` when checking for multiple source-to-target or target-to-source relationships.

Custom tests confirmed that the `is_one_to_many_target` (and by extension, `is_one_to_many_source`) flags are now set correctly, reflecting actual mapping multiplicities rather than data processing artifacts. This ensures more accurate data for downstream canonical mapping selection.
