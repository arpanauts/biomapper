## Context Brief:
We've updated `populate_metamapper_db.py` and mapping scripts to use Gene Names as targets for UKBB-to-HPA/QIN mappings. However, a critical issue in `MappingExecutor` prevents this workaround for HPA, as it incorrectly prioritizes a failing identity UniProt-to-UniProt path. QIN mapping to Gene Names works because no such conflicting identity path exists for it.

## Initial Steps:
1.  Review project context, particularly regarding `MappingExecutor` and mapping strategies: `/home/ubuntu/biomapper/CLAUDE.md` and `/home/ubuntu/biomapper/docs/iterative_mapping_strategy.md`.
2.  Review the latest status update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-28-gene-mapping-executor-issue.md`.
3.  Familiarize yourself with the `MappingExecutor` code, especially path discovery: `/home/ubuntu/biomapper/src/biomapper/mapping_executor.py` (specifically `_get_mapping_paths`).

## Work Priorities:
1.  **Investigate and Fix `MappingExecutor` Path Selection (Highest Priority):**
    *   **Goal:** Ensure `MappingExecutor` correctly selects the `UKBB_UniProt_to_HPA_GeneName` path (UNIPROTKB_AC -> GENE_NAME) for the UKBB to HPA mapping, instead of the problematic identity path (UNIPROTKB_AC -> UNIPROTKB_AC).
    *   **Areas to Investigate:**
        *   How does `MappingExecutor._get_mapping_paths` currently prioritize paths?
        *   Why is the `priority` field (set to 1 for the gene name path) in the `MappingPath` table not influencing the selection as expected?
        *   Is there logic that inherently prefers identity mappings (source_ontology_type == target_ontology_type) over conversion mappings, and if so, how can this be adjusted?
    *   **Possible Solutions to Implement:**
        *   Modify the query or logic in `_get_mapping_paths` to strictly adhere to the `priority` field.
        *   Introduce a mechanism to deprioritize or disable specific paths (e.g., identity paths that are known to cause issues for certain endpoint relationships).
        *   Consider allowing an optional `mapping_path_id` to be passed to `MappingExecutor.execute_mapping` to force the use of a specific path, bypassing automatic discovery for problematic cases.
2.  **Test Mappings:**
    *   After modifying `MappingExecutor`, run `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py --drop-all`.
    *   Execute `/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py` and verify it now uses the gene name path and produces successful mappings.
    *   Execute a QIN mapping script (e.g., `/home/ubuntu/biomapper/scripts/map_ukbb_to_qin_gene.py` or a user-created one) to confirm it still works.
3.  **Documentation:** Update any relevant documentation regarding `MappingExecutor`'s path selection logic.

## References:
- Status Update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-28-gene-mapping-executor-issue.md`
- `MappingExecutor`: `/home/ubuntu/biomapper/src/biomapper/mapping_executor.py`
- Database Population: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
- HPA Mapping Script: `/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py`
- Claude Feedback on previous attempt (archived): `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/archive/2025-05-28-214000-feedback-ukbb-hpa-qin-gene-mapping-workaround.md`

## Workflow Integration:
This task involves deep debugging and modification of core logic. It's recommended to:
1.  First, use Cascade (yourself) to perform detailed code analysis of `MappingExecutor._get_mapping_paths` and related functions. Use `view_code_item` and `grep_search` to understand the current logic.
2.  Formulate a hypothesis for the cause of the incorrect path selection.
3.  Propose specific code changes to `MappingExecutor`.
4.  Once a clear plan for modification is ready, you can either implement it directly or generate a detailed prompt for a Claude Code instance to make the specific changes.