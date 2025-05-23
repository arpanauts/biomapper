# Documentation Fix: Update Arivale Chemistries Column Names in MVP Spec

## 1. Overview

The implementation feedback for the "MVP UKBB NMR to Arivale Chemistries Mapping" (Feedback file: `2025-05-23-232700-feedback-implement-ukbb-arivale-chemistries-mvp.md`) revealed that the actual column names in the Arivale `chemistries_metadata.tsv` file differ from those documented in the original `spec.md` for that MVP.

This task is to update the `spec.md` to accurately reflect the *actual* column names found in the data.

## 2. Goal

*   Modify `/home/ubuntu/biomapper/roadmap/3_completed/mvp_ukbb_to_arivale_chemistries/spec.md`.
*   Replace the incorrect Arivale column list with the correct list as identified in the feedback.

## 3. Details

**File to Modify:** `/home/ubuntu/biomapper/roadmap/3_completed/mvp_ukbb_to_arivale_chemistries/spec.md`

**Current (Incorrect) Documented Columns (example from feedback):**
*   TestId, TestDisplayName, TestName, Units, Loinccode, Pubchem

**Actual Columns to Document (from feedback):**
*   Name
*   Display Name
*   Labcorp ID
*   Labcorp Name
*   Labcorp LOINC ID
*   Labcorp LOINC Name
*   Quest ID
*   Quest Name
*   Quest LOINC ID

## 4. Scope

*   **In Scope:** Editing the relevant section of the `spec.md` file.
*   **Out of Scope:** Any other changes to the MVP or its scripts.

## 5. Deliverable
*   Updated `spec.md` file with correct Arivale column names.
