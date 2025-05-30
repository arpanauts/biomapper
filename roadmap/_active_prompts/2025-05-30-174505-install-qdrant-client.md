# Prompt for Claude Code Instance: Verify qdrant-client Installation and Update Import

**Source Prompt:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-174505-install-qdrant-client.md` (revised)

## 1. Task Overview

This task involves verifying that the `qdrant-client` dependency is correctly installed in the Biomapper project environment (as it is already listed in `pyproject.toml`) and then uncommenting its import in the relevant Python file. This is in preparation for potential near-term work on RAG-based mapping strategies.

## 2. Context and References

*   This task was noted as optional in `/home/ubuntu/biomapper/roadmap/_status_updates/_suggested_next_prompt.md` (line 21-23).
*   Project uses Poetry for dependency management: `/home/ubuntu/biomapper/pyproject.toml`. `qdrant-client` is already listed as a dependency.
*   File with the import to uncomment: `/home/ubuntu/biomapper/src/biomapper/mapping_strategies.py`.

## 3. Detailed Steps

1.  **Verify/Ensure Dependency Installation using Poetry:**
    *   Navigate to the project root directory (`/home/ubuntu/biomapper/`).
    *   It's recommended to run: `poetry install --sync`. This command ensures that the virtual environment is synchronized with the `poetry.lock` file, installing any missing dependencies listed in `pyproject.toml` and removing any that are no longer required.
    *   Alternatively, you can verify by attempting to import `qdrant_client` in a Python interpreter within the Poetry environment.

2.  **Uncomment Import Statement:**
    *   Open the file `/home/ubuntu/biomapper/src/biomapper/mapping_strategies.py`.
    *   Locate the commented-out import statement for `qdrant_client` (it should be near the top, e.g., `# from qdrant_client import QdrantClient`).
    *   Uncomment this line.

## 4. Deliverables

Create a single Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-verify-qdrant-client.md` (use UTC timestamp of task completion) in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/`. This file must include:

*   Confirmation that `qdrant-client` is correctly installed/available in the Poetry environment (e.g., relevant output of `poetry install --sync` or confirmation of successful import).
*   Confirmation that the import statement in `/home/ubuntu/biomapper/src/biomapper/mapping_strategies.py` was uncommented.
*   A diff of the changes to `/home/ubuntu/biomapper/src/biomapper/mapping_strategies.py`.
*   Any issues encountered.

## 5. Constraints

*   Ensure all actions are performed within the Poetry-managed environment. All Python package management for this project should be done using Poetry.

