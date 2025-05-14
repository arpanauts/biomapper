# Stage Gate Prompt: Feature Completion

Context: A feature folder (e.g., `../2_inprogress/feature-name/`) has been moved into `3_completed`.

Instructions:

1.  **Review Feature:** Synthesize content from `README.md`, `spec.md`, `design.md`, `implementation_notes.md`.
2.  **Generate Completion Summary:** Write a 1-3 paragraph summary (purpose, what was built, notable decisions/results). Save as `summary.md` (using `../../_templates/summary_template.md`) in the feature folder.
3.  **Log Completion:** Create a single-line entry for `../../_reference/completed_features_log.md`:
    *   Format: `- **[Feature Name]:** Completed [YYYY-MM-DD]. [One-sentence summary].`
4.  **Suggest Architecture Review:** Identify sections of `../../_reference/architecture_notes.md` that might need human review.
