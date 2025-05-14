# Biomapper Project Roadmap

This directory houses the planning, tracking, and reference materials for the Biomapper toolkit. We utilize a staged development workflow to manage features from conception to completion.

## Staged Development Workflow

Our roadmap is managed through a series of stage directories, allowing for clear tracking of feature progress. This system is designed to be used collaboratively, including with AI assistants.

**For detailed instructions on how to use this system and update the stages based on project status, please see: [`HOW_TO_UPDATE_ROADMAP_STAGES.md`](./HOW_TO_UPDATE_ROADMAP_STAGES.md).**

### Core Stage Directories:

-   `0_backlog/`: Raw ideas, new feature requests, and items not yet ready for planning.
-   `1_planning/`: Features actively being planned. Contains subfolders for each feature with `README.md`, `spec.md`, and `design.md`.
-   `2_inprogress/`: Features actively being implemented. Contains subfolders for each feature, including `task_list.md` and `implementation_notes.md`.
-   `3_completed/`: Features that have been implemented, tested, and verified. Contains subfolders for each feature with a final `summary.md`.
-   `4_archived/`: Features or ideas that are obsolete, deferred indefinitely, or superseded.

### Supporting Directories:

-   `_reference/`: Contains foundational documents, existing architecture notes, design documents for larger systems (e.g., `api/`, `architecture/`, `enhanced_mappers/`, `ui/` which were moved here), style guides, and logs like `completed_features_log.md`.
-   `_templates/`: Standardized templates for feature documents (`feature_readme_template.md`, `spec_template.md`, etc.) used by the stage gate prompts.
-   `_status_updates/`: Chronological project status updates. These are key inputs for updating the staged roadmap.
-   `technical_notes/`: In-depth technical explorations, investigations, and notes on specific components or challenges.

## Current Status and Upcoming Work

The current development status, ongoing tasks, and planned work can be dynamically understood by reviewing the contents of the stage directories:

-   Review `0_backlog/` for new and unprioritized ideas.
-   Review `1_planning/` for features currently undergoing specification and design.
-   Review `2_inprogress/` for features under active development.
-   Review `3_completed/` for recently finished work.

## Long-term Vision

Biomapper aims to become a comprehensive toolkit for biological data harmonization, supporting seamless translation between different biological ontologies and datasets through a hybrid architecture leveraging:

1.  SPOKE Knowledge Graph (ArangoDB)
2.  Extension Graph for custom ontologies
3.  SQLite Mapping Cache for performance
4.  Resource metadata system for intelligent orchestration
