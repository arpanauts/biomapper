# Implementation Notes: Fix Phase 3 One-To-Many Bug

## Bug Description
The script `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py` had a bug where the `is_one_to_many_target` flag was incorrectly set to TRUE for all records. This was due to the count-based logic not filtering out rows with missing source or target IDs when calculating mapping counts.

## Debugging Process
1.  **Code Analysis**: Examined the script to locate where `is_one_to_many_target` flags were set.
2.  **Logic Analysis**: Identified that the count-based flags logic (lines 1030-1067 in the original script) was causing the issue.
3.  **Root Cause**: The logic counted all rows, including those with NULL values, when determining one-to-many relationships, leading to inflated counts.

## The Fix
The core changes were made in the `perform_bidirectional_validation` function:
1.  **Filter Valid Mappings**: A new DataFrame `valid_mapping_df` was created by filtering `reconciled_df` to include only rows where both `source_id_col` and `target_id_col` are not NA.
    ```python
    valid_mapping_df = reconciled_df[reconciled_df[source_id_col].notna() & reconciled_df[target_id_col].notna()]
    ```
2.  **Use Filtered Counts**: `source_id_counts` and `target_id_counts` are now calculated based on `valid_mapping_df`.
    ```python
    source_id_counts = valid_mapping_df[source_id_col].value_counts().to_dict()
    target_id_counts = valid_mapping_df[target_id_col].value_counts().to_dict()
    ```
3.  **Skip Invalid Rows During Flag Setting**: An explicit check was added in the loop that sets the flags to skip rows if `source_id` or `target_id` is NA.
    ```python
    if pd.isna(source_id) or pd.isna(target_id):
        continue
    ```
4.  **Use Filtered Data for Relationship Checks**: When determining if a source maps to multiple targets or a target is mapped by multiple sources, the lookups (`source_ids_for_target`, `target_ids_for_source`) are performed on `valid_mapping_df`.

## Testing
Custom verification tests were created with controlled data to confirm the fix:
-   **Test 1 (Simple):** Verified that only actual one-to-many target relationships were flagged.
-   **Test 2 (Complex):** Verified correct flagging for one-to-one, one-to-many source, and one-to-many target mappings.
The tests confirmed that `is_one_to_many_target` is now correctly set only for true one-to-many target scenarios.
