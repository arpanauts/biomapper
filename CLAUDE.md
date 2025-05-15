# Biomapper Project - Instructions for AI Assistants

## Project Structure and Workflow

### Roadmap Structure

The Biomapper project uses a staged development workflow to track features from conception to completion. Details on how to use this system are in [`/home/ubuntu/biomapper/roadmap/HOW_TO_UPDATE_ROADMAP_STAGES.md`](./roadmap/HOW_TO_UPDATE_ROADMAP_STAGES.md).

Key directories to understand:

- `/roadmap/0_backlog/`: Raw feature ideas and requests not yet planned
- `/roadmap/1_planning/`: Features actively being planned with specs and designs
- `/roadmap/2_inprogress/`: Features under active implementation
- `/roadmap/3_completed/`: Implemented and verified features
- `/roadmap/4_archived/`: Obsolete or deferred features
- `/roadmap/_reference/`: Foundational documents and architectural notes
- `/roadmap/_templates/`: Templates for various feature documents
- `/roadmap/_status_updates/`: Chronological project status updates
- `/roadmap/technical_notes/`: In-depth technical explorations

### Determining Project Status

Follow these steps to understand the current project status and priorities:

1. **Check Both Status Files**:
   - Read `/roadmap/_status_updates/_status_onboarding.md` to understand the format and context of status updates
   - Find and read the most recent file in `/roadmap/_status_updates/` by sorting files by date
   - Cross-reference these to get both the structure of status reporting and the latest content

2. **Review Stage Directories**: Examine the contents of stage directories to understand:
   - What's in the backlog → `/roadmap/0_backlog/`
   - What's being planned → `/roadmap/1_planning/`
   - What's under development → `/roadmap/2_inprogress/`
   - What was recently completed → `/roadmap/3_completed/`

3. **Consult Key Documents**: The following documents are particularly important:
   - `/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`: The central guide for mapping processes
   - `/roadmap/HOW_TO_UPDATE_ROADMAP_STAGES.md`: Instructions for maintaining the roadmap
   - Various README files within feature directories

## Working with the Roadmap

### Using Stage Gate Prompts

When instructed to process a feature through a stage gate, follow these steps:

1. Locate the appropriate stage gate prompt file. For example: `/roadmap/1_planning/STAGE_GATE_PROMPT_PLAN.md`
2. Read both the stage gate prompt and the source feature file
3. Execute the instructions in the prompt, creating appropriate folders and files
4. Ensure all required documentation is generated according to templates

### Creating or Updating Backlog Items

When creating new backlog items or updating existing ones:

1. Use the format established in existing backlog items
2. Ensure each item has clear sections for:
   - Overview
   - Problem Statement
   - Key Requirements
   - Success Criteria
   - Any other relevant sections

## Self-Correcting Mechanism

This mechanism applies to any AI assistant working on the project. When a user indicates deviations from the intended development process or expectations, follow this process:

1. **Recognize the deviation**: Acknowledge the gap between expectations and reality

2. **Document the deviation**: Create or update a CLAUDE.md file at the appropriate level:
   - Project level for project-wide deviations
   - Roadmap level for roadmap workflow deviations
   - Stage level for stage-specific process deviations
   - Feature level for feature-specific deviations

3. **Specify the correction**: Include clear instructions on what the correct process should be

4. **Suggest recovery steps**: Outline steps to get back on track

5. **Adapt to the new context**: Adjust future interactions to prevent similar deviations

### Deviation Detection Triggers

Look for these trigger phrases that indicate expectations are not being met:

- "That's not how we do it"
- "That's not the right process"
- "We don't use that approach"
- "You're not following our workflow"
- "That's not our convention"
- "That's not what I expected"
- "This isn't working how I wanted"
- "We need to change how this works"

### Example CLAUDE.md Update Format

When a deviation is detected for a feature in `roadmap/1_planning/feature_x/`, create or update `roadmap/1_planning/feature_x/CLAUDE.md` with content like:

```markdown
# Feature X - CLAUDE.md

## Workflow Deviation Notes

On [DATE], the following deviation was noted:
- [Description of the deviation]
- [Correct approach]

### Recovery Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Future Reference
When working on this feature, always:
- [Guideline 1]
- [Guideline 2]
- [Guideline 3]
```

## Key Technical Documents

- **Iterative Mapping Strategy**: `/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`
- **Composite Identifier Handling**: `/roadmap/technical_notes/core_mapping_logic/composite_identifier_handling.md`
- **Mapping Executor Metadata**: `/biomapper/core/mapping_executor_metadata_readme.md`

## Project Priorities - How to Determine

To determine current project priorities:

1. **Find the most recent status update** in `/roadmap/_status_updates/` by sorting files by date
2. **Review the 'Next Steps' and 'Priorities' sections** in that document
3. **Cross-reference with stage folders**:
   - High-priority items may already have entries in `/roadmap/1_planning/` or `/roadmap/2_inprogress/`
   - New priorities might still be in `/roadmap/0_backlog/` awaiting planning

This dynamic approach ensures you're always working with the most current priorities rather than relying on static lists that may become outdated.

**Note:** The iterative mapping strategy document (`/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`) is consistently a central guiding document for the project and should be referenced when implementing any mapping-related features.