# Mapping Complexities and Edge Cases

This document outlines known complexities, edge cases, and ontological challenges encountered during the entity mapping process within the `biomapper` project, particularly focusing on identifier changes (merges, splits, deprecations).

## UniProt Identifier Demergers

### Example: P0CG05 (Arivale) -> P0DOY2 (UKBB)

*   **Context:** The UniProt identifier `P0CG05` (present in the Arivale dataset) is documented by UniProt as having been demerged into two separate entries: `P0DOY2` and `P0DOY3`.
*   **Observation:**
    *   `P0DOY2` exists in both the Arivale and UKBB datasets.
    *   `P0DOY3` exists in neither dataset (based on current analysis).
*   **Biomapper Behavior (Forward: UKBB -> Arivale):** If `P0DOY2` from UKBB is mapped forward, it might potentially map to `P0CG05` in Arivale if the mapping resources treat `P0CG05` as a secondary/alternative identifier for `P0DOY2`.
*   **Biomapper Behavior (Backward: Arivale -> UKBB):** When mapping backward from `P0CG05` in Arivale, the ideal outcome is to identify its relationship to `P0DOY2` and successfully map it to the `P0DOY2` present in UKBB.
*   **Current Handling (Investigation Needed):** We need to verify if the underlying mapping resources (e.g., UniProt ID mapping files) and the `biomapper` logic correctly handle this demerger information. Ideally, the mapping path or output metadata should indicate that `P0CG05` is a historical/secondary ID related to the mapped target `P0DOY2`.
*   **Future Enhancements (Phase 2):** Multi-strategy mapping could offer explicit options for handling such cases, like choosing to map to all valid demerged targets found in the destination dataset or flagging them for review.

---

## Composite UniProt Identifiers in Arivale Metadata

*   **Issue:** The `uniprot` column in the Arivale metadata file (`proteomics_metadata.tsv`) sometimes contains multiple UniProt IDs concatenated into a single string, typically separated by a comma (e.g., `"P29460,P29459"`).
*   **Examples:**
    *   `P29460,P29459`
    *   `Q11128,P21217`
    *   `Q29983,Q29980`
    *   `Q8NEV9,Q14213`
*   **Impact (Backward Mapping: Arivale -> UKBB):** The `ArivaleReverseLookupClient` currently reads this composite string as a single value. Subsequent mapping steps expecting a valid UniProt ID will fail.
*   **Impact (Forward Mapping: UKBB -> Arivale):** The handling by the `ArivaleMetadataLookupClient` (which maps UniProt -> Arivale ID) needs investigation. It's unclear if it splits these IDs or how it associates them with Arivale IDs.
*   **Current Handling (Investigation Needed):** We need to verify the behavior of `ArivaleMetadataLookupClient` and confirm the behavior of `ArivaleReverseLookupClient` (likely takes the full string).
*   **Resolution Strategy (Phase 2 Recommended):** Both clients need modification. A clear strategy is required (e.g., split and take first, split and map all, exclude, configurable behavior). Splitting and deciding how to handle the resulting multiple mappings is complex and best suited for multi-strategy implementation.

---

*(More examples and explanations will be added as identified)*
