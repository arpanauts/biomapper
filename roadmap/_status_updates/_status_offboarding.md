# Development Status Update Prompt

```markdown
Based on our recent work on the biomapper project, please create a comprehensive status update document. Begin by reviewing the 1-3 most recent status update files in `/home/ubuntu/biomapper/roadmap/_status_updates/` (sorted by date) to understand context and progress history. Then incorporate information from the roadmap files in `/home/ubuntu/biomapper/roadmap/` as well as our recent conversations.

While maintaining awareness of historical context from previous updates, prioritize recent memory and progress in your update. Please organize your response into the following sections:

## 1. Recent Accomplishments (In Recent Memory)
- List the key features, components, or tasks we've completed since the last status update
- Highlight any significant milestones reached
- Note any critical bugs fixed or issues resolved
- Prioritize accomplishments from the most recent development period over those already mentioned in previous status updates

## 2. Current Project State
- Summarize the overall status of the biomapper project
- Describe the state of major components/modules
- Identify any areas that are stable vs. in active development
- Note any outstanding critical issues or blockers

## 3. Technical Context
- Document important architectural decisions made recently
- Summarize key data structures, algorithms, or patterns we're using
- Capture any important learnings about the codebase or technology stack
- Reference any specific implementation details worth remembering

## 4. Next Steps
- List the immediate tasks to be tackled next
- Outline priorities for the coming week
- Identify any dependencies or prerequisites
- Note any potential challenges or considerations for upcoming work

## 5. Open Questions & Considerations
- Document any unresolved questions or decisions
- Note areas where we might need to revisit our approach
- Identify topics requiring further research or exploration

Please be specific and reference relevant files, components, or concepts by name where appropriate. Always use full absolute file paths when referencing files (e.g., `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py` instead of just `phase3_bidirectional_reconciliation.py`) for clarity and to enable quick location of the exact files. This document serves as both a record of our progress and a guide for continuing development.

In addition to this status update, please also prepare a suggested prompt for the next work session by updating the file `/home/ubuntu/biomapper/roadmap/_status_updates/_suggested_next_prompt.md`. This should include:

1. **Context Brief**: A 2-3 sentence summary of the current status and most important recent context
2. **Initial Steps**: Begin with instructions to review `/home/ubuntu/biomapper/CLAUDE.md` for overall project context
3. **Work Priorities**: Clear recommendations on what tasks should be prioritized next
4. **References**: References to key files mentioned in your status update
5. **Workflow Integration**: Suggestions for incorporating Claude into the workflow as an independent step, including any specific, detailed Claude prompts if needed

This prompt should align with the priorities identified in your status update but be written as direct guidance to the USER for the next work session, allowing them to craft their own detailed prompts for Claude after understanding the context.
```

## Storage Recommendations
Save status documents with the following filename format:
```
/home/ubuntu/biomapper/roadmap/_status_updates/YYYY-MM-DD-[brief-description].md
```

Examples:
- `2025-04-04-api-refactoring.md`
- `2025-04-04-data-pipeline.md`
- `2025-04-04-weekly-summary.md`

The suggested next prompt should always be saved to:
```
/home/ubuntu/biomapper/roadmap/_status_updates/_suggested_next_prompt.md
```
Ensure you overwrite any existing content in this file to keep the prompt current.