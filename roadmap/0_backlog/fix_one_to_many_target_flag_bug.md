# Feature Idea: Fix is_one_to_many_target Flag Bug in Phase 3 Reconciliation

## Overview
Investigate and resolve an issue where the `is_one_to_many_target` flag is incorrectly set to TRUE for all records in the phase3 bidirectional reconciliation output.

## Problem Statement
The Phase 3 bidirectional reconciliation script (`phase3_bidirectional_reconciliation.py`) is generating output where every single `is_one_to_many_target` value is TRUE, which is logically inconsistent and compromises the reliability of this crucial flag.

The `is_one_to_many_target` flag should only be TRUE when a single target entity (e.g., an Arivale Protein ID) is mapped by multiple distinct source entities (e.g., multiple different UKBB Assay+UniProt combinations). It should not be TRUE for all records.

## Key Requirements
- Identify the specific logic error in the `perform_bidirectional_validation` function or related code in `phase3_bidirectional_reconciliation.py`
- Fix the calculation of `is_one_to_many_target` flag to correctly identify only true one-to-many target relationships
- Ensure the bug fix doesn't introduce new issues with related flags like `is_one_to_many_source` and `is_canonical_mapping`
- Validate the fix with real-world data containing known one-to-many relationships in both directions
- Update tests to explicitly verify the correctness of these flags

## Technical Context
This issue emerged after fixing the Phase 1 script (`map_ukbb_to_arivale.py`) to correctly generate multiple output rows for one-to-many source relationships (when a single source UniProt ID maps to multiple Arivale Protein IDs).

The issue specifically affects the final output columns:
- `is_one_to_many_source`
- `is_one_to_many_target`
- `is_canonical_mapping`

These flags are crucial for correctly identifying and handling many-to-many relationships in the mapping process, as described in the iterative mapping strategy.

## Success Criteria
- `is_one_to_many_target` flag is TRUE only for target entities that are mapped by multiple distinct source entities
- `is_one_to_many_source` flag is TRUE only for source entities that map to multiple distinct target entities
- Results verify correctly with test data containing known one-to-many relationships in both directions
- The flags align with the definitions and expectations in the iterative mapping strategy
- Improved documentation of the flag calculation logic to prevent similar issues in the future
