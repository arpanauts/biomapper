# Suggested Next Prompt for Biomapper Development

## Context Brief
The MVP0 Pipeline Orchestrator integration test using Arivale data has been completed. It revealed a very low mapping success rate (4%) primarily due to 90% of inputs not finding matches in the Qdrant `pubchem_bge_small_v1_5` collection. The immediate focus is on investigating and addressing this Qdrant hit rate issue.

## Initial Steps
1.  Review `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and development approach.
2.  Review the latest status update which details the MVP0 test results and Qdrant analysis: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-24-mvp0-orchestrator-test-analysis.md`.
3.  Review the implementer's feedback on the MVP0 test: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-24-061057-feedback-mvp0-orchestrator-arivale-test.md`.
4.  Review the details of how the `pubchem_bge_small_v1_5` Qdrant collection was constructed (Memory ID: `6d5ae2aa-d04f-4a4c-8732-b872af99aee6`, Content: "The pubchem_bge_small_v1_5 Qdrant collection generated embeddings from a concatenated text string for each compound: 'All names (including IUPAC variants) Formula: [Formula] InChIKey: [InChIKey]'. Compound descriptions (PC-Compound_comment) were NOT included...").

## Work Priorities

1.  **Investigate Low Qdrant Hit Rate:**
    *   **Task 1: Manual Verification & Query Structure Test:**
        *   Manually check a small sample of "NO_QDRANT_HITS" biochemical names from `/home/ubuntu/biomapper/data/testing_results/arivale_mvp0_test_run_20250524_044335_results.jsonl` (e.g., "spermidine", "alpha-ketoglutarate") against the PubChem website to confirm their existence and common nomenclature.
        *   For these same compounds, obtain their actual Formula and InChIKey.
        *   Construct test queries that mimic the Qdrant database's embedded text structure: `"[Name] Formula: [Formula] InChIKey: [InChIKey]"`.
        *   Use the existing `PubChemRAGMappingClient`'s search functionality (or a direct Qdrant client query if simpler for a quick test) to execute these structured queries against the `pubchem_bge_small_v1_5` collection.
        *   Compare results with the original name-only queries to see if hit rate/scores improve. This will help validate/invalidate the embedding structure mismatch hypothesis.
    *   **Task 2: Analyze Findings & Plan Qdrant Strategy:**
        *   Based on the results of Task 1, discuss and decide on the best strategy for improving Qdrant performance. Options include:
            *   Re-indexing with embeddings from "names only" or "names + descriptions".
            *   Exploring alternative/fine-tuned embedding models.
            *   Developing query augmentation techniques.
        *   Outline the steps for the chosen strategy.

2.  **Implement PubChem API Robustness:**
    *   **Task 3:** Add retry logic (e.g., using the `tenacity` library) to the PubChem API calling components within the pipeline.
    *   **Task 4:** Implement basic request rate limiting for PubChem API calls.
    *   (Optional, based on priority) Consider adding a caching layer for PubChem API responses.

## Key Files and References

*   **Latest Status Update:** `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-24-mvp0-orchestrator-test-analysis.md`
*   **MVP0 Test Results:** `/home/ubuntu/biomapper/data/testing_results/arivale_mvp0_test_run_20250524_044335_results.jsonl`
*   **MVP0 Test Feedback:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-24-061057-feedback-mvp0-orchestrator-arivale-test.md`
*   **`PubChemRAGMappingClient`:** `/home/ubuntu/biomapper/biomapper/mapping/clients/pubchem_rag_client.py`
*   **Qdrant Embedding Content Memory ID:** `6d5ae2aa-d04f-4a4c-8732-b872af99aee6`

## Workflow Integration (General for Next Task)

*   For tasks requiring code changes (e.g., PubChem API robustness, Qdrant client modifications for testing), Cascade will generate detailed prompts for a Claude code instance.
*   For analytical tasks (e.g., analyzing Qdrant test results, strategizing), engage in a discussion with Cascade to refine plans.
*   Ensure any new prompts created adhere to the updated naming convention and include the source prompt reference.