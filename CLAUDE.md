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

## Notebook-Driven Development Workflow

The Biomapper project leverages Jupyter Notebooks for several key aspects of development, including:
- Rapid prototyping of mapping strategies and client functionalities.
- Iterative development of complex data transformation and matching logic.
- Hands-on exploration of datasets and mapping challenges.
- Creation of practical mapping results.
- Generation of tutorial documentation that demonstrates Biomapper's capabilities and workflows.

When working with or creating Jupyter Notebooks, adhere to the following guidelines:

### Guidelines for Notebooks

1.  **Purpose Clarity:**
    *   Clearly define and state the purpose of each notebook at the beginning (e.g., exploratory data analysis, development of a specific mapping client, tutorial for a workflow, generation of a specific mapping dataset).

2.  **Structure and Readability:**
    *   Organize notebooks logically with clear markdown explanations for each step.
    *   Use meaningful variable names and add comments to code cells where necessary.
    *   Break down long processes into smaller, manageable cells.

3.  **Data Handling:**
    *   When loading data, prefer using configurations and paths managed by Biomapper (e.g., referencing `Endpoint` definitions from `metamapper.db` or YAML configs) rather than hardcoding paths directly in the notebook, especially for reusable workflows.
    *   Clearly document data sources and any preprocessing steps.

4.  **Biomapper Library Integration:**
    *   Notebooks should serve as a development and testing ground for `biomapper` core library components (`MappingExecutor`, clients, actions, etc.).
    *   Prioritize using and extending existing library functionalities over implementing standalone solutions within the notebook if the logic is intended to be core to Biomapper.

5.  **Refactoring into Core Library:**
    *   Logic developed and validated in notebooks that proves to be generalizable, reusable, or critical for Biomapper's functionality should be refactored into the main `biomapper` Python package.
    *   This includes creating appropriate classes, functions, modules, and adding comprehensive unit and integration tests.
    *   The notebook can then be updated to *use* the new library components, serving as a demonstration or tutorial.

6.  **Version Control:**
    *   Clear cell outputs before committing notebooks to version control to reduce noise in diffs. (`jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace my_notebook.ipynb`)
    *   Consider using tools like `jupytext` to pair notebooks with plain text versions if merge conflicts become frequent or difficult to resolve.

7.  **Testing:**
    *   Notebooks provide an excellent environment for interactive testing and experimentation.
    *   However, this does not replace the need for formal, automated tests (e.g., `pytest`) for core library components. Logic refactored from notebooks into the library must be accompanied by such tests.

8.  **Reproducibility:**
    *   Ensure notebooks are reproducible by clearly specifying dependencies (which should be managed by `pyproject.toml` via Poetry) and data versions.
    *   Document the expected execution order of cells if it's not strictly linear.

9.  **Separation of Concerns:**
    *   Maintain a clear distinction: notebooks are often *clients* or *drivers* of the Biomapper library. The library itself should contain the robust, well-tested, and reusable core logic.

By following these guidelines, we can effectively use notebooks to accelerate development, produce tangible mapping outcomes, and create valuable tutorial materials, while ensuring the long-term health and maintainability of the core Biomapper library.