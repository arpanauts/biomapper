# One-to-Many Mapping Fix

## Problem Overview

The Biomapper pipeline for mapping between biological entities (like UKBB proteins to Arivale proteins) was experiencing an issue with output file sizes. The `phase3_bidirectional_reconciliation.py` script was generating unexpectedly large output files (~50MB instead of the expected ~1MB).

### Root Cause Analysis

1. The large file size was due to columns like `ALL_FORWARD_MAPPED_TARGETS_COL` containing extremely long, semicolon-separated strings of thousands of gene symbols for many rows.

2. This was traced back to the `map_ukbb_to_arivale.py` script which, when encountering a single source ID mapping to multiple target IDs, was incorrectly taking only the first target ID (`target_ids[0]`) from the list and discarding the rest.

3. This loss of information was then inconsistently propagated through the pipeline, where at a later stage, these relationships were incorrectly represented as concatenated strings containing all possible targets, rather than as explicit one-to-many mappings.

## Solution: Exploding One-to-Many Mappings into Multiple Rows

The solution implemented modifies the `map_ukbb_to_arivale.py` script to properly handle one-to-many relationships by:

1. Creating multiple rows in the output DataFrame, one for each source-target pair, instead of just taking the first target ID.

2. For a source ID `S` that maps to target IDs `T1, T2, T3, ...`, the script now generates multiple rows:
   ```
   source_id | target_id | other_columns
   -------------------------------
   S         | T1        | ...
   S         | T2        | ...
   S         | T3        | ...
   ```

3. Metadata (confidence scores, validation status, etc.) is properly propagated to all rows for a given source ID.

## Benefits

1. **Data Integrity**: All mapping information is preserved, allowing downstream processes to access the complete set of relationships.

2. **Proper Representation**: One-to-many relationships are now explicitly represented as multiple rows with the same source ID, making the data structure cleaner and more intuitive.

3. **Reduced File Size**: The output files from `phase3_bidirectional_reconciliation.py` will be smaller because they no longer need to store large semicolon-concatenated strings.

4. **Improved Accuracy**: The bidirectional validation in Phase 3 will work more accurately because it will have access to all the mapping relationships, not just the first one or an aggregated string.

## Implementation

The key changes were made in `map_ukbb_to_arivale.py`:

1. Instead of creating a dictionary mapping source IDs to first target ID, we now create a list of expanded rows, one for each source-target pair.

2. For each source ID with multiple target IDs, we create multiple rows in the output DataFrame, with all other columns duplicated.

3. Metadata processing was updated to work with this expanded DataFrame structure, ensuring that metadata (like confidence scores and validation status) is correctly applied to all rows for a given source ID.

## Testing

A test script (`test_one_to_many_explode.py`) has been created to validate that the fix correctly handles one-to-many relationships:

1. It creates a synthetic test dataset with source IDs that map to different numbers of target IDs.
2. It mocks the `MappingExecutor` to return predetermined mapping results with one-to-many mappings.
3. It verifies that the output file correctly contains multiple rows for source IDs with multiple targets.
4. It checks that metadata is consistent across all rows for a given source ID.

Additionally, a real-world test script (`scripts/test_one_to_many_in_real_world.sh`) was developed to run the full pipeline (Phase 1, Phase 2, and Phase 3) using actual data files to confirm the fix under more realistic conditions.

## Verification

The fix was successfully verified using the `scripts/test_one_to_many_in_real_world.sh` script. Key aspects of this verification include:

1.  **Test Configuration:**
    *   The script executed all three phases of the mapping and reconciliation process.
    *   Input for Phase 1 (UKBB to Arivale): `data/UKBB_Protein_Meta.tsv`.
    *   Input for Phase 2 (Arivale to UKBB): `data/arivale_proteomics_metadata.tsv`.
    *   The core mapping script `scripts/map_ukbb_to_arivale.py` was used for both Phase 1 (forward) and Phase 2 (reverse) mappings, with appropriate parameter adjustments for the reverse direction.

2.  **Output Results & File Sizes:**
    *   Phase 1 output (`phase1_ukbb_to_arivale_results.tsv`) file size: ~483 KB (2924 rows).
    *   Phase 3 output (`phase3_bidirectional_reconciliation_results.tsv`) file size: ~1.2 MB (3356 rows). This is a significant reduction from the ~50MB observed before the fix.

3.  **Data Integrity Confirmation:**
    *   The test script specifically checked the `all_forward_mapped_target_ids` column in the Phase 3 output and confirmed: "`No abnormally large strings found...`". This directly verifies that one-to-many mappings are being represented as separate rows rather than long, semicolon-delimited strings.
    *   All mapping relationships are correctly preserved and represented.

4.  **Overall Outcome:**
    *   The primary objective of resolving the large output file size issue by correctly handling one-to-many relationships has been successfully achieved. The pipeline now produces manageable and correctly structured output.